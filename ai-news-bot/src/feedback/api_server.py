"""FastAPI リアクションサーバー

メール内のリアクションリンクを受け付け、
Markdown Frontmatter の更新を行う API サーバー。

エンドポイント:
- GET /react?date={date}&story={id}&reaction={type}  リアクション受信
- GET /health  ヘルスチェック
- GET /stats   蓄積統計情報
"""

import re
from datetime import datetime, timezone, timedelta

import uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from src.feedback.updater import REACTION_MAP, update_reaction
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# JST タイムゾーン
_JST = timezone(timedelta(hours=9))

# 日付バリデーション用正規表現
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _get_app_version() -> str:
    """config.yaml からアプリケーションバージョンを取得する。"""
    try:
        from src.utils.config import AppConfig
        config = AppConfig.get_instance()
        return config.get("app.version", "1.0.0")
    except Exception:
        return "1.0.0"


def _build_thank_you_html(reaction_type: str, story_id: int, date: str) -> str:
    """リアクション完了後に表示する HTML ページを生成する。

    Args:
        reaction_type: リアクション種別。
        story_id: ストーリー ID。
        date: 記事の日付。

    Returns:
        HTML 文字列。
    """
    reaction_info = REACTION_MAP[reaction_type]
    emoji = reaction_info["emoji"]
    label = reaction_info["label"]

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News - \u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u5b8c\u4e86</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 48px 40px;
            text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            max-width: 420px;
            width: 90%;
        }}
        .emoji {{ font-size: 64px; margin-bottom: 16px; }}
        .title {{
            font-size: 20px;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 8px;
        }}
        .message {{
            font-size: 14px;
            color: #718096;
            line-height: 1.6;
            margin-top: 12px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            background: #edf2f7;
            color: #4a5568;
            font-size: 13px;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="emoji">{emoji}</div>
        <div class="title">\u2705 \u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u3042\u308a\u304c\u3068\u3046\u3054\u3056\u3044\u307e\u3059\uff01</div>
        <div class="message">
            {date} \u306e\u8a18\u4e8b #{story_id} \u306b\u300c{label}\u300d\u3092\u8a18\u9332\u3057\u307e\u3057\u305f\u3002<br>
            \u3042\u306a\u305f\u306e\u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u306f\u3001\u3088\u308a\u826f\u3044\u30cb\u30e5\u30fc\u30b9\u914d\u4fe1\u306e\u6539\u5584\u306b\u5f79\u7acb\u3066\u307e\u3059\u3002
        </div>
        <div class="badge">\u30ea\u30a2\u30af\u30b7\u30e7\u30f3: {emoji} {label}</div>
    </div>
</body>
</html>"""


def create_app() -> FastAPI:
    """FastAPI アプリケーションを作成して返す。

    CORS ミドルウェアの設定と全エンドポイントの登録を行う。

    Returns:
        設定済みの FastAPI アプリケーションインスタンス。
    """
    app = FastAPI(
        title="AI News Feedback Server",
        description="\u30e1\u30fc\u30eb\u5185\u30ea\u30a2\u30af\u30b7\u30e7\u30f3\u30ea\u30f3\u30af\u306e\u53d7\u4fe1\u30fb Markdown Frontmatter \u66f4\u65b0 API",
        version=_get_app_version(),
    )

    # --- CORS ミドルウェア ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- GET /health ---
    @app.get("/health")
    async def health_check() -> JSONResponse:
        """ヘルスチェックエンドポイント。"""
        return JSONResponse(content={
            "status": "ok",
            "timestamp": datetime.now(_JST).isoformat(),
            "version": _get_app_version(),
        })

    # --- GET /react ---
    @app.get("/react", response_class=HTMLResponse)
    async def react(
        date: str = Query(
            ...,
            description="\u8a18\u4e8b\u306e\u65e5\u4ed8 (YYYY-MM-DD)",
            pattern=r"^\d{4}-\d{2}-\d{2}$",
        ),
        story: int = Query(
            ...,
            description="\u30b9\u30c8\u30fc\u30ea\u30fc ID (1-3)",
            ge=1,
            le=3,
        ),
        reaction: str = Query(
            ...,
            description="\u30ea\u30a2\u30af\u30b7\u30e7\u30f3\u7a2e\u5225",
        ),
    ) -> HTMLResponse:
        """リアクション受信エンドポイント。

        メール内リンクからのリアクションを受け付け、
        対応する Markdown ファイルの Frontmatter を更新する。
        """
        # reaction のバリデーション
        if reaction not in REACTION_MAP:
            valid_types = ", ".join(REACTION_MAP.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Invalid parameter: reaction must be one of {valid_types}",
            )

        # 日付フォーマットの追加バリデーション
        if not _DATE_PATTERN.match(date):
            raise HTTPException(
                status_code=400,
                detail="Invalid parameter: date must be in YYYY-MM-DD format",
            )

        # 日付の妥当性チェック
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date: {date}",
            )

        # Frontmatter 更新
        try:
            success = update_reaction(
                date=date,
                story_id=story,
                reaction_type=reaction,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Article not found: {date}, story {story}",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to update reaction. Please try again later.",
            )

        logger.info(
            "\u30ea\u30a2\u30af\u30b7\u30e7\u30f3\u53d7\u4fe1: date=%s, story=%d, reaction=%s",
            date,
            story,
            reaction,
        )

        html = _build_thank_you_html(reaction, story, date)
        return HTMLResponse(content=html, status_code=200)

    # --- GET /api/reaction/{date}/{story_id}/{type} (RESTful) ---
    @app.get("/api/reaction/{date}/{story_id}/{reaction_type}", response_class=HTMLResponse)
    async def react_restful(
        date: str,
        story_id: int,
        reaction_type: str,
    ) -> HTMLResponse:
        """RESTful リアクション受信エンドポイント (要件定義準拠)。"""
        if reaction_type not in REACTION_MAP:
            valid_types = ", ".join(REACTION_MAP.keys())
            raise HTTPException(
                status_code=400,
                detail=f"Invalid reaction type: must be one of {valid_types}",
            )
        if not _DATE_PATTERN.match(date):
            raise HTTPException(status_code=400, detail="Invalid date format")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date: {date}")
        if story_id < 1 or story_id > 3:
            raise HTTPException(status_code=400, detail="story_id must be 1-3")

        try:
            success = update_reaction(date=date, story_id=story_id, reaction_type=reaction_type)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Article not found: {date}, story {story_id}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update reaction.")

        logger.info("リアクション受信 (RESTful): date=%s, story=%d, reaction=%s", date, story_id, reaction_type)
        html = _build_thank_you_html(reaction_type, story_id, date)
        return HTMLResponse(content=html, status_code=200)

    # --- GET /api/stories/{date} ---
    @app.get("/api/stories/{date}")
    async def get_stories_by_date(date: str) -> JSONResponse:
        """指定日のニュース一覧取得。"""
        if not _DATE_PATTERN.match(date):
            raise HTTPException(status_code=400, detail="Invalid date format")
        try:
            from src.knowledge.search import get_all_articles
            articles = get_all_articles()
            day_articles = [a for a in articles if str(a.get("date", "")) == date]
            return JSONResponse(content={"date": date, "stories": day_articles})
        except Exception as e:
            logger.error("記事取得失敗: %s", str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # --- GET /api/stories/{date}/{story_id} ---
    @app.get("/api/stories/{date}/{story_id}")
    async def get_story_detail(date: str, story_id: int) -> JSONResponse:
        """指定ニュースの詳細取得。"""
        if not _DATE_PATTERN.match(date):
            raise HTTPException(status_code=400, detail="Invalid date format")
        try:
            from src.knowledge.search import get_all_articles
            articles = get_all_articles()
            matches = [a for a in articles if str(a.get("date", "")) == date and a.get("id") == story_id]
            if not matches:
                raise HTTPException(status_code=404, detail="Story not found")
            return JSONResponse(content=matches[0])
        except HTTPException:
            raise
        except Exception as e:
            logger.error("記事詳細取得失敗: %s", str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # --- GET /api/search ---
    @app.get("/api/search")
    async def search_articles(
        q: str = Query(None, description="全文検索キーワード"),
        tag: str = Query(None, description="タグ（カンマ区切り）"),
        min_rating: int = Query(None, description="最低リアクション数", ge=0),
    ) -> JSONResponse:
        """ナレッジベース検索。"""
        try:
            from src.knowledge.search import get_all_articles, search_by_tag, search_fulltext, filter_by_rating
            results = None
            if q:
                results = search_fulltext(q)
            elif tag:
                results = search_by_tag(tag.split(",")[0].strip())
            else:
                results = get_all_articles()
            if min_rating is not None and results is not None:
                results = [r for r in results if isinstance(r.get("rating"), (int, float)) and r["rating"] >= min_rating]
            return JSONResponse(content={"total": len(results or []), "results": results or []})
        except Exception as e:
            logger.error("検索失敗: %s", str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # --- GET /api/summary/{year}/{month} ---
    @app.get("/api/summary/{year}/{month}")
    async def get_monthly_summary(year: int, month: int) -> JSONResponse:
        """月次サマリー取得。"""
        try:
            from pathlib import Path
            from src.utils.config import AppConfig
            config = AppConfig.get_instance()
            monthly_dir = config.get("knowledge_base.monthly_dir", "./knowledge_base/monthly")
            summary_path = Path(monthly_dir) / f"{year:04d}-{month:02d}_summary.md"
            if not summary_path.exists():
                raise HTTPException(status_code=404, detail=f"Summary not found: {year}-{month:02d}")
            content = summary_path.read_text(encoding="utf-8")
            return JSONResponse(content={"year": year, "month": month, "content": content})
        except HTTPException:
            raise
        except Exception as e:
            logger.error("月次サマリー取得失敗: %s", str(e))
            raise HTTPException(status_code=500, detail=str(e))

    # --- GET /api/health ---
    @app.get("/api/health")
    async def api_health_check() -> JSONResponse:
        """API ヘルスチェック (/api/health)。"""
        return JSONResponse(content={
            "status": "ok",
            "timestamp": datetime.now(_JST).isoformat(),
            "version": _get_app_version(),
        })

    # --- GET /api/stats ---
    @app.get("/api/stats")
    async def api_stats() -> JSONResponse:
        """API 蓄積統計情報 (/api/stats)。"""
        return await stats()

    # --- GET /stats ---
    @app.get("/stats")
    async def stats() -> JSONResponse:
        """蓄積統計情報エンドポイント。

        ナレッジベースの全記事を走査し、統計を集計して返す。
        """
        try:
            from src.knowledge.search import get_all_articles
            articles = get_all_articles()
        except Exception as e:
            logger.error("\u7d71\u8a08\u60c5\u5831\u306e\u53d6\u5f97\u306b\u5931\u6557\u3057\u307e\u3057\u305f: %s", str(e))
            return JSONResponse(content={
                "total_articles": 0,
                "total_reactions": 0,
                "reaction_breakdown": {},
                "top_tags": [],
                "average_rating": 0.0,
                "date_range": {"from": None, "to": None},
            })

        # 統計の集計
        total_articles = len(articles)
        reaction_breakdown: dict[str, int] = {key: 0 for key in REACTION_MAP}
        tag_counter: dict[str, int] = {}
        ratings: list[int] = []
        dates: list[str] = []

        for article in articles:
            # リアクション集計
            reaction = article.get("reaction")
            if reaction and reaction in reaction_breakdown:
                reaction_breakdown[reaction] += 1

            # rating 集計
            rating = article.get("rating")
            if rating is not None and isinstance(rating, (int, float)):
                ratings.append(int(rating))

            # タグ集計
            tags = article.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str):
                        tag_counter[tag] = tag_counter.get(tag, 0) + 1

            # 日付集計
            article_date = article.get("date")
            if article_date:
                dates.append(str(article_date))

        total_reactions = sum(reaction_breakdown.values())
        average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

        # タグの上位取得（出現回数の降順）
        sorted_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)
        top_tags = [{"tag": tag, "count": count} for tag, count in sorted_tags[:10]]

        # 日付範囲
        sorted_dates = sorted(dates) if dates else []
        date_range = {
            "from": sorted_dates[0] if sorted_dates else None,
            "to": sorted_dates[-1] if sorted_dates else None,
        }

        return JSONResponse(content={
            "total_articles": total_articles,
            "total_reactions": total_reactions,
            "reaction_breakdown": reaction_breakdown,
            "top_tags": top_tags,
            "average_rating": average_rating,
            "date_range": date_range,
        })

    return app


def run_server(
    host: str | None = None,
    port: int | None = None,
) -> None:
    """FastAPI サーバーを起動する。

    Args:
        host: バインドアドレス。None の場合は config.yaml から取得。
        port: ポート番号。None の場合は config.yaml から取得。
    """
    # 設定の解決
    if host is None or port is None:
        try:
            from src.utils.config import AppConfig
            config = AppConfig.get_instance()
            if host is None:
                host = config.get("feedback_server.host", "127.0.0.1")
            if port is None:
                port = config.get("feedback_server.port", 8321)
        except Exception:
            host = host or "127.0.0.1"
            port = port or 8321

    app = create_app()

    logger.info(
        "\u30d5\u30a3\u30fc\u30c9\u30d0\u30c3\u30af\u30b5\u30fc\u30d0\u30fc\u3092\u8d77\u52d5\u3057\u307e\u3059: http://%s:%d",
        host,
        port,
    )

    uvicorn.run(app, host=host, port=port, log_level="info")
