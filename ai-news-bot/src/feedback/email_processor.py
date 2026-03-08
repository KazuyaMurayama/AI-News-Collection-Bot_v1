"""リアクション評価メール処理モジュール

Gmail IMAP 経由で受信メールをスキャンし、
[AI-NEWS-REACT] 形式の評価メールを検出してナレッジベースに反映する。

フロー:
    1. IMAP で Gmail に接続
    2. 件名に [AI-NEWS-REACT] を含む未読メールを検索
    3. 件名をパースして date / story_id / reaction_type を抽出
    4. updater.update_reaction() で Markdown Frontmatter を更新
    5. 処理済みメールを既読にマーク
"""

import email
import email.header
import imaplib
import os
import re

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# リアクションメールの件名パターン
# 例: [AI-NEWS-REACT] 2026-03-04 / 記事 1 / excellent
# 後方互換: Story も受け付ける
_SUBJECT_PATTERN = re.compile(
    r"\[AI-NEWS-REACT\]\s+(\d{4}-\d{2}-\d{2})\s*/\s*(?:Story|記事)\s+(\d+)\s*/\s*(\w+)"
)


def _decode_subject(raw_subject: str | None) -> str:
    """メールの件名をデコードする。

    Args:
        raw_subject: 生の件名文字列（MIME エンコード含む可能性あり）。

    Returns:
        デコード済み件名文字列。
    """
    if not raw_subject:
        return ""

    decoded_parts = email.header.decode_header(raw_subject)
    parts = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(part)
    return "".join(parts)


def _resolve_imap_credentials() -> tuple[str, str]:
    """IMAP 接続用の認証情報を取得する。

    config.yaml の delivery.gmail.sender と環境変数 GMAIL_APP_PASSWORD を使用。

    Returns:
        (メールアドレス, アプリパスワード) のタプル。

    Raises:
        ValueError: 認証情報が不足している場合。
    """
    try:
        from src.utils.config import load_config
        config = load_config()
        delivery = config.get("delivery", {})
        gmail_cfg = delivery.get("gmail", {})
        email_addr = gmail_cfg.get("sender", "")
    except Exception:
        email_addr = ""

    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not email_addr:
        raise ValueError(
            "Gmail アドレスが config.yaml の delivery.gmail.sender に設定されていません。"
        )
    if not app_password:
        raise ValueError(
            "環境変数 GMAIL_APP_PASSWORD が設定されていません。"
        )

    return email_addr, app_password


def process_reaction_emails() -> int:
    """受信メールからリアクション評価を処理する。

    Gmail IMAP に接続し、[AI-NEWS-REACT] 件名の未読メールを検出。
    評価情報を抽出してナレッジベースの Markdown ファイルに反映し、
    処理済みメールを既読にマークする。

    Returns:
        処理したリアクション数。
    """
    try:
        email_addr, app_password = _resolve_imap_credentials()
    except ValueError as e:
        logger.warning("リアクションメール処理をスキップ: %s", e)
        return 0

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_addr, app_password)
        mail.select("INBOX")
    except Exception as e:
        logger.error("IMAP 接続エラー: %s", e)
        return 0

    try:
        # [AI-NEWS-REACT] を含む未読メールを検索
        status, data = mail.search(None, '(SUBJECT "[AI-NEWS-REACT]" UNSEEN)')
        if status != "OK" or not data[0]:
            logger.info("未処理のリアクションメールはありません。")
            return 0

        from src.feedback.updater import update_reaction

        processed = 0
        message_ids = data[0].split()
        logger.info("リアクションメール %d 件を検出", len(message_ids))

        for msg_id in message_ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode_subject(msg["Subject"])

                match = _SUBJECT_PATTERN.search(subject)
                if not match:
                    logger.debug("件名パターン不一致: %s", subject)
                    continue

                date_str = match.group(1)
                story_id = int(match.group(2))
                reaction_type = match.group(3)

                try:
                    success = update_reaction(date_str, story_id, reaction_type)
                    if success:
                        processed += 1
                        # 処理済みとして既読マーク
                        mail.store(msg_id, "+FLAGS", "\\Seen")
                        logger.info(
                            "リアクション記録: %s / Story %d / %s",
                            date_str, story_id, reaction_type,
                        )
                    else:
                        logger.warning(
                            "リアクション更新失敗: %s / Story %d / %s",
                            date_str, story_id, reaction_type,
                        )
                except FileNotFoundError:
                    logger.warning(
                        "対象記事が見つかりません: %s / Story %d",
                        date_str, story_id,
                    )
                    # ファイルが無い場合も既読にする（再処理しても無駄なため）
                    mail.store(msg_id, "+FLAGS", "\\Seen")
                except ValueError as e:
                    logger.warning("バリデーションエラー: %s", e)
                    mail.store(msg_id, "+FLAGS", "\\Seen")

            except Exception as e:
                logger.warning("メール処理エラー (msg_id=%s): %s", msg_id, e)

        logger.info("リアクションメール処理完了: %d / %d 件", processed, len(message_ids))
        return processed

    finally:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass
