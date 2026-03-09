"""News API 収集モジュール

NewsAPI.org および Hacker News Algolia API からニュース記事を取得する。

使用例::

    from src.collector.news_api import fetch_from_newsapi, fetch_from_hackernews

    # NewsAPI から取得
    articles = fetch_from_newsapi(
        query="generative AI OR LLM",
        api_key="your-newsapi-key",
    )

    # Hacker News から取得
    hn_articles = fetch_from_hackernews()
"""

import os
from datetime import datetime, timezone
from typing import Any

import requests

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# --- NewsAPI 設定 ---
_NEWSAPI_BASE_URL = "https://newsapi.org/v2"
_NEWSAPI_EVERYTHING_ENDPOINT = "/everything"

# --- Hacker News Algolia API 設定 ---
_HN_API_BASE_URL = "http://hn.algolia.com/api/v1"
_HN_SEARCH_ENDPOINT = "/search_by_date"

# デフォルトのキーワード
_DEFAULT_NEWSAPI_QUERY = "generative AI OR LLM OR 生成AI"
_DEFAULT_HN_QUERY = "AI OR LLM OR GPT OR Claude"

# 共通 HTTP ヘッダー
_DEFAULT_HEADERS = {
    "User-Agent": "AI-News-Bot/1.0",
    "Accept": "application/json",
}

# デフォルトの取得件数
_DEFAULT_PAGE_SIZE = 20


@with_retry(
    max_attempts=3,
    exceptions=(ConnectionError, TimeoutError, OSError, requests.RequestException),
)
def fetch_from_newsapi(
    query: str | None = None,
    api_key: str | None = None,
    language: str = "en",
    sort_by: str = "publishedAt",
    page_size: int = _DEFAULT_PAGE_SIZE,
    base_url: str = _NEWSAPI_BASE_URL,
) -> list[dict[str, Any]]:
    """NewsAPI.org から記事を取得する。

    Args:
        query: 検索クエリ文字列。None の場合はデフォルトキーワードを使用。
        api_key: NewsAPI の API キー。None の場合は環境変数 NEWS_API_KEY から取得。
        language: 検索対象の言語コード。
        sort_by: ソート順（"publishedAt", "relevancy", "popularity"）。
        page_size: 1回の取得件数。
        base_url: NewsAPI のベース URL。

    Returns:
        記事情報の辞書のリスト。各辞書は以下のキーを持つ:
            - title (str): 記事タイトル
            - url (str): 記事 URL
            - summary (str): 概要
            - published_at (str): 公開日時（ISO 8601）
            - source (str): ソース名
            - category (str): カテゴリ
            - language (str): 言語コード
            - collected_via (str): "newsapi"

    Raises:
        requests.RequestException: API リクエストが失敗した場合。
        ValueError: API キーが設定されていない場合。
    """
    # API キーの解決
    resolved_key = api_key or os.environ.get("NEWS_API_KEY", "")
    if not resolved_key:
        logger.warning("NewsAPI の API キーが設定されていません。スキップします。")
        return []

    resolved_query = query or _DEFAULT_NEWSAPI_QUERY

    logger.info("NewsAPI から記事を取得中: query='%s'", resolved_query)

    url = f"{base_url}{_NEWSAPI_EVERYTHING_ENDPOINT}"
    params = {
        "q": resolved_query,
        "language": language,
        "sortBy": sort_by,
        "pageSize": page_size,
        "apiKey": resolved_key,
    }

    response = requests.get(url, params=params, headers=_DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    data = response.json()

    if data.get("status") != "ok":
        error_msg = data.get("message", "不明なエラー")
        logger.error("NewsAPI エラー: %s", error_msg)
        return []

    raw_articles = data.get("articles", [])
    articles: list[dict[str, Any]] = []

    for raw in raw_articles:
        title = (raw.get("title") or "").strip()
        article_url = (raw.get("url") or "").strip()

        if not title or not article_url:
            continue

        # "[Removed]" などの削除済み記事をスキップ
        if title == "[Removed]":
            continue

        # 公開日時のパース
        published_at = raw.get("publishedAt", "")
        if not published_at:
            published_at = datetime.now(tz=timezone.utc).isoformat()

        # ソース名の取得
        source_info = raw.get("source", {})
        source_name = source_info.get("name", "NewsAPI")

        # 概要の取得
        description = (raw.get("description") or "").strip()
        if len(description) > 1500:
            description = description[:1497] + "..."

        article = {
            "title": title,
            "url": article_url,
            "summary": description,
            "published_at": published_at,
            "source": f"NewsAPI/{source_name}",
            "category": "海外テック",
            "language": language,
            "collected_via": "newsapi",
        }
        articles.append(article)

    logger.info("NewsAPI から %d 件取得しました", len(articles))
    return articles


@with_retry(
    max_attempts=3,
    exceptions=(ConnectionError, TimeoutError, OSError, requests.RequestException),
)
def fetch_from_hackernews(
    query: str | None = None,
    num_results: int = _DEFAULT_PAGE_SIZE,
    tags: str = "story",
    base_url: str = _HN_API_BASE_URL,
) -> list[dict[str, Any]]:
    """Hacker News Algolia API から記事を取得する。

    Args:
        query: 検索クエリ文字列。None の場合はデフォルトキーワードを使用。
        num_results: 取得件数。
        tags: 検索フィルタ（"story", "comment" 等）。
        base_url: Hacker News API のベース URL。

    Returns:
        記事情報の辞書のリスト。各辞書は以下のキーを持つ:
            - title (str): 記事タイトル
            - url (str): 記事 URL
            - summary (str): 概要（Hacker News のポイント数等）
            - published_at (str): 公開日時（ISO 8601）
            - source (str): "Hacker News"
            - category (str): カテゴリ
            - language (str): 言語コード
            - collected_via (str): "hackernews_api"

    Raises:
        requests.RequestException: API リクエストが失敗した場合。
    """
    resolved_query = query or _DEFAULT_HN_QUERY

    logger.info("Hacker News API から記事を取得中: query='%s'", resolved_query)

    url = f"{base_url}{_HN_SEARCH_ENDPOINT}"
    params = {
        "query": resolved_query,
        "tags": tags,
        "hitsPerPage": num_results,
    }

    response = requests.get(url, params=params, headers=_DEFAULT_HEADERS, timeout=30)
    response.raise_for_status()

    data = response.json()
    hits = data.get("hits", [])
    articles: list[dict[str, Any]] = []

    for hit in hits:
        title = (hit.get("title") or "").strip()
        if not title:
            continue

        # URL: story_url がある場合はそちらを使用、無い場合は HN 上の URL
        article_url = (hit.get("url") or "").strip()
        if not article_url:
            # HN 上のディスカッションページ URL をフォールバックとして使用
            object_id = hit.get("objectID", "")
            if object_id:
                article_url = f"https://news.ycombinator.com/item?id={object_id}"
            else:
                continue

        # 公開日時の取得
        created_at = hit.get("created_at", "")
        if not created_at:
            created_at = datetime.now(tz=timezone.utc).isoformat()

        # ポイント数とコメント数を概要として使用
        points = hit.get("points", 0)
        num_comments = hit.get("num_comments", 0)
        summary = f"HNポイント: {points}, コメント数: {num_comments}"

        # story_text がある場合は概要に追加
        story_text = (hit.get("story_text") or "").strip()
        if story_text:
            # HTML タグを簡易除去
            import re

            clean_text = re.sub(r"<[^>]+>", "", story_text).strip()
            if clean_text:
                if len(clean_text) > 1500:
                    clean_text = clean_text[:1497] + "..."
                summary = f"HNポイント: {points}, コメント数: {num_comments}\n\n{clean_text}"

        article = {
            "title": title,
            "url": article_url,
            "summary": summary,
            "published_at": created_at,
            "source": "Hacker News",
            "category": "海外テック",
            "language": "en",
            "collected_via": "hackernews_api",
        }
        articles.append(article)

    logger.info("Hacker News API から %d 件取得しました", len(articles))
    return articles
