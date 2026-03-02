"""Gmail配信モジュール

Gmail API (OAuth2) または SMTP (アプリパスワード) によるメール配信機能を提供する。

認証方式:
- smtp (推奨): Gmail アプリパスワードを使った SMTP 送信。セットアップが簡単。
- oauth2: Google Cloud Project + OAuth2 認証フロー。高度だがセットアップが複雑。

config.yaml の delivery.gmail.auth_method で切り替え可能。
"""

import base64
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# Gmail API のスコープ (OAuth2 方式で使用)
_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# デフォルトのトークン保存パス
_DEFAULT_TOKEN_PATH = "./credentials/gmail_token.json"
_DEFAULT_CREDENTIALS_PATH = "./credentials/credentials.json"


class GmailSenderError(Exception):
    """Gmail 送信エラー"""
    pass


class GmailAuthenticationError(GmailSenderError):
    """Gmail 認証エラー"""
    pass


class GmailSender:
    """Gmail によるメール送信クラス。

    SMTP 方式と OAuth2 方式の両方をサポートする。

    SMTP 方式 (推奨)::

        sender = GmailSender()
        sender.authenticate()   # SMTP 接続テスト
        sender.send_email(
            subject="[AI News] 2026-03-02",
            html_body="<h1>Today's AI News</h1>...",
        )

    OAuth2 方式::

        sender = GmailSender()
        sender.authenticate()   # ブラウザ認証 or トークン再利用
        sender.send_email(...)
    """

    def __init__(
        self,
        token_path: str | Path | None = None,
        credentials_path: str | Path | None = None,
        sender_email: str | None = None,
    ):
        self._token_path = Path(
            token_path
            or os.environ.get("GMAIL_TOKEN_PATH", _DEFAULT_TOKEN_PATH)
        )
        self._credentials_path = Path(
            credentials_path
            or os.environ.get("GMAIL_CREDENTIALS_PATH", _DEFAULT_CREDENTIALS_PATH)
        )
        self._sender_email = sender_email or self._resolve_sender_email()
        self._service = None       # OAuth2 方式で使用
        self._credentials = None   # OAuth2 方式で使用
        self._auth_method = self._resolve_auth_method()
        self._smtp_authenticated = False

        logger.info(
            "GmailSender 初期化 (auth: %s, sender: %s)",
            self._auth_method,
            self._sender_email,
        )

    def _resolve_auth_method(self) -> str:
        """config.yaml から認証方式を取得する。"""
        try:
            from src.utils.config import load_config
            config = load_config()
            delivery = config.get("delivery", {})
            gmail_cfg = delivery.get("gmail", {})
            return gmail_cfg.get("auth_method", "smtp")
        except Exception:
            return "smtp"

    def _resolve_sender_email(self) -> str:
        """config.yaml から送信元メールアドレスを取得する。"""
        try:
            from src.utils.config import load_config
            config = load_config()
            delivery = config.get("delivery", {})
            gmail_cfg = delivery.get("gmail", {})
            return gmail_cfg.get("sender", "me")
        except Exception:
            logger.warning("config.yaml からの sender 取得に失敗。'me' を使用します。")
            return "me"

    def _resolve_recipients(self) -> list[str]:
        """config.yaml から送信先メールアドレスリストを取得する。"""
        try:
            from src.utils.config import load_config
            config = load_config()
            delivery = config.get("delivery", {})
            gmail_cfg = delivery.get("gmail", {})
            return gmail_cfg.get("recipients", [])
        except Exception:
            logger.warning("config.yaml からの recipients 取得に失敗。空リストを返します。")
            return []

    def _resolve_smtp_config(self) -> dict[str, Any]:
        """config.yaml から SMTP 設定を取得する。"""
        try:
            from src.utils.config import load_config
            config = load_config()
            delivery = config.get("delivery", {})
            gmail_cfg = delivery.get("gmail", {})
            return gmail_cfg.get("smtp", {})
        except Exception:
            return {}

    # ─── 認証 ───────────────────────────────────────────────────

    def authenticate(self) -> None:
        """設定された認証方式で認証を行う。"""
        if self._auth_method == "smtp":
            self._authenticate_smtp()
        else:
            self._authenticate_oauth2()

    def _authenticate_smtp(self) -> None:
        """SMTP 認証情報の検証を行う。

        実際の SMTP 接続は send_email 時に行う。
        ここではアプリパスワードが設定されているかを確認する。
        """
        app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
        if not app_password:
            raise GmailAuthenticationError(
                "環境変数 GMAIL_APP_PASSWORD が設定されていません。\n"
                "Gmail アプリパスワードを取得して .env に設定してください:\n"
                "  1. https://myaccount.google.com/security にアクセス\n"
                "  2. 「2段階認証プロセス」を有効化\n"
                "  3. 「アプリ パスワード」で新規作成（アプリ名: AI News Bot）\n"
                "  4. 生成された16文字のパスワードを .env の GMAIL_APP_PASSWORD に設定"
            )
        self._smtp_authenticated = True
        logger.info("SMTP 認証情報を確認しました")

    def _authenticate_oauth2(self) -> None:
        """OAuth2 認証を実行し、Gmail API サービスを構築する。"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as e:
            raise GmailAuthenticationError(
                "Gmail API ライブラリがインストールされていません。"
                " pip install google-auth google-auth-oauthlib google-api-python-client"
                f" を実行してください: {e}"
            )

        creds = None

        if self._token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self._token_path), _SCOPES
                )
                logger.info("既存のトークンファイルを読み込みました: %s", self._token_path)
            except Exception as e:
                logger.warning("トークンファイルの読み込みに失敗: %s", e)
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("トークンをリフレッシュしました")
            except Exception as e:
                logger.warning("トークンのリフレッシュに失敗。再認証を実行します: %s", e)
                creds = None

        if not creds or not creds.valid:
            if not self._credentials_path.exists():
                raise FileNotFoundError(
                    f"OAuth2 クライアント認証情報ファイルが見つかりません: {self._credentials_path}\n"
                    "Google Cloud Console から OAuth 2.0 クライアント ID の認証情報を"
                    "ダウンロードし、上記パスに配置してください。"
                )

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), _SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("ブラウザ認証フローが完了しました")
            except Exception as e:
                raise GmailAuthenticationError(
                    f"OAuth2 認証フローに失敗しました: {e}"
                )

        try:
            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
            logger.info("トークンを保存しました: %s", self._token_path)
        except Exception as e:
            logger.warning("トークンの保存に失敗しました: %s", e)

        try:
            self._service = build("gmail", "v1", credentials=creds)
            self._credentials = creds
            logger.info("Gmail API サービスの構築が完了しました")
        except Exception as e:
            raise GmailAuthenticationError(
                f"Gmail API サービスの構築に失敗しました: {e}"
            )

    # ─── 認証状態チェック ────────────────────────────────────────

    def _ensure_authenticated(self) -> None:
        """認証済みであることを確認する。"""
        if self._auth_method == "smtp":
            if not self._smtp_authenticated:
                raise GmailSenderError(
                    "SMTP 認証が完了していません。先に authenticate() を呼び出してください。"
                )
        else:
            if self._service is None:
                raise GmailSenderError(
                    "Gmail API が未認証です。先に authenticate() を呼び出してください。"
                )

    # ─── メッセージ作成 ──────────────────────────────────────────

    def _build_mime_message(
        self,
        subject: str,
        html_body: str,
        recipients: list[str],
    ) -> MIMEMultipart:
        """MIME メッセージを作成する。"""
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._sender_email
        message["To"] = ", ".join(recipients)

        plain_text = re.sub(r"<[^>]+>", "", html_body)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()
        text_part = MIMEText(plain_text, "plain", "utf-8")
        message.attach(text_part)

        html_part = MIMEText(html_body, "html", "utf-8")
        message.attach(html_part)

        return message

    def _create_message(
        self,
        subject: str,
        html_body: str,
        recipients: list[str],
    ) -> dict[str, str]:
        """Gmail API 用の Base64 エンコード済みメッセージを作成する。"""
        message = self._build_mime_message(subject, html_body, recipients)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw}

    # ─── 送信 ───────────────────────────────────────────────────

    @with_retry(
        max_attempts=3,
        exceptions=(ConnectionError, TimeoutError, OSError, smtplib.SMTPException),
    )
    def send_email(
        self,
        subject: str,
        html_body: str,
        recipients: list[str] | None = None,
    ) -> dict[str, Any]:
        """HTML メールを送信する。

        認証方式に応じて SMTP または Gmail API で送信する。
        """
        self._ensure_authenticated()

        if recipients is None:
            recipients = self._resolve_recipients()
        if not recipients:
            raise ValueError("送信先メールアドレスが指定されていません。")

        logger.info(
            "メール送信開始 (方式: %s, 件名: %s, 宛先: %s)",
            self._auth_method,
            subject,
            ", ".join(recipients),
        )

        if self._auth_method == "smtp":
            return self._send_via_smtp(subject, html_body, recipients)
        else:
            return self._send_via_api(subject, html_body, recipients)

    def _send_via_smtp(
        self,
        subject: str,
        html_body: str,
        recipients: list[str],
    ) -> dict[str, Any]:
        """SMTP 経由でメールを送信する。"""
        smtp_cfg = self._resolve_smtp_config()
        host = smtp_cfg.get("host", "smtp.gmail.com")
        port = smtp_cfg.get("port", 587)
        use_tls = smtp_cfg.get("use_tls", True)
        app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

        message = self._build_mime_message(subject, html_body, recipients)

        try:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                server.login(self._sender_email, app_password)
                server.send_message(message)

            logger.info(
                "SMTP メール送信完了 (宛先: %s)", ", ".join(recipients),
            )
            return {"status": "sent", "method": "smtp", "recipients": recipients}

        except smtplib.SMTPAuthenticationError as e:
            error_msg = (
                f"SMTP 認証に失敗しました: {e}\n"
                "アプリパスワードが正しいか確認してください。"
            )
            logger.error(error_msg)
            raise GmailSenderError(error_msg) from e
        except Exception as e:
            error_msg = f"SMTP メール送信に失敗しました: {e}"
            logger.error(error_msg)
            raise GmailSenderError(error_msg) from e

    def _send_via_api(
        self,
        subject: str,
        html_body: str,
        recipients: list[str],
    ) -> dict[str, Any]:
        """Gmail API 経由でメールを送信する。"""
        msg = self._create_message(subject, html_body, recipients)

        try:
            result = (
                self._service.users()
                .messages()
                .send(userId="me", body=msg)
                .execute()
            )
            logger.info(
                "API メール送信完了 (Message ID: %s, 宛先: %s)",
                result.get("id", "unknown"),
                ", ".join(recipients),
            )
            return result
        except Exception as e:
            error_msg = f"Gmail API メール送信に失敗しました: {e}"
            logger.error(error_msg)
            raise GmailSenderError(error_msg) from e

    # ─── 日次ダイジェスト ────────────────────────────────────────

    def send_daily_digest(
        self,
        date: str,
        html_content: str,
        recipients: list[str] | None = None,
        headline: str = "AI最新ニュース",
    ) -> dict[str, Any]:
        """日次ダイジェストメールを送信する。"""
        subject = self._generate_subject(date, headline)
        logger.info("日次ダイジェスト送信開始 (日付: %s)", date)
        result = self.send_email(
            subject=subject,
            html_body=html_content,
            recipients=recipients,
        )
        logger.info("日次ダイジェスト送信完了 (日付: %s)", date)
        return result

    def _generate_subject(self, date: str, headline: str) -> str:
        """メールの件名を生成する。"""
        try:
            from src.utils.config import load_config
            config = load_config()
            delivery = config.get("delivery", {})
            gmail_cfg = delivery.get("gmail", {})
            template = gmail_cfg.get("subject_template", "[AI News] {date} - {headline} 他")
        except Exception:
            template = "[AI News] {date} - {headline} 他"

        try:
            return template.format(date=date, headline=headline)
        except KeyError:
            return f"[AI News] {date} - {headline} 他"

    @property
    def is_authenticated(self) -> bool:
        """認証済みかどうかを返す。"""
        if self._auth_method == "smtp":
            return self._smtp_authenticated
        return self._service is not None

    @property
    def sender_email(self) -> str:
        """送信元メールアドレスを返す。"""
        return self._sender_email
