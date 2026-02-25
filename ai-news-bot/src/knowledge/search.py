"""ナレッジベース検索モジュール

python-frontmatter と glob を使用して、
ナレッジベースの日次 Markdown ファイルに対する
タグ検索・全文検索・評価フィルタリング機能を提供する。
"""

import re
from glob import glob
from pathlib import Path
from typing import Any

import frontmatter

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _resolve_daily_dir() -> Path:
    """config.yaml からナレッジベースの daily ディレクトリパスを解決する。

    config.yaml が読み込めない場合はデフォルトパスを使用する。

    Returns:
        daily ディレクトリの Path オブジェクト。
    """
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        daily_dir = config.get("knowledge_base.daily_dir", "./knowledge_base/daily")
    except Exception:
        daily_dir = "./knowledge_base/daily"
    return Path(daily_dir)


def _load_articles_from_file(md_path: Path) -> list[dict[str, Any]]:
    """Markdown ファイルからストーリーメタデータを読み込む。

    Frontmatter の stories 配列を展開し、各ストーリーに
    ファイル由来のメタデータ（date, file_path, body の先頭など）を付与する。

    Args:
        md_path: Markdown ファイルのパス。

    Returns:
        ストーリーメタデータの辞書リスト。
    """
    articles: list[dict[str, Any]] = []
    try:
        post = frontmatter.load(str(md_path))
        metadata = post.metadata
        body = post.content

        # ファイル名から日付を抽出 (YYYY-MM-DD_ai_news.md)
        file_date = md_path.stem.split("_")[0] if "_" in md_path.stem else ""

        stories: list[dict[str, Any]] = metadata.get("stories", [])
        file_tags: list[str] = metadata.get("tags", [])

        for story in stories:
            article: dict[str, Any] = {
                "date": metadata.get("date", file_date),
                "file_path": str(md_path),
                **story,
            }
            # ファイルレベルのタグをストーリーレベルにマージ
            story_tags = story.get("tags", [])
            if isinstance(story_tags, list) and isinstance(file_tags, list):
                merged_tags = list(dict.fromkeys(story_tags + file_tags))
                article["tags"] = merged_tags

            articles.append(article)

    except Exception as e:
        logger.warning(
            "Markdown ファイルの読み込みに失敗しました: %s (%s)",
            md_path,
            str(e),
        )

    return articles


def get_all_articles(daily_dir: Path | str | None = None) -> list[dict[str, Any]]:
    """ナレッジベース内の全記事メタデータを取得する。

    knowledge_base/daily/ 配下の全 *_ai_news.md ファイルを走査し、
    Frontmatter からストーリーメタデータを抽出する。

    Args:
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        全ストーリーメタデータの辞書リスト。日付の降順でソートされる。
    """
    if daily_dir is not None:
        daily_dir = Path(daily_dir)
    else:
        daily_dir = _resolve_daily_dir()

    if not daily_dir.exists():
        logger.warning("daily ディレクトリが存在しません: %s", daily_dir)
        return []

    pattern = str(daily_dir / "*_ai_news.md")
    md_files = sorted(glob(pattern), reverse=True)

    all_articles: list[dict[str, Any]] = []
    for md_file in md_files:
        articles = _load_articles_from_file(Path(md_file))
        all_articles.extend(articles)

    logger.info(
        "全記事取得完了: %d ファイル, %d 記事",
        len(md_files),
        len(all_articles),
    )
    return all_articles


def search_by_tag(
    tag: str,
    daily_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """タグに一致する記事を検索する。

    各ストーリーの tags 配列に指定タグが含まれる記事を返す。
    部分一致ではなく完全一致で検索する。

    Args:
        tag: 検索するタグ文字列。
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        マッチした記事メタデータの辞書リスト。
    """
    all_articles = get_all_articles(daily_dir)

    results = [
        article for article in all_articles
        if tag in article.get("tags", [])
    ]

    logger.info(
        "タグ検索完了: tag='%s', ヒット数=%d",
        tag,
        len(results),
    )
    return results


def search_fulltext(
    query: str,
    daily_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """全文検索で記事を検索する。

    Markdown ファイルの本文とストーリーの title / source / category を
    正規表現で検索する。大文字小文字を区別しない。

    Args:
        query: 検索クエリ文字列（正規表現対応）。
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        マッチした記事メタデータの辞書リスト。
    """
    if daily_dir is not None:
        daily_dir = Path(daily_dir)
    else:
        daily_dir = _resolve_daily_dir()

    if not daily_dir.exists():
        logger.warning("daily ディレクトリが存在しません: %s", daily_dir)
        return []

    try:
        pattern = re.compile(query, re.IGNORECASE)
    except re.error as e:
        logger.error("不正な正規表現です: '%s' (%s)", query, str(e))
        return []

    pattern_str = str(daily_dir / "*_ai_news.md")
    md_files = sorted(glob(pattern_str), reverse=True)

    results: list[dict[str, Any]] = []

    for md_file in md_files:
        try:
            md_path = Path(md_file)
            post = frontmatter.load(str(md_path))
            body = post.content
            metadata = post.metadata
            file_date = md_path.stem.split("_")[0] if "_" in md_path.stem else ""
            file_tags: list[str] = metadata.get("tags", [])

            stories: list[dict[str, Any]] = metadata.get("stories", [])

            for story in stories:
                # メタデータフィールドを検索対象に含める
                searchable_fields = [
                    str(story.get("title", "")),
                    str(story.get("source", "")),
                    str(story.get("category", "")),
                    str(story.get("url", "")),
                    body,
                ]
                combined_text = " ".join(searchable_fields)

                if pattern.search(combined_text):
                    article: dict[str, Any] = {
                        "date": metadata.get("date", file_date),
                        "file_path": str(md_path),
                        **story,
                    }
                    # タグマージ
                    story_tags = story.get("tags", [])
                    if isinstance(story_tags, list) and isinstance(file_tags, list):
                        merged_tags = list(dict.fromkeys(story_tags + file_tags))
                        article["tags"] = merged_tags

                    results.append(article)

        except Exception as e:
            logger.warning(
                "全文検索中にファイル読み込みエラー: %s (%s)",
                md_file,
                str(e),
            )

    logger.info(
        "全文検索完了: query='%s', ヒット数=%d",
        query,
        len(results),
    )
    return results


def filter_by_rating(
    min_rating: int = 4,
    daily_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """指定した最低 rating 以上の記事をフィルタリングする。

    rating フィールドが min_rating 以上のストーリーのみを返す。
    rating が未設定（None）の記事は除外される。

    Args:
        min_rating: 最低 rating (デフォルト: 4)。
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        フィルタリング後の記事メタデータの辞書リスト。rating の降順でソート。
    """
    all_articles = get_all_articles(daily_dir)

    results = [
        article for article in all_articles
        if isinstance(article.get("rating"), (int, float))
        and article["rating"] >= min_rating
    ]

    # rating の降順でソート
    results.sort(key=lambda a: a.get("rating", 0), reverse=True)

    logger.info(
        "高評価フィルタリング完了: min_rating=%d, ヒット数=%d",
        min_rating,
        len(results),
    )
    return results
