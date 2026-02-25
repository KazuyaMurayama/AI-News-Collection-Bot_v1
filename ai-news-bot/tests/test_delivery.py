"""delivery モジュールのテスト

html_converter, line_sender の各機能をテストする。
Gmail 送信はモック化して認証不要でテストする。
"""

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# テスト対象モジュール
from src.delivery.html_converter import (
    REACTIONS,
    apply_email_template,
    generate_reaction_url,
    markdown_to_html,
    _prepare_story_context,
)
from src.delivery.line_sender import (
    _LINE_MESSAGE_LIMIT,
    _extract_summary,
    format_for_line,
)


# ============================================================
# テスト用ヘルパー
# ============================================================

def _sample_stories() -> list[dict]:
    """テスト用のサンプルストーリーリストを返す。"""
    return [
        {
            "id": 1,
            "title": "AIが医療を革新する新技術",
            "body": "**Google DeepMind** は新しいAI診断ツールを発表しました。\n\nこのツールは画像診断の精度を大幅に向上させます。",
            "source": "TechCrunch",
            "url": "https://techcrunch.com/example-1",
            "category": "ヘルスケア",
            "tags": ["AI", "医療", "ヘルスケア"],
        },
        {
            "id": 2,
            "title": "LLMの新しいベンチマーク",
            "body": "# 新ベンチマーク\n\n大規模言語モデルの性能を測る新しいベンチマークが登場。\n\n- 推論能力\n- コード生成\n- 多言語対応",
            "source": "arXiv",
            "url": "https://arxiv.org/example-2",
            "category": "研究・学術",
            "tags": ["LLM", "ベンチマーク"],
        },
        {
            "id": 3,
            "title": "日本企業のAI活用最前線",
            "body": "日本の製造業でAI活用が加速しています。特に品質管理分野での導入が進んでいます。",
            "source": "日経クロステック",
            "url": "https://xtech.nikkei.com/example-3",
            "category": "製造",
            "tags": ["日本", "製造", "AI活用"],
        },
    ]


# ============================================================
# html_converter テスト
# ============================================================

class TestMarkdownToHtml:
    """markdown_to_html 関数のテスト"""

    def test_basic_conversion(self):
        """基本的な Markdown -> HTML 変換"""
        md = "# タイトル\n\nこれはテストです。"
        html = markdown_to_html(md)
        assert "<h1" in html  # toc 拡張により id 属性が付く
        assert "タイトル" in html
        assert "これはテストです" in html

    def test_empty_input(self):
        """空文字列の入力"""
        assert markdown_to_html("") == ""

    def test_bold_and_italic(self):
        """強調テキストの変換"""
        md = "**太字** と *イタリック*"
        html = markdown_to_html(md)
        assert "<strong>" in html or "<b>" in html
        assert "<em>" in html or "<i>" in html

    def test_links(self):
        """リンクの変換"""
        md = "[Google](https://www.google.com)"
        html = markdown_to_html(md)
        assert 'href="https://www.google.com"' in html
        assert "Google" in html

    def test_lists(self):
        """リストの変換"""
        md = "- item1\n- item2\n- item3"
        html = markdown_to_html(md)
        assert "<li>" in html
        assert "item1" in html

    def test_code_block(self):
        """コードブロックの変換"""
        md = "```python\nprint('hello')\n```"
        html = markdown_to_html(md)
        assert "print" in html
        # fenced_code 拡張が有効であることを確認
        assert "<code" in html or "<pre" in html

    def test_table(self):
        """テーブルの変換"""
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = markdown_to_html(md)
        assert "<table>" in html
        assert "<td>" in html

    def test_newlines_preserved(self):
        """改行が保持されること（nl2br 拡張）"""
        md = "1行目\n2行目"
        html = markdown_to_html(md)
        assert "<br" in html


class TestGenerateReactionUrl:
    """generate_reaction_url 関数のテスト"""

    def test_basic_url(self):
        """基本的なリアクション URL 生成"""
        url = generate_reaction_url(
            base_url="http://localhost:8080",
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
        )
        assert url == "http://localhost:8080/react?date=2026-02-25&story=1&reaction=excellent"

    def test_all_reaction_types(self):
        """全リアクション種別の URL 生成"""
        reaction_types = ["excellent", "good", "meh", "bookmark"]
        for rtype in reaction_types:
            url = generate_reaction_url(
                base_url="http://localhost:8080",
                date="2026-02-25",
                story_id=2,
                reaction_type=rtype,
            )
            assert f"reaction={rtype}" in url
            assert "story=2" in url

    def test_custom_base_url(self):
        """カスタムベース URL"""
        url = generate_reaction_url(
            base_url="https://my-server.example.com",
            date="2026-01-01",
            story_id=3,
            reaction_type="good",
        )
        assert url.startswith("https://my-server.example.com/react?")

    def test_story_id_range(self):
        """ストーリー ID の範囲"""
        for story_id in [1, 2, 3]:
            url = generate_reaction_url(
                base_url="http://localhost:8080",
                date="2026-02-25",
                story_id=story_id,
                reaction_type="excellent",
            )
            assert f"story={story_id}" in url


class TestPrepareStoryContext:
    """_prepare_story_context 関数のテスト"""

    def test_basic_context(self):
        """基本的なストーリーコンテキスト生成"""
        story = _sample_stories()[0]
        ctx = _prepare_story_context(
            story=story,
            date="2026-02-25",
            base_url="http://localhost:8080",
        )
        assert ctx["id"] == 1
        assert ctx["title"] == "AIが医療を革新する新技術"
        assert ctx["source"] == "TechCrunch"
        assert ctx["url"] == "https://techcrunch.com/example-1"
        assert ctx["category"] == "ヘルスケア"
        assert len(ctx["tags"]) == 3
        # HTML に変換されていること
        assert "<strong>" in ctx["html_body"] or "Google DeepMind" in ctx["html_body"]
        # リアクション情報が含まれること
        assert len(ctx["reactions"]) == 4

    def test_reaction_urls_in_context(self):
        """コンテキストに正しいリアクション URL が含まれること"""
        story = _sample_stories()[0]
        ctx = _prepare_story_context(
            story=story,
            date="2026-02-25",
            base_url="http://localhost:8080",
        )
        reaction_types = [r["type"] for r in ctx["reactions"]]
        assert reaction_types == ["excellent", "good", "meh", "bookmark"]

        for reaction in ctx["reactions"]:
            assert "http://localhost:8080/react?" in reaction["url"]
            assert "date=2026-02-25" in reaction["url"]
            assert "story=1" in reaction["url"]


class TestApplyEmailTemplate:
    """apply_email_template 関数のテスト"""

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_basic_template_rendering(self, mock_base_url):
        """基本的なテンプレートレンダリング"""
        stories = _sample_stories()
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
            insight="今日のAIニュースでは医療とLLMが注目されています。",
        )
        # HTML として有効であること
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        # 日付が含まれること
        assert "2026-02-25" in html
        # 各ストーリーのタイトルが含まれること
        for story in stories:
            assert story["title"] in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_reaction_buttons_present(self, mock_base_url):
        """リアクションボタンが含まれること"""
        stories = _sample_stories()[:1]
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
        )
        # リアクションリンクが含まれていること
        assert "reaction=excellent" in html
        assert "reaction=good" in html
        assert "reaction=meh" in html
        assert "reaction=bookmark" in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_responsive_meta_tags(self, mock_base_url):
        """レスポンシブデザイン用のメタタグが含まれること"""
        stories = _sample_stories()[:1]
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
        )
        assert "viewport" in html
        assert "width=device-width" in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_dark_mode_support(self, mock_base_url):
        """ダークモード対応 CSS が含まれること"""
        stories = _sample_stories()[:1]
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
        )
        assert "prefers-color-scheme: dark" in html
        assert "color-scheme" in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_insight_section(self, mock_base_url):
        """Today's Insight セクションが表示されること"""
        stories = _sample_stories()[:1]
        insight_text = "AIの医療分野への応用が加速しています。"
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
            insight=insight_text,
        )
        assert "Today&#39;s Insight" in html or "Today's Insight" in html or "Insight" in html
        assert "医療分野" in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_no_insight_when_none(self, mock_base_url):
        """insight が None の場合はセクションが表示されないこと"""
        stories = _sample_stories()[:1]
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
            insight=None,
        )
        # Insight セクションのタイトルが無いことを確認
        # (テンプレートの {% if insight %} で非表示)
        assert "Today&#39;s Insight" not in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_source_links(self, mock_base_url):
        """元記事リンクが含まれること"""
        stories = _sample_stories()[:1]
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
        )
        assert "https://techcrunch.com/example-1" in html

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_empty_stories(self, mock_base_url):
        """空のストーリーリストでもエラーにならないこと"""
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=[],
            base_url="http://localhost:8080",
        )
        assert "<!DOCTYPE html>" in html
        assert "2026-02-25" in html


class TestReactionsDefinition:
    """REACTIONS 定数のテスト"""

    def test_all_reaction_types_defined(self):
        """全リアクション種別が定義されていること"""
        types = [r["type"] for r in REACTIONS]
        assert "excellent" in types
        assert "good" in types
        assert "meh" in types
        assert "bookmark" in types

    def test_reaction_has_required_fields(self):
        """各リアクションに必要なフィールドが含まれること"""
        for reaction in REACTIONS:
            assert "type" in reaction
            assert "emoji" in reaction
            assert "label" in reaction
            assert "color" in reaction
            assert "text_color" in reaction


# ============================================================
# line_sender テスト
# ============================================================

class TestFormatForLine:
    """format_for_line 関数のテスト"""

    def test_basic_format(self):
        """基本的な LINE フォーマット"""
        stories = _sample_stories()
        text = format_for_line(stories)

        # ヘッダーが含まれること
        assert "AI News Daily Digest" in text
        # 各ストーリーのタイトルが含まれること
        assert "AIが医療を革新する新技術" in text
        assert "LLMの新しいベンチマーク" in text
        # ソース情報が含まれること
        assert "TechCrunch" in text

    def test_empty_stories(self):
        """空のストーリーリスト"""
        text = format_for_line([])
        assert "本日のAIニュースはありません" in text

    def test_message_length_limit(self):
        """メッセージが 1000 文字以内であること"""
        stories = _sample_stories()
        text = format_for_line(stories)
        assert len(text) <= _LINE_MESSAGE_LIMIT

    def test_long_stories_truncation(self):
        """長いストーリーが正しく切り詰められること"""
        long_stories = []
        for i in range(10):
            long_stories.append({
                "id": i + 1,
                "title": f"非常に長いタイトルのニュース記事 {i + 1} - AI技術の革新的な進歩について詳しく解説",
                "body": "A" * 500,
                "source": "TestSource",
                "url": f"https://example.com/very-long-article-{i + 1}",
                "category": "テスト",
            })
        text = format_for_line(long_stories)
        assert len(text) <= _LINE_MESSAGE_LIMIT

    def test_story_ids_in_output(self):
        """ストーリー ID がフォーマットに含まれること"""
        stories = _sample_stories()
        text = format_for_line(stories)
        assert "[1]" in text
        assert "[2]" in text

    def test_urls_included(self):
        """元記事 URL が含まれること"""
        stories = _sample_stories()[:1]
        text = format_for_line(stories)
        assert "https://techcrunch.com/example-1" in text

    def test_category_included(self):
        """カテゴリが含まれること"""
        stories = _sample_stories()[:1]
        text = format_for_line(stories)
        assert "ヘルスケア" in text


class TestExtractSummary:
    """_extract_summary 関数のテスト"""

    def test_basic_extraction(self):
        """基本的な要約抽出"""
        text = "これはテストテキストです。"
        result = _extract_summary(text, max_length=100)
        assert result == "これはテストテキストです。"

    def test_truncation(self):
        """長いテキストの切り詰め"""
        text = "あ" * 200
        result = _extract_summary(text, max_length=50)
        assert len(result) <= 50
        # 末尾が省略記号
        assert result.endswith("\u2026")

    def test_markdown_heading_removal(self):
        """Markdown 見出しの除去"""
        text = "# タイトル\n本文です"
        result = _extract_summary(text)
        assert "#" not in result
        assert "タイトル" in result
        assert "本文です" in result

    def test_markdown_bold_removal(self):
        """Markdown 強調の除去"""
        text = "**太字** と *イタリック*"
        result = _extract_summary(text)
        assert "**" not in result
        assert "*" not in result
        assert "太字" in result

    def test_markdown_link_removal(self):
        """Markdown リンクの除去"""
        text = "[リンクテキスト](https://example.com) です"
        result = _extract_summary(text)
        assert "](https" not in result
        assert "リンクテキスト" in result

    def test_code_block_removal(self):
        """コードブロックの除去"""
        text = "前文\n```python\ncode\n```\n後文"
        result = _extract_summary(text)
        assert "```" not in result
        assert "前文" in result
        assert "後文" in result

    def test_empty_text(self):
        """空テキスト"""
        result = _extract_summary("")
        assert result == ""


# ============================================================
# リアクションリンク統合テスト
# ============================================================

class TestReactionLinkIntegration:
    """リアクションリンク生成の統合テスト"""

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_reaction_links_format_in_html(self, mock_base_url):
        """HTML メール内のリアクションリンクが正しいフォーマットであること"""
        stories = _sample_stories()
        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=stories,
            base_url="http://localhost:8080",
        )

        # 各ストーリーの各リアクションリンクが正しいフォーマットであることを確認
        # Jinja2 テンプレートでは href 属性内の & はそのまま出力される
        for story in stories:
            story_id = story["id"]
            for rtype in ["excellent", "good", "meh", "bookmark"]:
                expected_url = f"http://localhost:8080/react?date=2026-02-25&story={story_id}&reaction={rtype}"
                assert expected_url in html, (
                    f"Expected reaction URL not found: story={story_id}, reaction={rtype}"
                )

    def test_reaction_url_pattern(self):
        """リアクション URL のパターンが仕様通りであること"""
        url = generate_reaction_url(
            base_url="http://localhost:8080",
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
        )
        # architecture.md のパターン: http://localhost:8080/react?date={YYYY-MM-DD}&story={1-3}&reaction={type}
        pattern = r"^http://localhost:\d+/react\?date=\d{4}-\d{2}-\d{2}&story=\d+&reaction=(excellent|good|meh|bookmark)$"
        assert re.match(pattern, url), f"URL pattern mismatch: {url}"

    def test_reaction_mapping_completeness(self):
        """リアクションの種別と architecture.md の定義が一致すること"""
        # architecture.md: excellent(5), good(4), bookmark(3), meh(2)
        expected_types = {"excellent", "good", "bookmark", "meh"}
        actual_types = {r["type"] for r in REACTIONS}
        assert actual_types == expected_types
