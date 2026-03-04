"""フィードバック・リアクションモジュール (feedback)

メール内リアクションリンクの受信処理と、
Markdown Frontmatter の更新を行う。

主要コンポーネント:
- api_server: FastAPI リアクションサーバー（エンドポイント定義・リクエスト処理）
- updater: Markdown ファイルの Frontmatter 更新（reaction, rating, reacted_at）
- email_processor: リアクション評価メールの受信・処理
"""

from src.feedback.updater import update_reaction
from src.feedback.api_server import create_app, run_server
from src.feedback.email_processor import process_reaction_emails

__all__ = [
    "update_reaction",
    "create_app",
    "run_server",
    "process_reaction_emails",
]
