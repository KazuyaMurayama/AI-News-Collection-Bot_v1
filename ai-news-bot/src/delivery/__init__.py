"""配信モジュール

ニュースコンテンツの配信を担当するモジュール群。
- html_converter: Markdown -> HTML 変換、メールテンプレート適用
- gmail_sender: Gmail API によるメール配信（OAuth2 認証）
- line_sender: LINE Notify API によるメッセージ配信（オプション）
"""

from src.delivery.html_converter import apply_email_template, markdown_to_html
from src.delivery.gmail_sender import GmailSender
from src.delivery.line_sender import format_for_line, send_line_notification

__all__ = [
    "markdown_to_html",
    "apply_email_template",
    "GmailSender",
    "send_line_notification",
    "format_for_line",
]
