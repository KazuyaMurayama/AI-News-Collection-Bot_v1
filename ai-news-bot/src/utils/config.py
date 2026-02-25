"""設定管理モジュール

config.yaml と .env ファイルの読み込み、バリデーション、
アプリケーション全体で共有する設定値へのアクセスを提供する。
シングルトンパターンにより、設定は一度だけロードされる。
"""

import os
import re
import threading
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class ConfigValidationError(Exception):
    """設定バリデーションエラー"""
    pass


def _find_project_root() -> Path:
    """プロジェクトルート（config.yaml が存在するディレクトリ）を探索する。

    以下の順序で探索する:
    1. 環境変数 APP_ROOT が設定されている場合はそのパス
    2. カレントディレクトリから上位に向かって config.yaml を探索
    3. このファイルから2階層上（src/utils/ -> プロジェクトルート）
    """
    # 環境変数による明示的な指定
    env_root = os.environ.get("APP_ROOT")
    if env_root:
        return Path(env_root)

    # カレントディレクトリから上方向へ探索
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "config.yaml").exists():
            return parent

    # フォールバック: このファイルの2階層上
    return Path(__file__).resolve().parent.parent.parent


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """config.yaml を読み込み、辞書として返す。

    Args:
        config_path: config.yaml のパス。None の場合はプロジェクトルートから自動検出。

    Returns:
        設定値を含む辞書。

    Raises:
        FileNotFoundError: config.yaml が見つからない場合。
        yaml.YAMLError: YAML のパースに失敗した場合。
    """
    if config_path is None:
        config_path = _find_project_root() / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ConfigValidationError("config.yaml が空です")

    return config


def load_env(env_path: str | Path | None = None) -> None:
    """.env ファイルを読み込み、環境変数に設定する。

    Args:
        env_path: .env ファイルのパス。None の場合はプロジェクトルートから自動検出。
    """
    if env_path is None:
        env_path = _find_project_root() / ".env"
    else:
        env_path = Path(env_path)

    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path), override=False)


def validate_config(config: dict[str, Any]) -> list[str]:
    """設定値のバリデーションを実行する。

    Args:
        config: load_config() で読み込んだ設定辞書。

    Returns:
        エラーメッセージのリスト。空リストの場合はバリデーション成功。
    """
    errors: list[str] = []

    # --- 必須セクションの存在チェック ---
    required_sections = ["app", "collection", "claude", "selection", "delivery",
                         "feedback_server", "knowledge_base", "logging", "retry"]
    for section in required_sections:
        if section not in config:
            errors.append(f"必須セクション '{section}' が config.yaml に存在しません")

    # 必須セクションが無い場合、以降のチェックは不要
    if errors:
        return errors

    # --- app セクション ---
    app = config.get("app", {})
    if not app.get("name"):
        errors.append("app.name が設定されていません")
    if not app.get("version"):
        errors.append("app.version が設定されていません")

    # --- collection セクション ---
    collection = config.get("collection", {})
    num_stories = collection.get("num_stories")
    if num_stories is not None and (not isinstance(num_stories, int) or num_stories < 1):
        errors.append("collection.num_stories は 1 以上の整数である必要があります")

    sources = collection.get("sources", [])
    url_pattern = re.compile(r"^https?://")
    for i, source in enumerate(sources):
        url = source.get("url", "")
        if url and not url_pattern.match(url):
            errors.append(f"collection.sources[{i}].url が不正なURL形式です: {url}")

    # --- claude セクション ---
    claude = config.get("claude", {})
    if not claude.get("model"):
        errors.append("claude.model が設定されていません")
    max_tokens = claude.get("max_tokens")
    if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens < 1):
        errors.append("claude.max_tokens は 1 以上の整数である必要があります")
    temperature = claude.get("temperature")
    if temperature is not None and (not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 1):
        errors.append("claude.temperature は 0.0 ~ 1.0 の数値である必要があります")

    # --- feedback_server セクション ---
    fb = config.get("feedback_server", {})
    port = fb.get("port")
    if port is not None and (not isinstance(port, int) or port < 1024 or port > 65535):
        errors.append("feedback_server.port は 1024 ~ 65535 の範囲である必要があります")

    # --- logging セクション ---
    log_cfg = config.get("logging", {})
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    level = log_cfg.get("level", "INFO")
    if level.upper() not in valid_levels:
        errors.append(f"logging.level が不正です: {level} (有効値: {valid_levels})")

    retention = log_cfg.get("retention_days")
    if retention is not None and (not isinstance(retention, int) or retention < 1):
        errors.append("logging.retention_days は 1 以上の整数である必要があります")

    # --- retry セクション ---
    retry = config.get("retry", {})
    max_attempts = retry.get("max_attempts")
    if max_attempts is not None and (not isinstance(max_attempts, int) or max_attempts < 1):
        errors.append("retry.max_attempts は 1 以上の整数である必要があります")

    return errors


def validate_env(config: dict[str, Any]) -> list[str]:
    """環境変数のバリデーションを実行する。

    config の enabled フラグに応じて、必要な環境変数が設定されているかチェックする。

    Args:
        config: load_config() で読み込んだ設定辞書。

    Returns:
        エラーメッセージのリスト。空リストの場合はバリデーション成功。
    """
    errors: list[str] = []

    # ANTHROPIC_API_KEY は常に必須
    if not os.environ.get("ANTHROPIC_API_KEY"):
        errors.append("環境変数 ANTHROPIC_API_KEY が設定されていません")

    # Gmail が有効な場合
    delivery = config.get("delivery", {})
    gmail_cfg = delivery.get("gmail", {})
    if gmail_cfg.get("enabled", False):
        if not os.environ.get("GMAIL_CREDENTIALS_PATH") and not os.environ.get("GMAIL_TOKEN_PATH"):
            errors.append(
                "Gmail が有効ですが、GMAIL_CREDENTIALS_PATH または GMAIL_TOKEN_PATH が設定されていません"
            )

    # LINE が有効な場合
    line_cfg = delivery.get("line", {})
    if line_cfg.get("enabled", False):
        if not os.environ.get("LINE_NOTIFY_TOKEN"):
            errors.append("LINE が有効ですが、LINE_NOTIFY_TOKEN が設定されていません")

    # NewsAPI の確認（sources の中に newsapi 設定がある場合）
    # config.yaml に newsapi セクションがあるかチェック
    newsapi_cfg = config.get("sources", {}).get("newsapi", {}) if isinstance(config.get("sources"), dict) else {}
    if newsapi_cfg.get("enabled", False):
        if not os.environ.get("NEWS_API_KEY"):
            errors.append("NewsAPI が有効ですが、NEWS_API_KEY が設定されていません")

    return errors


class AppConfig:
    """アプリケーション設定のシングルトンクラス。

    アプリケーション全体で一つの設定インスタンスを共有するために使用する。
    スレッドセーフな実装。

    使用例::

        # 初期化（アプリ起動時に1回呼ぶ）
        config = AppConfig.get_instance()

        # 設定値へのアクセス
        model = config.get("claude.model")
        port = config.get("feedback_server.port", default=8080)

        # 環境変数へのアクセス
        api_key = config.get_env("ANTHROPIC_API_KEY")
    """

    _instance: "AppConfig | None" = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, config_path: str | Path | None = None, env_path: str | Path | None = None):
        """設定を読み込み、バリデーションを実行する。

        Args:
            config_path: config.yaml のパス。
            env_path: .env ファイルのパス。

        Raises:
            ConfigValidationError: バリデーションエラーがある場合。
        """
        # .env ファイルの読み込み
        load_env(env_path)

        # config.yaml の読み込み
        self._config = load_config(config_path)
        self._config_path = config_path
        self._env_path = env_path

        # バリデーション
        config_errors = validate_config(self._config)
        if config_errors:
            raise ConfigValidationError(
                "設定ファイルにエラーがあります:\n" + "\n".join(f"  - {e}" for e in config_errors)
            )

    @classmethod
    def get_instance(
        cls,
        config_path: str | Path | None = None,
        env_path: str | Path | None = None,
        force_reload: bool = False,
    ) -> "AppConfig":
        """シングルトンインスタンスを取得する。

        Args:
            config_path: config.yaml のパス（初回呼び出し時のみ有効）。
            env_path: .env ファイルのパス（初回呼び出し時のみ有効）。
            force_reload: True の場合、既存のインスタンスを破棄して再読み込みする。

        Returns:
            AppConfig のシングルトンインスタンス。
        """
        if cls._instance is None or force_reload:
            with cls._lock:
                if cls._instance is None or force_reload:
                    cls._instance = cls(config_path=config_path, env_path=env_path)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """シングルトンインスタンスをリセットする（テスト用）。"""
        with cls._lock:
            cls._instance = None

    @property
    def raw(self) -> dict[str, Any]:
        """生の設定辞書を返す。"""
        return self._config

    def get(self, key_path: str, default: Any = None) -> Any:
        """ドット区切りのキーパスで設定値を取得する。

        Args:
            key_path: ドット区切りのキーパス (例: "claude.model")。
            default: キーが存在しない場合のデフォルト値。

        Returns:
            設定値。キーが存在しない場合は default。

        使用例::

            config.get("app.name")           # -> "AI News Collector Bot"
            config.get("claude.model")       # -> "claude-sonnet-4-20250514"
            config.get("nonexistent", "x")   # -> "x"
        """
        keys = key_path.split(".")
        value: Any = self._config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value

    def get_env(self, key: str, default: str | None = None) -> str | None:
        """環境変数を取得する。

        Args:
            key: 環境変数名。
            default: 環境変数が未設定の場合のデフォルト値。

        Returns:
            環境変数の値。未設定の場合は default。
        """
        return os.environ.get(key, default)

    def validate_all(self) -> list[str]:
        """設定ファイルと環境変数の全バリデーションを実行する。

        Returns:
            エラーメッセージのリスト。空リストの場合はすべて正常。
        """
        errors = validate_config(self._config)
        errors.extend(validate_env(self._config))
        return errors

    def __repr__(self) -> str:
        app_name = self.get("app.name", "unknown")
        version = self.get("app.version", "unknown")
        return f"<AppConfig {app_name} v{version}>"
