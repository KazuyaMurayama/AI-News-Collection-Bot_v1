"""Gmail配信モジュール

Gmail API を使用したメール配信機能を提供する。
OAuth2 認証フロー（初回ブラウザ認証 + リフレッシュトークン自動認証）を実装し、
HTML メールの送信をサポートする。

使用ライブラリ:
- google-auth / google-auth-oauthlib: OAuth2 認証
- google-api-python-client: Gmail API 操作
"""

import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# Gmail API のスコープ
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
    """Gmail API によるメール送信クラス。

    OAuth2 認証フローを管理し、HTML メールの送信機能を提供する。

    認証フロー:
    1. 初回: ブラウザを開いて Google アカウント認証 -> トークンファイル保存
    2. 以降: 保存済みトークンファイルから自動認証（リフレッシュトークンで自動更新）

    使用例::

        sender = GmailSender()
        sender.authenticate()
        sender.send_email(
            subject="[AI News] 2026-02-25",
            html_body="<h1>Today's AI News</h1>...",
            recipients=["user@example.com"],
        )
    """

    def __init__(
        self,
        token_path: str | Path | None = None,
        credentials_path: str | Path | None = None,
        sender_email: str | None = None,
    ):
        """GmailSender を初期化する。

        Args:
            token_path: OAuth2 トークンファイルのパス。
                None の場合は環境変数 GMAIL_TOKEN_PATH または デフォルトパスを使用。
            credentials_path: OAuth2 クライアント認証情報ファイルのパス。
                None の場合は環境変数 GMAIL_CREDENTIALS_PATH またはデフォルトパスを使用。
            sender_email: 送信元メールアドレス。
                None の場合は config.yaml の delivery.gmail.sender を使用。
        """
        self._token_path = Path(
            token_path
            or os.environ.get("GMAIL_TOKEN_PATH", _DEFAULT_TOKEN_PATH)
        )
        self._credentials_path = Path(
            credentials_path
            or os.environ.get("GMAIL_CREDENTIALS_PATH", _DEFAULT_CREDENTIALS_PATH)
        )
        self._sender_email = sender_email or self._resolve_sender_email()
        self._service = None
        self._credentials = None

        logger.info(
            "GmailSender 初期化 (token: %s, credentials: %s, sender: %s)",
            self._token_path,
            self._credentials_path,
            self._sender_email,
        )

    def _resolve_sender_email(self) -> str:
        """config.yaml から送信元メールアドレスを取得する。

        Returns:
            送信元メールアドレス。取得できない場合は "me"。
        """
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
        """config.yaml から送信先メールアドレスリストを取得する。

        Returns:
            送信先メールアドレスのリスト。
        """
        try:
            from src.utils.config import load_config
            config = load_config()
            delivery = config.get("delivery", {})
            gmail_cfg = delivery.get("gmail", {})
            return gmail_cfg.get("recipients", [])
        except Exception:
            logger.warning("config.yaml からの recipients 取得に失敗。空リストを返します。")
            return []

    def authenticate(self) -> None:
        """OAuth2 認証を実行し、Gmail API サービスを構築する。

        認証フロー:
        1. 既存のトークンファイルが存在する場合はそれを読み込む
        2. トークンが期限切れの場合はリフレッシュトークンで自動更新
        3. トークンファイルが存在しない場合はブラウザ認証フローを実行
        4. 新しいトークンをファイルに保存

        Raises:
            GmailAuthenticationError: 認証に失敗した場合。
            FileNotFoundError: クライアント認証情報ファイルが見つからない場合。
        """
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

        # 1. 既存トークンの読み込み
        if self._token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self._token_path), _SCOPES
                )
                logger.info("既存のトークンファイルを読み込みました: %s", self._token_path)
            except Exception as e:
                logger.warning("トークンファイルの読み込みに失敗: %s", e)
                creds = None

        # 2. トークンのリフレッシュまたは新規取得
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("トークンをリフレッシュしました")
            except Exception as e:
                logger.warning("トークンのリフレッシュに失敗。再認証を実行します: %s", e)
                creds = None

        if not creds or not creds.valid:
            # クライアント認証情報ファイルの確認
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

        # 3. トークンの保存
        try:
            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._token_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
            logger.info("トークンを保存しました: %s", self._token_path)
        except Exception as e:
            logger.warning("トークンの保存に失敗しました: %s", e)

        # 4. Gmail API サービスの構築
        try:
            self._service = build("gmail", "v1", credentials=creds)
            self._credentials = creds
            logger.info("Gmail API サービスの構築が完了しました")
        except Exception as e:
            raise GmailAuthenticationError(
                f"Gmail API サービスの構築に失敗しました: {e}"
            )

    def _ensure_authenticated(self) -> None:
        """認証済みであることを確認する。

        Raises:
            GmailSenderError: 認証が完了していない場合。
        """
        if self._service is None:
            raise GmailSenderError(
                "Gmail API が未認証です。先に authenticate() を呼び出してください。"
            )

    def _create_message(
        self,
        subject: str,
        html_body: str,
        recipients: list[str],
    ) -> dict[str, str]:
        """送信用の MIME メッセージを作成する。

        Args:
            subject: メールの件名。
            html_body: HTML 形式のメール本文。
            recipients: 送信先メールアドレスのリスト。

        Returns:
            Gmail API 送信用の Base64 エンコード済みメッセージ辞書。
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self._sender_email
        message["To"] = ", ".join(recipients)

        # プレーンテキスト版（フォールバック用）
        import re
        plain_text = re.sub(r"<[^>]+>", "", html_body)
        plain_text = re.sub(r"\s+", " ", plain_text).strip()
        text_part = MIMEText(plain_text, "plain", "utf-8")
        message.attach(text_part)

        # HTML 版
        html_part = MIMEText(html_body, "html", "utf-8")
        message.attach(html_part)

        # Base64 エンコード
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw}

    @with_retry(
        max_attempts=3,
        exceptions=(ConnectionError, TimeoutError, OSError),
    )
    def send_email(
        self,
        subject: str,
        html_body: str,
        recipients: list[str] | None = None,
    ) -> dict[str, Any]:
        """HTML メールを送信する。

        Args:
            subject: メールの件名。
            html_body: HTML 形式のメール本文。
            recipients: 送信先メールアドレスのリスト。
                None の場合は config.yaml の delivery.gmail.recipients を使用。

        Returns:
            Gmail API のレスポンス辞書。

        Raises:
            GmailSenderError: 送信に失敗した場合。
            ValueError: 送信先が空の場合。
        """
        self._ensure_authenticated()

        # 送信先の解決
        if recipients is None:
            recipients = self._resolve_recipients()

        if not recipients:
            raise ValueError("送信先メールアドレスが指定されていません。")

        # メッセージの作成
        msg = self._create_message(subject, html_body, recipients)

        logger.info(
            "メール送信開始 (件名: %s, 宛先: %s)",
            subject,
            ", ".join(recipients),
        )

        try:
            result = (
                self._service.users()
                .messages()
                .send(userId="me", body=msg)
                .execute()
            )
            logger.info(
                "メール送信完了 (Message ID: %s, 宛先: %s)",
                result.get("id", "unknown"),
                ", ".join(recipients),
            )
            return result

        except Exception as e:
            error_msg = f"メール送信に失敗しました: {e}"
            logger.error(error_msg)
            raise GmailSenderError(error_msg) from e

    def send_daily_digest(
        self,
        date: str,
        html_content: str,
        recipients: list[str] | None = None,
        headline: str = "AI最新ニュース",
    ) -> dict[str, Any]:
        """日次ダイジェストメールを送信する。

        config.yaml の subject_template を使用して件名を生成し、
        HTML コンテンツをメール本文として送信する。

        Args:
            date: 配信日付 (YYYY-MM-DD 形式)。
            html_content: レンダリング済みの HTML メール本文。
            recipients: 送信先メールアドレスのリスト。
                None の場合は config.yaml の設定を使用。
            headline: 件名に含めるヘッドライン。

        Returns:
            Gmail API のレスポンス辞書。
        """
        # 件名の生成
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
        """メールの件名を生成する。

        config.yaml の subject_template を使用する。

        Args:
            date: 配信日付。
            headline: ヘッドライン文字列。

        Returns:
            生成された件名文字列。
        """
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
        return self._service is not None

    @property
    def sender_email(self) -> str:
        """送信元メールアドレスを返す。"""
        return self._sender_email
