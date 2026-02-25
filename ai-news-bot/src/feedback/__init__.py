"""フィードバック・リアクションモジュール (feedback)

メール内リアクションリンクの受信処理と、
Markdown Frontmatter の更新を行う。

主要コンポーネント:
- api_server: FastAPI リアクションサーバー（エンドポイント定義・リクエスト処理）
- updater: Markdown ファイルの Frontmatter 更新（reaction, rating, reacted_at）
"""

from src.feedback.updater import update_reaction
from src.feedback.api_server import create_app, run_server

__all__ = [
    "update_reaction",
    "create_app",
    "run_server",
]
