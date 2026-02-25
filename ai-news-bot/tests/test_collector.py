"""collector モジュールのテスト

rss_collector, web_scraper, news_api, selector の各機能をテストする。
外部 API 呼び出しはモックで置き換える。
"""

import json
import os
from datetime import datetime, timezone
from time import struct_time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# テスト対象モジュールを事前にインポート（@patch デコレータが解決できるようにする）
import src.collector.rss_collector  # noqa: F401
import src.collector.web_scraper  # noqa: F401
import src.collector.news_api  # noqa: F401
import src.collector.selector  # noqa: F401


# ============================================================
# テスト用フィクスチャ・ヘルパー
# ============================================================


def _make_article(
    title: str = "Test Article",
    url: str = "https://example.com/article",
    summary: str = "Test summary",
    source: str = "TestSource",
    published_at: str | None = None,
    category: str = "テスト",
    language: str = "en",
) -> dict[str, Any]:
    """テスト用の記事辞書を生成する。"""
    if published_at is None:
        published_at = datetime.now(tz=timezone.utc).isoformat()
    return {
        "title": title,
        "url": url,
        "summary": summary,
        "published_at": published_at,
        "source": source,
        "category": category,
        "language": language,
        "collected_via": "test",
    }


def _make_feed_entry(
    title: str = "Feed Entry Title",
    link: str = "https://example.com/entry",
    summary: str = "Entry summary text",
    published_parsed: struct_time | None = None,
) -> MagicMock:
    """テスト用の feedparser エントリモックを生成する。"""
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.description = summary

    if published_parsed is None:
        # 2026-02-25 06:00:00 UTC
        published_parsed = struct_time((2026, 2, 25, 6, 0, 0, 2, 56, 0))
    entry.published_parsed = published_parsed
    entry.updated_parsed = None

    return entry


def _make_feed(entries: list | None = None, status: int = 200, bozo: bool = False) -> MagicMock:
    """テスト用の feedparser.FeedParserDict モックを生成する。"""
    feed = MagicMock()
    feed.entries = entries if entries is not None else []
    feed.status = status
    feed.bozo = bozo
    feed.bozo_exception = None
    return feed


# ============================================================
# rss_collector のテスト
# ============================================================


class TestRssCollector:
    """RSS 収集のテスト。"""

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_from_rss_success(self, mock_parse: MagicMock) -> None:
        """正常系: 複数ソースから記事を取得できること。"""
        from src.collector.rss_collector import collect_from_rss

        entries = [
            _make_feed_entry(
                title="Article 1",
                link="https://example.com/1",
                summary="Summary 1",
            ),
            _make_feed_entry(
                title="Article 2",
                link="https://example.com/2",
                summary="Summary 2",
            ),
        ]
        mock_parse.return_value = _make_feed(entries=entries)

        sources = [
            {
                "name": "TestFeed",
                "url": "https://example.com/feed.xml",
                "category": "テスト",
                "language": "en",
            }
        ]

        articles = collect_from_rss(sources)

        assert len(articles) == 2
        assert articles[0]["title"] == "Article 1"
        assert articles[0]["url"] == "https://example.com/1"
        assert articles[0]["source"] == "TestFeed"
        assert articles[0]["category"] == "テスト"
        assert articles[0]["collected_via"] == "rss"
        assert articles[1]["title"] == "Article 2"

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_from_rss_multiple_sources(self, mock_parse: MagicMock) -> None:
        """複数ソースからの収集結果がマージされること。"""
        from src.collector.rss_collector import collect_from_rss

        feed1_entries = [_make_feed_entry(title="From Feed 1", link="https://a.com/1")]
        feed2_entries = [_make_feed_entry(title="From Feed 2", link="https://b.com/1")]

        mock_parse.side_effect = [
            _make_feed(entries=feed1_entries),
            _make_feed(entries=feed2_entries),
        ]

        sources = [
            {"name": "Feed1", "url": "https://a.com/feed", "category": "A"},
            {"name": "Feed2", "url": "https://b.com/feed", "category": "B"},
        ]

        articles = collect_from_rss(sources)

        assert len(articles) == 2
        assert articles[0]["source"] == "Feed1"
        assert articles[1]["source"] == "Feed2"

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_from_rss_source_failure_continues(self, mock_parse: MagicMock) -> None:
        """個別ソースの失敗時に他のソースの収集が継続されること。"""
        from src.collector.rss_collector import collect_from_rss

        # 1つ目のフィードは失敗、2つ目は成功
        mock_parse.side_effect = [
            _make_feed(entries=[], bozo=True),
            _make_feed(entries=[_make_feed_entry(title="Success", link="https://b.com/1")]),
        ]

        sources = [
            {"name": "FailFeed", "url": "https://fail.com/feed", "category": "A"},
            {"name": "OkFeed", "url": "https://ok.com/feed", "category": "B"},
        ]

        articles = collect_from_rss(sources)

        # 2つ目のフィードの記事だけが取得されること
        assert len(articles) == 1
        assert articles[0]["title"] == "Success"

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_from_rss_empty_sources(self, mock_parse: MagicMock) -> None:
        """ソースリストが空の場合は空リストを返すこと。"""
        from src.collector.rss_collector import collect_from_rss

        articles = collect_from_rss([])
        assert articles == []
        mock_parse.assert_not_called()

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_from_rss_skip_entry_without_title(self, mock_parse: MagicMock) -> None:
        """タイトルがないエントリがスキップされること。"""
        from src.collector.rss_collector import collect_from_rss

        entries = [
            _make_feed_entry(title="", link="https://example.com/1"),
            _make_feed_entry(title="Valid Title", link="https://example.com/2"),
        ]
        mock_parse.return_value = _make_feed(entries=entries)

        sources = [{"name": "Test", "url": "https://example.com/feed", "category": "T"}]
        articles = collect_from_rss(sources)

        assert len(articles) == 1
        assert articles[0]["title"] == "Valid Title"

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_from_rss_max_articles_per_feed(self, mock_parse: MagicMock) -> None:
        """max_articles_per_feed で取得件数が制限されること。"""
        from src.collector.rss_collector import collect_from_rss

        entries = [
            _make_feed_entry(title=f"Article {i}", link=f"https://example.com/{i}")
            for i in range(10)
        ]
        mock_parse.return_value = _make_feed(entries=entries)

        sources = [{"name": "Test", "url": "https://example.com/feed", "category": "T"}]
        articles = collect_from_rss(sources, max_articles_per_feed=3)

        assert len(articles) == 3

    def test_parse_published_date_with_struct_time(self) -> None:
        """struct_time が正しく ISO 8601 に変換されること。"""
        from src.collector.rss_collector import _parse_published_date

        entry = MagicMock()
        entry.published_parsed = struct_time((2026, 2, 25, 6, 0, 0, 2, 56, 0))
        entry.updated_parsed = None

        result = _parse_published_date(entry)
        assert "2026-02-25" in result

    def test_parse_published_date_fallback(self) -> None:
        """公開日時が無い場合に現在時刻がフォールバックとして使われること。"""
        from src.collector.rss_collector import _parse_published_date

        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None

        result = _parse_published_date(entry)
        # 今日の日付を含むことを確認
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        assert today in result

    def test_extract_summary_html_stripped(self) -> None:
        """HTML タグが除去されて概要が返ること。"""
        from src.collector.rss_collector import _extract_summary

        entry = MagicMock()
        entry.summary = "<p>This is a <strong>test</strong> summary.</p>"
        entry.description = ""

        result = _extract_summary(entry)
        assert "<" not in result
        assert "This is a test summary." in result


# ============================================================
# selector のテスト
# ============================================================


class TestSelector:
    """記事選定のテスト。"""

    def test_deduplicate_candidates(self) -> None:
        """重複排除が正しく動作すること。"""
        from src.collector.selector import _deduplicate_candidates

        candidates = [
            _make_article(title="Article A", url="https://example.com/a"),
            _make_article(title="Article B", url="https://example.com/b"),
            _make_article(title="Article A", url="https://example.com/a"),  # URL 重複
            _make_article(title="article b", url="https://different.com/b"),  # タイトル重複 (小文字)
        ]

        unique = _deduplicate_candidates(candidates)
        assert len(unique) == 2

    def test_deduplicate_empty_list(self) -> None:
        """空リストの重複排除。"""
        from src.collector.selector import _deduplicate_candidates

        unique = _deduplicate_candidates([])
        assert unique == []

    def test_clamp_values(self) -> None:
        """_clamp が正しく値を制限すること。"""
        from src.collector.selector import _clamp

        assert _clamp(3, 0, 5) == 3
        assert _clamp(-1, 0, 5) == 0
        assert _clamp(10, 0, 5) == 5
        assert _clamp("invalid", 0, 5) == 0
        assert _clamp(None, 0, 5) == 0

    def test_parse_scoring_response_valid_json(self) -> None:
        """正常な JSON スコアリングレスポンスが正しくパースされること。"""
        from src.collector.selector import _parse_scoring_response

        response = json.dumps([
            {
                "index": 0,
                "novelty": 4,
                "surprise": 3,
                "practicality": 5,
                "japan_relevance": 2,
                "freshness": 2,
                "total": 16,
                "reason": "Test reason",
            },
            {
                "index": 1,
                "novelty": 2,
                "surprise": 1,
                "practicality": 3,
                "japan_relevance": 1,
                "freshness": 1,
                "total": 8,
                "reason": "Another reason",
            },
        ])

        scores = _parse_scoring_response(response, num_candidates=2)
        assert len(scores) == 2
        assert scores[0]["total"] == 16
        assert scores[1]["total"] == 8
        assert scores[0]["reason"] == "Test reason"

    def test_parse_scoring_response_with_code_block(self) -> None:
        """```json ``` で囲まれたレスポンスがパースされること。"""
        from src.collector.selector import _parse_scoring_response

        response = """ここにスコアリング結果です。

```json
[
  {
    "index": 0,
    "novelty": 5,
    "surprise": 4,
    "practicality": 3,
    "japan_relevance": 2,
    "freshness": 1,
    "total": 15,
    "reason": "Wrapped in code block"
  }
]
```
"""
        scores = _parse_scoring_response(response, num_candidates=1)
        assert len(scores) == 1
        assert scores[0]["total"] == 15

    def test_parse_scoring_response_invalid_json(self) -> None:
        """無効な JSON に対して空リストが返ること。"""
        from src.collector.selector import _parse_scoring_response

        scores = _parse_scoring_response("This is not valid JSON", num_candidates=1)
        assert scores == []

    def test_parse_scoring_response_clamps_values(self) -> None:
        """スコア値が基準値の範囲にクランプされること。"""
        from src.collector.selector import _parse_scoring_response

        response = json.dumps([
            {
                "index": 0,
                "novelty": 10,       # 最大5 -> 5にクランプ
                "surprise": -1,      # 最小0 -> 0にクランプ
                "practicality": 3,
                "japan_relevance": 5, # 最大3 -> 3にクランプ
                "freshness": 2,
                "total": 999,        # 再計算される
                "reason": "Clamped",
            }
        ])

        scores = _parse_scoring_response(response, num_candidates=1)
        assert len(scores) == 1
        assert scores[0]["novelty"] == 5
        assert scores[0]["surprise"] == 0
        assert scores[0]["japan_relevance"] == 3
        # total は再計算: 5 + 0 + 3 + 3 + 2 = 13
        assert scores[0]["total"] == 13

    def test_fallback_select_by_recency(self) -> None:
        """フォールバック選定が時間順で正しく動作すること。"""
        from src.collector.selector import _fallback_select_by_recency

        candidates = [
            _make_article(title="Old", published_at="2026-02-20T00:00:00+00:00"),
            _make_article(title="New", published_at="2026-02-25T12:00:00+00:00"),
            _make_article(title="Mid", published_at="2026-02-23T06:00:00+00:00"),
        ]

        selected = _fallback_select_by_recency(candidates, num=2)
        assert len(selected) == 2
        assert selected[0]["title"] == "New"
        assert selected[1]["title"] == "Mid"
        # フォールバックスコアが付与されていること
        assert selected[0]["score"]["total"] == 0
        assert "フォールバック" in selected[0]["score"]["reason"]

    @patch("src.collector.selector._score_with_claude")
    def test_select_top_articles_with_scores(self, mock_score: MagicMock) -> None:
        """Claude API スコアリングで上位記事が選定されること。"""
        from src.collector.selector import select_top_articles

        candidates = [
            _make_article(title="Low Score", url="https://example.com/low"),
            _make_article(title="High Score", url="https://example.com/high"),
            _make_article(title="Mid Score", url="https://example.com/mid"),
        ]

        mock_score.return_value = [
            {
                "index": 0, "novelty": 1, "surprise": 1, "practicality": 1,
                "japan_relevance": 0, "freshness": 0, "total": 3, "reason": "Low",
            },
            {
                "index": 1, "novelty": 5, "surprise": 5, "practicality": 5,
                "japan_relevance": 3, "freshness": 2, "total": 20, "reason": "High",
            },
            {
                "index": 2, "novelty": 3, "surprise": 3, "practicality": 3,
                "japan_relevance": 1, "freshness": 1, "total": 11, "reason": "Mid",
            },
        ]

        selected = select_top_articles(candidates, num=2)

        assert len(selected) == 2
        assert selected[0]["title"] == "High Score"
        assert selected[0]["score"]["total"] == 20
        assert selected[1]["title"] == "Mid Score"
        assert selected[1]["score"]["total"] == 11

    @patch("src.collector.selector._score_with_claude")
    def test_select_top_articles_fallback_on_api_failure(self, mock_score: MagicMock) -> None:
        """Claude API 失敗時にフォールバック選定が行われること。"""
        from src.collector.selector import select_top_articles

        mock_score.return_value = []  # API 失敗

        candidates = [
            _make_article(
                title="Newest", url="https://example.com/new",
                published_at="2026-02-25T12:00:00+00:00",
            ),
            _make_article(
                title="Oldest", url="https://example.com/old",
                published_at="2026-02-20T00:00:00+00:00",
            ),
            _make_article(
                title="Middle", url="https://example.com/mid",
                published_at="2026-02-23T00:00:00+00:00",
            ),
        ]

        selected = select_top_articles(candidates, num=2)

        assert len(selected) == 2
        # フォールバック: 時間順で新しい方から
        assert selected[0]["title"] == "Newest"
        assert selected[1]["title"] == "Middle"

    def test_select_top_articles_empty_candidates(self) -> None:
        """候補記事が空の場合に空リストが返ること。"""
        from src.collector.selector import select_top_articles

        selected = select_top_articles([], num=3)
        assert selected == []

    @patch("src.collector.selector._score_with_claude")
    def test_select_top_articles_fewer_than_num(self, mock_score: MagicMock) -> None:
        """候補記事が選定件数より少ない場合に全件が返ること。"""
        from src.collector.selector import select_top_articles

        candidates = [
            _make_article(title="Only One", url="https://example.com/only"),
        ]

        selected = select_top_articles(candidates, num=3)

        assert len(selected) == 1
        assert selected[0]["title"] == "Only One"
        # Claude API は呼ばれない（候補 <= num の場合はフォールバック）
        mock_score.assert_not_called()

    @patch("src.collector.selector._score_with_claude")
    def test_select_top_articles_dedup(self, mock_score: MagicMock) -> None:
        """重複する候補記事が排除されて選定されること。"""
        from src.collector.selector import select_top_articles

        candidates = [
            _make_article(title="Article A", url="https://example.com/a"),
            _make_article(title="Article A", url="https://example.com/a"),  # 重複
            _make_article(title="Article B", url="https://example.com/b"),
            _make_article(title="Article C", url="https://example.com/c"),
        ]

        mock_score.return_value = [
            {"index": 0, "novelty": 5, "surprise": 5, "practicality": 5,
             "japan_relevance": 3, "freshness": 2, "total": 20, "reason": "A"},
            {"index": 1, "novelty": 3, "surprise": 3, "practicality": 3,
             "japan_relevance": 1, "freshness": 1, "total": 11, "reason": "B"},
            {"index": 2, "novelty": 1, "surprise": 1, "practicality": 1,
             "japan_relevance": 0, "freshness": 0, "total": 3, "reason": "C"},
        ]

        selected = select_top_articles(candidates, num=2)

        # 重複排除後は3件なので、上位2件が選定される
        assert len(selected) == 2
        titles = [a["title"] for a in selected]
        assert "Article A" in titles

    def test_build_scoring_prompt(self) -> None:
        """スコアリングプロンプトが正しく生成されること。"""
        from src.collector.selector import _build_scoring_prompt

        candidates = [
            _make_article(title="Test Article", url="https://example.com/test"),
        ]

        prompt = _build_scoring_prompt(candidates)

        assert "1 件の記事" in prompt
        assert "Test Article" in prompt
        assert "https://example.com/test" in prompt
        assert "JSON" in prompt


# ============================================================
# news_api のテスト
# ============================================================


class TestNewsApi:
    """News API 収集のテスト。"""

    @patch("src.collector.news_api.requests.get")
    def test_fetch_from_newsapi_success(self, mock_get: MagicMock) -> None:
        """NewsAPI からの正常取得。"""
        from src.collector.news_api import fetch_from_newsapi

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "AI News Article",
                    "url": "https://example.com/ai-news",
                    "description": "Article about AI",
                    "publishedAt": "2026-02-25T06:00:00Z",
                    "source": {"name": "TechNews"},
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_from_newsapi(query="AI", api_key="test-key")

        assert len(articles) == 1
        assert articles[0]["title"] == "AI News Article"
        assert articles[0]["collected_via"] == "newsapi"
        assert "TechNews" in articles[0]["source"]

    @patch("src.collector.news_api.requests.get")
    def test_fetch_from_newsapi_no_api_key(self, mock_get: MagicMock) -> None:
        """API キーが無い場合に空リストが返ること。"""
        from src.collector.news_api import fetch_from_newsapi

        with patch.dict(os.environ, {}, clear=True):
            articles = fetch_from_newsapi(query="AI", api_key="")
            assert articles == []
            mock_get.assert_not_called()

    @patch("src.collector.news_api.requests.get")
    def test_fetch_from_newsapi_skips_removed(self, mock_get: MagicMock) -> None:
        """[Removed] タイトルの記事がスキップされること。"""
        from src.collector.news_api import fetch_from_newsapi

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "articles": [
                {
                    "title": "[Removed]",
                    "url": "https://example.com/removed",
                    "description": "",
                    "publishedAt": "2026-02-25T06:00:00Z",
                    "source": {"name": "X"},
                },
                {
                    "title": "Valid Article",
                    "url": "https://example.com/valid",
                    "description": "Valid desc",
                    "publishedAt": "2026-02-25T06:00:00Z",
                    "source": {"name": "Y"},
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_from_newsapi(query="AI", api_key="test-key")

        assert len(articles) == 1
        assert articles[0]["title"] == "Valid Article"

    @patch("src.collector.news_api.requests.get")
    def test_fetch_from_hackernews_success(self, mock_get: MagicMock) -> None:
        """Hacker News API からの正常取得。"""
        from src.collector.news_api import fetch_from_hackernews

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "title": "Show HN: AI Tool",
                    "url": "https://example.com/tool",
                    "objectID": "12345",
                    "created_at": "2026-02-25T06:00:00.000Z",
                    "points": 100,
                    "num_comments": 50,
                    "story_text": None,
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_from_hackernews()

        assert len(articles) == 1
        assert articles[0]["title"] == "Show HN: AI Tool"
        assert articles[0]["source"] == "Hacker News"
        assert articles[0]["collected_via"] == "hackernews_api"

    @patch("src.collector.news_api.requests.get")
    def test_fetch_from_hackernews_fallback_url(self, mock_get: MagicMock) -> None:
        """URL がない場合に HN ディスカッションページ URL がフォールバックとして使われること。"""
        from src.collector.news_api import fetch_from_hackernews

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "title": "Ask HN: Question",
                    "url": "",
                    "objectID": "99999",
                    "created_at": "2026-02-25T06:00:00.000Z",
                    "points": 50,
                    "num_comments": 30,
                    "story_text": None,
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = fetch_from_hackernews()

        assert len(articles) == 1
        assert "news.ycombinator.com" in articles[0]["url"]
        assert "99999" in articles[0]["url"]


# ============================================================
# web_scraper のテスト
# ============================================================


class TestWebScraper:
    """Web スクレイピングのテスト。"""

    @patch("src.collector.web_scraper._check_robots_txt", return_value=True)
    @patch("src.collector.web_scraper._fetch_page")
    def test_scrape_articles_success(
        self, mock_fetch: MagicMock, mock_robots: MagicMock
    ) -> None:
        """正常系: HTML から記事を抽出できること。"""
        from src.collector.web_scraper import scrape_articles

        html = """
        <html>
        <body>
            <div class="article-list__item">
                <h2 class="article-list__title">Test Article 1</h2>
                <a href="/articles/1">Read more</a>
                <p class="article-list__summary">Summary 1</p>
            </div>
            <div class="article-list__item">
                <h2 class="article-list__title">Test Article 2</h2>
                <a href="/articles/2">Read more</a>
                <p class="article-list__summary">Summary 2</p>
            </div>
        </body>
        </html>
        """
        mock_fetch.return_value = html

        sources = [
            {
                "name": "TestSite",
                "url": "https://example.com/articles/",
                "category": "テスト",
                "language": "ja",
                "selector": {
                    "article_list": ".article-list__item",
                    "title": ".article-list__title",
                    "url": "a",
                    "summary": ".article-list__summary",
                },
            }
        ]

        articles = scrape_articles(sources, request_interval=0)

        assert len(articles) == 2
        assert articles[0]["title"] == "Test Article 1"
        assert articles[0]["source"] == "TestSite"
        assert articles[0]["collected_via"] == "scraping"
        assert "https://example.com/articles/1" in articles[0]["url"]

    @patch("src.collector.web_scraper._check_robots_txt", return_value=True)
    @patch("src.collector.web_scraper._fetch_page")
    def test_scrape_articles_empty_selectors(
        self, mock_fetch: MagicMock, mock_robots: MagicMock
    ) -> None:
        """セレクタが未設定の場合にソースがスキップされること。"""
        from src.collector.web_scraper import scrape_articles

        sources = [
            {
                "name": "NoSelector",
                "url": "https://example.com/articles/",
                "category": "テスト",
                "selector": {},
            }
        ]

        articles = scrape_articles(sources, request_interval=0)
        assert articles == []
        mock_fetch.assert_not_called()

    @patch("src.collector.web_scraper._check_robots_txt", return_value=False)
    def test_scrape_articles_robots_denied(self, mock_robots: MagicMock) -> None:
        """robots.txt でアクセスが拒否されている場合にスキップされること。"""
        from src.collector.web_scraper import scrape_articles

        sources = [
            {
                "name": "Denied",
                "url": "https://example.com/private/",
                "category": "テスト",
                "selector": {"article_list": "article"},
            }
        ]

        articles = scrape_articles(sources, request_interval=0, respect_robots_txt=True)
        assert articles == []


# ============================================================
# __init__.py (collect_candidates / collect_all) のテスト
# ============================================================


class TestCollectorInit:
    """collector モジュール統合関数のテスト。"""

    @patch("src.collector.rss_collector.collect_from_rss")
    def test_collect_candidates_rss_only(self, mock_rss: MagicMock) -> None:
        """RSS ソースのみの場合に RSS 収集が実行されること。"""
        from src.collector import collect_candidates

        mock_rss.return_value = [
            _make_article(title="RSS Article", source="TestRSS"),
        ]

        config = {
            "collection": {
                "num_stories": 3,
                "sources": [
                    {
                        "name": "TestRSS",
                        "type": "rss",
                        "url": "https://example.com/feed",
                        "enabled": True,
                    },
                ],
            },
        }

        candidates = collect_candidates(config=config)

        assert len(candidates) == 1
        assert candidates[0]["title"] == "RSS Article"
        mock_rss.assert_called_once()

    @patch("src.collector.selector.select_top_articles")
    @patch("src.collector.rss_collector.collect_from_rss")
    def test_collect_all_pipeline(
        self, mock_rss: MagicMock, mock_select: MagicMock
    ) -> None:
        """collect_all が収集 -> 選定のパイプラインを実行すること。"""
        from src.collector import collect_all

        mock_rss.return_value = [
            _make_article(title="A", url="https://a.com"),
            _make_article(title="B", url="https://b.com"),
        ]
        mock_select.return_value = [
            _make_article(title="A", url="https://a.com"),
        ]

        config = {
            "collection": {
                "num_stories": 1,
                "sources": [
                    {
                        "name": "TestRSS",
                        "type": "rss",
                        "url": "https://example.com/feed",
                        "enabled": True,
                    },
                ],
            },
        }

        selected = collect_all(config=config, num_articles=1)

        assert len(selected) == 1
        mock_rss.assert_called_once()
        mock_select.assert_called_once()

    def test_collect_all_empty_config(self) -> None:
        """候補が0件の場合に空リストが返ること。"""
        from src.collector import collect_all

        config = {
            "collection": {
                "num_stories": 3,
                "sources": [],
            },
        }

        result = collect_all(config=config)
        assert result == []
