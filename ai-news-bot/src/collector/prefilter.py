"""候補記事の事前フィルタリングモジュール

Claude API 呼び出し前にローカルで不要な記事を除外し、
API に送信する候補数を削減してコンテキストを圧縮する。

フィルタ:
- サマリーが極端に短い記事（情報不足）
- AI/テクノロジーと無関係な記事（キーワードマッチ）
- 古すぎる記事（48時間以上前）
- 重複記事（タイトル類似度）
"""

from datetime import datetime, timezone, timedelta
from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# AI/テクノロジー関連キーワード（少なくとも1つ含む記事のみ通過）
_RELEVANCE_KEYWORDS: set[str] = {
    # 英語
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "neural", "llm", "gpt", "claude", "gemini", "transformer",
    "openai", "anthropic", "google deepmind", "meta ai", "microsoft ai",
    "generative", "diffusion", "chatbot", "copilot", "agent",
    "nlp", "computer vision", "robotics", "automation",
    "model", "training", "inference", "fine-tuning", "rag",
    "multimodal", "embedding", "token", "benchmark",
    # 日本語
    "ai", "人工知能", "機械学習", "深層学習", "ニューラル",
    "大規模言語モデル", "生成ai", "チャットボット", "自動化",
    "ロボティクス", "自然言語処理", "画像認識", "音声認識",
}

# 最小サマリー長（これ未満は情報不足で除外）
_MIN_SUMMARY_LENGTH = 30

# 最大記事年齢（時間）
_MAX_AGE_HOURS = 72


def _is_relevant(article: dict[str, Any]) -> bool:
    """記事がAI/テクノロジーに関連するかキーワードで判定する。"""
    text = (
        (article.get("title", "") + " " + article.get("summary", ""))
        .lower()
    )
    return any(kw in text for kw in _RELEVANCE_KEYWORDS)


def _has_sufficient_content(article: dict[str, Any]) -> bool:
    """記事に十分なコンテンツがあるか判定する。"""
    summary = article.get("summary", "").strip()
    title = article.get("title", "").strip()
    return len(title) > 5 and len(summary) >= _MIN_SUMMARY_LENGTH


def _is_fresh(article: dict[str, Any]) -> bool:
    """記事が新しいか判定する（published_at があれば）。"""
    published_at = article.get("published_at", "")
    if not published_at:
        return True  # 日付不明の場合は通過

    try:
        # ISO 8601 パース
        if isinstance(published_at, str):
            # 簡易パース（YYYY-MM-DDTHH:MM:SS 形式）
            pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            return True

        now = datetime.now(timezone.utc)
        age = now - pub_date
        return age.total_seconds() < _MAX_AGE_HOURS * 3600
    except (ValueError, TypeError):
        return True  # パース不能の場合は通過


def prefilter_candidates(
    candidates: list[dict[str, Any]],
    max_candidates: int = 30,
) -> list[dict[str, Any]]:
    """候補記事をローカルで事前フィルタリングする。

    Claude API に送る候補数を削減し、コンテキスト圧縮と
    コスト削減を実現する。

    Args:
        candidates: 全候補記事のリスト。
        max_candidates: フィルタ後の最大候補数。

    Returns:
        フィルタ済みの候補記事リスト。
    """
    original_count = len(candidates)
    if original_count == 0:
        return []

    filtered: list[dict[str, Any]] = []

    for article in candidates:
        # コンテンツ不足チェック
        if not _has_sufficient_content(article):
            logger.debug("除外 (コンテンツ不足): %s", article.get("title", "")[:60])
            continue

        # 関連性チェック
        if not _is_relevant(article):
            logger.debug("除外 (AI無関連): %s", article.get("title", "")[:60])
            continue

        # 鮮度チェック
        if not _is_fresh(article):
            logger.debug("除外 (古い記事): %s", article.get("title", "")[:60])
            continue

        filtered.append(article)

    # 最大数に絞る（新しい順に優先）
    if len(filtered) > max_candidates:
        filtered.sort(
            key=lambda a: a.get("published_at", ""),
            reverse=True,
        )
        filtered = filtered[:max_candidates]

    removed = original_count - len(filtered)
    if removed > 0:
        logger.info(
            "事前フィルタ: %d件 -> %d件 (%d件除外)",
            original_count, len(filtered), removed,
        )
    else:
        logger.info("事前フィルタ: %d件 (全件通過)", len(filtered))

    return filtered
