"""Markdown 生成モジュール

YAML Frontmatter 付きの日次レポート Markdown ファイルを生成する。
Jinja2 テンプレートを使用して本文を生成し、python-frontmatter で
Frontmatter を付加する。

出力形式:
    ---
    date: "YYYY-MM-DD"
    tags: [...]
    stories:
      - id: 1
        title: "..."
        source: "..."
        ...
    ---
    # AI News - YYYY-MM-DD
    ## Story 1: タイトル
    ...
    ## Today's Insight
    ...
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import frontmatter
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.utils.logger import setup_logger

_JST = timezone(timedelta(hours=9))

logger = setup_logger(__name__)

# テンプレートディレクトリ
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _get_jinja_env() -> Environment:
    """Jinja2 環境を取得する。

    Returns:
        テンプレートディレクトリが設定された Jinja2 Environment。
    """
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape([]),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _build_frontmatter_metadata(
    date: str,
    stories: list[dict],
) -> dict[str, Any]:
    """Frontmatter 用のメタデータ辞書を構築する。

    Args:
        date: 日付文字列 (YYYY-MM-DD)。
        stories: ストーリー情報のリスト。各要素は以下のキーを含む:
            - id (int): ストーリーID (1-3)
            - title (str): タイトル
            - source (str): ソース名
            - url (str): 元記事URL
            - category (str): カテゴリ
            - tags (list[str]): タグ配列
            - rating (int | None): 評価スコア
            - reaction (str | None): リアクション種別

    Returns:
        Frontmatter メタデータの辞書。
    """
    # 全ストーリーのタグを集約して重複排除
    all_tags: list[str] = []
    seen_tags: set[str] = set()
    for story in stories:
        for tag in story.get("tags", []):
            if tag not in seen_tags:
                all_tags.append(tag)
                seen_tags.add(tag)

    # ストーリーメタデータの構築
    stories_meta: list[dict[str, Any]] = []
    for story in stories:
        story_meta: dict[str, Any] = {
            "id": story.get("id", 0),
            "title": story.get("title", ""),
            "source": story.get("source", ""),
            "source_url": story.get("url", ""),
            "framework": story.get("framework", ""),
            "tags": story.get("tags", []),
            "reactions": {
                "excellent": 0,
                "good": 0,
                "so_so": 0,
                "read_later": 0,
            },
        }
        stories_meta.append(story_meta)

    return {
        "date": date,
        "generation_timestamp": datetime.now(_JST).isoformat(),
        "tags": all_tags,
        "stories": stories_meta,
        "total_reactions": {
            "excellent": 0,
            "good": 0,
            "so_so": 0,
            "read_later": 0,
        },
    }


def _render_body(date: str, stories: list[dict], insight: str) -> str:
    """Jinja2 テンプレートを使用して Markdown 本文をレンダリングする。

    Args:
        date: 日付文字列 (YYYY-MM-DD)。
        stories: ストーリー情報のリスト。各要素には body キーも含む。
        insight: Today's Insight テキスト。

    Returns:
        レンダリングされた Markdown 本文。
    """
    env = _get_jinja_env()

    try:
        template = env.get_template("daily_template.md")
    except Exception:
        # テンプレートが読み込めない場合はフォールバック
        logger.warning("Jinja2 テンプレートの読み込みに失敗しました。フォールバックを使用します。")
        return _render_body_fallback(date, stories, insight)

    # テンプレートには本文部分のみ渡す（frontmatter は python-frontmatter で処理）
    rendered = template.render(
        date=date,
        stories=stories,
        insight=insight,
        tags=[],  # テンプレートの frontmatter 部分は使わない
    )

    return rendered


def _render_body_fallback(date: str, stories: list[dict], insight: str) -> str:
    """テンプレート無しの Markdown 本文フォールバック生成。

    Args:
        date: 日付文字列 (YYYY-MM-DD)。
        stories: ストーリー情報のリスト。
        insight: Today's Insight テキスト。

    Returns:
        生成された Markdown 本文。
    """
    lines: list[str] = []
    lines.append(f"# AI News - {date}")
    lines.append("")

    for story in stories:
        story_id = story.get("id", 0)
        title = story.get("title", "不明")
        source = story.get("source", "不明")
        url = story.get("url", "")
        body = story.get("body", "")

        lines.append(f"## Story {story_id}: {title}")
        lines.append("")
        lines.append(f"> Source: [{source}]({url})")
        lines.append("")
        lines.append(body)
        lines.append("")

    lines.append("## Today's Insight")
    lines.append("")
    lines.append(insight)
    lines.append("")

    return "\n".join(lines)


def generate_daily_markdown(
    date: str,
    stories: list[dict],
    insight: str,
) -> str:
    """日次レポートの Markdown 文字列を生成する。

    YAML Frontmatter と Jinja2 テンプレートによる本文を結合して、
    完全な Markdown ドキュメントを生成する。

    Args:
        date: 日付文字列 (YYYY-MM-DD)。
        stories: ストーリー情報のリスト。各要素は以下のキーを含む:
            - id (int): ストーリーID (1-3)
            - title (str): タイトル
            - source (str): ソース名
            - url (str): 元記事URL
            - category (str): カテゴリ
            - tags (list[str]): タグ配列
            - rating (int | None): 評価スコア (null or 1-5)
            - reaction (str | None): リアクション種別 (null or type)
            - body (str): ストーリー本文
        insight: Today's Insight テキスト。

    Returns:
        YAML Frontmatter 付きの完全な Markdown 文字列。

    使用例::

        stories = [
            {
                "id": 1,
                "title": "AIが変える未来の働き方",
                "source": "TechCrunch",
                "url": "https://example.com/article1",
                "category": "業務効率化",
                "tags": ["AI", "DX"],
                "rating": None,
                "reaction": None,
                "body": "記事本文...",
            },
        ]
        md = generate_daily_markdown("2026-02-25", stories, "インサイト...")
    """
    logger.info("日次 Markdown を生成中 (日付: %s, 記事数: %d)", date, len(stories))

    # Frontmatter メタデータの構築
    metadata = _build_frontmatter_metadata(date, stories)

    # 本文のレンダリング
    body = _render_body_fallback(date, stories, insight)

    # python-frontmatter でまとめる
    post = frontmatter.Post(body, **metadata)

    # Frontmatter 内で None を null として出力するためのカスタム dumper
    content = frontmatter.dumps(post)

    logger.info("日次 Markdown 生成完了 (%d文字)", len(content))

    return content


def save_markdown(content: str, filepath: str) -> None:
    """Markdown 文字列をファイルに保存する。

    親ディレクトリが存在しない場合は自動的に作成する。

    Args:
        content: 保存する Markdown 文字列。
        filepath: 保存先のファイルパス。

    Raises:
        OSError: ファイル書き込みに失敗した場合。
    """
    output_path = Path(filepath)

    # 親ディレクトリの作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ファイル書き込み
    output_path.write_text(content, encoding="utf-8")

    logger.info("Markdown ファイルを保存しました: %s", filepath)
