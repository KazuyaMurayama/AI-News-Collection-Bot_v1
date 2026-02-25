"""Web スクレイピングモジュール

requests + BeautifulSoup を使用して Web サイトからニュース記事を取得する。
robots.txt を遵守し、サーバー負荷軽減のためリクエスト間隔を設ける。

使用例::

    from src.collector.web_scraper import scrape_articles

    sources = [
        {
            "name": "日経クロステック",
            "url": "https://xtech.nikkei.com/atcl/nxt/column/18/00001/",
            "category": "国内テック",
            "selector": {
                "article_list": ".article-list__item",
                "title": ".article-list__title",
                "url": "a",
                "summary": ".article-list__summary",
            },
        }
    ]
    articles = scrape_articles(sources)
"""

import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# デフォルトの HTTP ヘッダー
_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AI-News-Bot/1.0; "
        "+https://github.com/ai-news-bot)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

# デフォルトのリクエスト間隔（秒）- サーバー負荷軽減
_DEFAULT_REQUEST_INTERVAL = 2.0

# デフォルトのリクエストタイムアウト（秒）
_DEFAULT_FETCH_TIMEOUT = 30


def _check_robots_txt(base_url: str, path: str) -> bool:
    """robots.txt を確認し、指定パスへのアクセスが許可されているか判定する。

    NOTE: 簡易実装。本格的な robots.txt パーサーが必要な場合は
    robotparser (urllib.robotparser) の使用を検討すること。

    robots.txt の取得に失敗した場合は、安全側に倒してアクセスを許可する。

    Args:
        base_url: サイトのベース URL (例: "https://example.com")。
        path: チェック対象のパス (例: "/articles/")。

    Returns:
        True: アクセスが許可されている場合。
        False: アクセスが拒否されている場合。
    """
    try:
        from urllib.robotparser import RobotFileParser

        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        # User-Agent "AI-News-Bot" と "*" の両方でチェック
        full_url = urljoin(base_url, path)
        return rp.can_fetch("AI-News-Bot", full_url) and rp.can_fetch("*", full_url)
    except Exception as e:
        logger.warning(
            "robots.txt の確認に失敗しました (%s): %s - アクセスを許可として続行します",
            base_url,
            str(e),
        )
        # robots.txt が取得できない場合は許可として扱う
        return True


@with_retry(
    max_attempts=3,
    exceptions=(ConnectionError, TimeoutError, OSError, requests.RequestException),
)
def _fetch_page(url: str, timeout: int = _DEFAULT_FETCH_TIMEOUT) -> str:
    """指定 URL の HTML コンテンツを取得する。

    Args:
        url: 取得対象の URL。
        timeout: リクエストタイムアウト（秒）。

    Returns:
        HTML コンテンツ文字列。

    Raises:
        requests.RequestException: HTTP リクエストが失敗した場合。
    """
    response = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _extract_articles_from_html(
    html: str,
    base_url: str,
    source_name: str,
    category: str,
    language: str,
    selectors: dict[str, str],
) -> list[dict[str, Any]]:
    """HTML コンテンツから CSS セレクタを使って記事情報を抽出する。

    Args:
        html: HTML コンテンツ文字列。
        base_url: ベース URL（相対 URL の解決に使用）。
        source_name: ソース名。
        category: カテゴリ。
        language: 言語コード。
        selectors: CSS セレクタの辞書:
            - article_list: 記事要素のセレクタ
            - title: タイトル要素のセレクタ
            - url: URL を持つ要素のセレクタ (a タグ)
            - summary: 概要要素のセレクタ (オプション)

    Returns:
        記事情報の辞書のリスト。
    """
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict[str, Any]] = []

    article_selector = selectors.get("article_list", "article")
    title_selector = selectors.get("title", "h2")
    url_selector = selectors.get("url", "a")
    summary_selector = selectors.get("summary", "")

    article_elements = soup.select(article_selector)

    for element in article_elements:
        try:
            # タイトルの抽出
            title_elem = element.select_one(title_selector)
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            if not title:
                continue

            # URL の抽出
            link_elem = element.select_one(url_selector)
            if not link_elem:
                continue
            href = link_elem.get("href", "")
            if not href:
                continue
            article_url = urljoin(base_url, href)

            # 概要の抽出（オプション）
            summary = ""
            if summary_selector:
                summary_elem = element.select_one(summary_selector)
                if summary_elem:
                    summary = summary_elem.get_text(strip=True)

            article = {
                "title": title,
                "url": article_url,
                "summary": summary[:500] if summary else "",
                "published_at": datetime.now(tz=timezone.utc).isoformat(),
                "source": source_name,
                "category": category,
                "language": language,
                "collected_via": "scraping",
            }
            articles.append(article)

        except Exception as e:
            logger.debug(
                "記事要素のパースに失敗しました (%s): %s", source_name, str(e)
            )
            continue

    return articles


def scrape_articles(
    sources: list[dict[str, Any]],
    request_interval: float = _DEFAULT_REQUEST_INTERVAL,
    fetch_timeout: int = _DEFAULT_FETCH_TIMEOUT,
    respect_robots_txt: bool = True,
) -> list[dict[str, Any]]:
    """複数の Web ソースからスクレイピングで記事を収集する。

    個別ソースの取得が失敗した場合はログに記録し、他のソースの収集を継続する。
    robots.txt の準拠設定に従い、アクセスが拒否されているサイトはスキップする。
    リクエスト間隔を設けてサーバー負荷を軽減する。

    Args:
        sources: スクレイピングソース情報のリスト。各要素は以下のキーを持つ辞書:
            - name (str): ソース名
            - url (str): スクレイピング対象 URL
            - category (str, optional): カテゴリ
            - language (str, optional): 言語コード
            - selector (dict): CSS セレクタ辞書
                - article_list (str): 記事リスト要素のセレクタ
                - title (str): タイトル要素のセレクタ
                - url (str): URL 要素（a タグ）のセレクタ
                - summary (str, optional): 概要要素のセレクタ
        request_interval: リクエスト間隔（秒）。
        fetch_timeout: リクエストタイムアウト（秒）。
        respect_robots_txt: True の場合、robots.txt を確認してアクセスを制御する。

    Returns:
        記事情報の辞書のリスト。各辞書のキーは rss_collector と同じ構造に加え:
            - collected_via (str): "scraping"
    """
    all_articles: list[dict[str, Any]] = []

    if not sources:
        logger.warning("スクレイピングソースが指定されていません")
        return all_articles

    logger.info("Web スクレイピングを開始します: %d ソース", len(sources))

    for i, source in enumerate(sources):
        source_name = source.get("name", "Unknown")
        source_url = source.get("url", "")
        category = source.get("category", "")
        language = source.get("language", "ja")
        selectors = source.get("selector", {})

        if not source_url:
            logger.warning("URL が空のソースをスキップします: %s", source_name)
            continue

        if not selectors:
            logger.warning(
                "CSS セレクタが未設定のソースをスキップします: %s", source_name
            )
            continue

        # robots.txt の確認
        if respect_robots_txt:
            parsed_url = urlparse(source_url)
            base = f"{parsed_url.scheme}://{parsed_url.netloc}"
            path = parsed_url.path
            if not _check_robots_txt(base, path):
                logger.warning(
                    "robots.txt によりアクセスが拒否されています: %s (%s)",
                    source_name,
                    source_url,
                )
                continue

        try:
            logger.info("Web ページを取得中: %s (%s)", source_name, source_url)
            html = _fetch_page(source_url, timeout=fetch_timeout)

            articles = _extract_articles_from_html(
                html=html,
                base_url=source_url,
                source_name=source_name,
                category=category,
                language=language,
                selectors=selectors,
            )

            all_articles.extend(articles)
            logger.info(
                "Web スクレイピングで %d 件取得しました: %s",
                len(articles),
                source_name,
            )

        except Exception as e:
            logger.error(
                "Web スクレイピングに失敗しました: %s (%s) - %s",
                source_name,
                source_url,
                str(e),
            )
            continue

        # リクエスト間隔の確保（最後のソース以外）
        if i < len(sources) - 1:
            logger.debug("リクエスト間隔: %.1f 秒待機", request_interval)
            time.sleep(request_interval)

    logger.info("Web スクレイピングが完了しました: 合計 %d 件", len(all_articles))
    return all_articles
