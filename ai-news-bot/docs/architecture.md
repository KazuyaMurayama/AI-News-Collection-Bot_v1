# AI News Collector Bot - アーキテクチャ設計書

| 項目 | 内容 |
|------|------|
| **文書バージョン** | 1.0 |
| **作成日** | 2026-02-25 |
| **対応要件定義書** | requirements.md v1.0 |
| **ステータス** | 初版 |

---

## 1. システムアーキテクチャ図

### 1.1 全体アーキテクチャ

```mermaid
graph TB
    subgraph External["外部サービス"]
        RSS["RSS フィード<br/>(TechCrunch, VentureBeat,<br/>The Verge, Reddit, arXiv,<br/>HuggingFace, Publickey, ITmedia)"]
        WEB["Web サイト<br/>(日経クロステック, ITmedia)"]
        NEWSAPI["NewsAPI.org"]
        HNAPI["Hacker News<br/>Algolia API"]
        CLAUDE["Claude API<br/>(Anthropic)"]
        GMAIL["Gmail API<br/>(Google OAuth2)"]
        LINE["LINE Notify API"]
    end

    subgraph Scheduler["スケジューラ"]
        CRON["cron<br/>(毎朝 6:00 JST)"]
        MANUAL["手動実行<br/>(run_once.sh)"]
    end

    subgraph Core["AI News Bot コアシステム"]
        MAIN["main.py<br/>オーケストレーター"]

        subgraph Collector["収集レイヤー (collector/)"]
            RSS_C["rss_collector.py"]
            WEB_C["web_scraper.py"]
            NEWS_C["news_api.py"]
            SEL["selector.py<br/>(Claude API スコアリング)"]
        end

        subgraph Writer["生成レイヤー (writer/)"]
            STORY["storyteller.py<br/>(Claude API 変換)"]
            MDGEN["markdown_gen.py"]
            TMPL["templates/"]
        end

        subgraph Delivery["配信レイヤー (delivery/)"]
            HTML_C["html_converter.py"]
            GMAIL_S["gmail_sender.py"]
            LINE_S["line_sender.py"]
        end

        subgraph Feedback["フィードバックレイヤー (feedback/)"]
            API_SRV["api_server.py<br/>(FastAPI)"]
            UPD["updater.py"]
        end

        subgraph Knowledge["ナレッジレイヤー (knowledge/)"]
            SEARCH["search.py"]
            TAG["tagger.py"]
            SUM["summarizer.py"]
        end

        subgraph Utils["共通ユーティリティ (utils/)"]
            LOG["logger.py"]
            CFG["config.py"]
            RETRY["retry.py"]
        end
    end

    subgraph Storage["ストレージ"]
        KB_D["knowledge_base/daily/<br/>- YYYY-MM-DD_candidates.json<br/>- YYYY-MM-DD_ai_news.md"]
        KB_M["knowledge_base/monthly/<br/>- YYYY-MM_summary.md"]
        LOGS["logs/<br/>- app.log<br/>- cron.log"]
        CONFIG["config.yaml"]
        ENV[".env<br/>(APIキー・トークン)"]
    end

    subgraph User["ユーザー"]
        EMAIL_U["メール受信者"]
        LINE_U["LINE 受信者"]
        BROWSER["ブラウザ<br/>(リアクション)"]
    end

    CRON --> MAIN
    MANUAL --> MAIN

    MAIN --> RSS_C
    MAIN --> WEB_C
    MAIN --> NEWS_C
    RSS_C --> RSS
    WEB_C --> WEB
    NEWS_C --> NEWSAPI
    NEWS_C --> HNAPI

    RSS_C --> SEL
    WEB_C --> SEL
    NEWS_C --> SEL
    SEL --> CLAUDE

    SEL --> STORY
    STORY --> CLAUDE
    STORY --> MDGEN
    MDGEN --> TMPL

    MDGEN --> HTML_C
    HTML_C --> GMAIL_S
    GMAIL_S --> GMAIL
    HTML_C --> LINE_S
    LINE_S --> LINE

    GMAIL --> EMAIL_U
    LINE --> LINE_U
    EMAIL_U --> BROWSER
    BROWSER --> API_SRV
    API_SRV --> UPD
    UPD --> KB_D

    MDGEN --> KB_D
    SEL --> KB_D
    SUM --> KB_M
    TAG --> CLAUDE

    MAIN --> LOG
    MAIN --> CFG
    CFG --> CONFIG
    CFG --> ENV
    LOG --> LOGS
```

### 1.2 デプロイメント構成

```mermaid
graph LR
    subgraph Server["実行サーバー (Linux/Mac)"]
        subgraph Batch["バッチプロセス"]
            CRON_D["cron デーモン"]
            PYTHON["Python 3.11+<br/>main.py"]
        end

        subgraph Service["常駐サービス"]
            SYSTEMD["systemd / 手動起動"]
            FASTAPI["FastAPI サーバー<br/>:8080"]
        end

        subgraph FS["ファイルシステム"]
            PROJECT["ai-news-bot/"]
        end
    end

    subgraph External["外部"]
        APIS["外部 API 群"]
        NGROK["ngrok / Cloudflare Tunnel<br/>(外部公開時のみ)"]
    end

    CRON_D -->|"毎朝 6:00"| PYTHON
    PYTHON --> APIS
    SYSTEMD --> FASTAPI
    FASTAPI -.->|"外部公開時"| NGROK
    PYTHON --> FS
    FASTAPI --> FS
```

---

## 2. ディレクトリ構成

```
ai-news-bot/
├── config.yaml              # アプリケーション設定（ソース、配信先、API設定等）
├── .env                     # 秘密情報（APIキー、トークン）※ gitignore対象
├── .env.example             # .env のテンプレート（値は空）
├── requirements.txt         # Python 依存パッケージ一覧
├── setup.sh                 # 初期セットアップスクリプト（venv作成、依存インストール）
├── src/
│   ├── __init__.py
│   ├── main.py              # エントリポイント・オーケストレーター
│   ├── collector/            # ニュース収集モジュール群
│   │   ├── __init__.py
│   │   ├── rss_collector.py  # RSS フィード取得・パース
│   │   ├── web_scraper.py    # Web スクレイピング（robots.txt準拠）
│   │   ├── news_api.py       # NewsAPI / HackerNews API クライアント
│   │   └── selector.py       # Claude API によるスコアリング・記事選定
│   ├── writer/               # コンテンツ生成モジュール群
│   │   ├── __init__.py
│   │   ├── storyteller.py    # Claude API によるストーリーテリング変換
│   │   ├── markdown_gen.py   # Markdown ファイル生成（Frontmatter付き）
│   │   └── templates/        # Jinja2 テンプレート
│   │       ├── daily_report.md.j2      # 日次Markdownテンプレート
│   │       ├── email.html.j2           # メールHTMLテンプレート
│   │       └── line_message.txt.j2     # LINE メッセージテンプレート
│   ├── delivery/             # 配信モジュール群
│   │   ├── __init__.py
│   │   ├── gmail_sender.py   # Gmail API 送信（OAuth2認証）
│   │   ├── line_sender.py    # LINE Notify 送信
│   │   └── html_converter.py # Markdown → HTML 変換・スタイリング
│   ├── feedback/             # リアクション・フィードバックモジュール群
│   │   ├── __init__.py
│   │   ├── api_server.py     # FastAPI リアクションサーバー
│   │   └── updater.py        # Markdown Frontmatter 更新処理
│   ├── knowledge/            # ナレッジベース管理モジュール群
│   │   ├── __init__.py
│   │   ├── search.py         # タグ検索・全文検索・フィルタリング
│   │   ├── tagger.py         # Claude API による自動タグ付与
│   │   └── summarizer.py     # 月次サマリー生成
│   └── utils/                # 共通ユーティリティ
│       ├── __init__.py
│       ├── logger.py         # ログ設定（ローテーション付き）
│       ├── config.py         # config.yaml / .env 読み込み・バリデーション
│       └── retry.py          # リトライデコレータ（指数バックオフ）
├── knowledge_base/           # ナレッジベースストレージ
│   ├── daily/                # 日次データ
│   │   ├── YYYY-MM-DD_candidates.json  # 候補記事（中間データ）
│   │   └── YYYY-MM-DD_ai_news.md       # 日次レポート（最終出力）
│   └── monthly/              # 月次データ
│       └── YYYY-MM_summary.md           # 月次サマリー
├── logs/                     # ログファイル
│   ├── app.log               # アプリケーションログ（日次ローテーション）
│   └── cron.log              # cron 実行ログ
├── tests/                    # テストコード
│   ├── __init__.py
│   ├── test_collector/
│   ├── test_writer/
│   ├── test_delivery/
│   ├── test_feedback/
│   ├── test_knowledge/
│   └── conftest.py           # pytest 共通フィクスチャ
├── docs/                     # ドキュメント
│   ├── requirements.md       # 要件定義書
│   └── architecture.md       # アーキテクチャ設計書（本文書）
└── scripts/                  # 運用スクリプト
    ├── install_cron.sh       # cron ジョブ登録スクリプト
    └── run_once.sh           # 手動一回実行スクリプト
```

---

## 3. モジュール分割と責務

### 3.1 モジュール一覧

| モジュール | ファイル | 責務 | 依存先 |
|-----------|---------|------|--------|
| **main** | `main.py` | パイプライン全体の制御。収集→選定→生成→配信の一連フローを実行 | collector, writer, delivery, utils |
| **collector.rss_collector** | `rss_collector.py` | RSSフィード取得・パース。複数ソースの並列取得 | feedparser, utils.retry |
| **collector.web_scraper** | `web_scraper.py` | Webスクレイピングによる記事取得（robots.txt準拠） | requests, beautifulsoup4, utils.retry |
| **collector.news_api** | `news_api.py` | NewsAPI / Hacker News Algolia API からの記事取得 | requests, utils.retry |
| **collector.selector** | `selector.py` | 候補記事のClaude APIスコアリング、上位3件選定、中間JSON保存 | anthropic, utils.config |
| **writer.storyteller** | `storyteller.py` | Claude APIによるストーリーテリング形式変換。フレームワーク自動選択 | anthropic, utils.config |
| **writer.markdown_gen** | `markdown_gen.py` | Markdown生成（Frontmatter + 本文）。Jinja2テンプレート利用 | jinja2, python-frontmatter |
| **delivery.html_converter** | `html_converter.py` | Markdown→HTML変換。レスポンシブ・ダークモード対応のスタイリング | markdown, jinja2 |
| **delivery.gmail_sender** | `gmail_sender.py` | Gmail APIによるメール送信。OAuth2認証・トークン管理 | google-auth, google-api-python-client |
| **delivery.line_sender** | `line_sender.py` | LINE Notify APIによるメッセージ送信 | requests |
| **feedback.api_server** | `api_server.py` | FastAPIリアクションサーバー。エンドポイント定義・リクエスト処理 | fastapi, uvicorn |
| **feedback.updater** | `updater.py` | Markdownファイルの Frontmatter 更新（reaction, rating） | python-frontmatter |
| **knowledge.search** | `search.py` | ナレッジベースのタグ検索・全文検索・フィルタリング | python-frontmatter, glob |
| **knowledge.tagger** | `tagger.py` | Claude APIによる自動カテゴリ分類・タグ付与 | anthropic |
| **knowledge.summarizer** | `summarizer.py` | 月次サマリー生成（統計集計 + Claude APIインサイト生成） | anthropic, python-frontmatter |
| **utils.logger** | `logger.py` | ログ設定の初期化。日次ローテーション、フォーマット統一 | logging (標準ライブラリ) |
| **utils.config** | `config.py` | config.yaml / .env の読み込み・バリデーション・アクセス提供 | pyyaml, python-dotenv |
| **utils.retry** | `retry.py` | 指数バックオフ付きリトライデコレータ。HTTP/API呼び出し共通化 | tenacity |

### 3.2 モジュール依存関係図

```mermaid
graph TD
    MAIN["main.py<br/>(オーケストレーター)"]

    subgraph Collector["collector/"]
        RSS_C["rss_collector"]
        WEB_C["web_scraper"]
        NEWS_C["news_api"]
        SEL["selector"]
    end

    subgraph Writer["writer/"]
        STORY["storyteller"]
        MDGEN["markdown_gen"]
    end

    subgraph Delivery["delivery/"]
        HTML["html_converter"]
        GMAIL["gmail_sender"]
        LINE_S["line_sender"]
    end

    subgraph Feedback["feedback/"]
        API_SRV["api_server"]
        UPD["updater"]
    end

    subgraph KnowledgeMod["knowledge/"]
        SRCH["search"]
        TAGGER["tagger"]
        SUMM["summarizer"]
    end

    subgraph Utils["utils/"]
        LOG["logger"]
        CFG["config"]
        RET["retry"]
    end

    MAIN --> RSS_C
    MAIN --> WEB_C
    MAIN --> NEWS_C
    MAIN --> SEL
    MAIN --> STORY
    MAIN --> MDGEN
    MAIN --> HTML
    MAIN --> GMAIL
    MAIN --> LINE_S
    MAIN --> LOG
    MAIN --> CFG

    SEL --> CFG
    STORY --> CFG
    GMAIL --> CFG
    LINE_S --> CFG
    API_SRV --> UPD
    API_SRV --> CFG
    API_SRV --> LOG

    RSS_C --> RET
    WEB_C --> RET
    NEWS_C --> RET
    GMAIL --> RET

    TAGGER --> CFG
    SUMM --> CFG
    SUMM --> SRCH

    RSS_C --> LOG
    WEB_C --> LOG
    NEWS_C --> LOG
    SEL --> LOG
    STORY --> LOG
    GMAIL --> LOG
    UPD --> LOG
```

### 3.3 主要クラス・関数の設計方針

各モジュールは**関数ベース**を基本とし、状態管理が必要な場合のみクラスを使用する。

| モジュール | 設計パターン | 理由 |
|-----------|-------------|------|
| collector各種 | 関数ベース (`collect() -> list[Article]`) | ステートレスな取得処理 |
| selector | 関数ベース (`score_and_select(candidates) -> Selected`) | 入力→出力の単純な変換 |
| storyteller | 関数ベース (`transform(article) -> Story`) | 入力→出力の単純な変換 |
| markdown_gen | 関数ベース (`generate(stories) -> Path`) | テンプレートベースの生成 |
| gmail_sender | クラスベース (`GmailSender`) | OAuth2トークンの状態管理が必要 |
| api_server | FastAPI アプリインスタンス | フレームワーク規約 |
| updater | 関数ベース (`update_reaction(date, story_id, reaction)`) | ファイル操作のみ |
| config | シングルトンパターン (`AppConfig`) | アプリ全体で共有する設定 |

---

## 4. データフロー図

### 4.1 メインパイプライン（日次バッチ）

```mermaid
flowchart TD
    START(["開始<br/>(cron 6:00 JST / 手動)"])

    subgraph Phase1["Phase 1: 収集"]
        P1_1["RSS フィード取得<br/>(feedparser)"]
        P1_2["Web スクレイピング<br/>(BeautifulSoup)"]
        P1_3["NewsAPI / HN API<br/>(requests)"]
        P1_MERGE["候補記事マージ<br/>重複排除"]
    end

    subgraph Phase2["Phase 2: 選定"]
        P2_1["Claude API<br/>スコアリング<br/>(5基準 合計20点満点)"]
        P2_2["上位3件選定"]
        P2_3["中間JSON保存<br/>(candidates.json)"]
    end

    subgraph Phase3["Phase 3: 生成"]
        P3_1["フレームワーク自動選択<br/>(STAR/ヒーローズジャーニー/<br/>Before-After-Bridge/PAS)"]
        P3_2["Claude API<br/>ストーリーテリング変換<br/>(各800-1200文字)"]
        P3_3["Today's Insight 生成<br/>(Claude API)"]
        P3_4["Markdown 生成<br/>(Frontmatter + 本文)"]
    end

    subgraph Phase4["Phase 4: 配信"]
        P4_1["Markdown → HTML 変換<br/>(リアクションリンク埋め込み)"]
        P4_2["Gmail API 送信"]
        P4_3["LINE Notify 送信<br/>(オプション)"]
    end

    subgraph Phase5["Phase 5: 蓄積"]
        P5_1["Markdown ファイル保存<br/>(knowledge_base/daily/)"]
        P5_2["自動タグ付与<br/>(Claude API)"]
    end

    START --> P1_1
    START --> P1_2
    START --> P1_3
    P1_1 --> P1_MERGE
    P1_2 --> P1_MERGE
    P1_3 --> P1_MERGE

    P1_MERGE -->|"候補記事リスト<br/>(list[Article])"| P2_1
    P2_1 -->|"スコア付き記事"| P2_2
    P2_2 --> P2_3
    P2_2 -->|"選定3件<br/>(list[Article])"| P3_1

    P3_1 --> P3_2
    P3_2 -->|"3つのStory"| P3_3
    P3_3 --> P3_4

    P3_4 -->|"Markdown文字列"| P4_1
    P4_1 -->|"HTML文字列"| P4_2
    P4_1 -->|"テキスト要約"| P4_3

    P3_4 --> P5_1
    P5_1 --> P5_2

    P4_2 --> END(["完了"])
    P4_3 --> END
    P5_2 --> END

    style Phase1 fill:#e3f2fd,stroke:#1565c0
    style Phase2 fill:#fff3e0,stroke:#e65100
    style Phase3 fill:#e8f5e9,stroke:#2e7d32
    style Phase4 fill:#fce4ec,stroke:#c62828
    style Phase5 fill:#f3e5f5,stroke:#6a1b9a
```

### 4.2 リアクションフロー

```mermaid
sequenceDiagram
    participant U as ユーザー(メール)
    participant B as ブラウザ
    participant F as FastAPI サーバー<br/>(:8080)
    participant MD as Markdown ファイル<br/>(knowledge_base/daily/)

    U->>B: リアクションリンクをクリック
    B->>F: GET /react?date=2026-02-25&story=1&reaction=excellent
    F->>F: パラメータバリデーション
    F->>MD: Frontmatter 読み込み
    F->>MD: reaction / rating フィールド更新
    MD-->>F: 更新完了
    F-->>B: HTML レスポンス<br/>("ありがとうございます！" 画面)
    Note over F,MD: reaction: "excellent"<br/>rating: 5<br/>reacted_at: "2026-02-25T10:30:00+09:00"
```

### 4.3 データモデル

```mermaid
erDiagram
    CANDIDATES_JSON {
        string date "YYYY-MM-DD"
        array candidates "候補記事配列"
        array selected "選定インデックス"
    }

    ARTICLE {
        string title "記事タイトル"
        string url "記事URL"
        string source "ソース名"
        string summary "記事概要"
        datetime published_at "公開日時"
        object score "スコアオブジェクト"
    }

    SCORE {
        int novelty "先進性 (0-5)"
        int surprise "意外性 (0-5)"
        int practicality "実用性 (0-5)"
        int japan_relevance "日本企業関連性 (0-3)"
        int freshness "鮮度 (0-2)"
        int total "合計 (0-20)"
    }

    DAILY_MARKDOWN {
        string date "YYYY-MM-DD"
        array tags "全体タグ"
        array stories "ストーリー配列"
    }

    STORY_META {
        int id "ストーリーID (1-3)"
        string title "タイトル"
        string source "ソース名"
        string url "元記事URL"
        string category "カテゴリ"
        array tags "タグ配列"
        int rating "評価スコア (null or 1-5)"
        string reaction "リアクション種別 (null or type)"
        datetime reacted_at "リアクション日時"
    }

    MONTHLY_SUMMARY {
        string month "YYYY-MM"
        object tag_stats "タグ別集計"
        array top_rated "高評価Top5"
        object category_trends "カテゴリ別トレンド"
        string insight "月次インサイト(テキスト)"
    }

    CANDIDATES_JSON ||--o{ ARTICLE : contains
    ARTICLE ||--|| SCORE : has
    DAILY_MARKDOWN ||--o{ STORY_META : contains
```

---

## 5. 技術選定と根拠

### 5.1 コアランタイム

| 技術 | バージョン | 選定根拠 |
|------|-----------|---------|
| **Python** | 3.11+ | 要件定義の指定。データ処理・API連携のエコシステムが充実。型ヒント対応が成熟 |

### 5.2 外部API連携

| ライブラリ | 用途 | 選定根拠 |
|-----------|------|---------|
| **anthropic** | Claude API クライアント | 公式SDK。型安全なリクエスト/レスポンス処理 |
| **google-auth** + **google-auth-oauthlib** | Gmail OAuth2 認証 | Google公式。リフレッシュトークン管理が堅牢 |
| **google-api-python-client** | Gmail API 操作 | Google公式。メール送信・ラベル操作に対応 |
| **requests** | HTTP通信全般 | 軽量で安定。NewsAPI / HN API / LINE Notify に使用 |

### 5.3 データ収集

| ライブラリ | 用途 | 選定根拠 |
|-----------|------|---------|
| **feedparser** | RSS フィード解析 | RSSパースのデファクトスタンダード。Atom/RSS2.0両対応 |
| **beautifulsoup4** + **lxml** | Web スクレイピング | HTMLパースの定番。lxmlバックエンドで高速処理 |

### 5.4 コンテンツ生成・変換

| ライブラリ | 用途 | 選定根拠 |
|-----------|------|---------|
| **Jinja2** | テンプレートエンジン | Markdown/HTMLテンプレートの柔軟な生成。Python標準的なテンプレートエンジン |
| **python-frontmatter** | YAML Frontmatter 操作 | Markdownメタデータの読み書きに特化。要件FR-6.2に直結 |
| **markdown** | Markdown → HTML 変換 | 軽量。拡張機能（tables, fenced_code等）で十分な表現力 |

### 5.5 サーバー・API

| ライブラリ | 用途 | 選定根拠 |
|-----------|------|---------|
| **FastAPI** | リアクション API サーバー | 高速・型安全・自動ドキュメント生成。軽量APIサーバーに最適 |
| **uvicorn** | ASGI サーバー | FastAPIの推奨サーバー。本番利用可能な性能 |

### 5.6 設定・ユーティリティ

| ライブラリ | 用途 | 選定根拠 |
|-----------|------|---------|
| **PyYAML** | config.yaml 読み込み | YAML解析のデファクトスタンダード |
| **python-dotenv** | .env ファイル読み込み | 環境変数による秘密情報管理の標準的手法 |
| **tenacity** | リトライ処理 | 指数バックオフ・条件付きリトライを宣言的に記述可能 |

### 5.7 テスト

| ライブラリ | 用途 | 選定根拠 |
|-----------|------|---------|
| **pytest** | テストフレームワーク | Pythonのテスト標準。フィクスチャ・パラメタライズが強力 |
| **pytest-asyncio** | 非同期テスト | FastAPIのテストに必要 |
| **httpx** | テスト用HTTPクライアント | FastAPIのTestClientとして使用 |

### 5.8 技術選定で見送ったもの

| 技術 | 見送り理由 |
|------|-----------|
| **Celery** | タスクキューはオーバースペック。cronによる単純なバッチ実行で十分 |
| **SQLite / PostgreSQL** | RDBは不要。ファイルベース（Markdown + JSON）でナレッジベースを管理する方がシンプルで可搬性が高い |
| **Redis** | キャッシュ層は不要。日次1回実行のバッチ処理であり、状態管理はファイルで十分 |
| **Docker** | 初期段階では不要。セットアップスクリプト（venv）で十分。将来的にDocker化は検討可能 |
| **FAISS / ChromaDB** | ベクトル検索はCould Have要件（RAG連携）のため、初期段階では見送り |

---

## 6. APIエンドポイント設計

### 6.1 リアクションサーバー（FastAPI）

**ベースURL**: `http://localhost:8080`

#### GET /react

リアクション受信・Markdownファイル更新。

| パラメータ | 型 | 必須 | 説明 | 例 |
|-----------|-----|------|------|-----|
| `date` | string (YYYY-MM-DD) | Yes | 記事の日付 | `2026-02-25` |
| `story` | int (1-3) | Yes | ストーリーID | `1` |
| `reaction` | string (enum) | Yes | リアクション種別 | `excellent` |

**reaction の値と rating の対応**:

| reaction値 | 表示 | rating |
|-----------|------|--------|
| `excellent` | 素晴らしい | 5 |
| `good` | 良い | 4 |
| `bookmark` | 後で読む | 3 |
| `meh` | 微妙 | 2 |

**レスポンス**:

```
成功時 (200):
- Content-Type: text/html
- リアクション完了メッセージの HTML ページ

エラー時 (400):
{
  "detail": "Invalid parameter: reaction must be one of excellent, good, bookmark, meh"
}

エラー時 (404):
{
  "detail": "Article not found: 2026-02-25, story 1"
}
```

**処理フロー**:
1. パラメータバリデーション
2. `knowledge_base/daily/{date}_ai_news.md` を読み込み
3. 該当ストーリーの `reaction` / `rating` / `reacted_at` を更新
4. ファイルに書き戻し
5. 完了HTMLを返却

---

#### GET /health

ヘルスチェック。

**レスポンス**:
```json
{
  "status": "ok",
  "timestamp": "2026-02-25T10:00:00+09:00",
  "version": "1.0.0"
}
```

---

#### GET /stats

蓄積統計情報の取得。

**レスポンス**:
```json
{
  "total_articles": 150,
  "total_reactions": 87,
  "reaction_breakdown": {
    "excellent": 25,
    "good": 40,
    "bookmark": 15,
    "meh": 7
  },
  "top_tags": [
    {"tag": "業務効率化", "count": 32},
    {"tag": "創造支援", "count": 28},
    {"tag": "コスト削減", "count": 18}
  ],
  "average_rating": 3.8,
  "date_range": {
    "from": "2026-01-01",
    "to": "2026-02-25"
  }
}
```

---

### 6.2 メール内リアクションリンクの形式

メール本文に埋め込むリアクションリンクの生成規則:

```
http://localhost:8080/react?date={YYYY-MM-DD}&story={1-3}&reaction={type}
```

**HTMLボタン例**:
```html
<a href="http://localhost:8080/react?date=2026-02-25&story=1&reaction=excellent"
   style="padding:8px 16px; background:#ffd700; border-radius:4px; text-decoration:none;">
   ⭐ 素晴らしい
</a>
<a href="http://localhost:8080/react?date=2026-02-25&story=1&reaction=good"
   style="padding:8px 16px; background:#4caf50; border-radius:4px; text-decoration:none;">
   👍 良い
</a>
<a href="http://localhost:8080/react?date=2026-02-25&story=1&reaction=meh"
   style="padding:8px 16px; background:#ff9800; border-radius:4px; text-decoration:none;">
   🤔 微妙
</a>
<a href="http://localhost:8080/react?date=2026-02-25&story=1&reaction=bookmark"
   style="padding:8px 16px; background:#2196f3; border-radius:4px; text-decoration:none;">
   📌 後で読む
</a>
```

---

## 7. 設定ファイル (config.yaml) のスキーマ

### 7.1 完全なスキーマ定義

```yaml
# ============================================================
# AI News Collector Bot - 設定ファイル
# ============================================================

# --- アプリケーション全般 ---
app:
  name: "AI News Collector Bot"        # アプリケーション名
  version: "1.0.0"                     # バージョン
  timezone: "Asia/Tokyo"               # タイムゾーン
  daily_article_count: 3               # 日次配信記事数

# --- ニュース収集ソース設定 ---
sources:
  rss:
    enabled: true
    feeds:
      - name: "TechCrunch AI"
        url: "https://techcrunch.com/category/artificial-intelligence/feed/"
        category: "海外テック"
        language: "en"
      - name: "VentureBeat AI"
        url: "https://venturebeat.com/category/ai/feed/"
        category: "海外テック"
        language: "en"
      - name: "The Verge AI"
        url: "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
        category: "海外テック"
        language: "en"
      - name: "Reddit r/MachineLearning"
        url: "https://www.reddit.com/r/MachineLearning/.rss"
        category: "コミュニティ"
        language: "en"
      - name: "Reddit r/artificial"
        url: "https://www.reddit.com/r/artificial/.rss"
        category: "コミュニティ"
        language: "en"
      - name: "arXiv cs.AI"
        url: "http://export.arxiv.org/rss/cs.AI"
        category: "学術"
        language: "en"
      - name: "arXiv cs.CL"
        url: "http://export.arxiv.org/rss/cs.CL"
        category: "学術"
        language: "en"
      - name: "Hugging Face Blog"
        url: "https://huggingface.co/blog/feed.xml"
        category: "学術"
        language: "en"
      - name: "ITmedia AI+"
        url: "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"
        category: "国内テック"
        language: "ja"
      - name: "Publickey"
        url: "https://www.publickey1.jp/atom.xml"
        category: "国内テック"
        language: "ja"
    fetch_timeout: 30                  # 各フィードの取得タイムアウト(秒)
    max_articles_per_feed: 20          # フィードあたりの最大取得件数

  scraping:
    enabled: true                      # Should Have (false で無効化可能)
    targets:
      - name: "日経クロステック"
        url: "https://xtech.nikkei.com/atcl/nxt/column/18/00001/"
        category: "国内テック"
        language: "ja"
        selector:                      # CSSセレクタ設定
          article_list: ".article-list__item"
          title: ".article-list__title"
          url: "a"
          summary: ".article-list__summary"
    respect_robots_txt: true           # robots.txt 準拠
    fetch_timeout: 30
    request_interval: 2                # リクエスト間隔(秒) - サーバー負荷軽減

  newsapi:
    enabled: true
    base_url: "https://newsapi.org/v2"
    query: "artificial intelligence OR generative AI OR LLM"
    language: "en"
    sort_by: "publishedAt"
    page_size: 20                      # 1回の取得件数
    # API キーは .env で管理: NEWSAPI_API_KEY

  hackernews:
    enabled: true
    base_url: "http://hn.algolia.com/api/v1"
    query: "AI OR LLM OR GPT OR Claude"
    tags: "story"
    num_results: 20

# --- Claude API 設定 ---
claude:
  model: "claude-sonnet-4-20250514"    # 使用モデル
  max_tokens: 4096                     # 最大出力トークン数
  temperature: 0.7                     # 生成温度 (ストーリーテリング用)
  scoring_temperature: 0.3             # スコアリング用温度 (低めで安定)
  # API キーは .env で管理: ANTHROPIC_API_KEY

  prompts:
    scoring_system: |
      あなたはAIニュースの専門アナリストです。
      以下の基準で記事をスコアリングしてください。
      - 先進性 (0-5): 新技術・新手法の度合い
      - 意外性 (0-5): 予想外の活用法
      - 実用性 (0-5): すぐに業務適用可能か
      - 日本企業関連性 (0-3): 日本市場・企業への適用可能性
      - 鮮度 (0-2): 24時間以内の記事を優先
      JSON形式で回答してください。

    storytelling_system: |
      あなたはビジネスパーソン向けのAIニュースライターです。
      以下のフレームワークから最適なものを選び、ストーリーテリング形式で記事を書いてください。
      - STAR法: 企業導入事例向け
      - ヒーローズジャーニー簡易版: 技術革新系向け
      - Before/After/Bridge: 業務改善系向け
      - PAS: 課題解決系向け
      800-1200文字の日本語で書いてください。

    insight_system: |
      3つのAIニュース記事に共通するトレンドや示唆を分析し、
      「Today's Insight」として200-300文字でまとめてください。

# --- 記事選定設定 ---
selection:
  scoring_weights:                     # スコアリング配点
    novelty: 5                         # 先進性 (0-5)
    surprise: 5                        # 意外性 (0-5)
    practicality: 5                    # 実用性 (0-5)
    japan_relevance: 3                 # 日本企業関連性 (0-3)
    freshness: 2                       # 鮮度 (0-2)
  select_count: 3                      # 選定記事数
  freshness_hours: 24                  # 鮮度基準(時間)
  dedup_similarity_threshold: 0.8      # 重複判定の類似度しきい値

# --- 配信設定 ---
delivery:
  gmail:
    enabled: true
    sender: "your-email@gmail.com"     # 送信元アドレス
    recipients:                        # 送信先リスト
      - "recipient1@example.com"
      - "recipient2@example.com"
    subject_template: "[AI News] {date} - {headline} 他"
    # OAuth2 関連は .env で管理:
    #   GMAIL_CLIENT_ID
    #   GMAIL_CLIENT_SECRET
    #   GMAIL_TOKEN_PATH (デフォルト: ./credentials/gmail_token.json)

  line:
    enabled: false                     # オプション機能（デフォルトOFF）
    # アクセストークンは .env で管理: LINE_NOTIFY_TOKEN

# --- リアクションサーバー設定 ---
feedback_server:
  host: "0.0.0.0"                      # バインドアドレス
  port: 8080                           # ポート番号
  base_url: "http://localhost:8080"    # メール内リンクのベースURL
  # 外部公開時は ngrok/cloudflare tunnel の URL に変更

# --- ナレッジベース設定 ---
knowledge_base:
  daily_dir: "./knowledge_base/daily"
  monthly_dir: "./knowledge_base/monthly"
  categories:                          # 自動タグのカテゴリ一覧
    - "業務効率化"
    - "創造支援"
    - "コスト削減"
    - "新規事業"
    - "研究・学術"
    - "ヘルスケア"
    - "教育"
    - "金融"
    - "製造"
    - "マーケティング"

# --- ログ設定 ---
logging:
  level: "INFO"                        # ログレベル (DEBUG, INFO, WARNING, ERROR)
  dir: "./logs"                        # ログ出力ディレクトリ
  app_log: "app.log"                   # アプリケーションログファイル名
  cron_log: "cron.log"                 # cron実行ログファイル名
  rotation: "daily"                    # ローテーション方式
  retention_days: 30                   # ログ保持日数
  format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# --- リトライ設定 ---
retry:
  max_attempts: 3                      # 最大リトライ回数
  initial_wait: 1                      # 初回待機時間(秒)
  exponential_base: 2                  # 指数バックオフの底
  max_wait: 30                         # 最大待機時間(秒)
```

### 7.2 .env ファイルのスキーマ

```bash
# ============================================================
# AI News Collector Bot - 環境変数（秘密情報）
# ============================================================

# --- Claude API (Anthropic) ---
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# --- NewsAPI ---
NEWSAPI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# --- Gmail API (OAuth2) ---
GMAIL_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
GMAIL_TOKEN_PATH=./credentials/gmail_token.json

# --- LINE Notify (オプション) ---
LINE_NOTIFY_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 7.3 スキーマバリデーション方針

`utils/config.py` は以下のバリデーションを起動時に実行する:

| チェック項目 | 条件 | エラー時の動作 |
|-------------|------|---------------|
| config.yaml の存在 | ファイルが読み込めること | 起動中止 + エラーログ |
| .env の存在 | ファイルが読み込めること | 起動中止 + エラーログ |
| ANTHROPIC_API_KEY | 空でないこと | 起動中止 |
| NEWSAPI_API_KEY | newsapi.enabled=true の場合、空でないこと | 起動中止 |
| Gmail 認証情報 | gmail.enabled=true の場合、必要な値が揃っていること | 起動中止 |
| LINE トークン | line.enabled=true の場合、空でないこと | 起動中止 |
| ポート番号 | 1024-65535 の範囲 | 起動中止 |
| RSSフィード URL | 有効なURL形式 | 警告ログ + 該当フィードスキップ |
| ディレクトリパス | 書き込み権限があること | 起動中止 |

---

## 付録

### A. requirements.txt（想定）

```
# Core
anthropic>=0.40.0
feedparser>=6.0.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
requests>=2.31.0

# Content generation
Jinja2>=3.1.0
python-frontmatter>=1.1.0
Markdown>=3.5.0

# Gmail API
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
google-api-python-client>=2.110.0

# Feedback server
fastapi>=0.110.0
uvicorn>=0.27.0

# Configuration
PyYAML>=6.0.0
python-dotenv>=1.0.0

# Retry
tenacity>=8.2.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

### B. エラーハンドリング方針

| 障害パターン | 検知方法 | 対処方針 |
|-------------|---------|---------|
| RSSフィード取得失敗 | requests例外 / feedparser エラー | リトライ3回→スキップ。他ソースで補完 |
| Webスクレイピング失敗 | requests例外 / パース失敗 | リトライ3回→スキップ。RSSとAPIで補完 |
| NewsAPI/HN API 失敗 | HTTPステータスコード / タイムアウト | リトライ3回→スキップ。RSS等で補完 |
| Claude API 失敗 | anthropic例外（レート制限等） | リトライ3回（指数バックオフ）→エラー通知メール |
| 候補記事が3件未満 | 選定フェーズでのカウント | 収集できた件数で配信（最低1件）。エラー通知付加 |
| Gmail API 送信失敗 | google API例外 | リトライ3回→エラーログ。Markdownファイルは保存済みなのでデータ損失なし |
| LINE 送信失敗 | HTTPステータスコード | リトライ3回→スキップ（オプション機能のため） |
| リアクションサーバー宛先ファイルなし | FileNotFoundError | 404レスポンス + エラーログ |
| config.yaml 不正 | バリデーション失敗 | 起動中止 + 具体的なエラーメッセージ |

### C. セキュリティ考慮事項

1. **APIキー管理**: 全てのAPIキー・トークンは `.env` ファイルで管理し、`.gitignore` に登録
2. **OAuth2トークン**: `credentials/` ディレクトリを `.gitignore` に登録
3. **リアクションサーバー**: デフォルトは `localhost` 限定。外部公開時は ngrok / Cloudflare Tunnel を使用
4. **入力バリデーション**: リアクションAPIの全パラメータをバリデーション（SQLインジェクション等はDB不使用のため該当なし、ただしパストラバーサル対策としてdate/storyの形式を厳密にチェック）
5. **robots.txt準拠**: Webスクレイピングは対象サイトの robots.txt を事前に取得・遵守
6. **レート制限**: 各外部APIのレート制限を設定ファイルで管理し、遵守
