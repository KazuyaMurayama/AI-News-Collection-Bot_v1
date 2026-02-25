"""ナレッジベース管理モジュール (knowledge)

ナレッジベースの検索・タグ付け・月次サマリー生成を行う。

主要コンポーネント:
- search: タグ検索・全文検索・フィルタリング
- tagger: Claude API による自動カテゴリ分類・タグ付与
- summarizer: 月次サマリー生成（統計集計 + Claude API インサイト生成）
"""

from src.knowledge.search import (
    search_by_tag,
    search_fulltext,
    filter_by_rating,
    get_all_articles,
)
from src.knowledge.tagger import auto_tag
from src.knowledge.summarizer import (
    generate_monthly_summary,
    save_monthly_summary,
)

__all__ = [
    "search_by_tag",
    "search_fulltext",
    "filter_by_rating",
    "get_all_articles",
    "auto_tag",
    "generate_monthly_summary",
    "save_monthly_summary",
]
