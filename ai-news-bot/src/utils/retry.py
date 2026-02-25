"""リトライ機能モジュール

デコレータベースの指数バックオフ付きリトライ機能を提供する。
リトライ対象の例外を指定可能で、各リトライ時にログを出力する。

使用例::

    from src.utils.retry import with_retry

    @with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError))
    def fetch_data(url: str) -> dict:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
"""

import functools
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

# デフォルト設定値
_DEFAULT_MAX_ATTEMPTS = 3
_DEFAULT_BACKOFF_BASE = 1
_DEFAULT_BACKOFF_MULTIPLIER = 2
_DEFAULT_MAX_WAIT = 30

# リトライ対象のデフォルト例外
_DEFAULT_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

logger = logging.getLogger(__name__)


def _get_retry_config() -> dict[str, Any]:
    """config.yaml からリトライ設定を取得する。

    config.yaml が読み込めない場合はデフォルト値を使用する。

    Returns:
        リトライ設定の辞書。
    """
    try:
        from src.utils.config import load_config
        config = load_config()
        retry_cfg = config.get("retry", {})
        return {
            "max_attempts": retry_cfg.get("max_attempts", _DEFAULT_MAX_ATTEMPTS),
            "backoff_base": retry_cfg.get("backoff_base", _DEFAULT_BACKOFF_BASE),
            "backoff_multiplier": retry_cfg.get("backoff_multiplier", _DEFAULT_BACKOFF_MULTIPLIER),
            "max_wait": retry_cfg.get("max_wait", _DEFAULT_MAX_WAIT),
        }
    except Exception:
        return {
            "max_attempts": _DEFAULT_MAX_ATTEMPTS,
            "backoff_base": _DEFAULT_BACKOFF_BASE,
            "backoff_multiplier": _DEFAULT_BACKOFF_MULTIPLIER,
            "max_wait": _DEFAULT_MAX_WAIT,
        }


def with_retry(
    max_attempts: int | None = None,
    backoff_base: float | None = None,
    backoff_multiplier: float | None = None,
    max_wait: float | None = None,
    exceptions: tuple[type[BaseException], ...] | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> Callable[[F], F]:
    """指数バックオフ付きリトライデコレータ。

    対象関数で指定された例外が発生した場合、指数バックオフで待機しつつ
    最大試行回数までリトライする。

    Args:
        max_attempts: 最大試行回数（初回を含む）。None の場合は config.yaml から取得。
        backoff_base: バックオフの初期待機時間（秒）。None の場合は config.yaml から取得。
        backoff_multiplier: バックオフの乗数。None の場合は config.yaml から取得。
        max_wait: 最大待機時間（秒）。None の場合は config.yaml から取得。
        exceptions: リトライ対象の例外タプル。None の場合はデフォルト例外を使用。
        on_retry: リトライ時に呼ばれるコールバック。引数は (試行番号, 例外, 待機時間)。

    Returns:
        デコレータ関数。

    使用例::

        @with_retry(max_attempts=5, exceptions=(requests.RequestException,))
        def call_api():
            ...

        @with_retry()  # config.yaml のデフォルト設定を使用
        def fetch_rss(url):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 設定の解決（呼び出し時に解決することでテスト時のオーバーライドに対応）
            cfg = _get_retry_config()
            _max_attempts = max_attempts if max_attempts is not None else cfg["max_attempts"]
            _backoff_base = backoff_base if backoff_base is not None else cfg["backoff_base"]
            _backoff_multiplier = backoff_multiplier if backoff_multiplier is not None else cfg["backoff_multiplier"]
            _max_wait = max_wait if max_wait is not None else cfg["max_wait"]
            _exceptions = exceptions if exceptions is not None else _DEFAULT_EXCEPTIONS

            last_exception: BaseException | None = None

            for attempt in range(1, _max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except _exceptions as e:
                    last_exception = e

                    if attempt >= _max_attempts:
                        logger.error(
                            "リトライ上限に達しました: %s (関数: %s, 試行: %d/%d)",
                            str(e),
                            func.__name__,
                            attempt,
                            _max_attempts,
                        )
                        raise

                    # 指数バックオフの計算
                    wait_time = min(
                        _backoff_base * (_backoff_multiplier ** (attempt - 1)),
                        _max_wait,
                    )

                    logger.warning(
                        "リトライします: %s (関数: %s, 試行: %d/%d, 待機: %.1f秒)",
                        str(e),
                        func.__name__,
                        attempt,
                        _max_attempts,
                        wait_time,
                    )

                    # コールバックの呼び出し
                    if on_retry is not None:
                        on_retry(attempt, e, wait_time)

                    time.sleep(wait_time)

            # ここには到達しないが、型チェッカーのために記述
            if last_exception is not None:
                raise last_exception

        return wrapper  # type: ignore[return-value]
    return decorator
