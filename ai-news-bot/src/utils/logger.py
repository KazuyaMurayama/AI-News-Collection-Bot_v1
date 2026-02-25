"""ログ管理モジュール

日次ローテーション付きファイルハンドラとコンソールハンドラを設定し、
アプリケーション全体で統一されたログフォーマットを提供する。

フォーマット: [YYYY-MM-DD HH:MM:SS] [LEVEL] [MODULE] MESSAGE
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any


# デフォルト設定値
_DEFAULT_LOG_DIR = "./logs/"
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_RETENTION_DAYS = 30
_DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
_DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 初期化済みロガー名のトラッキング
_initialized_loggers: set[str] = set()


def _get_log_config() -> dict[str, Any]:
    """config.yaml からログ設定を取得する。

    config.yaml が読み込めない場合はデフォルト値を使用する。

    Returns:
        ログ設定の辞書。
    """
    try:
        from src.utils.config import load_config
        config = load_config()
        log_cfg = config.get("logging", {})
        return {
            "level": log_cfg.get("level", _DEFAULT_LOG_LEVEL),
            "dir": log_cfg.get("dir", _DEFAULT_LOG_DIR),
            "app_log": log_cfg.get("app_log", "app.log"),
            "retention_days": log_cfg.get("retention_days", _DEFAULT_RETENTION_DAYS),
            "format": log_cfg.get("format", _DEFAULT_LOG_FORMAT),
        }
    except Exception:
        return {
            "level": _DEFAULT_LOG_LEVEL,
            "dir": _DEFAULT_LOG_DIR,
            "app_log": "app.log",
            "retention_days": _DEFAULT_RETENTION_DAYS,
            "format": _DEFAULT_LOG_FORMAT,
        }


def setup_logger(
    name: str,
    log_dir: str | Path | None = None,
    log_file: str | None = None,
    level: str | None = None,
    log_format: str | None = None,
    retention_days: int | None = None,
) -> logging.Logger:
    """名前付きロガーをセットアップして返す。

    日次ローテーション付きファイルハンドラとコンソールハンドラを設定する。
    同名ロガーが既に初期化済みの場合は、ハンドラの重複追加を避けて既存のロガーを返す。

    Args:
        name: ロガー名（通常はモジュール名）。
        log_dir: ログ出力ディレクトリ。None の場合は config.yaml から取得。
        log_file: ログファイル名。None の場合は config.yaml から取得。
        level: ログレベル文字列。None の場合は config.yaml から取得。
        log_format: ログフォーマット文字列。None の場合は config.yaml から取得。
        retention_days: ログ保持日数。None の場合は config.yaml から取得。

    Returns:
        設定済みの logging.Logger インスタンス。

    使用例::

        from src.utils.logger import setup_logger

        logger = setup_logger(__name__)
        logger.info("処理を開始します")
        logger.error("エラーが発生しました", exc_info=True)
    """
    # 既に初期化済みならそのまま返す
    if name in _initialized_loggers:
        return logging.getLogger(name)

    # 設定の取得
    cfg = _get_log_config()
    log_dir = Path(log_dir or cfg["dir"])
    log_file = log_file or cfg["app_log"]
    level = level or cfg["level"]
    log_format = log_format or cfg["format"]
    retention_days = retention_days if retention_days is not None else cfg["retention_days"]

    # ログディレクトリの作成
    log_dir.mkdir(parents=True, exist_ok=True)

    # ロガーの取得と設定
    logger = logging.getLogger(name)
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # フォーマッタの作成
    formatter = logging.Formatter(
        fmt=log_format,
        datefmt=_DEFAULT_DATE_FORMAT,
    )

    # --- ファイルハンドラ（日次ローテーション） ---
    log_filepath = log_dir / log_file
    file_handler = TimedRotatingFileHandler(
        filename=str(log_filepath),
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # --- コンソールハンドラ ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 親ロガーへの伝搬を抑制（重複出力防止）
    logger.propagate = False

    # 初期化済みとして記録
    _initialized_loggers.add(name)

    return logger


def reset_loggers() -> None:
    """全ての初期化済みロガーをリセットする（テスト用）。

    登録済みのハンドラをすべて除去し、初期化済みトラッキングをクリアする。
    """
    for name in list(_initialized_loggers):
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
    _initialized_loggers.clear()
