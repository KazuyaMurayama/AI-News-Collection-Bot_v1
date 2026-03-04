"""メインオーケストレーター

AI News Collector Bot の全モジュールを統合し、
日次ニュース収集・変換・配信パイプラインを実行する。

フロー:
    1. ログ初期化、設定読み込み（AppConfig）
    2. ニュース収集: collect_all()
    3. 中間 JSON 保存
    4. ストーリーテリング変換: select_framework() + transform_to_story()
    5. 自動タグ付け: auto_tag()
    6. Today's Insight 生成: generate_insight()
    7. Markdown 生成・保存: generate_daily_markdown() + save_markdown()
    8. Gmail 配信: GmailSender + apply_email_template() + send_daily_digest()
    9. LINE 配信（有効な場合）
   10. 完了ログ出力

CLI 引数:
    --date YYYY-MM-DD   指定日として実行
    --dry-run            配信せずに Markdown 生成まで
    --server             リアクションサーバーを起動
"""

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

# --- JST タイムゾーン ---
_JST = timezone(timedelta(hours=9))


def _today_jst() -> str:
    """JST での今日の日付を YYYY-MM-DD 文字列で返す。"""
    return datetime.now(_JST).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# エラー通知
# ---------------------------------------------------------------------------
def send_error_notification(error_message: str, logger: Any) -> None:
    """致命的エラー発生時に Gmail でエラー通知を送信する。

    Args:
        error_message: エラー内容の文字列。
        logger: ロガーインスタンス。
    """
    try:
        from src.delivery.gmail_sender import GmailSender

        sender = GmailSender()
        sender.authenticate()

        subject = f"[AI News Bot] ERROR - {_today_jst()}"
        html_body = (
            "<html><body>"
            "<h2 style='color:#e53e3e;'>AI News Bot - Error Report</h2>"
            f"<p><strong>Date:</strong> {_today_jst()}</p>"
            f"<pre style='background:#f7fafc;padding:16px;border-radius:8px;"
            f"overflow-x:auto;'>{error_message}</pre>"
            "<p>Please check the logs for details.</p>"
            "</body></html>"
        )

        sender.send_email(subject=subject, html_body=html_body)
        logger.info("エラー通知メールを送信しました")
    except Exception as notify_err:
        logger.error("エラー通知メールの送信に失敗しました: %s", notify_err)


# ---------------------------------------------------------------------------
# パイプライン本体
# ---------------------------------------------------------------------------
def run_pipeline(target_date: str, dry_run: bool = False) -> None:
    """日次ニュース配信パイプラインを実行する。

    Args:
        target_date: 実行対象の日付 (YYYY-MM-DD)。
        dry_run: True の場合、配信（Gmail / LINE）をスキップする。
    """
    # ------------------------------------------------------------------
    # Step 1: ログ初期化、設定読み込み
    # ------------------------------------------------------------------
    from src.utils.logger import setup_logger
    logger = setup_logger("main")

    logger.info("=" * 60)
    logger.info("AI News Collector Bot - パイプライン開始")
    logger.info("対象日付: %s | dry-run: %s", target_date, dry_run)
    logger.info("=" * 60)

    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        logger.info("設定読み込み完了: %s", repr(config))
    except Exception as e:
        logger.critical("設定の読み込みに失敗しました: %s", e)
        raise

    # ------------------------------------------------------------------
    # Step 1.5: リアクションメール処理（前日分の評価を反映）
    # ------------------------------------------------------------------
    logger.info("--- Step 1.5: リアクションメール処理 ---")
    try:
        from src.feedback.email_processor import process_reaction_emails
        reaction_count = process_reaction_emails()
        if reaction_count > 0:
            logger.info("リアクションメールから %d 件の評価を反映しました", reaction_count)
        else:
            logger.info("処理対象のリアクションメールはありませんでした")
    except Exception as e:
        logger.warning("リアクションメール処理でエラー（続行します）: %s", e)

    # ------------------------------------------------------------------
    # Step 2: ニュース収集
    # ------------------------------------------------------------------
    logger.info("--- Step 2: ニュース収集 ---")
    try:
        from src.collector import collect_all
        selected_articles = collect_all()
        logger.info("収集完了: %d 件の記事を取得", len(selected_articles))
    except Exception as e:
        logger.error("ニュース収集でエラーが発生しました: %s", e, exc_info=True)
        selected_articles = []

    if not selected_articles:
        logger.warning("収集結果が 0 件です。フォールバック処理を実行します。")
        # フォールバック: 空のダイジェストとして処理を継続
        fallback_story = {
            "id": 1,
            "title": "本日のAIニュースは取得できませんでした",
            "source": "System",
            "url": "",
            "summary": "ニュースソースへのアクセスに問題が発生した可能性があります。",
            "body": (
                "本日のAIニュース収集において、ニュースソースからの取得に"
                "失敗しました。ネットワーク接続やAPIキーの設定をご確認ください。"
                "次回の配信をお待ちください。"
            ),
            "category": "",
            "tags": [],
        }
        selected_articles = [fallback_story]

    # ------------------------------------------------------------------
    # Step 3: 中間 JSON 保存
    # ------------------------------------------------------------------
    logger.info("--- Step 3: 中間 JSON 保存 ---")
    try:
        daily_dir = config.get("knowledge_base.daily_dir", "./knowledge_base/daily")
        daily_path = Path(daily_dir)
        daily_path.mkdir(parents=True, exist_ok=True)

        json_filename = f"{target_date}_candidates.json"
        json_filepath = daily_path / json_filename

        with open(json_filepath, "w", encoding="utf-8") as f:
            json.dump(selected_articles, f, ensure_ascii=False, indent=2)

        logger.info("中間 JSON を保存しました: %s", json_filepath)
    except Exception as e:
        logger.error("中間 JSON の保存に失敗しました: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # Step 4: ストーリーテリング変換
    # ------------------------------------------------------------------
    logger.info("--- Step 4: ストーリーテリング変換 ---")
    stories: list[dict[str, Any]] = []

    from src.writer import select_framework, transform_to_story

    for idx, article in enumerate(selected_articles, start=1):
        try:
            framework = select_framework(article)
            logger.info("記事 %d: フレームワーク '%s' を選択", idx, framework)

            story_text = transform_to_story(article, framework=framework)
            logger.info("記事 %d: ストーリー変換完了 (%d 文字)", idx, len(story_text))

            story_entry: dict[str, Any] = {
                "id": idx,
                "title": article.get("title", "無題"),
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "summary": article.get("summary", ""),
                "body": story_text,
                "story": story_text,
                "framework": framework,
                "category": article.get("category", ""),
                "tags": [],
            }
            stories.append(story_entry)
        except Exception as e:
            logger.error("記事 %d のストーリー変換に失敗しました: %s", idx, e, exc_info=True)
            # 変換に失敗した記事はそのまま含める
            stories.append({
                "id": idx,
                "title": article.get("title", "無題"),
                "source": article.get("source", ""),
                "url": article.get("url", ""),
                "summary": article.get("summary", ""),
                "body": article.get("summary", article.get("body", "")),
                "story": article.get("summary", article.get("body", "")),
                "framework": "",
                "category": article.get("category", ""),
                "tags": [],
            })

    # ------------------------------------------------------------------
    # Step 5: 自動タグ付け
    # ------------------------------------------------------------------
    logger.info("--- Step 5: 自動タグ付け ---")
    from src.knowledge.tagger import auto_tag

    for story in stories:
        try:
            tags = auto_tag(story)
            story["tags"] = tags
            logger.info("記事 %d: タグ付け完了 -> %s", story["id"], tags)
        except Exception as e:
            logger.error(
                "記事 %d のタグ付けに失敗しました: %s",
                story["id"], e, exc_info=True,
            )
            story["tags"] = []

    # ------------------------------------------------------------------
    # Step 6: Today's Insight 生成
    # ------------------------------------------------------------------
    logger.info("--- Step 6: Today's Insight 生成 ---")
    try:
        from src.writer import generate_insight
        insight = generate_insight(stories)
        logger.info("Insight 生成完了 (%d 文字)", len(insight))
    except Exception as e:
        logger.error("Insight 生成に失敗しました: %s", e, exc_info=True)
        insight = "本日のインサイトは生成できませんでした。"

    # ------------------------------------------------------------------
    # Step 7: Markdown 生成・保存
    # ------------------------------------------------------------------
    logger.info("--- Step 7: Markdown 生成・保存 ---")
    try:
        from src.writer import generate_daily_markdown, save_markdown

        md_content = generate_daily_markdown(
            date=target_date,
            stories=stories,
            insight=insight,
        )

        daily_dir = config.get("knowledge_base.daily_dir", "./knowledge_base/daily")
        md_filepath = str(Path(daily_dir) / f"{target_date}_ai_news.md")
        save_markdown(md_content, md_filepath)
        logger.info("Markdown を保存しました: %s", md_filepath)
    except Exception as e:
        logger.error("Markdown 生成・保存に失敗しました: %s", e, exc_info=True)
        md_content = ""

    # dry-run の場合はここで終了
    if dry_run:
        logger.info("=== dry-run モード: 配信をスキップします ===")
        logger.info("パイプライン完了 (dry-run)")
        return

    # ------------------------------------------------------------------
    # Step 8: Gmail 配信
    # ------------------------------------------------------------------
    logger.info("--- Step 8: Gmail 配信 ---")
    gmail_enabled = config.get("delivery.gmail.enabled", False)

    if gmail_enabled:
        try:
            from src.delivery.gmail_sender import GmailSender
            from src.delivery.html_converter import apply_email_template

            # HTML メール生成
            html_email = apply_email_template(
                html_body=md_content,
                date=target_date,
                stories=stories,
                insight=insight,
            )
            logger.info("メール HTML テンプレート適用完了")

            # Gmail 送信
            sender = GmailSender()
            sender.authenticate()

            headline = stories[0]["title"] if stories else "AI最新ニュース"
            sender.send_daily_digest(
                date=target_date,
                html_content=html_email,
                headline=headline,
            )
            logger.info("Gmail 配信完了")
        except Exception as e:
            logger.error("Gmail 配信に失敗しました: %s", e, exc_info=True)
    else:
        logger.info("Gmail 配信は無効です。スキップします。")

    # ------------------------------------------------------------------
    # Step 9: LINE 配信（有効な場合）
    # ------------------------------------------------------------------
    logger.info("--- Step 9: LINE 配信 ---")
    line_enabled = config.get("delivery.line.enabled", False)

    if line_enabled:
        try:
            from src.delivery.line_sender import format_for_line, send_line_notification

            line_message = format_for_line(stories)
            success = send_line_notification(line_message)

            if success:
                logger.info("LINE 配信完了")
            else:
                logger.warning("LINE 配信が失敗しました（send_line_notification が False を返しました）")
        except Exception as e:
            logger.error("LINE 配信に失敗しました: %s", e, exc_info=True)
    else:
        logger.info("LINE 配信は無効です。スキップします。")

    # ------------------------------------------------------------------
    # Step 10: 完了ログ
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("AI News Collector Bot - パイプライン完了")
    logger.info("日付: %s | 記事数: %d | dry-run: %s", target_date, len(stories), dry_run)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI エントリーポイント
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """コマンドライン引数をパースする。

    Args:
        argv: 引数リスト。None の場合は sys.argv を使用。

    Returns:
        パース済みの Namespace オブジェクト。
    """
    parser = argparse.ArgumentParser(
        description="AI News Collector Bot - 日次ニュース収集・配信パイプライン",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="実行対象の日付 (YYYY-MM-DD)。省略時は今日の日付 (JST)。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="配信せずに Markdown 生成まで実行する。",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        default=False,
        help="リアクションフィードバックサーバーを起動する。",
    )
    parser.add_argument(
        "--process-reactions",
        action="store_true",
        default=False,
        help="受信メールからリアクション評価を処理する。",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """メインエントリーポイント。

    Args:
        argv: コマンドライン引数リスト。None の場合は sys.argv を使用。
    """
    args = parse_args(argv)

    # --- サーバーモード ---
    if args.server:
        from src.utils.logger import setup_logger
        logger = setup_logger("main")
        logger.info("リアクションサーバーモードで起動します")

        try:
            from src.utils.config import AppConfig
            AppConfig.get_instance()
        except Exception as e:
            logger.critical("設定の読み込みに失敗しました: %s", e)
            sys.exit(1)

        from src.feedback import run_server
        run_server()
        return

    # --- リアクションメール処理モード ---
    if args.process_reactions:
        from src.utils.logger import setup_logger
        logger = setup_logger("main")
        logger.info("リアクションメール処理モードで起動します")

        try:
            from src.utils.config import AppConfig
            AppConfig.get_instance()
        except Exception as e:
            logger.critical("設定の読み込みに失敗しました: %s", e)
            sys.exit(1)

        from src.feedback.email_processor import process_reaction_emails
        count = process_reaction_emails()
        logger.info("リアクションメール処理完了: %d 件", count)
        return

    # --- パイプラインモード ---
    target_date = args.date or _today_jst()

    # 日付フォーマットの検証
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print(f"Error: 日付フォーマットが不正です: {target_date} (期待: YYYY-MM-DD)")
        sys.exit(1)

    # ログ初期化（エラー通知用に先に取得）
    from src.utils.logger import setup_logger
    logger = setup_logger("main")

    try:
        run_pipeline(target_date=target_date, dry_run=args.dry_run)
    except Exception as e:
        error_detail = traceback.format_exc()
        logger.critical("パイプラインで致命的エラーが発生しました:\n%s", error_detail)
        send_error_notification(error_detail, logger)
        sys.exit(1)


if __name__ == "__main__":
    main()
