"""utils モジュールのテスト

config.py, logger.py, retry.py の各機能をテストする。
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

# テスト対象モジュール
from src.utils.config import (
    AppConfig,
    ConfigValidationError,
    load_config,
    validate_config,
)
from src.utils.logger import reset_loggers, setup_logger
from src.utils.retry import with_retry


# ============================================================
# テスト用ヘルパー
# ============================================================

def _create_config_file(tmp_dir: Path, config_data: dict) -> Path:
    """一時ディレクトリに config.yaml を作成する。"""
    config_path = tmp_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)
    return config_path


def _create_env_file(tmp_dir: Path, env_vars: dict[str, str]) -> Path:
    """一時ディレクトリに .env ファイルを作成する。"""
    env_path = tmp_dir / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    return env_path


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


# ============================================================
# config.py のテスト
# ============================================================

class TestLoadConfig:
    """load_config() 関数のテスト。"""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """有効な config.yaml を正常に読み込めること。"""
        config_data = _minimal_config()
        config_path = _create_config_file(tmp_path, config_data)

        result = load_config(config_path)

        assert result["app"]["name"] == "Test App"
        assert result["app"]["version"] == "0.1.0"
        assert result["claude"]["model"] == "claude-sonnet-4-20250514"

    def test_load_config_file_not_found(self, tmp_path: Path) -> None:
        """存在しないファイルを指定した場合に FileNotFoundError が発生すること。"""
        config_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            load_config(config_path)

    def test_load_empty_config(self, tmp_path: Path) -> None:
        """空の config.yaml を読み込んだ場合に ConfigValidationError が発生すること。"""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")

        with pytest.raises(ConfigValidationError, match="空です"):
            load_config(config_path)


class TestValidateConfig:
    """validate_config() 関数のテスト。"""

    def test_valid_config_no_errors(self) -> None:
        """有効な設定に対してエラーが返らないこと。"""
        config = _minimal_config()
        errors = validate_config(config)
        assert errors == []

    def test_missing_required_section(self) -> None:
        """必須セクションが欠けている場合にエラーが返ること。"""
        config = _minimal_config()
        del config["claude"]

        errors = validate_config(config)
        assert any("claude" in e for e in errors)

    def test_invalid_port_range(self) -> None:
        """ポート番号が範囲外の場合にエラーが返ること。"""
        config = _minimal_config()
        config["feedback_server"]["port"] = 80

        errors = validate_config(config)
        assert any("port" in e for e in errors)

    def test_invalid_num_stories(self) -> None:
        """num_stories が不正値の場合にエラーが返ること。"""
        config = _minimal_config()
        config["collection"]["num_stories"] = -1

        errors = validate_config(config)
        assert any("num_stories" in e for e in errors)

    def test_invalid_temperature(self) -> None:
        """temperature が範囲外の場合にエラーが返ること。"""
        config = _minimal_config()
        config["claude"]["temperature"] = 1.5

        errors = validate_config(config)
        assert any("temperature" in e for e in errors)

    def test_invalid_source_url(self) -> None:
        """ソースURLが不正な形式の場合にエラーが返ること。"""
        config = _minimal_config()
        config["collection"]["sources"] = [
            {"name": "Bad Source", "url": "not-a-url", "enabled": True}
        ]

        errors = validate_config(config)
        assert any("url" in e.lower() or "URL" in e for e in errors)

    def test_invalid_log_level(self) -> None:
        """ログレベルが不正な場合にエラーが返ること。"""
        config = _minimal_config()
        config["logging"]["level"] = "INVALID"

        errors = validate_config(config)
        assert any("level" in e for e in errors)


class TestAppConfig:
    """AppConfig シングルトンクラスのテスト。"""

    # テスト間で汚染される可能性のある環境変数
    _ENV_KEYS = [
        "ANTHROPIC_API_KEY",
        "GMAIL_CREDENTIALS_PATH",
        "GMAIL_TOKEN_PATH",
        "LINE_NOTIFY_TOKEN",
        "NEWS_API_KEY",
    ]

    def setup_method(self) -> None:
        """各テスト前にシングルトンと環境変数をリセットする。"""
        AppConfig.reset()
        for key in self._ENV_KEYS:
            os.environ.pop(key, None)

    def teardown_method(self) -> None:
        """各テスト後にシングルトンと環境変数をリセットする。"""
        AppConfig.reset()
        for key in self._ENV_KEYS:
            os.environ.pop(key, None)

    def test_singleton_pattern(self, tmp_path: Path) -> None:
        """get_instance() が同一インスタンスを返すこと。"""
        config_data = _minimal_config()
        config_path = _create_config_file(tmp_path, config_data)
        env_path = _create_env_file(tmp_path, {"ANTHROPIC_API_KEY": "test-key"})

        instance1 = AppConfig.get_instance(config_path=config_path, env_path=env_path)
        instance2 = AppConfig.get_instance()

        assert instance1 is instance2

    def test_get_dot_notation(self, tmp_path: Path) -> None:
        """ドット区切りキーで設定値を取得できること。"""
        config_data = _minimal_config()
        config_path = _create_config_file(tmp_path, config_data)
        env_path = _create_env_file(tmp_path, {"ANTHROPIC_API_KEY": "test-key"})

        config = AppConfig.get_instance(config_path=config_path, env_path=env_path)

        assert config.get("app.name") == "Test App"
        assert config.get("claude.model") == "claude-sonnet-4-20250514"
        assert config.get("feedback_server.port") == 8080
        assert config.get("nonexistent.key", "default") == "default"

    def test_get_env(self, tmp_path: Path) -> None:
        """環境変数を取得できること。"""
        config_data = _minimal_config()
        config_path = _create_config_file(tmp_path, config_data)
        env_path = _create_env_file(tmp_path, {"ANTHROPIC_API_KEY": "sk-test-123"})

        config = AppConfig.get_instance(config_path=config_path, env_path=env_path)

        assert config.get_env("ANTHROPIC_API_KEY") == "sk-test-123"
        assert config.get_env("NONEXISTENT_VAR", "fallback") == "fallback"

    def test_force_reload(self, tmp_path: Path) -> None:
        """force_reload=True で設定を再読み込みできること。"""
        config_data = _minimal_config()
        config_path = _create_config_file(tmp_path, config_data)
        env_path = _create_env_file(tmp_path, {"ANTHROPIC_API_KEY": "test-key"})

        instance1 = AppConfig.get_instance(config_path=config_path, env_path=env_path)
        assert instance1.get("app.name") == "Test App"

        # config.yaml を更新
        config_data["app"]["name"] = "Updated App"
        _create_config_file(tmp_path, config_data)

        instance2 = AppConfig.get_instance(config_path=config_path, env_path=env_path, force_reload=True)
        assert instance2.get("app.name") == "Updated App"
        assert instance1 is not instance2

    def test_invalid_config_raises_error(self, tmp_path: Path) -> None:
        """不正な設定で ConfigValidationError が発生すること。"""
        config_data = {"app": {"name": "Test"}}  # 必須セクションが不足
        config_path = _create_config_file(tmp_path, config_data)
        env_path = _create_env_file(tmp_path, {})

        with pytest.raises(ConfigValidationError):
            AppConfig.get_instance(config_path=config_path, env_path=env_path)

    def test_repr(self, tmp_path: Path) -> None:
        """__repr__ が期待される形式であること。"""
        config_data = _minimal_config()
        config_path = _create_config_file(tmp_path, config_data)
        env_path = _create_env_file(tmp_path, {"ANTHROPIC_API_KEY": "test-key"})

        config = AppConfig.get_instance(config_path=config_path, env_path=env_path)
        assert "Test App" in repr(config)
        assert "0.1.0" in repr(config)


# ============================================================
# logger.py のテスト
# ============================================================

class TestSetupLogger:
    """setup_logger() 関数のテスト。"""

    def setup_method(self) -> None:
        """各テスト前にロガーをリセットする。"""
        reset_loggers()

    def teardown_method(self) -> None:
        """各テスト後にロガーをリセットする。"""
        reset_loggers()

    def test_logger_creation(self, tmp_path: Path) -> None:
        """ロガーが正常に作成されること。"""
        log_dir = tmp_path / "logs"

        logger = setup_logger(
            "test_module",
            log_dir=str(log_dir),
            log_file="test.log",
            level="DEBUG",
        )

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert logger.level == logging.DEBUG

    def test_logger_has_handlers(self, tmp_path: Path) -> None:
        """ロガーにファイルハンドラとコンソールハンドラが設定されること。"""
        log_dir = tmp_path / "logs"

        logger = setup_logger(
            "test_handlers",
            log_dir=str(log_dir),
            log_file="test.log",
            level="INFO",
        )

        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "TimedRotatingFileHandler" in handler_types
        assert "StreamHandler" in handler_types

    def test_logger_creates_log_dir(self, tmp_path: Path) -> None:
        """ログディレクトリが自動作成されること。"""
        log_dir = tmp_path / "nested" / "logs"
        assert not log_dir.exists()

        setup_logger(
            "test_dir_creation",
            log_dir=str(log_dir),
            log_file="test.log",
        )

        assert log_dir.exists()

    def test_logger_writes_to_file(self, tmp_path: Path) -> None:
        """ロガーがファイルにログを書き込むこと。"""
        log_dir = tmp_path / "logs"

        logger = setup_logger(
            "test_file_write",
            log_dir=str(log_dir),
            log_file="test.log",
            level="INFO",
        )

        logger.info("テストメッセージ")

        # ハンドラをフラッシュ
        for handler in logger.handlers:
            handler.flush()

        log_file = log_dir / "test.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "テストメッセージ" in content
        assert "INFO" in content

    def test_logger_format(self, tmp_path: Path) -> None:
        """ログフォーマットが期待通りであること。"""
        log_dir = tmp_path / "logs"

        logger = setup_logger(
            "test_format",
            log_dir=str(log_dir),
            log_file="test.log",
            level="INFO",
            log_format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        )

        logger.warning("フォーマットテスト")

        for handler in logger.handlers:
            handler.flush()

        log_file = log_dir / "test.log"
        content = log_file.read_text(encoding="utf-8")
        # フォーマット: [YYYY-MM-DD HH:MM:SS] [WARNING] [test_format] フォーマットテスト
        assert "[WARNING]" in content
        assert "[test_format]" in content
        assert "フォーマットテスト" in content

    def test_logger_no_duplicate_handlers(self, tmp_path: Path) -> None:
        """同名ロガーを複数回作成してもハンドラが重複しないこと。"""
        log_dir = tmp_path / "logs"

        logger1 = setup_logger(
            "test_no_dup",
            log_dir=str(log_dir),
            log_file="test.log",
        )
        handler_count_1 = len(logger1.handlers)

        logger2 = setup_logger(
            "test_no_dup",
            log_dir=str(log_dir),
            log_file="test.log",
        )
        handler_count_2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count_1 == handler_count_2


# ============================================================
# retry.py のテスト
# ============================================================

class TestWithRetry:
    """with_retry() デコレータのテスト。"""

    def test_success_no_retry(self) -> None:
        """正常時にリトライせず結果を返すこと。"""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0, exceptions=(ValueError,))
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        assert result == "ok"
        assert call_count == 1

    def test_retry_then_succeed(self) -> None:
        """リトライ後に成功した場合に結果を返すこと。"""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0, exceptions=(ValueError,))
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("一時的なエラー")
            return "recovered"

        result = fail_then_succeed()
        assert result == "recovered"
        assert call_count == 3

    def test_retry_exhausted_raises(self) -> None:
        """最大試行回数を超えた場合に例外が送出されること。"""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0, exceptions=(ValueError,))
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("永続的なエラー")

        with pytest.raises(ValueError, match="永続的なエラー"):
            always_fail()

        assert call_count == 3

    def test_non_retryable_exception_raises_immediately(self) -> None:
        """リトライ対象外の例外は即座に送出されること。"""
        call_count = 0

        @with_retry(max_attempts=3, backoff_base=0, exceptions=(ValueError,))
        def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("リトライ対象外")

        with pytest.raises(TypeError, match="リトライ対象外"):
            raise_type_error()

        assert call_count == 1

    def test_exponential_backoff(self) -> None:
        """指数バックオフで待機時間が増加すること。"""
        wait_times: list[float] = []

        def track_retry(attempt: int, exc: BaseException, wait_time: float) -> None:
            wait_times.append(wait_time)

        @with_retry(
            max_attempts=4,
            backoff_base=1,
            backoff_multiplier=2,
            max_wait=100,
            exceptions=(ValueError,),
            on_retry=track_retry,
        )
        def always_fail():
            raise ValueError("エラー")

        with patch("src.utils.retry.time.sleep"):
            with pytest.raises(ValueError):
                always_fail()

        # バックオフ: 1*2^0=1, 1*2^1=2, 1*2^2=4
        assert wait_times == [1.0, 2.0, 4.0]

    def test_max_wait_cap(self) -> None:
        """max_wait により待機時間が上限に制限されること。"""
        wait_times: list[float] = []

        def track_retry(attempt: int, exc: BaseException, wait_time: float) -> None:
            wait_times.append(wait_time)

        @with_retry(
            max_attempts=5,
            backoff_base=1,
            backoff_multiplier=10,
            max_wait=5,
            exceptions=(ValueError,),
            on_retry=track_retry,
        )
        def always_fail():
            raise ValueError("エラー")

        with patch("src.utils.retry.time.sleep"):
            with pytest.raises(ValueError):
                always_fail()

        # バックオフ: min(1*10^0, 5)=1, min(1*10^1, 5)=5, min(1*10^2, 5)=5, min(1*10^3, 5)=5
        assert wait_times == [1.0, 5.0, 5.0, 5.0]

    def test_preserves_function_metadata(self) -> None:
        """デコレータが元関数のメタデータを保持すること。"""

        @with_retry(max_attempts=3, backoff_base=0, exceptions=(ValueError,))
        def my_function():
            """関数のドキュメント"""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "関数のドキュメント"

    def test_on_retry_callback(self) -> None:
        """on_retry コールバックが正しく呼ばれること。"""
        callback_args: list[tuple] = []

        def on_retry_callback(attempt: int, exc: BaseException, wait_time: float) -> None:
            callback_args.append((attempt, str(exc), wait_time))

        call_count = 0

        @with_retry(
            max_attempts=3,
            backoff_base=0,
            exceptions=(RuntimeError,),
            on_retry=on_retry_callback,
        )
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"エラー {call_count}")
            return "ok"

        result = fail_twice()
        assert result == "ok"
        assert len(callback_args) == 2
        assert callback_args[0][0] == 1  # 1回目のリトライ
        assert callback_args[1][0] == 2  # 2回目のリトライ
