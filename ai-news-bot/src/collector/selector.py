"""記事選定モジュール

Anthropic Claude API を使用して候補記事をスコアリングし、上位記事を選定する。
スコアリング基準:
  - 先進性 (0-5): 新技術・新手法の度合い
  - 意外性 (0-5): 予想外の活用法
  - 実用性 (0-5): すぐに業務適用可能か
  - 日本企業関連性 (0-3): 日本市場・企業への適用可能性
  - 鮮度 (0-2): 24時間以内の記事を優先

使用例::

    from src.collector.selector import select_top_articles

    candidates = [...]  # collect_from_rss 等で取得した記事リスト
    top_articles = select_top_articles(candidates, num=3)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# スコアリング基準の最大値定義
_SCORING_CRITERIA = {
    "novelty": 5,        # 先進性
    "surprise": 5,       # 意外性
    "practicality": 5,   # 実用性
    "japan_relevance": 3, # 日本企業関連性
    "freshness": 2,      # 鮮度
}
_MAX_TOTAL_SCORE = sum(_SCORING_CRITERIA.values())  # 20

# Claude API に送るスコアリングシステムプロンプト
_DEFAULT_SCORING_SYSTEM_PROMPT = """\
あなたはAIニュースの専門アナリストです。
以下の基準で各記事をスコアリングしてください。

## スコアリング基準
- novelty (先進性, 0-5): 新技術・新手法の度合い
- surprise (意外性, 0-5): 予想外の活用法・意外な展開
- practicality (実用性, 0-5): すぐに業務適用可能か
- japan_relevance (日本企業関連性, 0-3): 日本市場・企業への適用可能性
- freshness (鮮度, 0-2): 新しい記事ほど高スコア

## 出力形式
以下の JSON 形式で回答してください。必ず有効な JSON のみを出力し、説明文は含めないでください。

```json
[
  {
    "index": 0,
    "novelty": 4,
    "surprise": 3,
    "practicality": 5,
    "japan_relevance": 2,
    "freshness": 2,
    "total": 16,
    "reason": "スコアリングの理由を1文で"
  }
]
```
"""


def _build_scoring_prompt(candidates: list[dict[str, Any]]) -> str:
    """候補記事リストからスコアリング用のプロンプトを生成する。

    Args:
        candidates: 候補記事のリスト。

    Returns:
        スコアリング依頼のプロンプト文字列。
    """
    articles_text = []
    for i, article in enumerate(candidates):
        text = (
            f"[記事 {i}]\n"
            f"タイトル: {article.get('title', 'N/A')}\n"
            f"ソース: {article.get('source', 'N/A')}\n"
            f"概要: {article.get('summary', 'N/A')}\n"
            f"公開日時: {article.get('published_at', 'N/A')}\n"
            f"URL: {article.get('url', 'N/A')}\n"
        )
        articles_text.append(text)

    joined = "\n---\n".join(articles_text)
    return (
        f"以下の {len(candidates)} 件の記事をスコアリングしてください。\n\n"
        f"{joined}\n\n"
        f"全記事のスコアを JSON 配列で返してください。"
    )


def _parse_scoring_response(response_text: str, num_candidates: int) -> list[dict[str, Any]]:
    """Claude API のスコアリングレスポンスを解析する。

    Args:
        response_text: Claude API のレスポンステキスト。
        num_candidates: 候補記事の件数（整合性チェック用）。

    Returns:
        スコア情報の辞書のリスト。パースに失敗した場合は空リスト。
    """
    try:
        # JSON ブロックの抽出（```json ... ``` で囲まれている場合に対応）
        text = response_text.strip()
        if "```json" in text:
            start = text.index("```json") + len("```json")
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
            else:
                text = text[start:].strip()
        elif "```" in text:
            start = text.index("```") + len("```")
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
            else:
                text = text[start:].strip()

        # JSON 配列部分のみを抽出（前後に余計なテキストがある場合に対応）
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
            text = text[bracket_start:bracket_end + 1]

        scores = json.loads(text)

        if not isinstance(scores, list):
            logger.error("スコアリングレスポンスがリスト形式ではありません")
            return []

        # 各スコアのバリデーション
        validated_scores: list[dict[str, Any]] = []
        for score in scores:
            if not isinstance(score, dict):
                continue

            validated = {
                "index": score.get("index", len(validated_scores)),
                "novelty": _clamp(score.get("novelty", 0), 0, _SCORING_CRITERIA["novelty"]),
                "surprise": _clamp(score.get("surprise", 0), 0, _SCORING_CRITERIA["surprise"]),
                "practicality": _clamp(
                    score.get("practicality", 0), 0, _SCORING_CRITERIA["practicality"]
                ),
                "japan_relevance": _clamp(
                    score.get("japan_relevance", 0), 0, _SCORING_CRITERIA["japan_relevance"]
                ),
                "freshness": _clamp(
                    score.get("freshness", 0), 0, _SCORING_CRITERIA["freshness"]
                ),
                "reason": score.get("reason", ""),
            }
            validated["total"] = (
                validated["novelty"]
                + validated["surprise"]
                + validated["practicality"]
                + validated["japan_relevance"]
                + validated["freshness"]
            )
            validated_scores.append(validated)

        return validated_scores

    except (json.JSONDecodeError, ValueError, IndexError) as e:
        logger.error("スコアリングレスポンスの解析に失敗しました: %s", str(e))
        return []


def _clamp(value: Any, min_val: int, max_val: int) -> int:
    """値を指定範囲内にクランプする。

    Args:
        value: クランプ対象の値。
        min_val: 最小値。
        max_val: 最大値。

    Returns:
        クランプされた整数値。数値でない場合は 0。
    """
    try:
        v = int(value)
        return max(min_val, min(v, max_val))
    except (TypeError, ValueError):
        return 0


def _score_with_claude(
    candidates: list[dict[str, Any]],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    temperature: float = 0.3,
    api_key: str | None = None,
    system_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """Claude API を使って候補記事をスコアリングする。

    Args:
        candidates: 候補記事のリスト。
        model: 使用する Claude モデル。
        max_tokens: 最大出力トークン数。
        temperature: 生成温度。
        api_key: Anthropic API キー。None の場合は環境変数から取得。
        system_prompt: システムプロンプト。None の場合はデフォルトを使用。

    Returns:
        スコア情報の辞書のリスト。API 呼び出しに失敗した場合は空リスト。
    """
    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not resolved_key:
        logger.warning("ANTHROPIC_API_KEY が設定されていません。スコアリングをスキップします。")
        return []

    resolved_system = system_prompt or _DEFAULT_SCORING_SYSTEM_PROMPT
    user_prompt = _build_scoring_prompt(candidates)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=resolved_key)

        logger.info(
            "Claude API でスコアリングを実行中: %d 件の候補, モデル=%s",
            len(candidates),
            model,
        )

        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=resolved_system,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )

        # レスポンスからテキストを抽出
        response_text = ""
        for block in message.content:
            if hasattr(block, "text"):
                response_text += block.text

        if not response_text:
            logger.error("Claude API からの応答が空です")
            return []

        logger.debug("Claude API スコアリングレスポンス: %s", response_text[:200])

        scores = _parse_scoring_response(response_text, len(candidates))
        logger.info("スコアリング結果: %d 件のスコアを取得", len(scores))
        return scores

    except Exception as e:
        logger.error("Claude API スコアリングに失敗しました: %s", str(e))
        return []


def _fallback_select_by_recency(
    candidates: list[dict[str, Any]],
    num: int,
) -> list[dict[str, Any]]:
    """フォールバック: 公開日時の新しい順に記事を選定する。

    Claude API によるスコアリングが利用できない場合のフォールバック。

    Args:
        candidates: 候補記事のリスト。
        num: 選定件数。

    Returns:
        選定された記事のリスト。
    """
    logger.warning("フォールバック選定を実行します: 時間順で上位 %d 件を選定", num)

    def sort_key(article: dict[str, Any]) -> str:
        return article.get("published_at", "")

    sorted_candidates = sorted(candidates, key=sort_key, reverse=True)
    selected = sorted_candidates[:num]

    # フォールバック時はスコアを付与しない
    for article in selected:
        article["score"] = {
            "novelty": 0,
            "surprise": 0,
            "practicality": 0,
            "japan_relevance": 0,
            "freshness": 0,
            "total": 0,
            "reason": "フォールバック選定（時間順）",
        }

    return selected


def _deduplicate_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """候補記事の重複を排除する。

    同一 URL の記事を排除する。タイトルの完全一致も重複と見なす。

    Args:
        candidates: 候補記事のリスト。

    Returns:
        重複排除後の記事リスト。
    """
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict[str, Any]] = []

    for article in candidates:
        url = article.get("url", "").strip().rstrip("/")
        title = article.get("title", "").strip().lower()

        if url in seen_urls or title in seen_titles:
            continue

        seen_urls.add(url)
        if title:
            seen_titles.add(title)
        unique.append(article)

    deduped_count = len(candidates) - len(unique)
    if deduped_count > 0:
        logger.info("重複記事を %d 件排除しました (%d -> %d)", deduped_count, len(candidates), len(unique))

    return unique


def select_top_articles(
    candidates: list[dict[str, Any]],
    num: int = 3,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    api_key: str | None = None,
    system_prompt: str | None = None,
) -> list[dict[str, Any]]:
    """候補記事をスコアリングし、上位 N 件を選定する。

    1. 重複排除
    2. Claude API によるスコアリング（失敗時は時間順フォールバック）
    3. スコア上位 N 件を選定して返す

    Args:
        candidates: 候補記事のリスト。
        num: 選定件数（デフォルト: 3）。
        model: 使用する Claude モデル。None の場合は config から取得。
        max_tokens: 最大出力トークン数。None の場合はデフォルト使用。
        temperature: 生成温度。None の場合はデフォルト使用。
        api_key: Anthropic API キー。None の場合は環境変数から取得。
        system_prompt: システムプロンプト。None の場合はデフォルトを使用。

    Returns:
        選定された記事のリスト。各記事に "score" キーが追加される:
            - score.novelty (int): 先進性スコア
            - score.surprise (int): 意外性スコア
            - score.practicality (int): 実用性スコア
            - score.japan_relevance (int): 日本企業関連性スコア
            - score.freshness (int): 鮮度スコア
            - score.total (int): 合計スコア
            - score.reason (str): スコアリング理由
    """
    if not candidates:
        logger.warning("候補記事がありません")
        return []

    logger.info("記事選定を開始します: 候補 %d 件から上位 %d 件を選定", len(candidates), num)

    # 1. 重複排除
    unique_candidates = _deduplicate_candidates(candidates)

    if not unique_candidates:
        logger.warning("重複排除後の候補記事がありません")
        return []

    # 候補が選定件数以下の場合はそのまま返す
    if len(unique_candidates) <= num:
        logger.info(
            "候補記事が選定件数以下のため、全件を選定します: %d 件",
            len(unique_candidates),
        )
        return _fallback_select_by_recency(unique_candidates, len(unique_candidates))

    # 2. Claude API によるスコアリング
    # config からモデル設定を取得（指定がない場合）
    resolved_model = model or "claude-sonnet-4-20250514"
    resolved_max_tokens = max_tokens or 4096
    resolved_temperature = temperature if temperature is not None else 0.3

    try:
        from src.utils.config import load_config
        config = load_config()
        claude_cfg = config.get("claude", {})
        if model is None:
            resolved_model = claude_cfg.get("model", resolved_model)
        if max_tokens is None:
            resolved_max_tokens = claude_cfg.get("max_tokens", resolved_max_tokens)
        if temperature is None:
            resolved_temperature = claude_cfg.get(
                "scoring_temperature", resolved_temperature
            )
    except Exception:
        pass  # config が読めない場合はデフォルト値を使用

    scores = _score_with_claude(
        candidates=unique_candidates,
        model=resolved_model,
        max_tokens=resolved_max_tokens,
        temperature=resolved_temperature,
        api_key=api_key,
        system_prompt=system_prompt,
    )

    # 3. スコアリング結果の適用と選定
    if not scores:
        # スコアリング失敗時はフォールバック
        return _fallback_select_by_recency(unique_candidates, num)

    # スコアをインデックスで引けるように辞書化
    score_map: dict[int, dict[str, Any]] = {}
    for score in scores:
        idx = score.get("index", -1)
        if 0 <= idx < len(unique_candidates):
            score_map[idx] = score

    # 全候補にスコアを付与
    scored_candidates: list[tuple[int, dict[str, Any]]] = []
    for i, article in enumerate(unique_candidates):
        if i in score_map:
            article["score"] = score_map[i]
            scored_candidates.append((score_map[i].get("total", 0), article))
        else:
            # スコアが無い記事はデフォルトスコアを付与
            article["score"] = {
                "novelty": 0,
                "surprise": 0,
                "practicality": 0,
                "japan_relevance": 0,
                "freshness": 0,
                "total": 0,
                "reason": "スコアリング対象外",
            }
            scored_candidates.append((0, article))

    # スコア降順でソートして上位 N 件を選定
    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    selected = [article for _, article in scored_candidates[:num]]

    logger.info(
        "記事選定が完了しました: %d 件を選定 (最高スコア: %d, 最低スコア: %d)",
        len(selected),
        scored_candidates[0][0] if scored_candidates else 0,
        scored_candidates[min(num - 1, len(scored_candidates) - 1)][0]
        if scored_candidates
        else 0,
    )

    for article in selected:
        logger.info(
            "  選定: [%d点] %s (%s)",
            article.get("score", {}).get("total", 0),
            article.get("title", "N/A")[:60],
            article.get("source", "N/A"),
        )

    return selected
