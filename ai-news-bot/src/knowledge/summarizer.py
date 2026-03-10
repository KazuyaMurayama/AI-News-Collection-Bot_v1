"""月次サマリー生成モジュール

ナレッジベースの月次集計と Claude API によるインサイト生成を行い、
月次サマリー Markdown ファイルを出力する。

出力先: knowledge_base/monthly/YYYY-MM_summary.md
"""

import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.knowledge.search import get_all_articles
from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)


def _get_claude_config() -> dict[str, Any]:
    """config.yaml から Claude API 設定を取得する。"""
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        return {
            "model": config.get("claude.model", "claude-sonnet-4-20250514"),
            "max_tokens": config.get("claude.max_tokens", 4096),
            "temperature": config.get("claude.temperature", 0.7),
        }
    except Exception:
        return {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }


def _resolve_monthly_dir() -> Path:
    """config.yaml から monthly ディレクトリパスを解決する。"""
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        monthly_dir = config.get("knowledge_base.monthly_dir", "./knowledge_base/monthly")
    except Exception:
        monthly_dir = "./knowledge_base/monthly"
    return Path(monthly_dir)


def _filter_articles_by_month(
    articles: list[dict[str, Any]],
    year: int,
    month: int,
) -> list[dict[str, Any]]:
    """記事を年月でフィルタリングする。

    Args:
        articles: 全記事メタデータのリスト。
        year: 対象年。
        month: 対象月 (1-12)。

    Returns:
        指定月に該当する記事のリスト。
    """
    target_prefix = f"{year:04d}-{month:02d}"
    filtered: list[dict[str, Any]] = []

    for article in articles:
        article_date = str(article.get("date", ""))
        if article_date.startswith(target_prefix):
            filtered.append(article)

    return filtered


def _compute_tag_stats(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """記事群からタグ集計を行う。

    Args:
        articles: 記事メタデータのリスト。

    Returns:
        タグと出現回数の辞書リスト（出現回数の降順）。
    """
    tag_counter: Counter[str] = Counter()

    for article in articles:
        tags = article.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    tag_counter[tag] += 1

    return [
        {"tag": tag, "count": count}
        for tag, count in tag_counter.most_common()
    ]


def _get_top_rated(
    articles: list[dict[str, Any]],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """高評価 Top N 記事を取得する。

    Args:
        articles: 記事メタデータのリスト。
        top_n: 取得する上位件数 (デフォルト: 5)。

    Returns:
        rating の降順でソートされた上位 N 件の記事リスト。
    """
    rated_articles = [
        a for a in articles
        if isinstance(a.get("rating"), (int, float)) and a["rating"] > 0
    ]
    rated_articles.sort(key=lambda a: a.get("rating", 0), reverse=True)
    return rated_articles[:top_n]


def _compute_category_trends(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """カテゴリ別のトレンド分析を行う。

    カテゴリごとの記事数、平均 rating、主要タグを集計する。

    Args:
        articles: 記事メタデータのリスト。

    Returns:
        カテゴリ別統計の辞書。
    """
    categories: dict[str, dict[str, Any]] = {}

    for article in articles:
        category = article.get("category", "未分類")
        if category not in categories:
            categories[category] = {
                "count": 0,
                "ratings": [],
                "tags": Counter(),
            }

        cat_data = categories[category]
        cat_data["count"] += 1

        rating = article.get("rating")
        if isinstance(rating, (int, float)) and rating > 0:
            cat_data["ratings"].append(rating)

        tags = article.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    cat_data["tags"][tag] += 1

    # 集計結果を整形
    result: dict[str, Any] = {}
    for category, data in categories.items():
        ratings = data["ratings"]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        top_tags = [tag for tag, _ in data["tags"].most_common(5)]

        result[category] = {
            "article_count": data["count"],
            "average_rating": avg_rating,
            "top_tags": top_tags,
        }

    return result


@with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError, OSError))
def _generate_insight_with_claude(
    year: int,
    month: int,
    tag_stats: list[dict[str, Any]],
    top_rated: list[dict[str, Any]],
    category_trends: dict[str, Any],
    total_articles: int,
) -> str:
    """Claude API で月次インサイトを生成する。

    Args:
        year: 対象年。
        month: 対象月。
        tag_stats: タグ集計結果。
        top_rated: 高評価 Top 記事。
        category_trends: カテゴリ別トレンド。
        total_articles: 記事総数。

    Returns:
        生成されたインサイトテキスト。

    Raises:
        ConnectionError: API 呼び出しに失敗した場合。
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ConnectionError("ANTHROPIC_API_KEY が設定されていません")

    claude_config = _get_claude_config()

    # プロンプトの構築
    top_tags_summary = ", ".join(
        f"{t['tag']}({t['count']}件)" for t in tag_stats[:10]
    )
    top_rated_summary = "\n".join(
        f"- {a.get('title', '不明')} (rating: {a.get('rating', '-')}, カテゴリ: {a.get('category', '不明')})"
        for a in top_rated
    )
    category_summary = "\n".join(
        f"- {cat}: {data['article_count']}件, 平均rating: {data['average_rating']}"
        for cat, data in category_trends.items()
    )

    prompt = f"""以下は{year}年{month}月のAIニュースの月次統計データです。
このデータに基づいて、月次インサイト（トレンド分析・示唆）を500-800文字の日本語で生成してください。

## 基本統計
- 記事総数: {total_articles}件
- 主要タグ: {top_tags_summary}

## 高評価記事 Top5
{top_rated_summary if top_rated_summary else "- (評価データなし)"}

## カテゴリ別トレンド
{category_summary if category_summary else "- (カテゴリデータなし)"}

## 出力要件
1. 今月のAI分野の全体的なトレンドを簡潔に分析
2. 特に注目すべき動向や技術領域を指摘
3. ビジネスパーソン向けに、来月以降の注目ポイントを提言
4. 客観的なデータに基づく洞察を重視"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=claude_config["model"],
        max_tokens=claude_config["max_tokens"],
        temperature=claude_config["temperature"],
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    if message.content and len(message.content) > 0:
        return message.content[0].text
    return ""


def _build_summary_markdown(
    year: int,
    month: int,
    total_articles: int,
    tag_stats: list[dict[str, Any]],
    top_rated: list[dict[str, Any]],
    category_trends: dict[str, Any],
    insight: str,
) -> str:
    """月次サマリーの Markdown 文字列を構築する。

    Args:
        year: 対象年。
        month: 対象月。
        total_articles: 記事総数。
        tag_stats: タグ集計結果。
        top_rated: 高評価 Top 記事。
        category_trends: カテゴリ別トレンド。
        insight: Claude API で生成したインサイト。

    Returns:
        Markdown 文字列。
    """
    month_str = f"{year:04d}-{month:02d}"

    lines: list[str] = [
        f"# AIニュース 月次サマリー - {month_str}",
        "",
        f"> 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## 基本統計",
        "",
        f"- **記事総数**: {total_articles}件",
        "",
    ]

    # タグ集計
    lines.extend([
        "## タグ集計",
        "",
        "| タグ | 記事数 |",
        "|------|--------|",
    ])
    for tag_info in tag_stats[:15]:
        lines.append(f"| {tag_info['tag']} | {tag_info['count']} |")
    lines.append("")

    # 高評価 Top5
    lines.extend([
        "## 高評価記事 Top5",
        "",
    ])
    if top_rated:
        for i, article in enumerate(top_rated, 1):
            title = article.get("title", "不明")
            rating = article.get("rating", "-")
            date = article.get("date", "不明")
            url = article.get("url", "")
            category = article.get("category", "不明")
            source = article.get("source", "不明")

            lines.append(f"### {i}. {title}")
            lines.append(f"- **日付**: {date}")
            lines.append(f"- **ソース**: {source}")
            lines.append(f"- **カテゴリ**: {category}")
            lines.append(f"- **評価**: {'*' * int(rating)} ({rating}/5)")
            if url:
                lines.append(f"- **URL**: [{url}]({url})")
            lines.append("")
    else:
        lines.append("_(評価データがまだありません)_")
        lines.append("")

    # カテゴリ別トレンド
    lines.extend([
        "## カテゴリ別トレンド",
        "",
        "| カテゴリ | 記事数 | 平均評価 | 主要タグ |",
        "|----------|--------|----------|----------|",
    ])
    for cat, data in sorted(
        category_trends.items(),
        key=lambda x: x[1]["article_count"],
        reverse=True,
    ):
        top_tags = ", ".join(data["top_tags"][:3]) if data["top_tags"] else "-"
        avg_rating = data["average_rating"] if data["average_rating"] > 0 else "-"
        lines.append(
            f"| {cat} | {data['article_count']} | {avg_rating} | {top_tags} |"
        )
    lines.append("")

    # 月次インサイト
    lines.extend([
        "## 月次インサイト",
        "",
        insight if insight else "_(インサイトの生成に失敗しました)_",
        "",
        "---",
        "",
        f"_このサマリーは {month_str} の記事データから自動生成されました。_",
    ])

    return "\n".join(lines)


def generate_monthly_summary(
    year: int,
    month: int,
    daily_dir: Path | str | None = None,
) -> str:
    """月次サマリーを生成する。

    指定年月の全記事を集計し、Claude API でインサイトを生成して
    Markdown 形式のサマリーを返す。

    Args:
        year: 対象年。
        month: 対象月 (1-12)。
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        月次サマリーの Markdown 文字列。

    使用例::

        summary = generate_monthly_summary(2026, 2)
        save_monthly_summary(summary, "knowledge_base/monthly/2026-02_summary.md")
    """
    logger.info("月次サマリー生成開始: %04d-%02d", year, month)

    # 全記事の取得とフィルタリング
    all_articles = get_all_articles(daily_dir)
    monthly_articles = _filter_articles_by_month(all_articles, year, month)

    total_articles = len(monthly_articles)
    logger.info("対象記事数: %d", total_articles)

    if total_articles == 0:
        logger.warning(
            "対象月 (%04d-%02d) の記事が見つかりませんでした",
            year,
            month,
        )
        return _build_summary_markdown(
            year=year,
            month=month,
            total_articles=0,
            tag_stats=[],
            top_rated=[],
            category_trends={},
            insight="対象月の記事がないため、インサイトを生成できませんでした。",
        )

    # 各種集計
    tag_stats = _compute_tag_stats(monthly_articles)
    top_rated = _get_top_rated(monthly_articles, top_n=5)
    category_trends = _compute_category_trends(monthly_articles)

    # Claude API でインサイト生成
    insight = ""
    try:
        insight = _generate_insight_with_claude(
            year=year,
            month=month,
            tag_stats=tag_stats,
            top_rated=top_rated,
            category_trends=category_trends,
            total_articles=total_articles,
        )
    except Exception as e:
        logger.error(
            "月次インサイトの生成に失敗しました: %s",
            str(e),
            exc_info=True,
        )
        insight = f"_(インサイトの生成に失敗しました: {str(e)})_"

    # Markdown 構築
    summary = _build_summary_markdown(
        year=year,
        month=month,
        total_articles=total_articles,
        tag_stats=tag_stats,
        top_rated=top_rated,
        category_trends=category_trends,
        insight=insight,
    )

    logger.info("月次サマリー生成完了: %04d-%02d", year, month)
    return summary


def save_monthly_summary(
    content: str,
    filepath: str | Path | None = None,
    year: int | None = None,
    month: int | None = None,
) -> None:
    """月次サマリーをファイルに保存する。

    Args:
        content: 月次サマリーの Markdown 文字列。
        filepath: 保存先ファイルパス。None の場合は year/month から自動生成。
        year: 対象年（filepath が None の場合に使用）。
        month: 対象月（filepath が None の場合に使用）。

    Raises:
        ValueError: filepath も year/month も指定されていない場合。
    """
    if filepath is None:
        if year is None or month is None:
            raise ValueError(
                "filepath が None の場合は year と month を指定してください"
            )
        monthly_dir = _resolve_monthly_dir()
        monthly_dir.mkdir(parents=True, exist_ok=True)
        filepath = monthly_dir / f"{year:04d}-{month:02d}_summary.md"
    else:
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

    filepath.write_text(content, encoding="utf-8")
    logger.info("月次サマリーを保存しました: %s", filepath)
