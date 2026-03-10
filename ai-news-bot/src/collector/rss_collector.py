"""RSS フィード収集モジュール

feedparser を使用して複数の RSS フィードからニュース記事を取得・パースする。
各ソースが失敗しても他のソースからの収集を継続する。

使用例::

    from src.collector.rss_collector import collect_from_rss

    sources = [
        {"name": "TechCrunch AI", "url": "https://techcrunch.com/.../feed/", "category": "海外テック"},
    ]
    articles = collect_from_rss(sources)
"""

from datetime import datetime, timezone
from time import mktime
from typing import Any

import feedparser

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# feedparser が返すフィードのステータスコード閾値
_HTTP_OK_MAX = 399


def _parse_published_date(entry: Any) -> str:
    """フィードエントリの公開日時を ISO 8601 文字列に変換する。

    feedparser は published_parsed / updated_parsed を time.struct_time で返す。
    いずれも存在しない場合は現在時刻を使用する。

    Args:
        entry: feedparser のフィードエントリ。

    Returns:
        ISO 8601 形式の日時文字列。
    """
    time_struct = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if time_struct:
        try:
            dt = datetime.fromtimestamp(mktime(time_struct), tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, OverflowError, OSError):
            pass
    return datetime.now(tz=timezone.utc).isoformat()


def _extract_summary(entry: Any) -> str:
    """フィードエントリから概要テキストを抽出する。

    summary -> description の順にフォールバックし、HTML タグを
    簡易的に除去して返す。

    Args:
        entry: feedparser のフィードエントリ。

    Returns:
        概要テキスト（最大500文字）。
    """
    raw = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

    # 簡易的な HTML タグ除去
    import re

    text = re.sub(r"<[^>]+>", "", raw)
    text = text.strip()

    # 長すぎる概要を切り詰め
    if len(text) > 1500:
        text = text[:1497] + "..."
    return text


@with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError, OSError))
def _fetch_single_feed(url: str, timeout: int = 30) -> feedparser.FeedParserDict:
    """単一の RSS フィード URL を取得・パースする。

    Args:
        url: RSS フィードの URL。
        timeout: リクエストタイムアウト（秒）。

    Returns:
        feedparser.FeedParserDict: パースされたフィードデータ。

    Raises:
        ConnectionError: フィード取得に失敗した場合。
    """
    feed = feedparser.parse(url, request_headers={"User-Agent": "AI-News-Bot/1.0"})

    # bozo フラグによるパースエラー検出
    if feed.bozo and not feed.entries:
        bozo_exception = getattr(feed, "bozo_exception", None)
        raise ConnectionError(
            f"RSS フィードのパースに失敗しました: {url} - {bozo_exception}"
        )

    # HTTP ステータスコードによるエラー検出（リモートフィードの場合）
    status = getattr(feed, "status", 200)
    if status > _HTTP_OK_MAX:
        raise ConnectionError(
            f"RSS フィード取得エラー (HTTP {status}): {url}"
        )

    return feed


def collect_from_rss(
    sources: list[dict[str, Any]],
    max_articles_per_feed: int = 20,
    fetch_timeout: int = 30,
) -> list[dict[str, Any]]:
    """複数の RSS ソースから記事を収集する。

    個別ソースの取得が失敗した場合はログに記録し、他のソースの収集を継続する。

    Args:
        sources: RSS ソース情報のリスト。各要素は以下のキーを持つ辞書:
            - name (str): ソース名
            - url (str): RSS フィード URL
            - category (str, optional): カテゴリ
            - language (str, optional): 言語コード
        max_articles_per_feed: フィードあたりの最大取得件数。
        fetch_timeout: 各フィードの取得タイムアウト（秒）。

    Returns:
        記事情報の辞書のリスト。各辞書は以下のキーを持つ:
            - title (str): 記事タイトル
            - url (str): 記事 URL
            - summary (str): 概要
            - published_at (str): 公開日時（ISO 8601）
            - source (str): ソース名
            - category (str): カテゴリ
            - language (str): 言語コード
            - collected_via (str): 収集方法（"rss"）
    """
    all_articles: list[dict[str, Any]] = []

    if not sources:
        logger.warning("RSS ソースが指定されていません")
        return all_articles

    logger.info("RSS 収集を開始します: %d ソース", len(sources))

    for source in sources:
        source_name = source.get("name", "不明")
        source_url = source.get("url", "")
        category = source.get("category", "")
        language = source.get("language", "en")

        if not source_url:
            logger.warning("URL が空のソースをスキップします: %s", source_name)
            continue

        try:
            logger.info("RSS フィードを取得中: %s (%s)", source_name, source_url)
            feed = _fetch_single_feed(source_url, timeout=fetch_timeout)

            entries = feed.entries[:max_articles_per_feed]
            feed_articles: list[dict[str, Any]] = []

            for entry in entries:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()

                # タイトルまたは URL が無い場合はスキップ
                if not title or not link:
                    continue

                article = {
                    "title": title,
                    "url": link,
                    "summary": _extract_summary(entry),
                    "published_at": _parse_published_date(entry),
                    "source": source_name,
                    "category": category,
                    "language": language,
                    "collected_via": "rss",
                }
                feed_articles.append(article)

            all_articles.extend(feed_articles)
            logger.info(
                "RSS フィードから %d 件取得しました: %s",
                len(feed_articles),
                source_name,
            )

        except Exception as e:
            logger.error(
                "RSS フィード取得に失敗しました: %s (%s) - %s",
                source_name,
                source_url,
                str(e),
            )
            # 個別ソースの失敗時も他のソースの収集を継続
            continue

    logger.info("RSS 収集が完了しました: 合計 %d 件", len(all_articles))
    return all_articles
