"""LINE配信モジュール（オプション）

LINE Notify API を使用したメッセージ配信機能を提供する。
1000文字制限に対応し、長いメッセージは自動的に分割して送信する。

使用ライブラリ:
- requests: HTTP 通信

環境変数:
- LINE_NOTIFY_TOKEN: LINE Notify のアクセストークン
"""

import os
from typing import Any

import requests

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# LINE Notify API エンドポイント
_LINE_NOTIFY_API_URL = "https://notify-api.line.me/api/notify"

# LINE Notify のメッセージ上限（文字数）
_LINE_MESSAGE_LIMIT = 1000

# メッセージ分割時の省略表記
_TRUNCATION_SUFFIX = "\n\n...（続きはメールをご確認ください）"


@with_retry(
    max_attempts=3,
    exceptions=(ConnectionError, TimeoutError, OSError, requests.RequestException),
)
def send_line_notification(message: str, token: str | None = None) -> bool:
    """LINE Notify でメッセージを送信する。

    1000文字を超えるメッセージは自動的に切り詰められる。

    Args:
        message: 送信するメッセージ。
        token: LINE Notify のアクセストークン。
            None の場合は環境変数 LINE_NOTIFY_TOKEN を使用。

    Returns:
        送信成功の場合 True、失敗の場合 False。

    Raises:
        ValueError: トークンが指定されていない場合。
    """
    # トークンの解決
    if token is None:
        token = os.environ.get("LINE_NOTIFY_TOKEN")

    if not token:
        raise ValueError(
            "LINE Notify トークンが指定されていません。"
            " 引数で指定するか、環境変数 LINE_NOTIFY_TOKEN を設定してください。"
        )

    if not message or not message.strip():
        logger.warning("空のメッセージが渡されました。送信をスキップします。")
        return False

    # メッセージの長さ制限対応
    if len(message) > _LINE_MESSAGE_LIMIT:
        truncated_length = _LINE_MESSAGE_LIMIT - len(_TRUNCATION_SUFFIX)
        message = message[:truncated_length] + _TRUNCATION_SUFFIX
        logger.info("メッセージを %d 文字に切り詰めました", _LINE_MESSAGE_LIMIT)

    headers = {
        "Authorization": f"Bearer {token}",
    }
    data = {
        "message": message,
    }

    logger.info("LINE Notify 送信開始 (メッセージ長: %d文字)", len(message))

    try:
        response = requests.post(
            _LINE_NOTIFY_API_URL,
            headers=headers,
            data=data,
            timeout=30,
        )

        if response.status_code == 200:
            logger.info("LINE Notify 送信成功")
            return True
        else:
            logger.error(
                "LINE Notify 送信失敗 (status: %d, body: %s)",
                response.status_code,
                response.text,
            )
            return False

    except requests.RequestException as e:
        logger.error("LINE Notify 送信エラー: %s", e)
        raise


def format_for_line(stories: list[dict[str, Any]]) -> str:
    """ストーリーリストを LINE 向けテキストフォーマットに変換する。

    1000文字制限に収まるように最適化されたテキストを生成する。
    各ストーリーはタイトル、概要、元記事リンクを含む。

    Args:
        stories: ストーリーデータのリスト。各要素は以下のキーを含む辞書:
            - id (int): ストーリー ID
            - title (str): タイトル
            - body (str): 本文
            - source (str): ソース名
            - url (str): 元記事 URL
            - category (str, optional): カテゴリ

    Returns:
        LINE 向けにフォーマットされたテキスト文字列。
        1000文字以内に収まるようにストーリー数を動的に調整する。
    """
    if not stories:
        return "\n[AIニュース] 本日のAIニュースはありません。"

    lines: list[str] = []
    lines.append("\n\U0001f916 AI ニュース デイリーダイジェスト")
    lines.append("=" * 24)

    for story in stories:
        story_id = story.get("id", 0)
        title = story.get("title", "無題")
        source = story.get("source", "")
        url = story.get("url", "")
        body = story.get("body", "")
        category = story.get("category", "")

        # ストーリーブロックの構築
        story_lines: list[str] = []
        story_lines.append("")

        # タイトル行
        header = f"\u25b6 [{story_id}] {title}"
        story_lines.append(header)

        # ソース / カテゴリ
        meta_parts = []
        if source:
            meta_parts.append(source)
        if category:
            meta_parts.append(category)
        if meta_parts:
            story_lines.append(f"  ({' | '.join(meta_parts)})")

        # 本文の要約（最初の100文字）
        if body:
            summary = _extract_summary(body, max_length=100)
            story_lines.append(f"  {summary}")

        # 元記事リンク
        if url:
            story_lines.append(f"  {url}")

        # ストーリーブロックを追加した場合の合計長チェック
        story_block = "\n".join(story_lines)
        current_text = "\n".join(lines)
        projected_length = len(current_text) + len(story_block) + len(_TRUNCATION_SUFFIX)

        if projected_length > _LINE_MESSAGE_LIMIT:
            # これ以上追加すると制限を超えるため打ち切り
            remaining = len(stories) - (story_id - 1) if story_id > 0 else 0
            if remaining > 0:
                lines.append(f"\n...他 {remaining} 件（詳細はメールで）")
            break

        lines.extend(story_lines)

    return "\n".join(lines)


def _extract_summary(text: str, max_length: int = 100) -> str:
    """テキストから要約を抽出する。

    Markdown の記法を除去し、指定文字数に切り詰める。

    Args:
        text: 入力テキスト。
        max_length: 最大文字数。

    Returns:
        切り詰められた要約テキスト。
    """
    import re

    # Markdown 記法の除去
    summary = text
    # 見出し
    summary = re.sub(r"^#{1,6}\s+", "", summary, flags=re.MULTILINE)
    # 強調
    summary = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", summary)
    summary = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", summary)
    # リンク
    summary = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", summary)
    # 画像
    summary = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", summary)
    # コードブロック
    summary = re.sub(r"```[\s\S]*?```", "", summary)
    summary = re.sub(r"`([^`]+)`", r"\1", summary)
    # リスト記号
    summary = re.sub(r"^[\s]*[-*+]\s+", "", summary, flags=re.MULTILINE)
    summary = re.sub(r"^[\s]*\d+\.\s+", "", summary, flags=re.MULTILINE)
    # 改行の正規化
    summary = re.sub(r"\n+", " ", summary)
    # 余分な空白
    summary = re.sub(r"\s+", " ", summary).strip()

    if len(summary) > max_length:
        summary = summary[: max_length - 1] + "\u2026"

    return summary
