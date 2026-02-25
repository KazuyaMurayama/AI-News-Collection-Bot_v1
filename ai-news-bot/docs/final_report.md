# AI News Collector Bot - 最終報告書

| 項目 | 内容 |
|------|------|
| **文書バージョン** | 1.0 |
| **作成日** | 2026-02-25 |
| **プロジェクト** | AI News Collector Bot v1.0.0 |

---

## 1. プロジェクト概要

### 1.1 システム名

**AI News Collector Bot**

### 1.2 目的

生成AI活用事例を国内外のメディアから自動収集し、ストーリーテリング手法を用いて読みやすい記事形式に変換したうえで、メール（Gmail）およびLINEで配信し、ローカルナレッジベースとして蓄積・検索可能にするシステムを構築する。

### 1.3 開発背景

生成AIの活用事例は日々増加しており、最新動向を効率的に把握することがビジネス上の意思決定に不可欠である。しかし、複数のメディアを毎日巡回して情報を収集・整理する作業には多大な時間がかかる。本システムはこの情報収集・整理・蓄積のプロセスを自動化し、読者が短時間で質の高いインサイトを得られる環境を提供する。

### 1.4 対象ユーザー

- 生成AIの最新動向を追いたいビジネスパーソン
- AI戦略の立案に携わるプロダクトマネージャー・経営企画担当者
- 技術トレンドを把握したいエンジニア・リサーチャー

### 1.5 マルチエージェント開発体制

本プロジェクトは、以下のマルチエージェント構成により開発を推進した。

| 役割 | 担当内容 |
|------|----------|
| **PM（プロジェクトマネージャー）** | 全体計画策定、進捗管理、タスク割り振り、品質基準の定義 |
| **アーキテクト** | システム全体設計、5層アーキテクチャ策定、モジュール間インターフェース定義 |
| **開発者 1（収集レイヤー担当）** | RSS収集、Webスクレイピング、News API連携、記事選定ロジック |
| **開発者 2（生成レイヤー担当）** | ストーリーテリング変換、Markdown生成、テンプレート設計 |
| **開発者 3（配信レイヤー担当）** | Gmail配信、LINE Notify配信、HTML変換 |
| **開発者 4（フィードバック・ナレッジ担当）** | リアクションAPI、MD更新、検索、タグ付け、月次サマリー |
| **QA（品質保証）** | テスト設計・実装、バグ検出・修正検証、テストレポート作成 |
| **テクニカルライター** | 要件定義書、アーキテクチャ設計書、テストレポート、最終報告書の作成 |

---

## 2. アーキテクチャ概要

### 2.1 5層構成

本システムは以下の5層アーキテクチャで構成される。

```
┌─────────────────────────────────────────────────────┐
│                   main.py (オーケストレーター)          │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│ 収集レイヤー │ 生成レイヤー │ 配信レイヤー │フィードバック│ ナレッジ   │
│ collector/ │ writer/   │ delivery/ │ feedback/ │ knowledge/│
│            │           │           │           │           │
│ RSS収集    │ストーリー  │ Gmail配信 │ FastAPI   │ 検索      │
│ Webスクレイ │テリング    │ LINE配信  │ サーバー   │ タグ付け  │
│ ピング     │ Markdown  │ HTML変換  │ MD更新    │ 月次      │
│ News API   │ 生成      │           │           │ サマリー   │
│ 記事選定   │           │           │           │           │
├──────────┴──────────┴──────────┴──────────┴──────────┤
│              共通ユーティリティ (utils/)                  │
│         設定管理 / ログ / リトライ                        │
└─────────────────────────────────────────────────────┘
```

1. **収集レイヤー（collector/）**: RSS、Webスクレイピング、NewsAPI/Hacker News APIを用いた記事収集と、Claude APIによるスコアリングに基づく記事選定
2. **生成レイヤー（writer/）**: Claude APIを活用したストーリーテリング変換（STAR、ヒーローズジャーニー、Before/After/Bridge、PAS等）と、Markdownファイル生成
3. **配信レイヤー（delivery/）**: Gmail API（OAuth2）によるメール配信、LINE Notify APIによるメッセージ配信、Markdown-HTML変換
4. **フィードバックレイヤー（feedback/）**: FastAPIベースのリアクション収集サーバーと、Markdownファイルへのリアクション反映
5. **ナレッジレイヤー（knowledge/）**: 蓄積記事の全文・タグ検索、自動タグ付け、月次サマリー生成

### 2.2 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **言語** | Python 3.11+ |
| **LLM** | Claude API (Anthropic) |
| **Webフレームワーク** | FastAPI (リアクションサーバー) |
| **RSS解析** | feedparser |
| **Webスクレイピング** | BeautifulSoup4 (bs4), requests |
| **ニュースAPI** | NewsAPI.org, Hacker News Algolia API |
| **メール配信** | Gmail API (Google OAuth2) |
| **LINE配信** | LINE Notify API |
| **Markdown処理** | Jinja2, markdown |
| **テスト** | pytest, pytest-asyncio |
| **設定管理** | PyYAML, python-dotenv |
| **スケジューリング** | cron |

### 2.3 ハイブリッド収集方式

本システムは3種類の収集方式を組み合わせたハイブリッド方式を採用している。

| 方式 | 対象ソース | 特徴 |
|------|-----------|------|
| **RSS** | TechCrunch, VentureBeat, The Verge, Reddit, arXiv, HuggingFace, Publickey, ITmedia | 構造化フィードから安定した取得が可能 |
| **Webスクレイピング** | 日経クロステック, ITmedia | RSS非対応サイトからCSSセレクタで抽出 |
| **API** | NewsAPI.org, Hacker News (Algolia API) | キーワード検索による横断的な記事収集 |

---

## 3. 実装モジュール一覧

### 3.1 ソースコード構成

総ファイル数: Pythonソース 25ファイル + テンプレート 2ファイル + スクリプト 2ファイル

#### src/utils/ -- 共通ユーティリティ（3ファイル + __init__.py）

| ファイル | 説明 |
|---------|------|
| `config.py` | YAML設定読み込み、バリデーション、AppConfigシングルトン、環境変数アクセス |
| `logger.py` | ログ設定、ファイル・コンソール出力、ログディレクトリ自動作成 |
| `retry.py` | 指数バックオフ付きリトライデコレータ、リトライコールバック対応 |

#### src/collector/ -- 収集レイヤー（4ファイル + __init__.py）

| ファイル | 説明 |
|---------|------|
| `rss_collector.py` | feedparserを用いたRSSフィード収集、日付パース、HTMLタグ除去 |
| `web_scraper.py` | BeautifulSoup4によるWebスクレイピング、robots.txt準拠チェック |
| `news_api.py` | NewsAPI.org / Hacker News Algolia APIからの記事取得 |
| `selector.py` | Claude APIによるスコアリング、重複排除、記事選定ロジック |
| `__init__.py` | `collect_all()` 統合関数（RSS + スクレイピング + API の結合） |

#### src/writer/ -- 生成レイヤー（2ファイル + __init__.py + テンプレート2ファイル）

| ファイル | 説明 |
|---------|------|
| `storyteller.py` | Claude APIを用いたストーリーテリング変換（STAR/ヒーローズジャーニー/Before-After-Bridge/PAS）、フレームワーク自動選択、インサイト生成 |
| `markdown_gen.py` | Jinja2テンプレートベースの日次Markdown生成、frontmatterメタデータ構築、ファイル保存 |
| `templates/daily_template.md` | 日次レポートのMarkdownテンプレート |
| `templates/email_template.html` | メール配信用HTMLテンプレート |

#### src/delivery/ -- 配信レイヤー（3ファイル + __init__.py）

| ファイル | 説明 |
|---------|------|
| `gmail_sender.py` | Gmail API (OAuth2) によるメール送信、認証フロー管理 |
| `line_sender.py` | LINE Notify APIによるメッセージ送信、テキストフォーマット |
| `html_converter.py` | MarkdownからHTMLへの変換、リアクションURL生成、メールテンプレート適用 |

#### src/feedback/ -- フィードバックレイヤー（2ファイル + __init__.py）

| ファイル | 説明 |
|---------|------|
| `api_server.py` | FastAPIベースのリアクション収集サーバー（エンドポイント定義、バリデーション） |
| `updater.py` | Markdownファイルへのリアクション情報書き込み・更新 |

#### src/knowledge/ -- ナレッジレイヤー（3ファイル + __init__.py）

| ファイル | 説明 |
|---------|------|
| `search.py` | ナレッジベース全文検索、タグ検索、評価フィルタリング |
| `tagger.py` | 記事への自動タグ付け（キーワードベース） |
| `summarizer.py` | Claude APIを用いた月次サマリー生成 |

#### src/main.py -- メインオーケストレーター

| ファイル | 説明 |
|---------|------|
| `main.py` | 全モジュール統合、日次パイプライン実行（収集 -> 選定 -> 変換 -> タグ付け -> Markdown生成 -> 配信）、CLI引数パース（--date / --dry-run / --server） |

#### scripts/ -- 運用スクリプト（2ファイル）

| ファイル | 説明 |
|---------|------|
| `install_cron.sh` | cron ジョブ設定スクリプト（毎朝 6:00 JST 実行） |
| `run_once.sh` | 手動での1回実行スクリプト |

---

## 4. テスト結果サマリー

### 4.1 全体結果

| 項目 | 値 |
|------|-----|
| **テストファイル数** | 6 |
| **総テスト数** | 219 |
| **PASS** | 219 |
| **FAIL** | 0 |
| **ERROR** | 0 |
| **SKIP** | 0 |
| **実行時間** | 7.97 秒 |
| **結果** | **ALL PASS** |
| **推定カバレッジ** | 約82% |

### 4.2 テストファイル別内訳

| テストファイル | テスト数 | 結果 | 対象モジュール |
|--------------|---------|------|--------------|
| `tests/test_utils.py` | 22 | 全 PASS | config.py, logger.py, retry.py |
| `tests/test_collector.py` | 34 | 全 PASS | rss_collector.py, web_scraper.py, news_api.py, selector.py, __init__.py |
| `tests/test_writer.py` | 21 | 全 PASS | storyteller.py, markdown_gen.py |
| `tests/test_delivery.py` | 41 | 全 PASS | html_converter.py, gmail_sender.py, line_sender.py |
| `tests/test_feedback.py` | 20 | 全 PASS | api_server.py, updater.py, search.py |
| `tests/test_integration.py` | 47 | 全 PASS | main.py（統合テスト）、エッジケース全般 |
| **合計** | **219** | **全 PASS** | |

### 4.3 テスト種別分類

| 種別 | テスト数 | 内容 |
|------|---------|------|
| **ユニットテスト** | 138 | 各モジュール単体の機能検証 |
| **統合テスト** | 12 | パイプライン全体、モジュール間連携 |
| **CLIテスト** | 8 | コマンドライン引数のパース検証 |
| **エッジケーステスト** | 27 | 記事0件、不正入力、重複更新等 |
| **バグ回帰テスト** | 3 | MDファイル命名規則一貫性（BUG-001修正検証） |

### 4.4 発見・修正したバグ

#### BUG-001: MDファイル命名規則の不一致（重大度: HIGH）

- **概要**: `main.py` が `{date}.md` 形式で保存していたが、`updater.py` と `search.py` は `{date}_ai_news.md` 形式を期待していた
- **影響**: リアクションAPIがファイルを発見できず全リクエスト失敗、ナレッジベース検索で日次レポートが検出不可
- **修正**: `main.py` の保存ファイル名を `{date}_ai_news.md` に統一
- **検証**: `TestMdFileNamingConsistency` クラスの3テストで一貫性を確認済み

### 4.5 推定カバレッジ（モジュール別）

| モジュール | 推定カバレッジ | テスト種別 |
|-----------|---------------|-----------|
| src/utils/config.py | ~90% | ユニット + 統合 |
| src/utils/logger.py | ~85% | ユニット |
| src/utils/retry.py | ~95% | ユニット |
| src/collector/__init__.py | ~85% | ユニット + 統合 |
| src/collector/rss_collector.py | ~80% | ユニット + 統合 |
| src/collector/news_api.py | ~75% | ユニット |
| src/collector/web_scraper.py | ~70% | ユニット |
| src/collector/selector.py | ~90% | ユニット + 統合 |
| src/writer/storyteller.py | ~85% | ユニット + 統合 |
| src/writer/markdown_gen.py | ~90% | ユニット + 統合 |
| src/delivery/html_converter.py | ~85% | ユニット + 統合 |
| src/delivery/gmail_sender.py | ~40% | 外部API依存のため限定的 |
| src/delivery/line_sender.py | ~80% | ユニット + 統合 |
| src/feedback/api_server.py | ~90% | ユニット + 統合 |
| src/feedback/updater.py | ~95% | ユニット + 統合 |
| src/knowledge/search.py | ~90% | ユニット + 統合 |
| src/knowledge/tagger.py | ~75% | ユニット + 統合 |
| src/knowledge/summarizer.py | ~60% | ユニット（Claude API依存） |
| src/main.py | ~80% | 統合 |
| **全体推定** | **~82%** | |

---

## 5. 既知の制限事項

### 5.1 外部API利用コスト

| API | 制限事項 |
|-----|---------|
| **Claude API** | 推定月額 $5-15（記事数・ストーリー数に依存）。スコアリング + ストーリーテリング変換 + インサイト生成 + 月次サマリーで複数回呼び出しが発生する |
| **Gmail API** | 1日あたり500通の送信上限。通常運用では問題ないが、大規模配信には不向き |
| **NewsAPI** | 無料プランでは1日100リクエストの制限。開発者プランへのアップグレードで緩和可能 |

### 5.2 収集に関する制約

| 制約 | 説明 |
|------|------|
| **ペイウォール** | 有料記事はタイトル・概要のみ取得可能。本文の全文取得は不可 |
| **robots.txt制約** | Webスクレイピング対象サイトの robots.txt を尊重するため、一部サイトで取得不可の場合がある |
| **arXiv論文** | Abstractのみを対象としており、論文全文の解析は行わない |

### 5.3 インフラ・運用上の制約

| 制約 | 説明 |
|------|------|
| **リアクションサーバー** | localhost（デフォルト: 8000番ポート）での起動を前提としており、外部からのアクセスにはngrok等のトンネリングツールが必要 |
| **ローカル実行前提** | クラウドデプロイは対象外。cronによるスケジューリングはローカルマシンの稼働が前提 |
| **シングルユーザー** | 複数ユーザーの権限管理・個別設定には対応していない |

---

## 6. 今後の改善案（拡張ロードマップ）

### Phase 1: 短期改善（1-2ヶ月）

| 改善項目 | 概要 | 期待効果 |
|---------|------|---------|
| **Slack配信対応** | Slack Webhook / Bot APIによる配信チャネル追加 | チーム内での情報共有が容易になる |
| **Docker化** | Dockerfile + docker-compose.ymlによるコンテナ化 | 環境構築の簡素化、ポータビリティ向上 |
| **リアクションサーバーのクラウドデプロイ** | Render / Railway 等へのデプロイ | メールのリアクションリンクが外部からアクセス可能になる |
| **テストカバレッジ向上** | gmail_sender.py, summarizer.py のテスト拡充 | 全体カバレッジ 82% -> 90%+ を目指す |

### Phase 2: 中期拡張（3-6ヶ月）

| 改善項目 | 概要 | 期待効果 |
|---------|------|---------|
| **Web UIダッシュボード** | Streamlit / Gradioによる記事閲覧・検索UI | ナレッジベースの視認性・操作性が大幅に向上 |
| **RAG連携** | ChromaDB / FAISS等でベクトル検索を導入 | セマンティック検索による高精度な記事発見 |
| **ユーザー好み学習** | リアクション履歴に基づく記事選定最適化 | パーソナライズされた記事配信が可能になる |
| **配信頻度のカスタマイズ** | 即時通知 / 日次 / 週次ダイジェストの選択 | ユーザーのニーズに応じた柔軟な配信 |

### Phase 3: 長期ビジョン（6ヶ月-1年）

| 改善項目 | 概要 | 期待効果 |
|---------|------|---------|
| **マルチユーザー対応** | ユーザー登録・認証・個別設定管理 | 組織内での複数メンバー利用が可能 |
| **クラウドネイティブ化** | AWS Lambda + DynamoDB / S3 によるサーバーレス構成 | スケーラビリティ向上、運用コスト最適化 |
| **多言語対応** | 英語・中国語等の記事を日本語に翻訳して配信 | 情報ソースの多様化、グローバルトレンド把握 |
| **AIエージェント連携** | 自律的にトレンド分析・レポート生成するエージェント化 | 人手を介さない高度な情報分析 |

---

## 7. ユーザー設定手順の要約

### 7.1 初期セットアップ

```bash
# 1. セットアップスクリプトの実行
cd ai-news-bot
chmod +x setup.sh
./setup.sh
```

セットアップスクリプトにより、Python仮想環境の作成、依存パッケージのインストール、ディレクトリ構造の初期化が行われる。

### 7.2 APIキー・トークンの設定

`.env` ファイルに以下のAPIキー・トークンを設定する。

```bash
# 2. .env ファイルの編集
cp .env.example .env
vi .env
```

| 環境変数 | 説明 | 必須 |
|---------|------|------|
| `ANTHROPIC_API_KEY` | Claude API キー | 必須 |
| `NEWSAPI_KEY` | NewsAPI.org API キー | 任意 |
| `LINE_NOTIFY_TOKEN` | LINE Notify トークン | 任意 |

### 7.3 設定ファイルの編集

```bash
# 3. config.yaml の編集
vi config.yaml
```

`config.yaml` で以下を設定する:
- 収集対象のRSSフィード URL一覧
- スクレイピング対象サイトとCSSセレクタ
- 配信先メールアドレス
- 記事選定数（num_stories）
- Claude APIのモデル名・temperature
- リアクションサーバーのポート番号

### 7.4 Gmail OAuth2 認証

```bash
# 4. Gmail API の OAuth2 認証
# Google Cloud Console でプロジェクトを作成し、Gmail API を有効化
# OAuth2 クライアント ID を作成し、credentials.json をプロジェクトルートに配置
# 初回実行時にブラウザで認証フローが起動する
```

### 7.5 テスト実行確認

```bash
# 5. テスト実行
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

全219テストがPASSすることを確認する。

### 7.6 動作確認（dry-run）

```bash
# 6. dry-run で動作確認（配信は行わない）
python -m src.main --dry-run
```

### 7.7 cron 設定

```bash
# 7. cron ジョブの設定（毎朝 6:00 JST に自動実行）
chmod +x scripts/install_cron.sh
./scripts/install_cron.sh
```

### 7.8 手動実行

```bash
# 特定日付を指定して実行
python -m src.main --date 2026-02-25

# リアクションサーバーを起動
python -m src.main --server

# 手動で1回実行
./scripts/run_once.sh
```

---

## 8. まとめ

AI News Collector Bot v1.0.0 は、5層アーキテクチャに基づくモジュラー設計により、ニュースの収集から配信・蓄積までの一連のパイプラインを自動化するシステムとして完成した。

**主な成果:**

- ハイブリッド収集方式（RSS + Webスクレイピング + API）により、幅広いソースからの情報収集を実現
- Claude APIを活用したストーリーテリング変換により、単なる要約ではなく読みやすい記事形式での配信を実現
- Gmail / LINE の2チャネル配信に対応
- リアクション収集によるフィードバックループを構築
- ナレッジベースとしての検索・タグ付け・月次サマリー機能を実装
- 全219テストがPASS、推定カバレッジ約82%の品質を確保
- QAプロセスにおいてMDファイル命名規則の不一致バグ（BUG-001）を発見・修正し、回帰テストで再発防止を担保

本システムはローカル環境での個人利用を想定した初期バージョンであり、今後のフェーズでSlack配信対応、Docker化、Web UIダッシュボード、RAG連携、クラウドネイティブ化といった拡張を段階的に進めることで、より多くのユーザーに価値を提供できるシステムへと発展させる計画である。
