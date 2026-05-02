"""統合品質チェックモジュール

パイプライン全体の品質を一元管理する。
各ステップの入出力を検証し、品質レポートを生成する。

チェック項目:
- 収集: 候補記事の件数・重複率・ソース多様性
- 変換: ストーリー品質（文字数・日本語率・構造）
- 配信: HTML 整合性・テンプレート変数の充足
"""

import re
from typing import Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
MIN_STORY_LENGTH = 600  # ストーリー最小文字数
MIN_STORY_PARAGRAPHS = 2  # ストーリー最小段落数
MIN_CANDIDATES = 3  # 最低候補記事数
MIN_SOURCES_DIVERSITY = 2  # 最低ソース種類数


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------
def _contains_japanese(text: str) -> bool:
    """テキストに日本語文字が含まれるかを判定する。"""
    for char in text:
        cp = ord(char)
        if (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF) or (0x4E00 <= cp <= 0x9FFF):
            return True
    return False


def _count_paragraphs(text: str) -> int:
    """空行区切りの段落数を数える。"""
    return len([p for p in text.split("\n\n") if p.strip()])


# ---------------------------------------------------------------------------
# 個別チェック関数
# ---------------------------------------------------------------------------
def check_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """収集候補記事の品質チェック。

    Args:
        candidates: 候補記事のリスト。

    Returns:
        チェック結果の辞書:
            - passed (bool): 合格か
            - total (int): 候補記事数
            - sources (list[str]): ソース一覧
            - duplicates (int): 重複数
            - issues (list[str]): 問題リスト
    """
    issues: list[str] = []
    total = len(candidates)

    if total == 0:
        return {"passed": False, "total": 0, "sources": [], "duplicates": 0,
                "issues": ["候補記事が0件です"]}

    if total < MIN_CANDIDATES:
        issues.append(f"候補記事が少ない: {total}件 (推奨: {MIN_CANDIDATES}件以上)")

    # ソースの多様性
    sources = list({c.get("source", "不明") for c in candidates})
    if len(sources) < MIN_SOURCES_DIVERSITY:
        issues.append(f"ソースの多様性不足: {len(sources)}種類 (推奨: {MIN_SOURCES_DIVERSITY}以上)")

    # URL 重複チェック
    urls = [c.get("url", "").strip().rstrip("/") for c in candidates if c.get("url")]
    duplicates = len(urls) - len(set(urls))
    if duplicates > 0:
        issues.append(f"URL重複: {duplicates}件")

    # タイトル空チェック
    empty_titles = sum(1 for c in candidates if not c.get("title", "").strip())
    if empty_titles > 0:
        issues.append(f"タイトル空: {empty_titles}件")

    return {
        "passed": len(issues) == 0,
        "total": total,
        "sources": sources,
        "duplicates": duplicates,
        "issues": issues,
    }


def check_story(story: dict[str, Any]) -> dict[str, Any]:
    """個別ストーリーの品質チェック。

    Args:
        story: ストーリー辞書 (id, title, body, source, url 等)。

    Returns:
        チェック結果の辞書:
            - passed (bool): 品質基準を満たしているか
            - story_id (int): ストーリーID
            - char_count (int): 文字数
            - has_japanese (bool): 日本語含有
            - paragraph_count (int): 段落数
            - issues (list[str]): 問題リスト
    """
    issues: list[str] = []
    story_id = story.get("id", 0)
    body = story.get("body", "").strip()
    title = story.get("title", "").strip()

    # 本文チェック
    if not body:
        issues.append("本文が空です")
        return {"passed": False, "story_id": story_id, "char_count": 0,
                "has_japanese": False, "paragraph_count": 0, "issues": issues}

    char_count = len(body)
    has_japanese = _contains_japanese(body)
    paragraph_count = _count_paragraphs(body)

    if char_count < MIN_STORY_LENGTH:
        issues.append(f"文字数不足: {char_count}文字 (最低{MIN_STORY_LENGTH}文字)")

    if not has_japanese:
        issues.append("日本語が含まれていません")

    if paragraph_count < MIN_STORY_PARAGRAPHS:
        issues.append(f"段落数不足: {paragraph_count}段落 (最低{MIN_STORY_PARAGRAPHS}段落)")

    # タイトルチェック
    if not title:
        issues.append("タイトルが空です")

    # RSS残骸チェック
    rss_markers = [
        "submitted by /u/", "[link] [comments]",
        "Continue reading", "<![CDATA[",
    ]
    for marker in rss_markers:
        if marker.lower() in body.lower():
            issues.append(f"RSS残骸検出: '{marker}'")

    # URLチェック
    if not story.get("url", "").strip():
        issues.append("元記事URLが空です")

    return {
        "passed": len(issues) == 0,
        "story_id": story_id,
        "char_count": char_count,
        "has_japanese": has_japanese,
        "paragraph_count": paragraph_count,
        "issues": issues,
    }


def check_all_stories(stories: list[dict[str, Any]]) -> dict[str, Any]:
    """全ストーリーの品質チェック。

    Args:
        stories: ストーリーのリスト。

    Returns:
        チェック結果の辞書:
            - passed (bool): 全体として合格か
            - total (int): 記事数
            - pass_count (int): 合格記事数
            - results (list[dict]): 各記事の個別結果
            - summary (str): サマリーメッセージ
    """
    if not stories:
        return {"passed": False, "total": 0, "pass_count": 0,
                "results": [], "summary": "記事がありません"}

    results = [check_story(s) for s in stories]
    pass_count = sum(1 for r in results if r["passed"])
    total = len(stories)

    if pass_count == total:
        summary = f"全記事合格 ({pass_count}/{total})"
        passed = True
    elif pass_count == 0:
        summary = f"全記事不合格 ({pass_count}/{total}) - 配信不可"
        passed = False
    else:
        summary = f"一部合格 ({pass_count}/{total}) - 配信可"
        passed = True  # 1件でも合格なら配信可

    return {
        "passed": passed,
        "total": total,
        "pass_count": pass_count,
        "results": results,
        "summary": summary,
    }


def check_insight(insight: str) -> dict[str, Any]:
    """インサイトの品質チェック。

    Args:
        insight: インサイトテキスト。

    Returns:
        チェック結果の辞書。
    """
    issues: list[str] = []

    if not insight or not insight.strip():
        return {"passed": False, "char_count": 0, "issues": ["インサイトが空です"]}

    text = insight.strip()
    char_count = len(text)

    if char_count < 150:
        issues.append(f"インサイトが短すぎます: {char_count}文字 (最低150文字)")

    if not _contains_japanese(text):
        issues.append("日本語が含まれていません")

    # 失敗メッセージの検出
    if "生成できませんでした" in text or "失敗しました" in text:
        issues.append("生成失敗メッセージが検出されました")

    return {
        "passed": len(issues) == 0,
        "char_count": char_count,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# 統合品質レポート
# ---------------------------------------------------------------------------
def run_full_quality_check(
    candidates: list[dict[str, Any]] | None = None,
    stories: list[dict[str, Any]] | None = None,
    insight: str | None = None,
) -> dict[str, Any]:
    """パイプライン全体の品質チェックを実行する。

    各フェーズの結果を統合し、配信可否を判定する。

    Args:
        candidates: 候補記事リスト（Step 2 の出力）。
        stories: 変換済みストーリーリスト（Step 4 の出力）。
        insight: インサイトテキスト（Step 6 の出力）。

    Returns:
        統合品質レポート:
            - deliverable (bool): 配信可能か
            - candidates_check (dict | None): 候補記事チェック結果
            - stories_check (dict | None): ストーリーチェック結果
            - insight_check (dict | None): インサイトチェック結果
            - blocking_issues (list[str]): 配信をブロックする問題
            - warnings (list[str]): 警告（配信は可能）
    """
    blocking_issues: list[str] = []
    warnings: list[str] = []

    # 候補記事チェック
    candidates_result = None
    if candidates is not None:
        candidates_result = check_candidates(candidates)
        if not candidates_result["passed"]:
            for issue in candidates_result["issues"]:
                warnings.append(f"[収集] {issue}")

    # ストーリーチェック
    stories_result = None
    if stories is not None:
        stories_result = check_all_stories(stories)
        if not stories_result["passed"]:
            blocking_issues.append(
                f"[変換] {stories_result['summary']}"
            )
        elif stories_result["pass_count"] < stories_result["total"]:
            for r in stories_result["results"]:
                if not r["passed"]:
                    warnings.append(
                        f"[変換] 記事{r['story_id']}: {', '.join(r['issues'])}"
                    )

    # インサイトチェック
    insight_result = None
    if insight is not None:
        insight_result = check_insight(insight)
        if not insight_result["passed"]:
            for issue in insight_result["issues"]:
                warnings.append(f"[インサイト] {issue}")

    deliverable = len(blocking_issues) == 0

    # ログ出力
    if deliverable and not warnings:
        logger.info("品質チェック: 全項目合格 - 配信可能")
    elif deliverable:
        logger.warning("品質チェック: 配信可能（警告あり: %d件）", len(warnings))
        for w in warnings:
            logger.warning("  %s", w)
    else:
        logger.error("品質チェック: 配信不可")
        for b in blocking_issues:
            logger.error("  [BLOCK] %s", b)
        for w in warnings:
            logger.warning("  [WARN] %s", w)

    return {
        "deliverable": deliverable,
        "candidates_check": candidates_result,
        "stories_check": stories_result,
        "insight_check": insight_result,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
    }
