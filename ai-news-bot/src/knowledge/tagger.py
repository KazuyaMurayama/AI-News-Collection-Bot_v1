"""自動タグ付けモジュール

Claude API を使用して、記事の内容からカテゴリ・技術タグを自動付与する。

カテゴリ: 業務効率化, 創造支援, コスト削減, 新規事業, 研究・学術,
          ヘルスケア, 教育, 金融, 製造, マーケティング
技術タグ: LLM, 画像生成, 音声AI, マルチモーダル, RAG, Agent 等
"""

import json
import os
from typing import Any

from src.utils.logger import setup_logger
from src.utils.retry import with_retry

logger = setup_logger(__name__)

# デフォルトカテゴリ一覧
DEFAULT_CATEGORIES: list[str] = [
    "業務効率化",
    "創造支援",
    "コスト削減",
    "新規事業",
    "研究・学術",
    "ヘルスケア",
    "教育",
    "金融",
    "製造",
    "マーケティング",
]

# デフォルト技術タグ一覧
DEFAULT_TECH_TAGS: list[str] = [
    "LLM",
    "画像生成",
    "音声AI",
    "マルチモーダル",
    "RAG",
    "Agent",
    "ファインチューニング",
    "プロンプトエンジニアリング",
    "自然言語処理",
    "コンピュータビジョン",
    "強化学習",
    "ロボティクス",
    "エッジAI",
    "AutoML",
    "データセット",
]


def _get_claude_config() -> dict[str, Any]:
    """config.yaml から Claude API 設定を取得する。

    Returns:
        Claude API 設定の辞書。
    """
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        return {
            "model": config.get("claude.model", "claude-sonnet-4-20250514"),
            "max_tokens": config.get("claude.max_tokens", 4096),
            "temperature": config.get("claude.scoring_temperature", 0.3),
        }
    except Exception:
        return {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": 0.3,
        }


def _get_categories() -> list[str]:
    """config.yaml からカテゴリ一覧を取得する。

    Returns:
        カテゴリ文字列のリスト。
    """
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        categories = config.get("knowledge_base.categories")
        if categories and isinstance(categories, list):
            return categories
    except Exception:
        pass
    return DEFAULT_CATEGORIES


def _build_tagging_prompt(article: dict[str, Any]) -> str:
    """タグ付けプロンプトを構築する。

    Args:
        article: 記事情報の辞書。

    Returns:
        Claude API に送信するプロンプト文字列。
    """
    categories = _get_categories()
    categories_str = ", ".join(categories)
    tech_tags_str = ", ".join(DEFAULT_TECH_TAGS)

    title = article.get("title", "")
    source = article.get("source", "")
    summary = article.get("summary", "")
    body = article.get("body", "")
    url = article.get("url", "")

    # 本文テキストの構築（最大2000文字に制限）
    content_text = summary or body
    if len(content_text) > 2000:
        content_text = content_text[:2000] + "..."

    return f"""以下のAIニュース記事を分析し、最も適切なカテゴリタグと技術タグを付与してください。

## 記事情報
- タイトル: {title}
- ソース: {source}
- URL: {url}
- 内容: {content_text}

## カテゴリタグ（以下から1-3個選択）
{categories_str}

## 技術タグ（以下から0-5個選択、該当するもののみ）
{tech_tags_str}

## 回答形式
以下のJSON形式で回答してください。カテゴリタグは必ず1個以上、技術タグは該当するもののみ含めてください。

```json
{{
    "category_tags": ["カテゴリ1", "カテゴリ2"],
    "tech_tags": ["技術タグ1", "技術タグ2"]
}}
```"""


@with_retry(max_attempts=3, exceptions=(ConnectionError, TimeoutError, OSError))
def _call_claude_api(prompt: str) -> str:
    """Claude API を呼び出してタグ付け結果を取得する。

    Args:
        prompt: 送信するプロンプト文字列。

    Returns:
        Claude API のレスポンステキスト。

    Raises:
        ConnectionError: API 呼び出しに失敗した場合。
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ConnectionError("ANTHROPIC_API_KEY が設定されていません")

    claude_config = _get_claude_config()

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=claude_config["model"],
        max_tokens=claude_config["max_tokens"],
        temperature=claude_config["temperature"],
        messages=[
            {"role": "user", "content": prompt},
        ],
    )

    # レスポンスからテキストを抽出
    if message.content and len(message.content) > 0:
        return message.content[0].text
    return ""


def _parse_tags_response(response_text: str) -> list[str]:
    """Claude API のレスポンスからタグリストを抽出する。

    JSON ブロックを探してパースし、category_tags と tech_tags を結合して返す。

    Args:
        response_text: Claude API のレスポンステキスト。

    Returns:
        抽出されたタグのリスト。
    """
    # JSON ブロックの抽出（```json ... ``` または { ... } を探す）
    json_str = ""

    # コードブロック内の JSON を探す
    import re
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    else:
        # コードブロックがない場合、最初の { ... } を探す
        brace_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)

    if not json_str:
        logger.warning("レスポンスから JSON を抽出できませんでした")
        return []

    try:
        data = json.loads(json_str)
        category_tags = data.get("category_tags", [])
        tech_tags = data.get("tech_tags", [])

        # 型チェックとフィルタリング
        valid_categories = set(_get_categories())
        valid_tech = set(DEFAULT_TECH_TAGS)

        result_tags: list[str] = []

        for tag in category_tags:
            if isinstance(tag, str) and tag in valid_categories:
                result_tags.append(tag)

        for tag in tech_tags:
            if isinstance(tag, str) and tag in valid_tech:
                result_tags.append(tag)

        return result_tags

    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning("タグ JSON のパースに失敗しました: %s", str(e))
        return []


def auto_tag(article: dict[str, Any]) -> list[str]:
    """Claude API を使用して記事に自動でタグを付与する。

    記事のタイトル・内容を Claude API に送信し、
    カテゴリタグと技術タグを自動分類する。

    API 呼び出しに失敗した場合は空リストを返す（エラーログを出力）。

    Args:
        article: 記事情報の辞書。少なくとも "title" を含むこと。
            オプションで "source", "summary", "body", "url" を含められる。

    Returns:
        付与されたタグの文字列リスト。

    使用例::

        article = {
            "title": "Google DeepMind、新しいAIモデルを発表",
            "source": "TechCrunch",
            "summary": "Google DeepMind は...",
        }
        tags = auto_tag(article)
        # -> ["研究・学術", "LLM", "マルチモーダル"]
    """
    if not article.get("title"):
        logger.warning("記事にタイトルがありません。タグ付けをスキップします。")
        return []

    prompt = _build_tagging_prompt(article)

    try:
        response_text = _call_claude_api(prompt)
        tags = _parse_tags_response(response_text)

        logger.info(
            "自動タグ付け完了: title='%s', tags=%s",
            article.get("title", "")[:50],
            tags,
        )
        return tags

    except Exception as e:
        logger.error(
            "自動タグ付けに失敗しました: title='%s', error=%s",
            article.get("title", "")[:50],
            str(e),
        )
        return []
