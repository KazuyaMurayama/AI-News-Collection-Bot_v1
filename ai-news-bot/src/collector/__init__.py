"""ニュース収集モジュール

RSS フィード、Web スクレイピング、News API の3つの収集チャネルを統合し、
Claude API による記事選定を行う。

使用例::

    from src.collector import collect_all

    # 全ソースから収集し、上位5件を選定
    selected_articles = collect_all()

    # 収集のみ（選定なし）
    from src.collector import collect_candidates
    candidates = collect_candidates()
"""

from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def collect_candidates(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """全チャネルから候補記事を収集する（選定は行わない）。

    config.yaml の sources 設定に基づき、RSS、Web スクレイピング、
    News API の各チャネルから記事を収集してマージする。
    個別チャネルの失敗時も他のチャネルの収集を継続する。

    Args:
        config: 設定辞書。None の場合は config.yaml から自動読み込み。

    Returns:
        候補記事の辞書のリスト。
    """
    if config is None:
        try:
            from src.utils.config import load_config
            config = load_config()
        except Exception as e:
            logger.error("設定ファイルの読み込みに失敗しました: %s", str(e))
            return []

    all_candidates: list[dict[str, Any]] = []
    collection_cfg = config.get("collection", {})
    sources = collection_cfg.get("sources", [])

    # --- RSS フィード収集 ---
    rss_sources = [s for s in sources if s.get("type") == "rss" and s.get("enabled", True)]
    if rss_sources:
        try:
            from src.collector.rss_collector import collect_from_rss
            rss_articles = collect_from_rss(rss_sources)
            all_candidates.extend(rss_articles)
            logger.info("RSS 収集完了: %d 件", len(rss_articles))
        except Exception as e:
            logger.error("RSS 収集でエラーが発生しました: %s", str(e))
    else:
        logger.info("有効な RSS ソースがないためスキップします")

    # --- Web スクレイピング ---
    scraping_sources = [
        s for s in sources if s.get("type") == "scraping" and s.get("enabled", True)
    ]
    if scraping_sources:
        try:
            from src.collector.web_scraper import scrape_articles
            scraping_articles = scrape_articles(scraping_sources)
            all_candidates.extend(scraping_articles)
            logger.info("Web スクレイピング収集完了: %d 件", len(scraping_articles))
        except Exception as e:
            logger.error("Web スクレイピングでエラーが発生しました: %s", str(e))
    else:
        logger.info("有効なスクレイピングソースがないためスキップします")

    # --- News API / Hacker News API ---
    api_sources = [s for s in sources if s.get("type") == "api" and s.get("enabled", True)]
    for api_source in api_sources:
        source_name = api_source.get("name", "")
        try:
            if "newsapi" in source_name.lower():
                from src.collector.news_api import fetch_from_newsapi
                query = api_source.get("query", None)
                newsapi_articles = fetch_from_newsapi(query=query)
                all_candidates.extend(newsapi_articles)
                logger.info("NewsAPI 収集完了: %d 件", len(newsapi_articles))

            elif "hacker" in source_name.lower():
                from src.collector.news_api import fetch_from_hackernews
                query = api_source.get("query", None)
                hn_articles = fetch_from_hackernews(query=query)
                all_candidates.extend(hn_articles)
                logger.info("Hacker News API 収集完了: %d 件", len(hn_articles))

        except Exception as e:
            logger.error(
                "API 収集でエラーが発生しました (%s): %s", source_name, str(e)
            )

    logger.info("候補記事の収集が完了しました: 合計 %d 件", len(all_candidates))
    return all_candidates


def collect_all(
    config: dict[str, Any] | None = None,
    num_articles: int | None = None,
) -> list[dict[str, Any]]:
    """全チャネルから候補記事を収集し、上位記事を選定する。

    1. collect_candidates() で全チャネルから候補を収集
    2. selector.select_top_articles() で Claude API スコアリング・選定

    Args:
        config: 設定辞書。None の場合は config.yaml から自動読み込み。
        num_articles: 選定する記事数。None の場合は config の num_stories を使用。

    Returns:
        選定された記事の辞書のリスト（スコア付き）。
    """
    if config is None:
        try:
            from src.utils.config import load_config
            config = load_config()
        except Exception as e:
            logger.error("設定ファイルの読み込みに失敗しました: %s", str(e))
            return []

    # 選定件数の決定
    if num_articles is None:
        num_articles = config.get("collection", {}).get("num_stories", 5)

    logger.info("=== ニュース収集パイプライン開始 ===")

    # Phase 1: 候補記事の収集
    candidates = collect_candidates(config)

    if not candidates:
        logger.warning("候補記事が0件のため、選定をスキップします")
        return []

    # Phase 2: 記事の選定
    try:
        from src.collector.selector import select_top_articles
        selected = select_top_articles(candidates, num=num_articles)
        logger.info("=== ニュース収集パイプライン完了: %d 件選定 ===", len(selected))
        return selected
    except Exception as e:
        logger.error("記事選定でエラーが発生しました: %s", str(e))
        return []
