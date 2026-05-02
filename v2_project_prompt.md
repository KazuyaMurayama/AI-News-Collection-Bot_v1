# AI News Collection Bot v2 - 構築プロンプト

## 概要

AIニュースを自動収集し、Claude APIで日本語に翻訳・解説記事化して、毎朝メールで配信するPythonアプリケーションを **ゼロから** 構築してください。

**リポジトリ**: https://github.com/KazuyaMurayama/AI-News-Collection-Bot_v2.git

---

## 1. プロジェクト構造

```
ai-news-bot/
├── config.yaml              # アプリ全体の設定ファイル
├── .env.example             # 環境変数テンプレート
├── .env                     # 環境変数（git管理外）
├── .gitignore
├── requirements.txt         # Python依存パッケージ
├── setup.sh                 # セットアップスクリプト
├── src/
│   ├── __init__.py
│   ├── main.py              # メインオーケストレーター（CLIエントリーポイント）
│   ├── collector/           # ニュース収集モジュール
│   │   ├── __init__.py      # collect_all(), collect_candidates() を公開
│   │   ├── rss_collector.py # RSS フィード収集
│   │   ├── news_api.py      # NewsAPI / Hacker News API 収集
│   │   ├── web_scraper.py   # Webスクレイピング収集
│   │   └── selector.py      # Claude APIスコアリング・記事選定
│   ├── writer/              # コンテンツ生成モジュール
│   │   ├── __init__.py      # transform_to_story等を公開
│   │   ├── storyteller.py   # Claude API日本語翻訳・解説記事生成
│   │   ├── markdown_gen.py  # YAML Frontmatter付きMarkdown生成
│   │   └── templates/
│   │       ├── email_template.html  # HTMLメールテンプレート
│   │       └── daily_template.md    # Markdown日次テンプレート
│   ├── delivery/            # 配信モジュール
│   │   ├── __init__.py
│   │   ├── gmail_sender.py  # Gmail SMTP/OAuth2 送信
│   │   ├── html_converter.py# Markdown→HTML変換・テンプレート適用
│   │   └── line_sender.py   # LINE Notify送信（オプション）
│   ├── feedback/            # フィードバック・評価モジュール
│   │   ├── __init__.py
│   │   ├── email_processor.py # IMAP経由リアクションメール処理
│   │   ├── updater.py        # Markdown Frontmatter更新
│   │   └── api_server.py     # FastAPIリアクションサーバー
│   ├── knowledge/           # ナレッジベースモジュール
│   │   ├── __init__.py
│   │   ├── search.py        # タグ検索・全文検索・評価フィルタ
│   │   ├── tagger.py        # Claude API自動タグ付け
│   │   └── summarizer.py    # 月次サマリー生成
│   └── utils/               # ユーティリティ
│       ├── __init__.py
│       ├── config.py        # 設定管理（シングルトン・バリデーション）
│       ├── logger.py        # ログ管理（日次ローテーション）
│       └── retry.py         # 指数バックオフリトライデコレータ
├── tests/                   # テスト
│   ├── __init__.py
│   ├── test_collector.py
│   ├── test_writer.py
│   ├── test_delivery.py
│   ├── test_feedback.py
│   ├── test_utils.py
│   └── test_integration.py
├── scripts/                 # 運用スクリプト
│   ├── install_cron.sh      # Linux cron設定
│   ├── run_once.sh          # 手動実行用
│   ├── run_daily.bat        # Windows用
│   └── install_task_scheduler.bat  # Windowsタスクスケジューラ設定
├── knowledge_base/          # ナレッジベース（自動生成）
│   ├── daily/               # 日次レポート（YYYY-MM-DD_ai_news.md）
│   └── monthly/             # 月次サマリー
├── logs/                    # ログファイル
├── credentials/             # OAuth2認証情報（git管理外）
└── docs/                    # ドキュメント
```

---

## 2. メインパイプラインフロー (`src/main.py`)

CLIエントリーポイント。`python -m src.main` で実行。

### CLI引数
- `--date YYYY-MM-DD`: 実行対象日付（デフォルト: 今日JST）
- `--dry-run`: 配信せずMarkdown生成まで
- `--server`: リアクションFastAPIサーバー起動
- `--process-reactions`: リアクションメール処理のみ実行

### パイプライン10ステップ
1. **ログ初期化・設定読み込み**: `AppConfig.get_instance()` でconfig.yaml + .envを読み込み
2. **リアクションメール処理（Step 1.5）**: 前日の評価メールをIMAP経由で処理し、ナレッジベースに反映
3. **ニュース収集**: `collect_all()` - RSS + API + スクレイピングで候補記事を収集し、Claude APIスコアリングで上位5件選定
4. **中間JSON保存**: `knowledge_base/daily/YYYY-MM-DD_candidates.json`
5. **ストーリーテリング変換**: 各記事をClaude APIで2000-3000文字の **日本語** 解説記事に変換。フレームワーク自動選択（STAR/ヒーローズジャーニー/Before-After-Bridge/PAS）
6. **自動タグ付け**: Claude APIでカテゴリタグ + 技術タグを自動付与
7. **本日のインサイト生成**: 記事群の共通テーマを分析し、800-1200文字の日本語インサイトを生成
8. **Markdown生成・保存**: YAML Frontmatter付きMarkdownを `knowledge_base/daily/` に保存
9. **Gmail配信**: HTMLテンプレート適用 → SMTP or OAuth2でメール送信
10. **LINE配信（オプション）**: LINE Notifyでテキスト通知
11. **エラー通知**: 致命的エラー時にGmailでエラーレポート送信

### フォールバック
- 記事0件 → 「本日のAIニュースは取得できませんでした」のフォールバック記事
- ストーリー変換失敗 → 「【要確認】元タイトル」プレフィックス付きで元の内容を表示

---

## 3. ニュース収集 (`src/collector/`)

### 3.1 RSSフィード収集 (`rss_collector.py`)
- `feedparser` ライブラリ使用
- 公開日時パース（`published_parsed` / `updated_parsed` → ISO 8601）
- HTML概要のタグ除去（最大1500文字）
- `User-Agent: AI-News-Bot/1.0`
- 個別フィード失敗時も他ソースの収集を継続

### 3.2 API収集 (`news_api.py`)
- **NewsAPI.org**: `/v2/everything` エンドポイント。`NEWS_API_KEY` 環境変数。`[Removed]` 記事をスキップ
- **Hacker News Algolia API**: `/search_by_date` エンドポイント。ポイント数・コメント数を概要に含む。URLが無い場合はHNディスカッションページをフォールバック

### 3.3 Webスクレイピング (`web_scraper.py`)
- `requests` + `BeautifulSoup`（lxmlパーサー）
- CSSセレクタベースの記事抽出
- `robots.txt` 遵守（`urllib.robotparser`）
- リクエスト間隔2秒

### 3.4 記事選定 (`selector.py`)
- **Claude APIスコアリング**（JSON出力）:
  - novelty (先進性, 0-5)
  - surprise (意外性, 0-5)
  - practicality (実用性, 0-5)
  - japan_relevance (日本企業関連性, 0-3)
  - freshness (鮮度, 0-2)
  - 合計最大20点
- 重複排除: URL完全一致 + タイトル完全一致（小文字化）
- フォールバック: API失敗時は公開日時の新しい順

### 3.5 ニュースソース（config.yaml `collection.sources`）

| ソース名 | タイプ | カテゴリ | 言語 |
|---------|-------|---------|------|
| TechCrunch AI | rss | 海外テック | en |
| VentureBeat AI | rss | 海外テック | en |
| The Verge AI | rss | 海外テック | en |
| Reddit r/MachineLearning | rss | コミュニティ | en |
| Reddit r/artificial | rss | コミュニティ | en |
| arXiv cs.AI | rss | 学術 | en |
| arXiv cs.CL | rss | 学術 | en |
| Hugging Face Blog | rss | 学術 | en |
| ITmedia AI+ | rss | 国内テック | ja |
| Publickey | rss | 国内テック | ja |
| Hacker News | api | 海外テック | en |
| NewsAPI | api | 海外テック | en |

---

## 4. 日本語ストーリーテリング変換 (`src/writer/storyteller.py`)

**v1で最も重要な問題だった部分。確実に日本語で出力させること。**

### 4.1 フレームワーク自動選択
1. **キーワードベース分類**（先に試行、API不要）:
   - STAR: 導入, 採用, 実装, deploy, case study, 企業, ROI 等
   - ヒーローズジャーニー: 革新, breakthrough, 新モデル, 論文, リリース, GPT, LLM 等
   - Before/After/Bridge: 効率化, 自動化, DX, ワークフロー, update 等
   - PAS: 課題, リスク, セキュリティ, 規制, バイアス, 脆弱性 等
2. **Claude API分類**（キーワード判定不能時）: JSON `{"framework": "...", "reason": "..."}` で回答

### 4.2 ストーリー生成（`transform_to_story()`）
- **Claude APIに送るシステムプロンプト** の要点:
  - 「日本のビジネスパーソン向けAIトレンド解説の一流テクノロジーライター」ペルソナ
  - **最重要ルール**: すべて日本語。英語出力禁止。固有名詞（GPT, Claude等）・技術用語（LLM, API等）はそのまま可
  - フレームワーク指定（STAR/ヒーローズジャーニー/Before-After-Bridge/PAS）
  - 必須要素8つ: フック、背景・文脈、技術詳細、数字・データ、業界インパクト、日本企業への示唆、今後の展望と課題、クロージング
  - 2000-3000文字
  - タイトルは日本語（疑問形 or 数字入り）
  - Markdown太字対応、見出し（#）不使用

### 4.3 日本語バリデーション（`_contains_japanese()`）
- ひらがな（U+3040-U+309F）、カタカナ（U+30A0-U+30FF）、漢字（U+4E00-U+9FFF）の割合チェック
- 最低10%以上（`min_ratio=0.1`）
- **日本語が含まれない場合**: 「前回の出力が英語でした。必ず日本語で出力してください」と再プロンプトして再試行

### 4.4 タイトル・本文分離（`extract_title_and_body()`）
- 最初の非空行をタイトルとして抽出
- Markdown太字`**...**`や見出し`#`を除去してクリーンなタイトルに
- 残りを本文に

### 4.5 インサイト生成（`generate_insight()`）
- 記事群の共通テーマ分析
- 800-1200文字の日本語
- 必須要素: 共通テーマ、マクロトレンド、日本市場の機会と課題、アクションポイント5つ以上、今後1-3ヶ月の注目点

---

## 5. 自動タグ付け (`src/knowledge/tagger.py`)

Claude APIで記事内容を分析し、以下から自動選択:

### カテゴリタグ（1-3個）
業務効率化, 創造支援, コスト削減, 新規事業, 研究・学術, ヘルスケア, 教育, 金融, 製造, マーケティング

### 技術タグ（0-5個）
LLM, 画像生成, 音声AI, マルチモーダル, RAG, Agent, ファインチューニング, プロンプトエンジニアリング, 自然言語処理, コンピュータビジョン, 強化学習, ロボティクス, エッジAI, AutoML, データセット

---

## 6. メール配信 (`src/delivery/`)

### 6.1 Gmail送信 (`gmail_sender.py`)
- **2つの認証方式**:
  - `smtp`（推奨）: Gmailアプリパスワード + `smtplib.SMTP`。ポート587 + STARTTLS
  - `oauth2`: Google Cloud Project + OAuth2フロー。`google-api-python-client`
- `GmailSender` クラス: `authenticate()` → `send_email()` / `send_daily_digest()`
- 件名テンプレート: `[AIニュース] {date} - {headline} 他`
- MIME multipart/alternative（text/plain + text/html）
- エラー通知メール機能

### 6.2 HTML変換 (`html_converter.py`)
- Markdown → HTML: `markdown` ライブラリ（tables, fenced_code, nl2br等の拡張）
- Jinja2テンプレート適用
- **リアクションボタン**: `mailto:` 方式
  - 4種類: 素晴らしい(⭐), 良い(👍), 微妙(🤔), 後で読む(📌)
  - 件名: `[AI-NEWS-REACT] {date} / 記事 {story_id} / {reaction_type}`
  - メール送信するだけで評価が記録される

### 6.3 HTMLメールテンプレート
- レスポンシブデザイン（600px以下対応）
- ダークモード対応（`prefers-color-scheme: dark`）
- カード型レイアウト（各記事がカードUI）
- ヘッダー: 「AI ニュース デイリーダイジェスト」+ 日付
- カテゴリバッジ、タグバッジ
- 「元記事を読む」リンク
- 「本日のインサイト」セクション
- フッター: 「AI ニュース Bot v1.0 | Claude API で自動生成」

### 6.4 LINE Notify (`line_sender.py`)
- 1000文字制限対応（自動切り詰め）
- テキストフォーマット: タイトル + ソース + 概要 + URL

---

## 7. フィードバックシステム (`src/feedback/`)

### 7.1 メール処理 (`email_processor.py`)
- Gmail IMAP接続（`imaplib.IMAP4_SSL`）
- `[AI-NEWS-REACT]` 件名の未読メールを検索
- 正規表現パース: `\[AI-NEWS-REACT\]\s+(\d{4}-\d{2}-\d{2})\s*/\s*(?:Story|記事)\s+(\d+)\s*/\s*(\w+)`
- 処理後メールを既読マーク

### 7.2 Frontmatter更新 (`updater.py`)
- `python-frontmatter` でYAML Frontmatter読み書き
- リアクションのカウンターインクリメント（stories[].reactions, total_reactions）
- ファイルロック（`threading.Lock`）で同時書き込み防止
- reaction_typeとrating対応: excellent=5, good=4, read_later=3, so_so=2

### 7.3 FastAPIサーバー (`api_server.py`)
- `GET /react?date=...&story=...&reaction=...` → HTML感謝ページ
- `GET /api/reaction/{date}/{story_id}/{type}` → RESTful版
- `GET /api/stories/{date}` → 日次記事一覧
- `GET /api/stories/{date}/{story_id}` → 記事詳細
- `GET /api/search?q=...&tag=...&min_rating=...` → 検索
- `GET /api/summary/{year}/{month}` → 月次サマリー
- `GET /health`, `GET /api/health` → ヘルスチェック
- `GET /stats`, `GET /api/stats` → 蓄積統計

---

## 8. ナレッジベース (`src/knowledge/`)

### 8.1 検索 (`search.py`)
- `get_all_articles()`: 全Markdown Frontmatterからメタデータ抽出
- `search_by_tag(tag)`: タグ完全一致検索
- `search_fulltext(query)`: 正規表現全文検索
- `filter_by_rating(min_rating)`: 評価フィルタ

### 8.2 月次サマリー (`summarizer.py`)
- タグ集計、高評価Top5、カテゴリ別トレンド
- Claude APIでインサイト生成（500-800文字）
- Markdown形式で `knowledge_base/monthly/YYYY-MM_summary.md` に保存

---

## 9. ユーティリティ (`src/utils/`)

### 9.1 設定管理 (`config.py`)
- `load_config()`: config.yamlを読み込み
- `load_env()`: .envをdotenvで読み込み
- `validate_config()`, `validate_env()`: バリデーション
- `AppConfig`: シングルトン。ドット区切りキーパスアクセス（例: `config.get("claude.model")`）
- プロジェクトルート自動探索（APP_ROOT環境変数 or config.yaml存在ディレクトリ）

### 9.2 ログ (`logger.py`)
- `setup_logger(name)`: 名前付きロガー
- 日次ローテーション（`TimedRotatingFileHandler`）
- コンソール + ファイル出力
- フォーマット: `[YYYY-MM-DD HH:MM:SS] [LEVEL] [MODULE] MESSAGE`
- 重複ハンドラ防止

### 9.3 リトライ (`retry.py`)
- `@with_retry()` デコレータ
- 指数バックオフ: `wait = base * (multiplier ^ (attempt - 1))`、最大待機時間制限
- リトライ対象例外を指定可能
- config.yamlのretryセクションから設定取得

---

## 10. config.yaml 完全定義

```yaml
app:
  name: "AI News Collector Bot"
  version: "2.0.0"

collection:
  schedule_time: "06:00"
  timezone: "Asia/Tokyo"
  num_stories: 5
  sources:
    - name: "TechCrunch AI"
      type: "rss"
      url: "https://techcrunch.com/category/artificial-intelligence/feed/"
      category: "海外テック"
      language: "en"
      enabled: true
    - name: "VentureBeat AI"
      type: "rss"
      url: "https://venturebeat.com/category/ai/feed/"
      category: "海外テック"
      language: "en"
      enabled: true
    - name: "The Verge AI"
      type: "rss"
      url: "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
      category: "海外テック"
      language: "en"
      enabled: true
    - name: "Reddit r/MachineLearning"
      type: "rss"
      url: "https://www.reddit.com/r/MachineLearning/.rss"
      category: "コミュニティ"
      language: "en"
      enabled: true
    - name: "Reddit r/artificial"
      type: "rss"
      url: "https://www.reddit.com/r/artificial/.rss"
      category: "コミュニティ"
      language: "en"
      enabled: true
    - name: "arXiv cs.AI"
      type: "rss"
      url: "http://export.arxiv.org/rss/cs.AI"
      category: "学術"
      language: "en"
      enabled: true
    - name: "arXiv cs.CL"
      type: "rss"
      url: "http://export.arxiv.org/rss/cs.CL"
      category: "学術"
      language: "en"
      enabled: true
    - name: "Hugging Face Blog"
      type: "rss"
      url: "https://huggingface.co/blog/feed.xml"
      category: "学術"
      language: "en"
      enabled: true
    - name: "ITmedia AI+"
      type: "rss"
      url: "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml"
      category: "国内テック"
      language: "ja"
      enabled: true
    - name: "Publickey"
      type: "rss"
      url: "https://www.publickey1.jp/atom.xml"
      category: "国内テック"
      language: "ja"
      enabled: true
    - name: "Hacker News"
      type: "api"
      url: "http://hn.algolia.com/api/v1"
      query: "AI OR LLM OR GPT OR Claude"
      category: "海外テック"
      language: "en"
      enabled: true
    - name: "NewsAPI"
      type: "api"
      url: "https://newsapi.org/v2"
      query: "artificial intelligence OR generative AI OR LLM"
      category: "海外テック"
      language: "en"
      enabled: true

claude:
  model: "claude-sonnet-4-20250514"
  max_tokens: 8192
  temperature: 0.7
  scoring_temperature: 0.3

selection:
  scoring_weights:
    novelty: 5
    surprise: 5
    practicality: 5
    japan_relevance: 3
    freshness: 2
  select_count: 5
  freshness_hours: 24
  dedup_similarity_threshold: 0.8

delivery:
  gmail:
    enabled: true
    auth_method: "smtp"
    sender: "kazuya.murayama.21@gmail.com"
    recipients:
      - "kazuya.murayama.21@gmail.com"
    subject_template: "[AIニュース] {date} - {headline} 他"
    smtp:
      host: "smtp.gmail.com"
      port: 587
      use_tls: true
  line:
    enabled: false

feedback_server:
  host: "127.0.0.1"
  port: 8321
  base_url: ""

knowledge_base:
  daily_dir: "./knowledge_base/daily"
  monthly_dir: "./knowledge_base/monthly"
  categories:
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

logging:
  level: "INFO"
  dir: "./logs/"
  app_log: "app.log"
  cron_log: "cron.log"
  rotation: "daily"
  retention_days: 30
  format: "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

retry:
  max_attempts: 3
  backoff_base: 1
  backoff_multiplier: 2
  max_wait: 30
```

---

## 11. 環境変数 (.env)

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
GMAIL_APP_PASSWORD=（16文字のGmailアプリパスワード）
GMAIL_CREDENTIALS_PATH=./credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=./credentials/gmail_token.json
LINE_NOTIFY_TOKEN=（オプション）
NEWS_API_KEY=（オプション）
```

---

## 12. 依存パッケージ

```
# ニュース収集
feedparser>=6.0.11
requests>=2.31.0
beautifulsoup4>=4.12.3
lxml>=5.1.0

# LLM API
anthropic>=0.40.0

# 設定・ユーティリティ
PyYAML>=6.0.1
python-frontmatter>=1.1.0
python-dotenv>=1.0.1

# コンテンツ生成・変換
Jinja2>=3.1.3
Markdown>=3.5.2

# APIサーバー
fastapi>=0.110.0
uvicorn>=0.27.1

# Gmail API (OAuth2方式用)
google-api-python-client>=2.114.0
google-auth-httplib2>=0.2.0
google-auth-oauthlib>=1.2.0

# テスト
pytest>=8.0.2
httpx>=0.27.0
```

Python 3.11以上が必要。

---

## 13. v1からの改善ポイント（v2で重点的に対応すべき点）

### 最重要: 日本語翻訳の確実性
v1では、Claude APIの出力が英語のまま返ってくるケースがあり、メールに英語記事がそのまま表示される問題があった。

**v2で強化すべき対策**:
1. ストーリーテリングのシステムプロンプトで「日本語」を最重要ルールとして強調
2. `_contains_japanese()` によるバリデーション（10%以上の日本語文字割合チェック）
3. 日本語が不十分な場合は自動リトライ（最大2回）
4. それでも失敗する場合は「【要確認】」プレフィックス付きフォールバック
5. **タイトルも必ず日本語に変換** する（`extract_title_and_body()`でClaude出力の1行目をタイトルとして取得）

### デプロイメントの簡素化
- setup.shで仮想環境作成から依存パッケージインストールまで1コマンド
- cron/タスクスケジューラのインストールスクリプト
- `--dry-run` モードで配信前テスト可能

### テストの充実
- 各モジュールのユニットテスト
- Claude APIのモック対応
- 統合テスト

---

## 14. 実行方法

```bash
# セットアップ
cd ai-news-bot
chmod +x setup.sh && ./setup.sh

# .envに API キーを設定
vi .env

# テスト実行
source venv/bin/activate
pytest tests/

# ドライラン（メール送信せず）
python -m src.main --dry-run

# 通常実行
python -m src.main

# 特定日付で実行
python -m src.main --date 2026-03-11

# リアクションメール処理のみ
python -m src.main --process-reactions

# リアクションサーバー起動
python -m src.main --server

# cron設定（毎朝6:00 JST）
./scripts/install_cron.sh
```

---

## 15. 注意事項

- **全てのUI・ログ・コメント・docstringは日本語**で記述してください
- Claude APIモデルは `claude-sonnet-4-20250514` を使用
- タイムゾーンは `Asia/Tokyo` (JST)
- HTMLメールはGmailクライアント互換を重視（inline styleを優先）
- セキュリティ: APIキーは環境変数管理、.envは`.gitignore`に含める
- エラー耐性: 個別ソースの失敗が全体を止めないこと
- ファイル管理: 中間ファイルの自動生成ディレクトリは `mkdir -p` で対応
