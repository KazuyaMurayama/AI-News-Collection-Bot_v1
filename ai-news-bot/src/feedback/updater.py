"""Markdown Frontmatter 更新モジュール

python-frontmatter を使用して、ナレッジベースの日次 Markdown ファイルに
リアクション情報（reaction, rating, reacted_at）を書き込む。

ファイルロックにより複数同時アクセスに対応する。
"""

import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import frontmatter

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# リアクション種別と rating の対応マッピング
REACTION_MAP: dict[str, dict[str, Any]] = {
    "excellent":   {"emoji": "⭐", "label": "素晴らしい", "rating": 5},
    "good":        {"emoji": "👍", "label": "良い", "rating": 4},
    "read_later":  {"emoji": "📌", "label": "後で読む", "rating": 3},
    "so_so":       {"emoji": "🤔", "label": "微妙", "rating": 2},
}

# ファイル単位のロック管理
_file_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()

# JST タイムゾーン
_JST = timezone(timedelta(hours=9))


def _get_file_lock(filepath: str) -> threading.Lock:
    """ファイルパスに対応するスレッドロックを取得する。

    同一ファイルへの同時書き込みを防止するために使用する。

    Args:
        filepath: 対象ファイルのパス文字列。

    Returns:
        ファイルパスに紐づく threading.Lock インスタンス。
    """
    with _locks_lock:
        if filepath not in _file_locks:
            _file_locks[filepath] = threading.Lock()
        return _file_locks[filepath]


def _resolve_daily_dir() -> Path:
    """config.yaml からナレッジベースの daily ディレクトリパスを解決する。

    config.yaml が読み込めない場合はデフォルトパスを使用する。

    Returns:
        daily ディレクトリの Path オブジェクト。
    """
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        daily_dir = config.get("knowledge_base.daily_dir", "./knowledge_base/daily")
    except Exception:
        daily_dir = "./knowledge_base/daily"
    return Path(daily_dir)


def _build_md_filepath(date: str, daily_dir: Path | None = None) -> Path:
    """日付から Markdown ファイルのパスを構築する。

    Args:
        date: 日付文字列 (YYYY-MM-DD)。
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        Markdown ファイルの Path オブジェクト。
    """
    if daily_dir is None:
        daily_dir = _resolve_daily_dir()
    return daily_dir / f"{date}_ai_news.md"


def update_reaction(
    date: str,
    story_id: int,
    reaction_type: str,
    daily_dir: Path | str | None = None,
) -> bool:
    """指定した日次レポートのストーリーにリアクションを記録する。

    Markdown ファイルの Frontmatter 内にある stories 配列から、
    該当 story_id のエントリを探し、reaction / rating / reacted_at を更新する。

    Args:
        date: 記事の日付 (YYYY-MM-DD)。
        story_id: ストーリー ID (1-3)。
        reaction_type: リアクション種別 ("excellent", "good", "bookmark", "meh")。
        daily_dir: daily ディレクトリのパス。None の場合は設定から自動解決。

    Returns:
        更新成功時は True、失敗時は False。

    Raises:
        FileNotFoundError: 対象の Markdown ファイルが存在しない場合。
        ValueError: reaction_type が不正な場合。
    """
    # バリデーション: reaction_type
    if reaction_type not in REACTION_MAP:
        valid_types = ", ".join(REACTION_MAP.keys())
        raise ValueError(
            f"Invalid reaction type: '{reaction_type}'. Must be one of: {valid_types}"
        )

    # バリデーション: story_id
    if not isinstance(story_id, int) or story_id < 1 or story_id > 3:
        raise ValueError(
            f"Invalid story_id: {story_id}. Must be an integer between 1 and 3."
        )

    # ファイルパスの解決
    if daily_dir is not None:
        daily_dir = Path(daily_dir)
    md_path = _build_md_filepath(date, daily_dir)

    if not md_path.exists():
        raise FileNotFoundError(
            f"Article not found: {date}, story {story_id} (file: {md_path})"
        )

    filepath_str = str(md_path.resolve())
    lock = _get_file_lock(filepath_str)

    with lock:
        try:
            # Frontmatter 付き Markdown の読み込み
            post = frontmatter.load(str(md_path))
            metadata = post.metadata

            # stories 配列の取得
            stories: list[dict[str, Any]] = metadata.get("stories", [])
            if not stories:
                logger.error(
                    "Frontmatter に stories が存在しません: %s", md_path
                )
                return False

            # 該当ストーリーの検索
            target_story: dict[str, Any] | None = None
            for story in stories:
                if story.get("id") == story_id:
                    target_story = story
                    break

            if target_story is None:
                logger.error(
                    "story_id=%d が見つかりません: %s", story_id, md_path
                )
                return False

            # リアクション情報の更新（カウンターベース）
            now_jst = datetime.now(_JST).isoformat()

            # stories[].reactions のカウンターをインクリメント
            reactions = target_story.get("reactions", {
                "excellent": 0, "good": 0, "so_so": 0, "read_later": 0,
            })
            if not isinstance(reactions, dict):
                reactions = {"excellent": 0, "good": 0, "so_so": 0, "read_later": 0}
            reactions[reaction_type] = reactions.get(reaction_type, 0) + 1
            target_story["reactions"] = reactions

            # total_reactions の更新
            total_reactions = metadata.get("total_reactions", {
                "excellent": 0, "good": 0, "so_so": 0, "read_later": 0,
            })
            if not isinstance(total_reactions, dict):
                total_reactions = {"excellent": 0, "good": 0, "so_so": 0, "read_later": 0}
            total_reactions[reaction_type] = total_reactions.get(reaction_type, 0) + 1
            metadata["total_reactions"] = total_reactions

            # ファイルに書き戻し
            frontmatter.dump(post, str(md_path))

            logger.info(
                "リアクション更新完了: date=%s, story=%d, reaction=%s, count=%d",
                date,
                story_id,
                reaction_type,
                reactions[reaction_type],
            )
            return True

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "リアクション更新中にエラーが発生しました: %s (file: %s)",
                str(e),
                md_path,
                exc_info=True,
            )
            return False
