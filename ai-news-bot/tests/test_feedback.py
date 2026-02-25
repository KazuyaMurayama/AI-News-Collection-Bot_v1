"""feedback / knowledge モジュールのテスト

FastAPI エンドポイント、MD ファイル更新、検索機能をテストする。
"""

import os
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

# テスト対象モジュール
from src.feedback.updater import (
    REACTION_MAP,
    update_reaction,
)
from src.feedback.api_server import create_app
from src.knowledge.search import (
    get_all_articles,
    search_by_tag,
    search_fulltext,
    filter_by_rating,
)


# ============================================================
# テスト用ヘルパー
# ============================================================

_SAMPLE_FRONTMATTER_MD = textwrap.dedent("""\
    ---
    date: "{date}"
    tags:
      - "LLM"
      - "業務効率化"
    stories:
      - id: 1
        title: "Claude 4が登場、驚異的な性能向上"
        source: "TechCrunch"
        url: "https://example.com/article1"
        category: "海外テック"
        tags:
          - "LLM"
          - "Agent"
        rating: null
        reaction: null
        reacted_at: null
      - id: 2
        title: "日本企業のAI活用最前線"
        source: "日経クロステック"
        url: "https://example.com/article2"
        category: "国内テック"
        tags:
          - "業務効率化"
          - "RAG"
        rating: null
        reaction: null
        reacted_at: null
      - id: 3
        title: "画像生成AIで広告クリエイティブ革命"
        source: "VentureBeat"
        url: "https://example.com/article3"
        category: "マーケティング"
        tags:
          - "画像生成"
          - "マーケティング"
        rating: null
        reaction: null
        reacted_at: null
    ---

    # AI News Daily Report - {date}

    ## Story 1: Claude 4が登場、驚異的な性能向上
    テスト本文 Story 1...

    ## Story 2: 日本企業のAI活用最前線
    テスト本文 Story 2...

    ## Story 3: 画像生成AIで広告クリエイティブ革命
    テスト本文 Story 3...
""")


def _create_sample_md(tmp_dir: Path, date: str = "2026-02-25") -> Path:
    """テスト用の日次 Markdown ファイルを作成する。"""
    daily_dir = tmp_dir / "knowledge_base" / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    md_path = daily_dir / f"{date}_ai_news.md"
    content = _SAMPLE_FRONTMATTER_MD.format(date=date)
    md_path.write_text(content, encoding="utf-8")
    return daily_dir


def _create_multiple_sample_mds(tmp_dir: Path) -> Path:
    """複数日のテスト用 Markdown ファイルを作成する。"""
    daily_dir = tmp_dir / "knowledge_base" / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    dates = ["2026-02-20", "2026-02-21", "2026-02-22"]
    for date in dates:
        md_path = daily_dir / f"{date}_ai_news.md"
        content = _SAMPLE_FRONTMATTER_MD.format(date=date)
        md_path.write_text(content, encoding="utf-8")

    # 評価済みの記事を追加
    rated_content = textwrap.dedent("""\
        ---
        date: "2026-02-23"
        tags:
          - "音声AI"
        stories:
          - id: 1
            title: "音声AIの進化が止まらない"
            source: "The Verge"
            url: "https://example.com/voice-ai"
            category: "研究・学術"
            tags:
              - "音声AI"
              - "マルチモーダル"
            rating: 5
            reaction: "excellent"
            reacted_at: "2026-02-23T10:00:00+09:00"
          - id: 2
            title: "金融AI規制の最新動向"
            source: "日経クロステック"
            url: "https://example.com/finance-ai"
            category: "金融"
            tags:
              - "金融"
              - "LLM"
            rating: 4
            reaction: "good"
            reacted_at: "2026-02-23T11:00:00+09:00"
          - id: 3
            title: "教育用AIチューター比較"
            source: "ITmedia"
            url: "https://example.com/edu-ai"
            category: "教育"
            tags:
              - "教育"
              - "LLM"
            rating: 2
            reaction: "meh"
            reacted_at: "2026-02-23T12:00:00+09:00"
        ---

        # AI News Daily Report - 2026-02-23

        ## Story 1: 音声AIの進化が止まらない
        テスト本文...

        ## Story 2: 金融AI規制の最新動向
        テスト本文...

        ## Story 3: 教育用AIチューター比較
        テスト本文...
    """)
    rated_md = daily_dir / "2026-02-23_ai_news.md"
    rated_md.write_text(rated_content, encoding="utf-8")

    return daily_dir


# ============================================================
# updater.py のテスト
# ============================================================

class TestUpdateReaction:
    """update_reaction() 関数のテスト。"""

    def test_update_excellent_reaction(self, tmp_path: Path) -> None:
        """excellent リアクションで rating=5, reaction='excellent' に更新されること。"""
        daily_dir = _create_sample_md(tmp_path)

        result = update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
            daily_dir=daily_dir,
        )

        assert result is True

        # 更新後のファイルを検証
        import frontmatter
        md_path = daily_dir / "2026-02-25_ai_news.md"
        post = frontmatter.load(str(md_path))
        story = post.metadata["stories"][0]
        assert story["reaction"] == "excellent"
        assert story["rating"] == 5
        assert story["reacted_at"] is not None

    def test_update_good_reaction(self, tmp_path: Path) -> None:
        """good リアクションで rating=4 に更新されること。"""
        daily_dir = _create_sample_md(tmp_path)

        result = update_reaction(
            date="2026-02-25",
            story_id=2,
            reaction_type="good",
            daily_dir=daily_dir,
        )

        assert result is True

        import frontmatter
        md_path = daily_dir / "2026-02-25_ai_news.md"
        post = frontmatter.load(str(md_path))
        story = post.metadata["stories"][1]
        assert story["reaction"] == "good"
        assert story["rating"] == 4

    def test_update_bookmark_reaction(self, tmp_path: Path) -> None:
        """bookmark リアクションで rating=3 に更新されること。"""
        daily_dir = _create_sample_md(tmp_path)

        result = update_reaction(
            date="2026-02-25",
            story_id=3,
            reaction_type="bookmark",
            daily_dir=daily_dir,
        )

        assert result is True

        import frontmatter
        md_path = daily_dir / "2026-02-25_ai_news.md"
        post = frontmatter.load(str(md_path))
        story = post.metadata["stories"][2]
        assert story["reaction"] == "bookmark"
        assert story["rating"] == 3

    def test_update_meh_reaction(self, tmp_path: Path) -> None:
        """meh リアクションで rating=2 に更新されること。"""
        daily_dir = _create_sample_md(tmp_path)

        result = update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="meh",
            daily_dir=daily_dir,
        )

        assert result is True

        import frontmatter
        md_path = daily_dir / "2026-02-25_ai_news.md"
        post = frontmatter.load(str(md_path))
        story = post.metadata["stories"][0]
        assert story["reaction"] == "meh"
        assert story["rating"] == 2

    def test_invalid_reaction_type_raises(self, tmp_path: Path) -> None:
        """不正な reaction_type で ValueError が発生すること。"""
        daily_dir = _create_sample_md(tmp_path)

        with pytest.raises(ValueError, match="Invalid reaction type"):
            update_reaction(
                date="2026-02-25",
                story_id=1,
                reaction_type="invalid",
                daily_dir=daily_dir,
            )

    def test_invalid_story_id_raises(self, tmp_path: Path) -> None:
        """不正な story_id で ValueError が発生すること。"""
        daily_dir = _create_sample_md(tmp_path)

        with pytest.raises(ValueError, match="Invalid story_id"):
            update_reaction(
                date="2026-02-25",
                story_id=0,
                reaction_type="excellent",
                daily_dir=daily_dir,
            )

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """対象ファイルが存在しない場合に FileNotFoundError が発生すること。"""
        daily_dir = tmp_path / "empty_dir"
        daily_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(FileNotFoundError, match="Article not found"):
            update_reaction(
                date="2099-12-31",
                story_id=1,
                reaction_type="excellent",
                daily_dir=daily_dir,
            )

    def test_nonexistent_story_id_returns_false(self, tmp_path: Path) -> None:
        """Frontmatter 内に存在しない story_id の場合 False が返ること。"""
        daily_dir = _create_sample_md(tmp_path)

        # story_id=3 は存在するが、ファイル内の stories から id=4 は見つからない
        # ただし story_id のバリデーションは 1-3 の範囲なので、
        # ここでは stories の中身を改変してテスト
        md_path = daily_dir / "2026-02-25_ai_news.md"
        import frontmatter
        post = frontmatter.load(str(md_path))
        # 全 story の id を 10, 20, 30 に変更
        for story in post.metadata["stories"]:
            story["id"] = story["id"] + 100
        frontmatter.dump(post, str(md_path))

        result = update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
            daily_dir=daily_dir,
        )

        assert result is False


# ============================================================
# api_server.py のテスト (FastAPI)
# ============================================================

class TestFastAPIEndpoints:
    """FastAPI エンドポイントのテスト。"""

    @pytest.fixture
    def client(self):
        """テスト用の httpx AsyncClient を生成する。"""
        from httpx import AsyncClient, ASGITransport
        app = create_app()
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_check(self, client) -> None:
        """GET /health が正常にレスポンスを返すこと。"""
        async with client as c:
            response = await c.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_react_success(self, tmp_path: Path, client) -> None:
        """GET /react が正常にリアクションを更新し HTML を返すこと。"""
        daily_dir = _create_sample_md(tmp_path)

        with patch(
            "src.feedback.api_server.update_reaction",
            return_value=True,
        ) as mock_update:
            async with client as c:
                response = await c.get(
                    "/react",
                    params={
                        "date": "2026-02-25",
                        "story": 1,
                        "reaction": "excellent",
                    },
                )

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "フィードバックありがとうございます" in response.text
            mock_update.assert_called_once_with(
                date="2026-02-25",
                story_id=1,
                reaction_type="excellent",
            )

    @pytest.mark.asyncio
    async def test_react_invalid_reaction(self, client) -> None:
        """不正な reaction パラメータで 400 エラーが返ること。"""
        async with client as c:
            response = await c.get(
                "/react",
                params={
                    "date": "2026-02-25",
                    "story": 1,
                    "reaction": "invalid_type",
                },
            )

        assert response.status_code == 400
        assert "Invalid parameter" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_react_invalid_story_range(self, client) -> None:
        """story パラメータが範囲外で 422 エラーが返ること。"""
        async with client as c:
            response = await c.get(
                "/react",
                params={
                    "date": "2026-02-25",
                    "story": 5,
                    "reaction": "excellent",
                },
            )

        # FastAPI のバリデーションエラーは 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_react_file_not_found(self, client) -> None:
        """対象ファイルが存在しない場合に 404 エラーが返ること。"""
        with patch(
            "src.feedback.api_server.update_reaction",
            side_effect=FileNotFoundError("Article not found"),
        ):
            async with client as c:
                response = await c.get(
                    "/react",
                    params={
                        "date": "2099-12-31",
                        "story": 1,
                        "reaction": "excellent",
                    },
                )

        assert response.status_code == 404
        assert "Article not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_react_update_failure(self, client) -> None:
        """更新処理が False を返した場合に 500 エラーが返ること。"""
        with patch(
            "src.feedback.api_server.update_reaction",
            return_value=False,
        ):
            async with client as c:
                response = await c.get(
                    "/react",
                    params={
                        "date": "2026-02-25",
                        "story": 1,
                        "reaction": "good",
                    },
                )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_stats_empty(self, client) -> None:
        """記事が存在しない場合に空の統計が返ること。"""
        with patch(
            "src.knowledge.search.get_all_articles",
            return_value=[],
        ):
            async with client as c:
                response = await c.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_articles"] == 0
        assert data["total_reactions"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_articles(self, client) -> None:
        """記事データがある場合に正しい統計が返ること。"""
        mock_articles = [
            {
                "date": "2026-02-25",
                "title": "Article 1",
                "tags": ["LLM", "Agent"],
                "rating": 5,
                "reaction": "excellent",
            },
            {
                "date": "2026-02-25",
                "title": "Article 2",
                "tags": ["LLM", "RAG"],
                "rating": 4,
                "reaction": "good",
            },
            {
                "date": "2026-02-24",
                "title": "Article 3",
                "tags": ["画像生成"],
                "rating": None,
                "reaction": None,
            },
        ]

        with patch(
            "src.knowledge.search.get_all_articles",
            return_value=mock_articles,
        ):
            async with client as c:
                response = await c.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_articles"] == 3
        assert data["total_reactions"] == 2
        assert data["reaction_breakdown"]["excellent"] == 1
        assert data["reaction_breakdown"]["good"] == 1
        assert data["average_rating"] == 4.5
        assert data["date_range"]["from"] == "2026-02-24"
        assert data["date_range"]["to"] == "2026-02-25"
        # LLM が最も多いタグ
        assert data["top_tags"][0]["tag"] == "LLM"
        assert data["top_tags"][0]["count"] == 2


# ============================================================
# search.py のテスト
# ============================================================

class TestKnowledgeSearch:
    """search.py の各検索関数のテスト。"""

    def test_get_all_articles(self, tmp_path: Path) -> None:
        """全記事メタデータが取得できること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        articles = get_all_articles(daily_dir=daily_dir)

        # 4日分 x 3ストーリー = 12記事
        assert len(articles) == 12

    def test_get_all_articles_empty_dir(self, tmp_path: Path) -> None:
        """空のディレクトリで空リストが返ること。"""
        daily_dir = tmp_path / "empty_daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        articles = get_all_articles(daily_dir=daily_dir)
        assert articles == []

    def test_get_all_articles_nonexistent_dir(self, tmp_path: Path) -> None:
        """存在しないディレクトリで空リストが返ること。"""
        daily_dir = tmp_path / "nonexistent"
        articles = get_all_articles(daily_dir=daily_dir)
        assert articles == []

    def test_search_by_tag(self, tmp_path: Path) -> None:
        """タグ検索で該当記事が返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = search_by_tag("音声AI", daily_dir=daily_dir)

        # 2026-02-23 の story 1 が "音声AI" タグを持つ
        assert len(results) >= 1
        assert any("音声AI" in r.get("tags", []) for r in results)

    def test_search_by_tag_no_match(self, tmp_path: Path) -> None:
        """存在しないタグで空リストが返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = search_by_tag("存在しないタグ", daily_dir=daily_dir)
        assert results == []

    def test_search_fulltext(self, tmp_path: Path) -> None:
        """全文検索でタイトルに一致する記事が返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = search_fulltext("Claude", daily_dir=daily_dir)

        # "Claude 4が登場" がタイトルに含まれる記事が少なくとも3件
        # （本文にも "Claude" が含まれる場合があるため、タイトル一致のみに限定しない）
        assert len(results) >= 3
        # タイトルに "Claude" を含む記事が存在すること
        title_matches = [r for r in results if "Claude" in r.get("title", "")]
        assert len(title_matches) >= 3

    def test_search_fulltext_body(self, tmp_path: Path) -> None:
        """全文検索で本文テキストに一致する記事が返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = search_fulltext("テスト本文", daily_dir=daily_dir)

        # 全記事の本文に "テスト本文" が含まれる
        assert len(results) >= 1

    def test_search_fulltext_case_insensitive(self, tmp_path: Path) -> None:
        """全文検索が大文字小文字を区別しないこと。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results_lower = search_fulltext("claude", daily_dir=daily_dir)
        results_upper = search_fulltext("CLAUDE", daily_dir=daily_dir)

        assert len(results_lower) == len(results_upper)

    def test_search_fulltext_invalid_regex(self, tmp_path: Path) -> None:
        """不正な正規表現で空リストが返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = search_fulltext("[invalid(regex", daily_dir=daily_dir)
        assert results == []

    def test_filter_by_rating(self, tmp_path: Path) -> None:
        """高評価フィルタで rating >= 4 の記事が返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = filter_by_rating(min_rating=4, daily_dir=daily_dir)

        # 2026-02-23 の story 1 (rating=5) と story 2 (rating=4)
        assert len(results) == 2
        assert all(r.get("rating", 0) >= 4 for r in results)
        # rating の降順ソート
        assert results[0]["rating"] >= results[1]["rating"]

    def test_filter_by_rating_min5(self, tmp_path: Path) -> None:
        """rating >= 5 でフィルタすると最高評価のみが返ること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        results = filter_by_rating(min_rating=5, daily_dir=daily_dir)

        assert len(results) == 1
        assert results[0]["rating"] == 5
        assert results[0]["title"] == "音声AIの進化が止まらない"

    def test_filter_by_rating_no_match(self, tmp_path: Path) -> None:
        """評価のない記事のみの場合に空リストが返ること。"""
        daily_dir = _create_sample_md(tmp_path)

        results = filter_by_rating(min_rating=4, daily_dir=daily_dir)
        assert results == []

    def test_articles_have_date(self, tmp_path: Path) -> None:
        """全記事に date フィールドが含まれること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        articles = get_all_articles(daily_dir=daily_dir)

        for article in articles:
            assert "date" in article
            assert article["date"] is not None

    def test_articles_have_file_path(self, tmp_path: Path) -> None:
        """全記事に file_path フィールドが含まれること。"""
        daily_dir = _create_multiple_sample_mds(tmp_path)

        articles = get_all_articles(daily_dir=daily_dir)

        for article in articles:
            assert "file_path" in article
            assert article["file_path"].endswith("_ai_news.md")
