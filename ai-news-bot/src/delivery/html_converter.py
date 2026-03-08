"""HTML変換モジュール

Markdown コンテンツを HTML に変換し、メール配信用の
レスポンシブ・ダークモード対応テンプレートを適用する。

主な機能:
- Markdown -> HTML 変換（tables, fenced_code 等の拡張対応）
- Jinja2 テンプレートによるメール HTML 生成
- リアクションボタン付きカード型レイアウト（mailto 方式）
"""

import urllib.parse
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# テンプレートディレクトリのパス
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "writer" / "templates"

# リアクション定義
REACTIONS = [
    {"type": "excellent",   "emoji": "⭐", "label": "素晴らしい", "color": "#ffd700", "text_color": "#7c6200"},
    {"type": "good",        "emoji": "👍", "label": "良い",       "color": "#4caf50", "text_color": "#ffffff"},
    {"type": "so_so",       "emoji": "🤔", "label": "微妙",       "color": "#ff9800", "text_color": "#ffffff"},
    {"type": "read_later",  "emoji": "📌", "label": "後で読む",   "color": "#2196f3", "text_color": "#ffffff"},
]


def markdown_to_html(md_content: str) -> str:
    """Markdown テキストを HTML に変換する。

    tables, fenced_code, codehilite, toc, nl2br 等の拡張を有効にして変換を行う。

    Args:
        md_content: Markdown 形式のテキスト。

    Returns:
        変換後の HTML 文字列。
    """
    if not md_content:
        return ""

    extensions = [
        "markdown.extensions.tables",
        "markdown.extensions.fenced_code",
        "markdown.extensions.codehilite",
        "markdown.extensions.toc",
        "markdown.extensions.nl2br",
        "markdown.extensions.sane_lists",
    ]
    extension_configs = {
        "markdown.extensions.codehilite": {
            "css_class": "highlight",
            "guess_lang": False,
        },
    }

    html = markdown.markdown(
        md_content,
        extensions=extensions,
        extension_configs=extension_configs,
        output_format="html",
    )

    logger.debug("Markdown -> HTML 変換完了 (入力: %d文字, 出力: %d文字)", len(md_content), len(html))
    return html


def _get_jinja_env() -> Environment:
    """Jinja2 テンプレート環境を取得する。

    Returns:
        設定済みの Jinja2 Environment インスタンス。

    Raises:
        FileNotFoundError: テンプレートディレクトリが存在しない場合。
    """
    if not _TEMPLATE_DIR.exists():
        raise FileNotFoundError(f"テンプレートディレクトリが見つかりません: {_TEMPLATE_DIR}")

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env


def generate_reaction_url(base_url: str, date: str, story_id: int, reaction_type: str) -> str:
    """リアクション URL を生成する（mailto 方式）。

    ボタンクリックでメールアプリが起動し、評価情報が記載された
    メールが作成される。送信するだけで評価が記録される。

    Args:
        base_url: 未使用（互換性のために残す）。
        date: 記事の日付 (YYYY-MM-DD)。
        story_id: ストーリー ID (1-3)。
        reaction_type: リアクション種別 (excellent, good, so_so, read_later)。

    Returns:
        mailto: URL 文字列。
    """
    recipient = _resolve_feedback_email()

    reaction_info = next((r for r in REACTIONS if r["type"] == reaction_type), None)
    emoji = reaction_info["emoji"] if reaction_info else ""
    label = reaction_info["label"] if reaction_info else reaction_type

    subject = f"[AI-NEWS-REACT] {date} / 記事 {story_id} / {reaction_type}"
    body = (
        f"{emoji} 「{label}」と評価しました\n"
        f"\n"
        f"日付: {date}\n"
        f"記事: 記事 {story_id}\n"
        f"評価: {label}\n"
        f"\n"
        f"※ このメールを送信するだけで評価が記録されます。"
    )

    params = urllib.parse.urlencode(
        {"subject": subject, "body": body},
        quote_via=urllib.parse.quote,
    )
    return f"mailto:{recipient}?{params}"


def _prepare_story_context(
    story: dict[str, Any],
    date: str,
    base_url: str,
) -> dict[str, Any]:
    """ストーリー辞書をテンプレートコンテキスト用に整形する。

    ストーリーの body (Markdown) を HTML に変換し、リアクション URL を生成する。

    Args:
        story: ストーリーデータ辞書。
        date: 記事の日付。
        base_url: フィードバックサーバーのベース URL。

    Returns:
        テンプレートレンダリング用の整形済み辞書。
    """
    story_id = story.get("id", 0)
    body_md = story.get("body", "")
    html_body = markdown_to_html(body_md)

    reactions = []
    for r in REACTIONS:
        reactions.append({
            "url": generate_reaction_url(base_url, date, story_id, r["type"]),
            "emoji": r["emoji"],
            "label": r["label"],
            "color": r["color"],
            "text_color": r["text_color"],
            "type": r["type"],
        })

    return {
        "id": story_id,
        "title": story.get("title", ""),
        "source": story.get("source", ""),
        "url": story.get("url", ""),
        "category": story.get("category", ""),
        "tags": story.get("tags", []),
        "html_body": html_body,
        "reactions": reactions,
    }


def apply_email_template(
    html_body: str,
    date: str,
    stories: list[dict[str, Any]],
    base_url: str | None = None,
    insight: str | None = None,
) -> str:
    """メール用 HTML テンプレートを適用する。

    ストーリーデータとインサイトを Jinja2 テンプレートにレンダリングし、
    レスポンシブ・ダークモード対応のカード型 HTML メールを生成する。

    各ストーリーカードにはリアクションボタン（素晴らしい/良い/微妙/後で読む）を含む。

    Args:
        html_body: テンプレート外で使用する場合の HTML 本文（テンプレート内では stories を使用）。
        date: 配信日付 (YYYY-MM-DD)。
        stories: ストーリーデータのリスト。各要素は以下のキーを含む辞書:
            - id (int): ストーリー ID
            - title (str): タイトル
            - body (str): 本文 (Markdown)
            - source (str): ソース名
            - url (str): 元記事 URL
            - category (str): カテゴリ
            - tags (list[str]): タグリスト
        base_url: フィードバックサーバーのベース URL。
            None の場合は config.yaml から取得を試みる。
        insight: Today's Insight テキスト。None の場合は非表示。

    Returns:
        レンダリング済みの HTML メール文字列。

    Raises:
        FileNotFoundError: テンプレートファイルが見つからない場合。
    """
    # base_url のデフォルト解決
    if base_url is None:
        base_url = _resolve_base_url()

    # Jinja2 環境の取得
    env = _get_jinja_env()
    template = env.get_template("email_template.html")

    # ストーリーコンテキストの準備
    story_contexts = []
    for story in stories:
        ctx = _prepare_story_context(story, date, base_url)
        story_contexts.append(ctx)

    # インサイトの HTML 変換
    insight_html = None
    if insight:
        insight_html = markdown_to_html(insight)

    # テンプレートレンダリング
    rendered = template.render(
        date=date,
        stories=story_contexts,
        insight=insight_html,
        base_url=base_url,
        html_body=html_body,
    )

    logger.info("メール HTML テンプレート適用完了 (日付: %s, ストーリー数: %d)", date, len(stories))
    return rendered


def _resolve_base_url() -> str:
    """config.yaml からフィードバックサーバーの base_url を取得する。

    設定が読み込めない場合はデフォルト値を返す。

    Returns:
        フィードバックサーバーのベース URL（mailto 方式では未使用）。
    """
    try:
        from src.utils.config import load_config
        config = load_config()
        fb = config.get("feedback_server", {})
        return fb.get("base_url", "")
    except Exception:
        return ""


def _resolve_feedback_email() -> str:
    """フィードバック受信用メールアドレスを config.yaml から取得する。

    delivery.gmail.sender の値を使用する。

    Returns:
        フィードバック受信用メールアドレス。
    """
    try:
        from src.utils.config import load_config
        config = load_config()
        delivery = config.get("delivery", {})
        gmail_cfg = delivery.get("gmail", {})
        return gmail_cfg.get("sender", "")
    except Exception:
        logger.warning("config.yaml からメールアドレスを取得できませんでした。")
        return ""
