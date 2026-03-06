"""ストーリーテリング変換モジュール

Claude API を使用して、ニュース記事をストーリーテリング形式の解説記事に変換する。
記事の内容に応じて最適なフレームワークを自動選択し、
ビジネスパーソン向けの読みやすい日本語解説を生成する。

フレームワーク:
- STAR法: 企業導入事例向け（Situation, Task, Action, Result）
- ヒーローズジャーニー簡易版: 技術革新系向け
- Before/After/Bridge: 業務改善系向け
- PAS: 課題解決系向け（Problem, Agitate, Solution）
"""

import json
import os
import re
from typing import Any

import anthropic

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# フレームワーク定義
FRAMEWORKS = {
    "STAR": "STAR法（Situation: 状況, Task: 課題, Action: 行動, Result: 成果）",
    "ヒーローズジャーニー": "ヒーローズジャーニー簡易版（日常→課題発見→挑戦→変革→新世界）",
    "Before/After/Bridge": "Before/After/Bridge（変化前の状態→変化後の理想→そこに至る橋渡し）",
    "PAS": "PAS（Problem: 問題提起, Agitate: 問題の深刻さを強調, Solution: 解決策の提示）",
}

# フレームワーク自動選択のためのキーワードマッピング
_FRAMEWORK_KEYWORDS: dict[str, list[str]] = {
    "STAR": [
        "導入", "採用", "活用事例", "事例", "実装", "deploy", "implementation",
        "case study", "enterprise", "企業", "運用", "本番", "production",
        "ROI", "成果", "実績", "パートナー", "提携",
    ],
    "ヒーローズジャーニー": [
        "革新", "画期的", "ブレイクスルー", "breakthrough", "新技術",
        "発明", "世界初", "first", "新モデル", "新手法", "novel",
        "研究", "論文", "paper", "発表", "リリース", "launch",
        "オープンソース", "open source", "GPT", "LLM", "基盤モデル",
    ],
    "Before/After/Bridge": [
        "効率化", "改善", "最適化", "自動化", "automation", "productivity",
        "コスト削減", "時間短縮", "ワークフロー", "workflow", "業務",
        "トランスフォーメーション", "DX", "デジタル化", "streamline",
        "アップデート", "アップグレード", "update", "upgrade",
    ],
    "PAS": [
        "課題", "問題", "リスク", "脅威", "懸念", "セキュリティ",
        "規制", "倫理", "bias", "バイアス", "privacy", "プライバシー",
        "対策", "解決", "solution", "ガバナンス", "コンプライアンス",
        "脆弱性", "vulnerability", "対応", "防止",
    ],
}

# ストーリーテリング用システムプロンプト
_STORYTELLING_SYSTEM_PROMPT = """あなたはAIトレンドを解説する一流のテクノロジーライターです。
以下の記事情報を元に、{framework}のフレームワークで **1500〜2500文字** の日本語解説記事を書いてください。

【重要】すべての出力は必ず日本語で書いてください。タイトルも本文もすべて日本語です。
英語の記事が入力された場合でも、出力は完全に日本語で書いてください。
技術用語（LLM、API、Transformer 等）はそのままカタカナまたは英語表記で構いませんが、
文章自体は必ず日本語で記述してください。

必須要素（すべて含めること）:
1. **フック**（読者の興味を強く引く冒頭の1〜2文。驚きのある事実や問いかけ）
2. **背景・文脈**（なぜ今この技術やニュースが注目されているのか、業界の流れ）
3. **技術的な詳細**（具体的な仕組み、アーキテクチャ、手法の説明。技術者にも読み応えある内容）
4. **具体的な数字・データ**（記事内の数値データ、ベンチマーク結果、市場規模など）
5. **業界・社会へのインパクト**（この技術が広まるとどう変わるか、影響範囲）
6. **日本企業・日本市場への示唆**（国内での応用可能性、日本企業が取るべきアクション）
7. **今後の展望と課題**（今後の発展の方向性、残された課題やリスク）
8. **クロージング**（まとめと読者へのメッセージ）

タイトル: 必ず日本語で、疑問形 or 数字入りの魅力的なタイトルにしてください。

出力形式:
- 最初の行に日本語タイトルを書いてください（英語タイトルは禁止）。
- 本文は段落ごとに空行で区切ってください（読みやすさのため必ず段落分けすること）。
- 重要なキーワードは **太字** にしてください。
- Markdownの見出し（#）は使わないでください。
- 十分な文量を確保してください。短すぎる記事は不可です。"""

# フレームワーク選択用システムプロンプト
_FRAMEWORK_SELECTION_SYSTEM_PROMPT = """あなたはAIニュースの分析専門家です。
記事の内容を分析し、最適なストーリーテリングフレームワークを選択してください。

選択肢:
- STAR: 企業導入事例、具体的な成果や実績がある記事向け
- ヒーローズジャーニー: 技術革新、新技術・新モデルの発表記事向け
- Before/After/Bridge: 業務改善、効率化、DX推進の記事向け
- PAS: 課題・問題提起、リスク対応、規制関連の記事向け

以下のJSON形式で回答してください（他のテキストは不要です）:
{"framework": "選択したフレームワーク名", "reason": "選択理由（1文）"}"""

# インサイト生成用システムプロンプト
_INSIGHT_SYSTEM_PROMPT = """あなたはAIトレンドの分析専門家です。
3つのAIニュース記事に共通するトレンドや示唆を分析し、
「Today's Insight」として **500〜800文字** の日本語でまとめてください。

【重要】すべての出力は必ず日本語で書いてください。

以下の要素を含めてください:
- 3記事の共通テーマまたはつながり
- そこから読み取れるAI業界のトレンドと背景
- 具体的なビジネスパーソンへの示唆・アクションポイント（3つ以上）
- 今後注目すべきポイント

段落ごとに空行で区切り、読みやすく書いてください。
重要なキーワードは **太字** にしてください。
Markdownの見出し（#）は使わないでください。
短すぎる出力は不可です。十分な分量で深い分析を提供してください。"""


def extract_title_and_body(story_text: str) -> tuple[str, str]:
    """生成されたストーリーテキストからタイトルと本文を分離する。

    ストーリーの最初の行をタイトルとして抽出し、残りを本文とする。

    Args:
        story_text: Claude が生成したストーリーテキスト全体。

    Returns:
        (タイトル, 本文) のタプル。分離できない場合はタイトルを空文字にする。
    """
    if not story_text:
        return "", ""

    lines = story_text.strip().split("\n")
    if not lines:
        return "", story_text

    # 最初の非空行をタイトルとして取得
    title = ""
    body_start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            # Markdown の太字や装飾を除去してタイトルにする
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
            title = re.sub(r"^#+\s*", "", title)  # 見出し記号を除去
            body_start_idx = i + 1
            break

    # 残りを本文とする（タイトル直後の空行もスキップ）
    body_lines = lines[body_start_idx:]
    body = "\n".join(body_lines).strip()

    return title, body


def _get_claude_client() -> anthropic.Anthropic:
    """Anthropic クライアントを生成する。

    Returns:
        Anthropic クライアントインスタンス。

    Raises:
        ValueError: ANTHROPIC_API_KEY が未設定の場合。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("環境変数 ANTHROPIC_API_KEY が設定されていません")
    return anthropic.Anthropic(api_key=api_key)


def _get_model_config() -> dict[str, Any]:
    """config.yaml から Claude API の設定を取得する。

    Returns:
        モデル名、max_tokens、temperature を含む辞書。
    """
    try:
        from src.utils.config import load_config
        config = load_config()
        claude_cfg = config.get("claude", {})
        return {
            "model": claude_cfg.get("model", "claude-sonnet-4-20250514"),
            "max_tokens": claude_cfg.get("max_tokens", 4096),
            "temperature": claude_cfg.get("temperature", 0.7),
        }
    except Exception:
        return {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.7,
        }


def _classify_by_keywords(article: dict) -> str | None:
    """キーワードベースでフレームワークを分類する。

    記事のタイトルと要約に含まれるキーワードを分析し、
    最もマッチするフレームワークを返す。

    Args:
        article: 記事情報の辞書。title, summary を含む。

    Returns:
        フレームワーク名。判定不能の場合は None。
    """
    text = (
        (article.get("title", "") + " " + article.get("summary", ""))
        .lower()
    )

    scores: dict[str, int] = {}
    for framework, keywords in _FRAMEWORK_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        scores[framework] = score

    max_score = max(scores.values())
    if max_score == 0:
        return None

    # 最高スコアのフレームワークを返す
    return max(scores, key=lambda k: scores[k])


@with_retry(max_attempts=3, exceptions=(anthropic.APIError, anthropic.APIConnectionError))
def select_framework(article: dict) -> str:
    """記事に最適なストーリーテリングフレームワークを選択する。

    まずキーワードベースの分類を試み、判定が難しい場合は
    Claude API を使用して最適なフレームワークを選択する。

    Args:
        article: 記事情報の辞書。以下のキーを含む:
            - title (str): 記事タイトル
            - summary (str): 記事の要約
            - source (str, optional): ソース名
            - url (str, optional): 記事URL

    Returns:
        選択されたフレームワーク名（"STAR", "ヒーローズジャーニー",
        "Before/After/Bridge", "PAS" のいずれか）。
    """
    # まずキーワードベースで試行
    keyword_result = _classify_by_keywords(article)
    if keyword_result is not None:
        logger.info(
            "フレームワークをキーワードで選択: %s (記事: %s)",
            keyword_result,
            article.get("title", "不明"),
        )
        return keyword_result

    # キーワードで判定できない場合は Claude API を使用
    logger.info(
        "Claude API でフレームワークを選択中: %s",
        article.get("title", "不明"),
    )

    client = _get_claude_client()
    model_cfg = _get_model_config()

    user_message = (
        f"記事タイトル: {article.get('title', '不明')}\n"
        f"記事概要: {article.get('summary', '情報なし')}\n"
        f"ソース: {article.get('source', '不明')}"
    )

    response = client.messages.create(
        model=model_cfg["model"],
        max_tokens=256,
        temperature=0.3,
        system=_FRAMEWORK_SELECTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text.strip()

    try:
        result = json.loads(response_text)
        framework = result.get("framework", "ヒーローズジャーニー")
        reason = result.get("reason", "")
    except (json.JSONDecodeError, KeyError, IndexError):
        # JSON パースに失敗した場合、レスポンスからフレームワーク名を探す
        framework = "ヒーローズジャーニー"
        reason = "デフォルト選択"
        for fw_name in FRAMEWORKS:
            if fw_name in response_text:
                framework = fw_name
                reason = "テキストマッチ"
                break

    # 有効なフレームワーク名かチェック
    if framework not in FRAMEWORKS:
        logger.warning(
            "不明なフレームワーク '%s' が返されました。デフォルトに変更します。",
            framework,
        )
        framework = "ヒーローズジャーニー"

    logger.info(
        "フレームワークを選択: %s (理由: %s, 記事: %s)",
        framework,
        reason,
        article.get("title", "不明"),
    )

    return framework


@with_retry(max_attempts=3, exceptions=(anthropic.APIError, anthropic.APIConnectionError))
def transform_to_story(article: dict, framework: str | None = None) -> str:
    """記事をストーリーテリング形式の解説記事に変換する。

    Claude API を使用して、指定されたフレームワークに基づいて
    1500-2500文字の日本語解説記事を生成する。

    Args:
        article: 記事情報の辞書。以下のキーを含む:
            - title (str): 記事タイトル
            - summary (str): 記事の要約
            - source (str, optional): ソース名
            - url (str, optional): 記事URL
            - published_at (str, optional): 公開日時
        framework: 使用するフレームワーク名。None の場合は自動選択。

    Returns:
        生成されたストーリーテリング形式の解説記事テキスト。
    """
    # フレームワークの決定
    if framework is None:
        framework = select_framework(article)

    framework_desc = FRAMEWORKS.get(framework, framework)

    logger.info(
        "ストーリー変換を開始: %s (フレームワーク: %s)",
        article.get("title", "不明"),
        framework,
    )

    client = _get_claude_client()
    model_cfg = _get_model_config()

    system_prompt = _STORYTELLING_SYSTEM_PROMPT.format(framework=framework_desc)

    user_message = (
        f"記事タイトル: {article.get('title', '不明')}\n"
        f"ソース: {article.get('source', '不明')}\n"
        f"公開日: {article.get('published_at', '不明')}\n"
        f"URL: {article.get('url', '')}\n"
        f"\n記事概要:\n{article.get('summary', '情報なし')}"
    )

    response = client.messages.create(
        model=model_cfg["model"],
        max_tokens=model_cfg["max_tokens"],
        temperature=model_cfg["temperature"],
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    story = response.content[0].text.strip()

    logger.info(
        "ストーリー変換完了: %s (%d文字)",
        article.get("title", "不明"),
        len(story),
    )

    return story


@with_retry(max_attempts=3, exceptions=(anthropic.APIError, anthropic.APIConnectionError))
def generate_insight(stories: list[dict]) -> str:
    """3記事の共通テーマを分析し、Today's Insight を生成する。

    Claude API を使用して、3つの記事に共通するトレンドや示唆を
    500-800文字でまとめる。

    Args:
        stories: ストーリー情報のリスト。各要素は以下のキーを含む:
            - title (str): ストーリータイトル
            - story (str): 生成されたストーリー本文
            - source (str, optional): ソース名
            - category (str, optional): カテゴリ
            - tags (list[str], optional): タグリスト

    Returns:
        生成された Today's Insight テキスト。
    """
    if not stories:
        logger.warning("ストーリーが空のため、インサイトを生成できません")
        return "本日のインサイトは生成できませんでした。"

    logger.info("Today's Insight を生成中 (%d記事)", len(stories))

    client = _get_claude_client()
    model_cfg = _get_model_config()

    # 記事情報をまとめる
    stories_text_parts: list[str] = []
    for i, story in enumerate(stories, 1):
        part = (
            f"--- 記事{i} ---\n"
            f"タイトル: {story.get('title', '不明')}\n"
            f"カテゴリ: {story.get('category', '不明')}\n"
            f"タグ: {', '.join(story.get('tags', []))}\n"
            f"本文:\n{story.get('story', '情報なし')}\n"
        )
        stories_text_parts.append(part)

    user_message = "\n".join(stories_text_parts)

    response = client.messages.create(
        model=model_cfg["model"],
        max_tokens=2048,
        temperature=model_cfg["temperature"],
        system=_INSIGHT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    insight = response.content[0].text.strip()

    logger.info("Today's Insight 生成完了 (%d文字)", len(insight))

    return insight
