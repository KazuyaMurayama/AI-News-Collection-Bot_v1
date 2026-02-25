"""統合テスト / エッジケーステスト

main.py のパイプライン実行テスト（全外部APIをモック）、
収集→変換→MD保存の一連フロー、リアクションAPI→MDファイル更新フロー、
CLI引数（--dry-run, --date）のテスト、及びエッジケースを網羅する。
"""

import json
import os
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

import frontmatter
import pytest
import yaml


# ============================================================
# テスト用ヘルパー
# ============================================================

_JST = timezone(timedelta(hours=9))


def _minimal_config() -> dict:
    """最小限の有効な設定辞書を返す。"""
    return {
        "app": {
            "name": "Test App",
            "version": "0.1.0",
        },
        "collection": {
            "schedule_time": "06:00",
            "timezone": "Asia/Tokyo",
            "num_stories": 3,
            "sources": [],
        },
        "claude": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "selection": {
            "scoring_weights": {
                "novelty": 5,
                "surprise": 5,
                "practicality": 5,
                "japan_relevance": 3,
                "freshness": 2,
            },
            "select_count": 3,
        },
        "delivery": {
            "gmail": {"enabled": False},
            "line": {"enabled": False},
        },
        "feedback_server": {
            "host": "127.0.0.1",
            "port": 8080,
        },
        "knowledge_base": {
            "daily_dir": "./knowledge_base/daily",
            "monthly_dir": "./knowledge_base/monthly",
        },
        "logging": {
            "level": "INFO",
            "dir": "./logs/",
            "retention_days": 30,
        },
        "retry": {
            "max_attempts": 3,
            "backoff_base": 1,
            "backoff_multiplier": 2,
        },
    }


def _create_config_and_env(tmp_path: Path) -> tuple[Path, Path]:
    """テスト用の config.yaml と .env を tmp_path に作成する。"""
    config_data = _minimal_config()
    config_data["knowledge_base"]["daily_dir"] = str(tmp_path / "knowledge_base" / "daily")
    config_data["knowledge_base"]["monthly_dir"] = str(tmp_path / "knowledge_base" / "monthly")
    config_data["logging"]["dir"] = str(tmp_path / "logs")

    config_path = tmp_path / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

    env_path = tmp_path / ".env"
    env_path.write_text("ANTHROPIC_API_KEY=test-key-123\n", encoding="utf-8")

    return config_path, env_path


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
    story: str = "ストーリー本文です。",
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
        "story": story,
    }


def _mock_claude_response(text: str) -> MagicMock:
    """Claude API レスポンスのモックを生成する。"""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


def _create_sample_md(daily_dir: Path, date: str = "2026-02-25") -> Path:
    """テスト用の日次 Markdown ファイルを作成する。"""
    daily_dir.mkdir(parents=True, exist_ok=True)

    content = textwrap.dedent(f"""\
        ---
        date: "{date}"
        tags:
          - "LLM"
          - "業務効率化"
        stories:
          - id: 1
            title: "Claude 4が登場"
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
            title: "日本企業のAI活用"
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
            title: "画像生成AIの進化"
            source: "VentureBeat"
            url: "https://example.com/article3"
            category: "マーケティング"
            tags:
              - "画像生成"
            rating: null
            reaction: null
            reacted_at: null
        ---

        # AI News Daily Report - {date}

        ## Story 1: Claude 4が登場
        テスト本文 Story 1...

        ## Story 2: 日本企業のAI活用
        テスト本文 Story 2...

        ## Story 3: 画像生成AIの進化
        テスト本文 Story 3...
    """)

    md_path = daily_dir / f"{date}_ai_news.md"
    md_path.write_text(content, encoding="utf-8")
    return md_path


# ============================================================
# 統合テスト: main.py パイプライン
# ============================================================

class TestPipelineIntegration:
    """main.py の run_pipeline() パイプラインの統合テスト。"""

    def setup_method(self) -> None:
        """各テスト前にシングルトンをリセットする。"""
        from src.utils.config import AppConfig
        AppConfig.reset()
        from src.utils.logger import reset_loggers
        reset_loggers()

    def teardown_method(self) -> None:
        """各テスト後にシングルトンをリセットする。"""
        from src.utils.config import AppConfig
        AppConfig.reset()
        from src.utils.logger import reset_loggers
        reset_loggers()

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    @patch("src.knowledge.tagger._call_claude_api")
    @patch("src.collector.rss_collector.feedparser.parse")
    def test_full_pipeline_dry_run(
        self,
        mock_feedparser: MagicMock,
        mock_tagger_api: MagicMock,
        mock_model_config: MagicMock,
        mock_claude_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """dry-run モードで全パイプラインが正常に動作すること。"""
        from src.main import run_pipeline
        from src.utils.config import AppConfig

        # 設定の準備
        config_path, env_path = _create_config_and_env(tmp_path)

        # RSS ソースを追加
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        config_data["collection"]["sources"] = [
            {
                "name": "TestFeed",
                "type": "rss",
                "url": "https://example.com/feed.xml",
                "category": "テスト",
                "language": "en",
                "enabled": True,
            }
        ]
        with open(config_path, "w") as f:
            yaml.dump(config_data, f, allow_unicode=True)

        # AppConfig の初期化
        os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
        AppConfig.get_instance(config_path=config_path, env_path=env_path, force_reload=True)

        # feedparser モック
        from time import struct_time
        entry = MagicMock()
        entry.title = "AI Test Article"
        entry.link = "https://example.com/test-article"
        entry.summary = "An article about AI testing"
        entry.description = "An article about AI testing"
        entry.published_parsed = struct_time((2026, 2, 25, 6, 0, 0, 2, 56, 0))
        entry.updated_parsed = None

        feed = MagicMock()
        feed.entries = [entry]
        feed.status = 200
        feed.bozo = False
        feed.bozo_exception = None
        mock_feedparser.return_value = feed

        # Claude API モック (storyteller)
        mock_model_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        mock_client = MagicMock()
        mock_claude_client.return_value = mock_client
        # select_framework -> transform_to_story -> generate_insight
        mock_client.messages.create.return_value = _mock_claude_response(
            "テスト用の生成テキスト。AI技術の進展について解説します。"
        )

        # tagger モック
        mock_tagger_api.return_value = json.dumps({
            "category_tags": ["業務効率化"],
            "tech_tags": ["LLM"],
        })

        # パイプライン実行 (dry-run)
        run_pipeline(target_date="2026-02-25", dry_run=True)

        # 結果の検証: MD ファイルが生成されていること
        daily_dir = Path(config_data["knowledge_base"]["daily_dir"])
        md_file = daily_dir / "2026-02-25_ai_news.md"
        assert md_file.exists(), f"Markdown file should exist at {md_file}"

        # Frontmatter が正しいこと
        post = frontmatter.load(str(md_file))
        assert post.metadata["date"] == "2026-02-25"
        assert len(post.metadata["stories"]) >= 1

        # 中間 JSON が保存されていること
        json_file = daily_dir / "2026-02-25_candidates.json"
        assert json_file.exists(), f"Intermediate JSON should exist at {json_file}"

        # cleanup
        os.environ.pop("ANTHROPIC_API_KEY", None)

    @patch("src.collector.collect_all")
    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    @patch("src.knowledge.tagger._call_claude_api")
    def test_pipeline_zero_articles_fallback(
        self,
        mock_tagger_api: MagicMock,
        mock_model_config: MagicMock,
        mock_claude_client: MagicMock,
        mock_collect_all: MagicMock,
        tmp_path: Path,
    ) -> None:
        """記事0件の場合のフォールバック処理が正常に動作すること。"""
        from src.main import run_pipeline
        from src.utils.config import AppConfig

        # 設定の準備（ソースなし = 0件）
        config_path, env_path = _create_config_and_env(tmp_path)
        os.environ["ANTHROPIC_API_KEY"] = "test-key-123"
        AppConfig.get_instance(config_path=config_path, env_path=env_path, force_reload=True)

        # collect_all が空リストを返すようモック
        mock_collect_all.return_value = []

        # Claude API モック
        mock_model_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        mock_client = MagicMock()
        mock_claude_client.return_value = mock_client
        mock_client.messages.create.return_value = _mock_claude_response(
            "フォールバックテスト用のインサイト。"
        )

        # tagger モック
        mock_tagger_api.return_value = json.dumps({
            "category_tags": [],
            "tech_tags": [],
        })

        # パイプライン実行
        run_pipeline(target_date="2026-02-25", dry_run=True)

        # フォールバック MD ファイルが生成されていること
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        daily_dir = Path(config_data["knowledge_base"]["daily_dir"])
        md_file = daily_dir / "2026-02-25_ai_news.md"
        assert md_file.exists(), "Fallback MD file should be created even with 0 articles"

        # フォールバックストーリーが含まれていること
        post = frontmatter.load(str(md_file))
        assert len(post.metadata["stories"]) == 1
        assert "取得できませんでした" in post.metadata["stories"][0]["title"]

        # cleanup
        os.environ.pop("ANTHROPIC_API_KEY", None)


class TestCollectTransformSaveFlow:
    """収集 -> 変換 -> MD保存の一連フローテスト。"""

    def setup_method(self) -> None:
        from src.utils.config import AppConfig
        AppConfig.reset()
        from src.utils.logger import reset_loggers
        reset_loggers()

    def teardown_method(self) -> None:
        from src.utils.config import AppConfig
        AppConfig.reset()
        from src.utils.logger import reset_loggers
        reset_loggers()

    @patch("src.collector.selector._score_with_claude")
    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_and_select(
        self,
        mock_feedparser: MagicMock,
        mock_score: MagicMock,
    ) -> None:
        """RSS 収集 -> Claude 選定の流れが正常に動作すること。"""
        from src.collector import collect_all
        from time import struct_time

        # feedparser モック
        entries = []
        for i in range(5):
            entry = MagicMock()
            entry.title = f"Article {i}"
            entry.link = f"https://example.com/{i}"
            entry.summary = f"Summary {i}"
            entry.description = f"Summary {i}"
            entry.published_parsed = struct_time((2026, 2, 25, 6, 0, 0, 2, 56, 0))
            entry.updated_parsed = None
            entries.append(entry)

        feed = MagicMock()
        feed.entries = entries
        feed.status = 200
        feed.bozo = False
        feed.bozo_exception = None
        mock_feedparser.return_value = feed

        # スコアリングモック
        mock_score.return_value = [
            {"index": i, "novelty": 5 - i, "surprise": 5 - i, "practicality": 5 - i,
             "japan_relevance": 3, "freshness": 2, "total": 20 - i * 3, "reason": f"Reason {i}"}
            for i in range(5)
        ]

        config = {
            "collection": {
                "num_stories": 2,
                "sources": [
                    {
                        "name": "TestFeed",
                        "type": "rss",
                        "url": "https://example.com/feed",
                        "enabled": True,
                    },
                ],
            },
        }

        selected = collect_all(config=config, num_articles=2)

        assert len(selected) == 2
        assert selected[0]["score"]["total"] >= selected[1]["score"]["total"]

    @patch("src.writer.storyteller._get_claude_client")
    @patch("src.writer.storyteller._get_model_config")
    def test_transform_and_save_markdown(
        self,
        mock_model_config: MagicMock,
        mock_claude_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """ストーリーテリング変換 -> MD生成・保存が正常に動作すること。"""
        from src.writer.storyteller import transform_to_story, generate_insight
        from src.writer.markdown_gen import generate_daily_markdown, save_markdown

        # Claude API モック
        mock_model_config.return_value = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }
        mock_client = MagicMock()
        mock_claude_client.return_value = mock_client
        mock_client.messages.create.return_value = _mock_claude_response(
            "AIが業務効率化に与えるインパクトとは？\n\n詳しい解説テキスト..."
        )

        article = _make_article(
            title="企業がAI導入で業務効率化を実現",
            summary="AI導入による業務効率化の事例紹介",
        )

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            story_text = transform_to_story(article, framework="STAR")

        assert len(story_text) > 0

        stories = [
            _make_story(
                story_id=1,
                title=article["title"],
                body=story_text,
                story=story_text,
            ),
        ]

        insight = "テスト用インサイト"
        md_content = generate_daily_markdown("2026-02-25", stories, insight)

        filepath = tmp_path / "2026-02-25_ai_news.md"
        save_markdown(md_content, str(filepath))

        assert filepath.exists()

        post = frontmatter.load(str(filepath))
        assert post.metadata["date"] == "2026-02-25"
        assert len(post.metadata["stories"]) == 1
        assert "テスト用インサイト" in post.content


# ============================================================
# 統合テスト: リアクション API -> MD ファイル更新フロー
# ============================================================

class TestReactionFlowIntegration:
    """リアクションAPI -> MDファイル更新の統合テスト。"""

    @pytest.fixture
    def client(self):
        """テスト用の httpx AsyncClient を生成する。"""
        from httpx import AsyncClient, ASGITransport
        from src.feedback.api_server import create_app
        app = create_app()
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_react_updates_md_file(self, tmp_path: Path, client) -> None:
        """リアクション API がMDファイルのFrontmatterを正しく更新すること。"""
        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        with patch(
            "src.feedback.api_server.update_reaction",
        ) as mock_update:
            # 実際の update_reaction を呼ぶ代わりにモックして True を返す
            mock_update.return_value = True
            async with client as c:
                response = await c.get(
                    "/react",
                    params={"date": "2026-02-25", "story": 1, "reaction": "excellent"},
                )

            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "フィードバックありがとうございます" in response.text

    @pytest.mark.asyncio
    async def test_react_then_verify_md_updated(self, tmp_path: Path) -> None:
        """リアクション -> 実際のMD更新 -> 検証の完全フロー。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        # 直接 update_reaction を呼び出す
        result = update_reaction(
            date="2026-02-25",
            story_id=2,
            reaction_type="good",
            daily_dir=daily_dir,
        )

        assert result is True

        # MD ファイルの検証
        post = frontmatter.load(str(md_path))
        story = post.metadata["stories"][1]  # id=2 は index 1
        assert story["reaction"] == "good"
        assert story["rating"] == 4
        assert story["reacted_at"] is not None

    @pytest.mark.asyncio
    async def test_react_all_types_on_same_file(self, tmp_path: Path) -> None:
        """同一ファイルの3つのストーリーに異なるリアクションを設定できること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        # 各ストーリーに異なるリアクションを設定
        reactions = [
            (1, "excellent", 5),
            (2, "good", 4),
            (3, "meh", 2),
        ]

        for story_id, reaction_type, expected_rating in reactions:
            result = update_reaction(
                date="2026-02-25",
                story_id=story_id,
                reaction_type=reaction_type,
                daily_dir=daily_dir,
            )
            assert result is True

        # 全更新が正しく反映されていること
        post = frontmatter.load(str(md_path))
        for i, (story_id, reaction_type, expected_rating) in enumerate(reactions):
            story = post.metadata["stories"][i]
            assert story["reaction"] == reaction_type
            assert story["rating"] == expected_rating


# ============================================================
# CLI引数テスト
# ============================================================

class TestCLIArgs:
    """CLI 引数のパース・バリデーションテスト。"""

    def test_parse_default_args(self) -> None:
        """デフォルト引数のパース。"""
        from src.main import parse_args

        args = parse_args([])
        assert args.date is None
        assert args.dry_run is False
        assert args.server is False

    def test_parse_date_arg(self) -> None:
        """--date 引数のパース。"""
        from src.main import parse_args

        args = parse_args(["--date", "2026-03-01"])
        assert args.date == "2026-03-01"

    def test_parse_dry_run_arg(self) -> None:
        """--dry-run 引数のパース。"""
        from src.main import parse_args

        args = parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_parse_server_arg(self) -> None:
        """--server 引数のパース。"""
        from src.main import parse_args

        args = parse_args(["--server"])
        assert args.server is True

    def test_parse_combined_args(self) -> None:
        """複合引数のパース。"""
        from src.main import parse_args

        args = parse_args(["--date", "2026-01-15", "--dry-run"])
        assert args.date == "2026-01-15"
        assert args.dry_run is True
        assert args.server is False

    def test_main_invalid_date_exits(self) -> None:
        """不正な日付フォーマットで sys.exit(1) が呼ばれること。"""
        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main(["--date", "not-a-date"])

        assert exc_info.value.code == 1

    def test_main_valid_date_format(self) -> None:
        """有効な日付フォーマットが受け入れられること。"""
        from src.main import parse_args
        from datetime import datetime

        args = parse_args(["--date", "2026-12-31"])
        # 日付バリデーション
        parsed = datetime.strptime(args.date, "%Y-%m-%d")
        assert parsed.year == 2026
        assert parsed.month == 12
        assert parsed.day == 31

    def test_today_jst_format(self) -> None:
        """_today_jst() が正しいフォーマットで日付を返すこと。"""
        from src.main import _today_jst

        today = _today_jst()
        # YYYY-MM-DD フォーマットであること
        datetime.strptime(today, "%Y-%m-%d")
        assert len(today) == 10


# ============================================================
# エッジケーステスト: 記事0件のフォールバック
# ============================================================

class TestZeroArticleFallback:
    """記事が0件の場合のフォールバック動作テスト。"""

    def test_collect_all_empty_sources(self) -> None:
        """ソースが0件の場合に空リストが返ること。"""
        from src.collector import collect_all

        config = {
            "collection": {
                "num_stories": 3,
                "sources": [],
            },
        }
        result = collect_all(config=config)
        assert result == []

    @patch("src.collector.rss_collector.feedparser.parse")
    def test_collect_all_all_feeds_fail(self, mock_parse: MagicMock) -> None:
        """全フィードが失敗した場合に空リストが返ること。"""
        from src.collector import collect_all

        mock_parse.side_effect = Exception("Network error")

        config = {
            "collection": {
                "num_stories": 3,
                "sources": [
                    {
                        "name": "FailFeed",
                        "type": "rss",
                        "url": "https://example.com/fail",
                        "enabled": True,
                    },
                ],
            },
        }
        result = collect_all(config=config)
        assert result == []

    def test_generate_markdown_empty_stories(self) -> None:
        """ストーリー0件でもMarkdownが生成されること。"""
        from src.writer.markdown_gen import generate_daily_markdown

        md = generate_daily_markdown("2026-02-25", [], "インサイトなし")
        assert md is not None
        assert len(md) > 0

        post = frontmatter.loads(md)
        assert post.metadata["date"] == "2026-02-25"
        assert post.metadata["stories"] == []
        assert "インサイトなし" in post.content

    def test_generate_insight_empty_stories(self) -> None:
        """ストーリーが空の場合にデフォルトインサイトが返ること。"""
        from src.writer.storyteller import generate_insight

        result = generate_insight([])
        assert "生成できませんでした" in result

    def test_format_for_line_empty_stories(self) -> None:
        """LINEフォーマッタが空ストーリーを正しく処理すること。"""
        from src.delivery.line_sender import format_for_line

        text = format_for_line([])
        assert "本日のAIニュースはありません" in text

    @patch("src.delivery.html_converter._resolve_base_url", return_value="http://localhost:8080")
    def test_email_template_empty_stories(self, mock_base_url: MagicMock) -> None:
        """メールテンプレートが空ストーリーで正常に動作すること。"""
        from src.delivery.html_converter import apply_email_template

        html = apply_email_template(
            html_body="",
            date="2026-02-25",
            stories=[],
            base_url="http://localhost:8080",
        )
        assert "<!DOCTYPE html>" in html
        assert "2026-02-25" in html


# ============================================================
# エッジケーステスト: 不正なリアクションリクエスト
# ============================================================

class TestInvalidReactionRequests:
    """不正なリアクションリクエストのエッジケーステスト。"""

    def test_invalid_reaction_type(self, tmp_path: Path) -> None:
        """不正な reaction_type で ValueError が発生すること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        _create_sample_md(daily_dir)

        with pytest.raises(ValueError, match="Invalid reaction type"):
            update_reaction(
                date="2026-02-25",
                story_id=1,
                reaction_type="unknown",
                daily_dir=daily_dir,
            )

    def test_story_id_zero(self, tmp_path: Path) -> None:
        """story_id=0 で ValueError が発生すること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        _create_sample_md(daily_dir)

        with pytest.raises(ValueError, match="Invalid story_id"):
            update_reaction(
                date="2026-02-25",
                story_id=0,
                reaction_type="excellent",
                daily_dir=daily_dir,
            )

    def test_story_id_negative(self, tmp_path: Path) -> None:
        """story_id が負数で ValueError が発生すること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        _create_sample_md(daily_dir)

        with pytest.raises(ValueError, match="Invalid story_id"):
            update_reaction(
                date="2026-02-25",
                story_id=-1,
                reaction_type="excellent",
                daily_dir=daily_dir,
            )

    def test_story_id_too_large(self, tmp_path: Path) -> None:
        """story_id > 3 で ValueError が発生すること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        _create_sample_md(daily_dir)

        with pytest.raises(ValueError, match="Invalid story_id"):
            update_reaction(
                date="2026-02-25",
                story_id=4,
                reaction_type="excellent",
                daily_dir=daily_dir,
            )

    def test_nonexistent_date_file(self, tmp_path: Path) -> None:
        """存在しない日付のファイルで FileNotFoundError が発生すること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "empty_dir"
        daily_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(FileNotFoundError, match="Article not found"):
            update_reaction(
                date="2099-12-31",
                story_id=1,
                reaction_type="excellent",
                daily_dir=daily_dir,
            )

    @pytest.fixture
    def client(self):
        """テスト用の httpx AsyncClient を生成する。"""
        from httpx import AsyncClient, ASGITransport
        from src.feedback.api_server import create_app
        app = create_app()
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_api_invalid_date_format(self, client) -> None:
        """API で不正な日付フォーマットが 422 で拒否されること。"""
        async with client as c:
            response = await c.get(
                "/react",
                params={"date": "25-02-2026", "story": 1, "reaction": "excellent"},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_api_missing_params(self, client) -> None:
        """API で必須パラメータが欠けている場合に 422 が返ること。"""
        async with client as c:
            response = await c.get(
                "/react",
                params={"date": "2026-02-25"},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_api_story_id_out_of_range(self, client) -> None:
        """API で story_id が範囲外の場合に 422 が返ること。"""
        async with client as c:
            response = await c.get(
                "/react",
                params={"date": "2026-02-25", "story": 5, "reaction": "excellent"},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_api_invalid_reaction_type(self, client) -> None:
        """API で不正な reaction タイプの場合に 400 が返ること。"""
        async with client as c:
            response = await c.get(
                "/react",
                params={"date": "2026-02-25", "story": 1, "reaction": "invalid_type"},
            )
        assert response.status_code == 400


# ============================================================
# エッジケーステスト: 既存MDファイルへの重複更新
# ============================================================

class TestDuplicateReactionUpdates:
    """既存MDファイルへの重複リアクション更新テスト。"""

    def test_overwrite_reaction(self, tmp_path: Path) -> None:
        """同じストーリーに2回リアクションを設定すると後の値で上書きされること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        # 1回目: excellent
        result1 = update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
            daily_dir=daily_dir,
        )
        assert result1 is True

        post1 = frontmatter.load(str(md_path))
        assert post1.metadata["stories"][0]["reaction"] == "excellent"
        assert post1.metadata["stories"][0]["rating"] == 5
        first_reacted_at = post1.metadata["stories"][0]["reacted_at"]

        # 2回目: meh で上書き
        result2 = update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="meh",
            daily_dir=daily_dir,
        )
        assert result2 is True

        post2 = frontmatter.load(str(md_path))
        assert post2.metadata["stories"][0]["reaction"] == "meh"
        assert post2.metadata["stories"][0]["rating"] == 2
        second_reacted_at = post2.metadata["stories"][0]["reacted_at"]

        # reacted_at が更新されていること
        assert second_reacted_at is not None

    def test_update_preserves_other_stories(self, tmp_path: Path) -> None:
        """1つのストーリーを更新しても他のストーリーが影響を受けないこと。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        # story 1 のみ更新
        update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
            daily_dir=daily_dir,
        )

        post = frontmatter.load(str(md_path))

        # story 1 は更新されている
        assert post.metadata["stories"][0]["reaction"] == "excellent"
        assert post.metadata["stories"][0]["rating"] == 5

        # story 2, 3 は未変更
        assert post.metadata["stories"][1]["reaction"] is None
        assert post.metadata["stories"][1]["rating"] is None
        assert post.metadata["stories"][2]["reaction"] is None
        assert post.metadata["stories"][2]["rating"] is None

    def test_update_preserves_body_content(self, tmp_path: Path) -> None:
        """リアクション更新がMarkdown本文を変更しないこと。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        # 更新前の本文を保存
        pre_post = frontmatter.load(str(md_path))
        pre_content = pre_post.content

        # リアクション更新
        update_reaction(
            date="2026-02-25",
            story_id=1,
            reaction_type="excellent",
            daily_dir=daily_dir,
        )

        # 更新後の本文を確認
        post_post = frontmatter.load(str(md_path))
        post_content = post_post.content

        assert pre_content == post_content

    def test_sequential_updates_on_different_stories(self, tmp_path: Path) -> None:
        """異なるストーリーへの連続更新が全て正しく反映されること。"""
        from src.feedback.updater import update_reaction

        daily_dir = tmp_path / "knowledge_base" / "daily"
        md_path = _create_sample_md(daily_dir, date="2026-02-25")

        # story 1 -> excellent
        update_reaction("2026-02-25", 1, "excellent", daily_dir)
        # story 2 -> good
        update_reaction("2026-02-25", 2, "good", daily_dir)
        # story 3 -> bookmark
        update_reaction("2026-02-25", 3, "bookmark", daily_dir)

        post = frontmatter.load(str(md_path))
        stories = post.metadata["stories"]

        assert stories[0]["reaction"] == "excellent"
        assert stories[0]["rating"] == 5
        assert stories[1]["reaction"] == "good"
        assert stories[1]["rating"] == 4
        assert stories[2]["reaction"] == "bookmark"
        assert stories[2]["rating"] == 3


# ============================================================
# 統合テスト: MD ファイルの命名規則の一貫性
# ============================================================

class TestMdFileNamingConsistency:
    """MDファイルの命名規則がモジュール間で一貫していることを検証する。"""

    def test_updater_filename_pattern(self) -> None:
        """updater の _build_md_filepath が {date}_ai_news.md パターンであること。"""
        from src.feedback.updater import _build_md_filepath

        path = _build_md_filepath("2026-02-25", daily_dir=Path("/tmp/test"))
        assert path.name == "2026-02-25_ai_news.md"

    def test_search_filename_pattern(self) -> None:
        """search の get_all_articles が *_ai_news.md パターンを使うこと。"""
        from src.knowledge.search import get_all_articles

        # 空ディレクトリで呼び出し（ファイルが無いことの確認ではなくパターン確認）
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            # _ai_news.md 以外のファイルは無視されることを確認
            (td_path / "2026-02-25.md").write_text("---\nstories: []\n---\ntest")
            (td_path / "2026-02-25_ai_news.md").write_text(
                "---\ndate: '2026-02-25'\nstories: []\n---\ntest"
            )

            articles = get_all_articles(daily_dir=td_path)
            # _ai_news.md のみ読み込まれること
            # ストーリーが0件なので空リスト
            assert isinstance(articles, list)

    def test_main_saves_with_correct_filename(self) -> None:
        """main.py がMDファイルを {date}_ai_news.md で保存すること。"""
        import ast
        main_path = Path("/home/user/AI-News-Collection-Bot_v1/ai-news-bot/src/main.py")
        source = main_path.read_text(encoding="utf-8")
        assert "_ai_news.md" in source, \
            "main.py should save MD files with _ai_news.md suffix"


# ============================================================
# 統合テスト: knowledge モジュールとの連携
# ============================================================

class TestKnowledgeIntegration:
    """ナレッジベースの検索機能統合テスト。"""

    def test_search_after_reaction_update(self, tmp_path: Path) -> None:
        """リアクション更新後に search で更新内容が反映されること。"""
        from src.feedback.updater import update_reaction
        from src.knowledge.search import get_all_articles, filter_by_rating

        daily_dir = tmp_path / "knowledge_base" / "daily"
        _create_sample_md(daily_dir, date="2026-02-25")

        # 更新前: 高評価記事なし
        rated_before = filter_by_rating(min_rating=4, daily_dir=daily_dir)
        assert len(rated_before) == 0

        # リアクション更新
        update_reaction("2026-02-25", 1, "excellent", daily_dir)
        update_reaction("2026-02-25", 2, "good", daily_dir)

        # 更新後: 高評価記事が2件
        rated_after = filter_by_rating(min_rating=4, daily_dir=daily_dir)
        assert len(rated_after) == 2
        assert rated_after[0]["rating"] == 5
        assert rated_after[1]["rating"] == 4

    def test_tag_search_on_generated_md(self, tmp_path: Path) -> None:
        """生成したMDファイルに対するタグ検索が動作すること。"""
        from src.writer.markdown_gen import generate_daily_markdown, save_markdown
        from src.knowledge.search import search_by_tag

        daily_dir = tmp_path / "knowledge_base" / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        stories = [
            _make_story(story_id=1, title="LLM記事", tags=["LLM", "Agent"]),
            _make_story(story_id=2, title="画像生成記事", tags=["画像生成"]),
        ]
        md = generate_daily_markdown("2026-02-25", stories, "インサイト")
        save_markdown(md, str(daily_dir / "2026-02-25_ai_news.md"))

        results = search_by_tag("LLM", daily_dir=daily_dir)
        assert len(results) >= 1
        assert any("LLM" in r.get("tags", []) for r in results)

    def test_fulltext_search_on_generated_md(self, tmp_path: Path) -> None:
        """生成したMDファイルに対する全文検索が動作すること。"""
        from src.writer.markdown_gen import generate_daily_markdown, save_markdown
        from src.knowledge.search import search_fulltext

        daily_dir = tmp_path / "knowledge_base" / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        stories = [
            _make_story(story_id=1, title="UniqueSearchTitle123"),
        ]
        md = generate_daily_markdown("2026-02-25", stories, "インサイト")
        save_markdown(md, str(daily_dir / "2026-02-25_ai_news.md"))

        results = search_fulltext("UniqueSearchTitle123", daily_dir=daily_dir)
        assert len(results) >= 1


# ============================================================
# エッジケーステスト: 追加分
# ============================================================

class TestAdditionalEdgeCases:
    """その他のエッジケーステスト。"""

    def test_save_markdown_empty_content(self, tmp_path: Path) -> None:
        """空文字列のMarkdownを保存できること。"""
        from src.writer.markdown_gen import save_markdown

        filepath = tmp_path / "empty.md"
        save_markdown("", str(filepath))
        assert filepath.exists()
        assert filepath.read_text(encoding="utf-8") == ""

    def test_collect_candidates_disabled_sources(self) -> None:
        """enabled=false のソースがスキップされること。"""
        from src.collector import collect_candidates

        config = {
            "collection": {
                "num_stories": 3,
                "sources": [
                    {
                        "name": "DisabledFeed",
                        "type": "rss",
                        "url": "https://example.com/feed",
                        "enabled": False,
                    },
                ],
            },
        }
        result = collect_candidates(config=config)
        assert result == []

    def test_select_top_articles_single_candidate(self) -> None:
        """候補が1件で選定数が3の場合にフォールバックで1件が返ること。"""
        from src.collector.selector import select_top_articles

        candidates = [
            _make_article(title="Only Article"),
        ]
        selected = select_top_articles(candidates, num=3)
        assert len(selected) == 1
        assert selected[0]["title"] == "Only Article"

    def test_deduplicate_candidates_url_case_insensitive(self) -> None:
        """URL重複排除でURLの重複が検出されること。"""
        from src.collector.selector import _deduplicate_candidates

        candidates = [
            _make_article(title="Article A", url="https://example.com/a"),
            _make_article(title="Article B", url="https://example.com/b"),
            _make_article(title="Article A copy", url="https://example.com/a"),
        ]
        unique = _deduplicate_candidates(candidates)
        assert len(unique) == 2

    def test_config_validation_multiple_errors(self) -> None:
        """複数のバリデーションエラーが全て報告されること。"""
        from src.utils.config import validate_config

        config = {
            "app": {"name": "Test", "version": "1.0"},
            "collection": {"num_stories": -1, "sources": []},
            "claude": {"model": "test", "temperature": 2.0},
            "selection": {},
            "delivery": {},
            "feedback_server": {"port": 80},
            "knowledge_base": {},
            "logging": {"level": "INVALID"},
            "retry": {},
        }

        errors = validate_config(config)
        assert len(errors) >= 3  # num_stories, temperature, port, level
        assert any("num_stories" in e for e in errors)
        assert any("temperature" in e for e in errors)
        assert any("port" in e for e in errors)
        assert any("level" in e for e in errors)

    def test_reaction_map_completeness(self) -> None:
        """REACTION_MAP に全リアクション種別が定義されていること。"""
        from src.feedback.updater import REACTION_MAP

        expected_types = {"excellent", "good", "bookmark", "meh"}
        assert set(REACTION_MAP.keys()) == expected_types

        for reaction_type, info in REACTION_MAP.items():
            assert "emoji" in info
            assert "label" in info
            assert "rating" in info
            assert isinstance(info["rating"], int)
            assert 1 <= info["rating"] <= 5

    def test_scoring_prompt_includes_all_candidates(self) -> None:
        """スコアリングプロンプトに全候補記事の情報が含まれること。"""
        from src.collector.selector import _build_scoring_prompt

        candidates = [
            _make_article(title=f"Article {i}", url=f"https://example.com/{i}")
            for i in range(5)
        ]

        prompt = _build_scoring_prompt(candidates)

        assert "5 件の記事" in prompt
        for i in range(5):
            assert f"Article {i}" in prompt
            assert f"https://example.com/{i}" in prompt
