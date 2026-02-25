"""writer モジュールのテスト

storyteller.py のフレームワーク選択ロジックと、
markdown_gen.py の Markdown 生成・Frontmatter 構造を検証する。
"""

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import frontmatter
import pytest
import yaml

# テスト対象モジュール
from src.writer.storyteller import (
    FRAMEWORKS,
    _classify_by_keywords,
    select_framework,
    transform_to_story,
    generate_insight,
)
from src.writer.markdown_gen import (
    _build_frontmatter_metadata,
    _render_body_fallback,
    generate_daily_markdown,
    save_markdown,
)


# ============================================================
# テスト用ヘルパー・フィクスチャ
# ============================================================

def _make_article(
    title: str = "テスト記事",
    summary: str = "テスト要約",
    source: str = "TestSource",
    url: str = "https://example.com/article",
    published_at: str = "2026-02-25",
) -> dict[str, Any]:
    """テスト用の記事辞書を生成する。"""
    return {
        "title": title,
        "summary": summary,
        "source": source,
        "url": url,
        "published_at": published_at,
    }


def _make_story(
    story_id: int = 1,
    title: str = "テストストーリー",
    source: str = "TestSource",
    url: str = "https://example.com/article",
    category: str = "業務効率化",
    tags: list[str] | None = None,
    rating: int | None = None,
    reaction: str | None = None,
    body: str = "ストーリー本文です。",
) -> dict[str, Any]:
    """テスト用のストーリー辞書を生成する。"""
    return {
        "id": story_id,
        "title": title,
        "source": source,
        "url": url,
        "category": category,
        "tags": tags if tags is not None else ["AI", "テスト"],
        "rating": rating,
        "reaction": reaction,
        "body": body,
    }


def _make_story_for_insight(
    title: str = "テストストーリー",
    story: str = "本文テキスト",
    source: str = "TestSource",
    category: str = "業務効率化",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """generate_insight 用のストーリー辞書を生成する。"""
    return {
        "title": title,
        "story": story,
        "source": source,
        "category": category,
        "tags": tags if tags is not None else ["AI"],
    }


def _mock_claude_response(text: str) -> MagicMock:
    """Claude API レスポンスのモックを生成する。"""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


# ============================================================
# storyteller.py - フレームワーク選択ロジックのテスト
# ============================================================

class TestClassifyByKeywords:
    """_classify_by_keywords() 関数のテスト。"""

    def test_enterprise_adoption_selects_star(self) -> None:
        """企業導入事例の記事に対して STAR が選択されること。"""
        article = _make_article(
            title="大手企業がAIを導入、業務効率が大幅に向上",
            summary="企業の採用事例として、AI活用で成果を上げた実績を紹介",
        )
        result = _classify_by_keywords(article)
        assert result == "STAR"

    def test_tech_innovation_selects_heros_journey(self) -> None:
        """技術革新系の記事に対してヒーローズジャーニーが選択されること。"""
        article = _make_article(
            title="画期的な新モデルが発表、ブレイクスルーを達成",
            summary="研究チームが革新的な新技術を論文で発表した",
        )
        result = _classify_by_keywords(article)
        assert result == "ヒーローズジャーニー"

    def test_business_improvement_selects_before_after_bridge(self) -> None:
        """業務改善系の記事に対して Before/After/Bridge が選択されること。"""
        article = _make_article(
            title="AIによる業務効率化でコスト削減を実現",
            summary="ワークフローの自動化により業務の最適化に成功",
        )
        result = _classify_by_keywords(article)
        assert result == "Before/After/Bridge"

    def test_problem_solving_selects_pas(self) -> None:
        """課題解決系の記事に対して PAS が選択されること。"""
        article = _make_article(
            title="AIのセキュリティリスクと規制の課題",
            summary="プライバシーの懸念に対する解決策とガバナンス対応",
        )
        result = _classify_by_keywords(article)
        assert result == "PAS"

    def test_ambiguous_article_returns_none(self) -> None:
        """キーワードにマッチしない記事に対して None が返ること。"""
        article = _make_article(
            title="天気予報",
            summary="明日の天気は晴れです。",
        )
        result = _classify_by_keywords(article)
        assert result is None

    def test_empty_article_returns_none(self) -> None:
        """空の記事に対して None が返ること。"""
        article = _make_article(title="", summary="")
        result = _classify_by_keywords(article)
        assert result is None

    def test_english_keywords_match(self) -> None:
        """英語キーワードでもマッチすること。"""
        article = _make_article(
            title="New breakthrough in AI research",
            summary="A novel open source LLM paper was released",
        )
        result = _classify_by_keywords(article)
        assert result == "ヒーローズジャーニー"

    def test_highest_score_wins(self) -> None:
        """複数フレームワークにマッチする場合、最高スコアが選択されること。"""
        article = _make_article(
            title="企業が導入した革新的AIの採用事例と成果・実績",
            summary="活用事例の実装で大きな成果。運用開始後に企業が成功。",
        )
        # STAR キーワードが圧倒的に多い
        result = _classify_by_keywords(article)
        assert result == "STAR"


class TestSelectFramework:
    """select_framework() 関数のテスト。"""

    def test_keyword_match_without_api_call(self) -> None:
        """キーワードマッチで決定できる場合は API を呼ばないこと。"""
        article = _make_article(
            title="企業がAI導入で成果を達成",
            summary="企業の採用事例として大きな実績",
        )

        with patch("src.writer.storyteller._get_claude_client") as mock_client:
            result = select_framework(article)
            mock_client.assert_not_called()

        assert result == "STAR"

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_api_fallback_for_ambiguous_article(
        self, mock_config: MagicMock, mock_client_factory: MagicMock
    ) -> None:
        """キーワードで判定できない場合に Claude API にフォールバックすること。"""
        article = _make_article(
            title="天気予報アプリの紹介",
            summary="便利なアプリの使い方",
        )

        mock_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.messages.create.return_value = _mock_claude_response(
            json.dumps({"framework": "PAS", "reason": "課題提起型のため"})
        )

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = select_framework(article)

        assert result == "PAS"
        mock_client.messages.create.assert_called_once()

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_api_invalid_json_fallback(
        self, mock_config: MagicMock, mock_client_factory: MagicMock
    ) -> None:
        """API が不正な JSON を返した場合にテキストマッチでフォールバックすること。"""
        article = _make_article(title="不明な記事", summary="")

        mock_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.messages.create.return_value = _mock_claude_response(
            "この記事にはBefore/After/Bridgeが最適です。"
        )

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = select_framework(article)

        assert result == "Before/After/Bridge"

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_api_unknown_framework_defaults(
        self, mock_config: MagicMock, mock_client_factory: MagicMock
    ) -> None:
        """API が未知のフレームワーク名を返した場合にデフォルトに変更されること。"""
        article = _make_article(title="不明な記事", summary="")

        mock_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.messages.create.return_value = _mock_claude_response(
            json.dumps({"framework": "UNKNOWN_FRAMEWORK", "reason": "テスト"})
        )

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = select_framework(article)

        assert result == "ヒーローズジャーニー"


class TestTransformToStory:
    """transform_to_story() 関数のテスト。"""

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_transform_with_explicit_framework(
        self, mock_config: MagicMock, mock_client_factory: MagicMock
    ) -> None:
        """明示的なフレームワーク指定でストーリーが生成されること。"""
        article = _make_article(
            title="AIで業務が変わる",
            summary="新しいAIツールの紹介",
        )

        mock_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        expected_story = "AIはどのように業務を変革するのか？\n\n本文テキスト..."
        mock_client.messages.create.return_value = _mock_claude_response(expected_story)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = transform_to_story(article, framework="STAR")

        assert result == expected_story
        # フレームワーク選択の API 呼び出しは行われない
        assert mock_client.messages.create.call_count == 1

    @patch("src.writer.storyteller.select_framework")
    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_transform_with_auto_framework_selection(
        self,
        mock_config: MagicMock,
        mock_client_factory: MagicMock,
        mock_select: MagicMock,
    ) -> None:
        """フレームワーク未指定の場合に自動選択されること。"""
        article = _make_article(title="テスト記事", summary="テスト")

        mock_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        mock_select.return_value = "PAS"

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        mock_client.messages.create.return_value = _mock_claude_response("生成されたストーリー")

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = transform_to_story(article)

        mock_select.assert_called_once_with(article)
        assert result == "生成されたストーリー"


class TestGenerateInsight:
    """generate_insight() 関数のテスト。"""

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_generate_insight_with_stories(
        self, mock_config: MagicMock, mock_client_factory: MagicMock
    ) -> None:
        """ストーリーリストからインサイトが生成されること。"""
        stories = [
            _make_story_for_insight(title=f"記事{i}", story=f"本文{i}")
            for i in range(1, 4)
        ]

        mock_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client
        expected_insight = "今日の3記事に共通するテーマはAI活用の拡大です。"
        mock_client.messages.create.return_value = _mock_claude_response(expected_insight)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            result = generate_insight(stories)

        assert result == expected_insight
        mock_client.messages.create.assert_called_once()

    def test_generate_insight_empty_stories(self) -> None:
        """ストーリーが空の場合にデフォルトメッセージが返ること。"""
        result = generate_insight([])
        assert "生成できませんでした" in result


# ============================================================
# markdown_gen.py - Markdown 生成のテスト
# ============================================================

class TestBuildFrontmatterMetadata:
    """_build_frontmatter_metadata() 関数のテスト。"""

    def test_metadata_structure(self) -> None:
        """メタデータに必要なキーが含まれること。"""
        stories = [_make_story(story_id=1), _make_story(story_id=2)]
        metadata = _build_frontmatter_metadata("2026-02-25", stories)

        assert "date" in metadata
        assert "tags" in metadata
        assert "stories" in metadata
        assert metadata["date"] == "2026-02-25"
        assert len(metadata["stories"]) == 2

    def test_tags_aggregated_and_deduplicated(self) -> None:
        """タグが全ストーリーから集約され、重複排除されること。"""
        stories = [
            _make_story(story_id=1, tags=["AI", "DX"]),
            _make_story(story_id=2, tags=["AI", "クラウド"]),
            _make_story(story_id=3, tags=["DX", "セキュリティ"]),
        ]
        metadata = _build_frontmatter_metadata("2026-02-25", stories)

        assert metadata["tags"] == ["AI", "DX", "クラウド", "セキュリティ"]

    def test_story_meta_fields(self) -> None:
        """各ストーリーのメタデータに必要なフィールドが含まれること。"""
        stories = [
            _make_story(
                story_id=1,
                title="テスト記事",
                source="TechCrunch",
                url="https://example.com",
                category="業務効率化",
                tags=["AI"],
                rating=None,
                reaction=None,
            )
        ]
        metadata = _build_frontmatter_metadata("2026-02-25", stories)
        story_meta = metadata["stories"][0]

        assert story_meta["id"] == 1
        assert story_meta["title"] == "テスト記事"
        assert story_meta["source"] == "TechCrunch"
        assert story_meta["source_url"] == "https://example.com"
        assert "framework" in story_meta
        assert story_meta["tags"] == ["AI"]
        assert story_meta["reactions"] == {"excellent": 0, "good": 0, "so_so": 0, "read_later": 0}

    def test_empty_stories_list(self) -> None:
        """ストーリーが空の場合でもメタデータが生成されること。"""
        metadata = _build_frontmatter_metadata("2026-02-25", [])

        assert metadata["date"] == "2026-02-25"
        assert metadata["tags"] == []
        assert metadata["stories"] == []


class TestRenderBodyFallback:
    """_render_body_fallback() 関数のテスト。"""

    def test_body_contains_heading(self) -> None:
        """本文に日付入りの見出しが含まれること。"""
        stories = [_make_story()]
        body = _render_body_fallback("2026-02-25", stories, "インサイト")

        assert "# AI News - 2026-02-25" in body

    def test_body_contains_stories(self) -> None:
        """本文に各ストーリーのセクションが含まれること。"""
        stories = [
            _make_story(story_id=1, title="記事A", body="本文A"),
            _make_story(story_id=2, title="記事B", body="本文B"),
        ]
        body = _render_body_fallback("2026-02-25", stories, "インサイト")

        assert "## Story 1: 記事A" in body
        assert "## Story 2: 記事B" in body
        assert "本文A" in body
        assert "本文B" in body

    def test_body_contains_source_link(self) -> None:
        """本文にソースリンクが含まれること。"""
        stories = [
            _make_story(source="TechCrunch", url="https://example.com/art")
        ]
        body = _render_body_fallback("2026-02-25", stories, "インサイト")

        assert "[TechCrunch](https://example.com/art)" in body

    def test_body_contains_insight(self) -> None:
        """本文に Today's Insight セクションが含まれること。"""
        body = _render_body_fallback("2026-02-25", [], "これは重要なインサイトです。")

        assert "## Today's Insight" in body
        assert "これは重要なインサイトです。" in body


class TestGenerateDailyMarkdown:
    """generate_daily_markdown() 関数のテスト。"""

    def test_output_contains_frontmatter(self) -> None:
        """出力に YAML Frontmatter が含まれること。"""
        stories = [_make_story(story_id=1)]
        result = generate_daily_markdown("2026-02-25", stories, "テストインサイト")

        assert result.startswith("---")
        # Frontmatter の終了マーカーが2回目に出現する
        parts = result.split("---", 2)
        assert len(parts) >= 3  # 先頭空文字、frontmatter、本文

    def test_frontmatter_parseable(self) -> None:
        """Frontmatter が python-frontmatter で正常にパースできること。"""
        stories = [
            _make_story(story_id=1, title="記事1", tags=["AI"]),
            _make_story(story_id=2, title="記事2", tags=["DX"]),
        ]
        result = generate_daily_markdown("2026-02-25", stories, "インサイト")

        post = frontmatter.loads(result)

        assert post.metadata["date"] == "2026-02-25"
        assert isinstance(post.metadata["tags"], list)
        assert isinstance(post.metadata["stories"], list)
        assert len(post.metadata["stories"]) == 2

    def test_frontmatter_story_structure(self) -> None:
        """Frontmatter 内のストーリーメタデータが正しい構造であること。"""
        stories = [
            _make_story(
                story_id=1,
                title="AIニュース",
                source="TechCrunch",
                url="https://example.com/1",
                category="業務効率化",
                tags=["AI", "自動化"],
                rating=None,
                reaction=None,
            ),
        ]
        result = generate_daily_markdown("2026-02-25", stories, "インサイト")

        post = frontmatter.loads(result)
        story_meta = post.metadata["stories"][0]

        assert story_meta["id"] == 1
        assert story_meta["title"] == "AIニュース"
        assert story_meta["source"] == "TechCrunch"
        assert story_meta["source_url"] == "https://example.com/1"
        assert "framework" in story_meta
        assert story_meta["tags"] == ["AI", "自動化"]
        assert story_meta["reactions"] == {"excellent": 0, "good": 0, "so_so": 0, "read_later": 0}

    def test_body_contains_all_sections(self) -> None:
        """Markdown 本文に全セクションが含まれること。"""
        stories = [
            _make_story(story_id=1, title="記事A", body="本文A"),
            _make_story(story_id=2, title="記事B", body="本文B"),
            _make_story(story_id=3, title="記事C", body="本文C"),
        ]
        result = generate_daily_markdown("2026-02-25", stories, "共通インサイト")

        post = frontmatter.loads(result)
        body = post.content

        assert "## Story 1: 記事A" in body
        assert "## Story 2: 記事B" in body
        assert "## Story 3: 記事C" in body
        assert "## Today's Insight" in body
        assert "共通インサイト" in body

    def test_tags_aggregated_in_frontmatter(self) -> None:
        """Frontmatter の tags に全ストーリーのタグが集約されること。"""
        stories = [
            _make_story(story_id=1, tags=["AI", "DX"]),
            _make_story(story_id=2, tags=["AI", "セキュリティ"]),
        ]
        result = generate_daily_markdown("2026-02-25", stories, "インサイト")

        post = frontmatter.loads(result)
        tags = post.metadata["tags"]

        assert "AI" in tags
        assert "DX" in tags
        assert "セキュリティ" in tags
        # 重複排除されている
        assert tags.count("AI") == 1

    def test_empty_stories(self) -> None:
        """ストーリーが空の場合でも Markdown が生成されること。"""
        result = generate_daily_markdown("2026-02-25", [], "空のインサイト")

        post = frontmatter.loads(result)
        assert post.metadata["date"] == "2026-02-25"
        assert post.metadata["stories"] == []
        assert "空のインサイト" in post.content


class TestSaveMarkdown:
    """save_markdown() 関数のテスト。"""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """ファイルが正常に作成されること。"""
        filepath = tmp_path / "test_output.md"
        content = "# テスト\n\nテスト本文"

        save_markdown(content, str(filepath))

        assert filepath.exists()
        assert filepath.read_text(encoding="utf-8") == content

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        """親ディレクトリが存在しない場合に自動作成されること。"""
        filepath = tmp_path / "nested" / "deep" / "output.md"
        content = "# テスト"

        save_markdown(content, str(filepath))

        assert filepath.exists()
        assert filepath.read_text(encoding="utf-8") == content

    def test_save_overwrites_existing_file(self, tmp_path: Path) -> None:
        """既存ファイルが上書きされること。"""
        filepath = tmp_path / "existing.md"
        filepath.write_text("古い内容", encoding="utf-8")

        new_content = "新しい内容"
        save_markdown(new_content, str(filepath))

        assert filepath.read_text(encoding="utf-8") == new_content

    def test_save_utf8_content(self, tmp_path: Path) -> None:
        """日本語コンテンツが正しく保存されること。"""
        filepath = tmp_path / "japanese.md"
        content = "# AI ニュース\n\nストーリーテリング形式の解説記事"

        save_markdown(content, str(filepath))

        saved = filepath.read_text(encoding="utf-8")
        assert "AI ニュース" in saved
        assert "ストーリーテリング形式" in saved


# ============================================================
# 統合テスト
# ============================================================

class TestMarkdownIntegration:
    """Markdown 生成の統合テスト。"""

    def test_full_pipeline_roundtrip(self, tmp_path: Path) -> None:
        """生成 -> 保存 -> 読み込みの一連のフローが正常に動作すること。"""
        stories = [
            _make_story(
                story_id=i,
                title=f"AI記事{i}",
                source=f"Source{i}",
                url=f"https://example.com/{i}",
                category="業務効率化" if i % 2 == 0 else "技術革新",
                tags=[f"tag{i}", "共通タグ"],
                body=f"これは記事{i}のストーリー本文です。",
            )
            for i in range(1, 4)
        ]
        insight = "今日の3記事から見える共通トレンドです。"

        # 生成
        markdown = generate_daily_markdown("2026-02-25", stories, insight)

        # 保存
        filepath = tmp_path / "2026-02-25_ai_news.md"
        save_markdown(markdown, str(filepath))

        # 読み込み・検証
        loaded = frontmatter.load(str(filepath))

        assert loaded.metadata["date"] == "2026-02-25"
        assert len(loaded.metadata["stories"]) == 3
        assert "共通タグ" in loaded.metadata["tags"]
        assert "tag1" in loaded.metadata["tags"]

        for i in range(3):
            story_meta = loaded.metadata["stories"][i]
            assert story_meta["id"] == i + 1
            assert story_meta["title"] == f"AI記事{i + 1}"

        assert "## Story 1: AI記事1" in loaded.content
        assert "## Today's Insight" in loaded.content
        assert insight in loaded.content


class TestFrameworkConstants:
    """FRAMEWORKS 定数のテスト。"""

    def test_all_frameworks_defined(self) -> None:
        """全フレームワークが定義されていること。"""
        expected = {"STAR", "ヒーローズジャーニー", "Before/After/Bridge", "PAS"}
        assert set(FRAMEWORKS.keys()) == expected

    def test_framework_descriptions_not_empty(self) -> None:
        """各フレームワークの説明が空でないこと。"""
        for name, desc in FRAMEWORKS.items():
            assert desc, f"フレームワーク '{name}' の説明が空です"
