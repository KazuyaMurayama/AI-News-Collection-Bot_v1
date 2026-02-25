"""コンテンツ生成モジュール (writer)

Claude API によるストーリーテリング変換と、
YAML Frontmatter 付き Markdown 日次レポートの生成を行う。

主要コンポーネント:
- storyteller: Claude API を使用したストーリーテリング形式変換
- markdown_gen: Jinja2 テンプレートによる Markdown ファイル生成
"""

from src.writer.storyteller import (
    generate_insight,
    select_framework,
    transform_to_story,
)
from src.writer.markdown_gen import (
    generate_daily_markdown,
    save_markdown,
)

__all__ = [
    "transform_to_story",
    "select_framework",
    "generate_insight",
    "generate_daily_markdown",
    "save_markdown",
]
