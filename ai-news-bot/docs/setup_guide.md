# AI News Collector Bot - セットアップガイド

| 項目 | 内容 |
|------|------|
| **文書バージョン** | 1.0 |
| **作成日** | 2026-02-25 |
| **対象バージョン** | AI News Collector Bot v1.0.0 |

---

## 目次

1. [前提条件](#1-前提条件)
2. [インストール手順](#2-インストール手順)
3. [Gmail API OAuth2 設定手順](#3-gmail-api-oauth2-設定手順)
4. [LINE Notify 設定手順](#4-line-notify-設定手順)
5. [config.yaml の設定](#5-configyaml-の設定)
6. [.env ファイルの設定](#6-env-ファイルの設定)
7. [手動実行方法](#7-手動実行方法)
8. [cron 定時実行の設定](#8-cron-定時実行の設定)
9. [リアクションサーバーの起動](#9-リアクションサーバーの起動)
10. [トラブルシューティング](#10-トラブルシューティング)

---

## 1. 前提条件

### 必須要件

| 項目 | 要件 |
|------|------|
| **Python** | 3.11 以上 |
| **OS** | macOS / Linux / Windows (WSL2) |
| **インターネット接続** | 必須（外部 API へのアクセス） |
| **Anthropic API キー** | Claude API の利用に必要 |
| **Google アカウント** | Gmail 配信機能を利用する場合 |

### API キー取得先

| API | 取得先 URL | 備考 |
|-----|-----------|------|
| **Anthropic (Claude)** | https://console.anthropic.com/ | 必須。アカウント作成後、API Keys ページで生成 |
| **NewsAPI** | https://newsapi.org/register | 任意。無料プランは1日100リクエストまで |
| **LINE Notify** | https://notify-bot.line.me/my/ | 任意。LINE 配信を利用する場合のみ |

### Python バージョンの確認

```bash
python3 --version
# Python 3.11.x 以上であることを確認
```

Python 3.11 未満の場合は、[python.org](https://www.python.org/downloads/) または pyenv 等を使用してインストールしてください。

---

## 2. インストール手順

### 2.1 リポジトリのクローン

```bash
git clone <repository-url> ai-news-bot
cd ai-news-bot
```

### 2.2 セットアップスクリプトの実行

セットアップスクリプトが以下の処理を自動的に実行します。

- Python バージョンの確認（3.11 以上）
- 仮想環境 (`venv`) の作成
- 依存パッケージのインストール (`requirements.txt`)
- ディレクトリ構造の作成
- `.env.example` から `.env` のコピー

```bash
chmod +x setup.sh
./setup.sh
```

### 2.3 仮想環境のアクティベート

セットアップ完了後、以降の操作はすべて仮想環境内で実行してください。

```bash
source venv/bin/activate
```

### 2.4 インストールの確認

```bash
# 依存パッケージの確認
pip list | grep -E "anthropic|feedparser|fastapi"

# テストの実行
PYTHONPATH=. python -m pytest tests/ -v
```

全 219 テストがパスすれば、インストールは正常に完了しています。

---

## 3. Gmail API OAuth2 設定手順

Gmail でニュースを配信するには、Google Cloud Console で OAuth2 認証を設定する必要があります。

### 3.1 Google Cloud Console でプロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 画面上部のプロジェクトセレクタをクリック
3. 「新しいプロジェクト」をクリック
4. プロジェクト名（例: `ai-news-bot`）を入力し、「作成」をクリック
5. 作成したプロジェクトが選択されていることを確認

### 3.2 Gmail API を有効化

1. 左側メニューから「API とサービス」 > 「ライブラリ」を選択
2. 検索バーに「Gmail API」と入力
3. 「Gmail API」をクリックし、「有効にする」ボタンをクリック

### 3.3 OAuth 同意画面の設定

1. 左側メニューから「API とサービス」 > 「OAuth 同意画面」を選択
2. ユーザータイプで「外部」を選択（Google Workspace を利用している場合は「内部」も可）
3. 「作成」をクリック
4. 以下の情報を入力:
   - **アプリ名**: AI News Collector Bot
   - **ユーザーサポートメール**: 自分のメールアドレス
   - **デベロッパーの連絡先**: 自分のメールアドレス
5. 「保存して次へ」をクリック
6. スコープの設定画面で「スコープを追加または削除」をクリック
7. `https://www.googleapis.com/auth/gmail.send` を検索して追加
8. 「保存して次へ」をクリック
9. テストユーザーに自分の Gmail アドレスを追加（外部タイプの場合）
10. 「保存して次へ」をクリック

### 3.4 認証情報（credentials.json）のダウンロード

1. 左側メニューから「API とサービス」 > 「認証情報」を選択
2. 「認証情報を作成」 > 「OAuth クライアント ID」を選択
3. アプリケーションの種類で「デスクトップアプリ」を選択
4. 名前（例: `ai-news-bot-desktop`）を入力し、「作成」をクリック
5. ダイアログの「JSON をダウンロード」をクリック

### 3.5 credentials ディレクトリに配置

```bash
# ダウンロードしたファイルを配置
cp ~/Downloads/client_secret_*.json credentials/credentials.json
```

ディレクトリ構成:
```
credentials/
  credentials.json    <- ここに配置
  gmail_token.json    <- 初回認証時に自動生成される
```

### 3.6 初回認証の実行

初回実行時にブラウザが開き、Google アカウントの認証画面が表示されます。

```bash
source venv/bin/activate
PYTHONPATH=. python -m src.main --dry-run
```

1. ブラウザで Google アカウントにログイン
2. 「許可」をクリック
3. 認証完了後、`credentials/gmail_token.json` が自動生成される

以降の実行ではトークンファイルが自動的に使用され、ブラウザ認証は不要です。トークンの有効期限が切れた場合も、リフレッシュトークンにより自動更新されます。

---

## 4. LINE Notify 設定手順

LINE Notify による配信はオプション機能です。不要な場合はこのセクションをスキップしてください。

### 4.1 LINE Notify トークンの取得

1. [LINE Notify](https://notify-bot.line.me/my/) にアクセスし、LINE アカウントでログイン
2. 「トークンを発行する」をクリック
3. トークン名（例: `AI News Bot`）を入力
4. 通知を送信するトークルームを選択（「1:1でLINE Notifyから通知を受け取る」または任意のグループ）
5. 「発行する」をクリック
6. 表示されたトークンをコピー（このトークンは再表示できないため、必ず控えてください）

### 4.2 設定ファイルへの反映

1. `.env` ファイルにトークンを設定:
   ```
   LINE_NOTIFY_TOKEN=取得したトークン
   ```

2. `config.yaml` で LINE 配信を有効化:
   ```yaml
   delivery:
     line:
       enabled: true
   ```

> **注意**: LINE Notify はサービス終了の可能性があります。将来的に LINE Messaging API への移行が必要になる場合があります。

---

## 5. config.yaml の設定

`config.yaml` はアプリケーション全体の動作を制御する設定ファイルです。以下に各セクションの説明を記載します。

### 5.1 app セクション（アプリケーション全般）

```yaml
app:
  name: "AI News Collector Bot"   # アプリケーション名
  version: "1.0.0"                # バージョン番号
```

### 5.2 collection セクション（ニュース収集設定）

```yaml
collection:
  schedule_time: "06:00"          # cron 実行時刻（参照用）
  timezone: "Asia/Tokyo"          # タイムゾーン
  num_stories: 3                  # 日次配信記事数（1以上の整数）
  sources:                        # ニュースソース一覧
    - name: "TechCrunch AI"       # ソース名
      type: "rss"                 # 取得方式: rss / api / scraping
      url: "https://..."          # フィード / API の URL
      category: "海外テック"       # カテゴリ（表示用）
      language: "en"              # 言語コード（en / ja）
      enabled: true               # true: 有効 / false: 無効
```

**ソースの type 別設定:**

| type | 説明 | 対応モジュール |
|------|------|---------------|
| `rss` | RSS/Atom フィード取得 | `rss_collector.py` |
| `api` | REST API 取得（NewsAPI, Hacker News） | `news_api.py` |
| `scraping` | Web スクレイピング | `web_scraper.py` |

### 5.3 claude セクション（Claude API 設定）

```yaml
claude:
  model: "claude-sonnet-4-20250514"  # 使用する Claude モデル
  max_tokens: 4096                   # 最大出力トークン数
  temperature: 0.7                   # ストーリーテリング用温度（0.0-1.0）
  scoring_temperature: 0.3           # スコアリング用温度（低めで安定出力）
```

- `temperature`: 値が高いほど創造的な出力。ストーリーテリングには 0.7 程度が推奨
- `scoring_temperature`: スコアリングには安定した出力が必要なため、0.3 程度が推奨

### 5.4 selection セクション（記事選定設定）

```yaml
selection:
  scoring_weights:                   # スコアリング配点（合計20点）
    novelty: 5                       # 先進性 (0-5)
    surprise: 5                      # 意外性 (0-5)
    practicality: 5                  # 実用性 (0-5)
    japan_relevance: 3               # 日本企業関連性 (0-3)
    freshness: 2                     # 鮮度 (0-2)
  select_count: 3                    # 選定記事数
  freshness_hours: 24                # 鮮度基準時間（時間）
  dedup_similarity_threshold: 0.8    # 重複判定の類似度しきい値
```

### 5.5 delivery セクション（配信設定）

```yaml
delivery:
  gmail:
    enabled: true                    # Gmail 配信の有効/無効
    sender: "your-email@gmail.com"   # 送信元メールアドレス
    recipients:                      # 送信先リスト
      - "recipient1@example.com"
      - "recipient2@example.com"
    subject_template: "[AI News] {date} - {headline} 他"  # 件名テンプレート
  line:
    enabled: false                   # LINE 配信の有効/無効（デフォルト: 無効）
```

- `subject_template` では `{date}` と `{headline}` がプレースホルダとして使用可能

### 5.6 feedback_server セクション（リアクションサーバー設定）

```yaml
feedback_server:
  host: "127.0.0.1"                 # バインドアドレス
  port: 8080                        # ポート番号（1024-65535）
  base_url: "http://localhost:8080" # メール内リアクションリンクのベース URL
```

- `host`: デフォルトは `127.0.0.1`（ローカルアクセスのみ）。外部公開時は `0.0.0.0` に変更
- `base_url`: メール内に埋め込まれるリアクションリンクの URL。外部公開時は ngrok 等の URL に変更

### 5.7 knowledge_base セクション（ナレッジベース設定）

```yaml
knowledge_base:
  daily_dir: "./knowledge_base/daily"    # 日次レポート保存先
  monthly_dir: "./knowledge_base/monthly" # 月次サマリー保存先
  categories:                             # 自動タグ付与のカテゴリ一覧
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
```

### 5.8 logging セクション（ログ設定）

```yaml
logging:
  level: "INFO"                          # ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  dir: "./logs/"                         # ログ出力ディレクトリ
  app_log: "app.log"                     # アプリケーションログファイル名
  cron_log: "cron.log"                   # cron 実行ログファイル名
  rotation: "daily"                      # ローテーション方式
  retention_days: 30                     # ログ保持日数
  format: "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
```

- 開発時は `level: "DEBUG"` に設定するとより詳細なログが出力されます

### 5.9 retry セクション（リトライ設定）

```yaml
retry:
  max_attempts: 3                        # 最大リトライ回数（初回含む）
  backoff_base: 1                        # 初回待機時間（秒）
  backoff_multiplier: 2                  # 指数バックオフの乗数
  max_wait: 30                           # 最大待機時間（秒）
```

- 待機時間の計算: `min(backoff_base * backoff_multiplier^(attempt-1), max_wait)`
- 例: 1秒 -> 2秒 -> 4秒 -> ... -> 最大30秒

---

## 6. .env ファイルの設定

`.env` ファイルには API キーやトークンなどの秘匿情報を記述します。Git にはコミットされません。

### 6.1 .env ファイルの作成

セットアップスクリプト実行時に `.env.example` から自動コピーされます。手動で作成する場合は以下の通りです。

```bash
cp .env.example .env
```

### 6.2 設定項目

```bash
# ============================================================
# 必須: Claude API (Anthropic)
# ============================================================
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx

# ============================================================
# 任意: NewsAPI（ニュースソースとして使用する場合）
# ============================================================
NEWSAPI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============================================================
# Gmail API（Gmail 配信を有効にする場合）
# ============================================================
GMAIL_CREDENTIALS_PATH=./credentials/credentials.json
GMAIL_TOKEN_PATH=./credentials/gmail_token.json

# ============================================================
# LINE Notify（LINE 配信を有効にする場合）
# ============================================================
LINE_NOTIFY_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | 必須 | Claude API キー |
| `NEWSAPI_API_KEY` | 任意 | NewsAPI の API キー |
| `GMAIL_CREDENTIALS_PATH` | Gmail 使用時 | OAuth2 クライアント認証情報ファイルのパス |
| `GMAIL_TOKEN_PATH` | Gmail 使用時 | OAuth2 トークンファイルの保存パス |
| `LINE_NOTIFY_TOKEN` | LINE 使用時 | LINE Notify のアクセストークン |

> **重要**: `.env` ファイルを Git にコミットしないでください。`.gitignore` に既に登録されています。

---

## 7. 手動実行方法

### 7.1 scripts/run_once.sh を使用する方法（推奨）

```bash
# 今日の日付でフル実行（収集 -> 変換 -> 配信）
./scripts/run_once.sh

# 配信なしで実行（Markdown 生成まで）
./scripts/run_once.sh --dry-run

# 特定日付を指定して実行
./scripts/run_once.sh --date 2026-02-20

# リアクションサーバーを起動
./scripts/run_once.sh --server
```

`run_once.sh` は仮想環境の自動検出とアクティベートを行うため、`source venv/bin/activate` を事前に実行する必要はありません。

### 7.2 Python コマンドで直接実行する方法

```bash
# 仮想環境をアクティベート
source venv/bin/activate

# 今日の日付で実行
PYTHONPATH=. python -m src.main

# dry-run モード
PYTHONPATH=. python -m src.main --dry-run

# 特定日付を指定
PYTHONPATH=. python -m src.main --date 2026-02-20

# リアクションサーバーの起動
PYTHONPATH=. python -m src.main --server
```

### 7.3 CLI 引数一覧

| 引数 | 説明 | デフォルト |
|------|------|-----------|
| `--date YYYY-MM-DD` | 実行対象の日付を指定 | 今日の日付（JST） |
| `--dry-run` | 配信（Gmail/LINE）をスキップし、Markdown 生成まで実行 | 無効 |
| `--server` | パイプラインを実行せず、リアクションサーバーを起動 | 無効 |

---

## 8. cron 定時実行の設定

### 8.1 install_cron.sh を使用する方法（推奨）

```bash
chmod +x scripts/install_cron.sh
./scripts/install_cron.sh
```

このスクリプトは以下を実行します:

1. Python 実行環境の確認
2. 既存の同一ジョブの重複チェックと置き換え
3. 毎朝 06:00 (JST) に `main.py` を実行する cron ジョブを登録
4. ログ出力先を `logs/cron.log` に設定

### 8.2 登録される cron ジョブ

```
0 6 * * * TZ=Asia/Tokyo cd /path/to/ai-news-bot && /path/to/venv/bin/python src/main.py >> logs/cron.log 2>&1 # ai-news-bot-daily
```

### 8.3 手動で cron を設定する方法

```bash
crontab -e
```

以下の行を追加:

```
0 6 * * * TZ=Asia/Tokyo cd /path/to/ai-news-bot && /path/to/ai-news-bot/venv/bin/python /path/to/ai-news-bot/src/main.py >> /path/to/ai-news-bot/logs/cron.log 2>&1
```

### 8.4 cron ジョブの確認と削除

```bash
# 現在の cron ジョブを一覧表示
crontab -l

# cron ジョブを編集（削除する場合は該当行を削除）
crontab -e
```

---

## 9. リアクションサーバーの起動

リアクションサーバーは、メール内のリアクションリンク（素晴らしい/良い/微妙/後で読む）を受け付け、ナレッジベースの Markdown ファイルにフィードバックを記録します。

### 9.1 起動方法

```bash
# scripts を使用
./scripts/run_once.sh --server

# または直接起動
source venv/bin/activate
PYTHONPATH=. python -m src.main --server
```

デフォルトでは `http://127.0.0.1:8080` で起動します。

### 9.2 動作確認

```bash
# ヘルスチェック
curl http://localhost:8080/health

# 統計情報の取得
curl http://localhost:8080/stats
```

### 9.3 バックグラウンド実行

```bash
# nohup で起動
nohup ./scripts/run_once.sh --server > logs/server.log 2>&1 &

# プロセスの確認
ps aux | grep "src.main --server"

# 停止
kill $(pgrep -f "src.main --server")
```

### 9.4 外部公開（オプション）

ローカルネットワーク外からリアクションを受け付ける場合は、ngrok や Cloudflare Tunnel を使用してください。

```bash
# ngrok の場合
ngrok http 8080

# config.yaml の base_url を ngrok の URL に変更
feedback_server:
  base_url: "https://xxxx-xx-xx.ngrok-free.app"
```

### 9.5 API エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/react?date={date}&story={id}&reaction={type}` | リアクション受信 |
| GET | `/stats` | 蓄積統計情報 |

---

## 10. トラブルシューティング

### 10.1 Python バージョンエラー

**症状**: `setup.sh` 実行時に「Python 3.11 以上が必要です」と表示される

**解決策**:
```bash
# Python バージョンの確認
python3 --version

# pyenv を使用してインストール
pyenv install 3.11.14
pyenv local 3.11.14

# または PYTHON_CMD 環境変数で指定
PYTHON_CMD=python3.11 ./setup.sh
```

### 10.2 ANTHROPIC_API_KEY が未設定

**症状**: 実行時に「環境変数 ANTHROPIC_API_KEY が設定されていません」と表示される

**解決策**:
1. `.env` ファイルに `ANTHROPIC_API_KEY=sk-ant-...` を設定
2. API キーが正しいことを確認（https://console.anthropic.com/ で確認）

### 10.3 Gmail 認証エラー

**症状**: 「OAuth2 クライアント認証情報ファイルが見つかりません」

**解決策**:
1. `credentials/credentials.json` が存在するか確認
2. Google Cloud Console から再度ダウンロード
3. `.env` の `GMAIL_CREDENTIALS_PATH` が正しいパスを指しているか確認

**症状**: 「トークンのリフレッシュに失敗」

**解決策**:
1. `credentials/gmail_token.json` を削除
2. 再度 `--dry-run` で実行し、ブラウザ認証を行う

```bash
rm credentials/gmail_token.json
PYTHONPATH=. python -m src.main --dry-run
```

### 10.4 RSS フィード取得エラー

**症状**: 「RSS フィード取得に失敗しました」がログに出力される

**解決策**:
- インターネット接続を確認
- 該当フィードの URL がブラウザでアクセス可能か確認
- 一時的な障害の場合はリトライにより自動回復（最大3回）
- 特定ソースが恒常的に失敗する場合は、`config.yaml` で `enabled: false` に設定

### 10.5 NewsAPI のレート制限

**症状**: 「NewsAPI エラー」がログに出力される

**解決策**:
- 無料プランは1日100リクエストまで。制限に達した場合は翌日まで待機
- 有料プランへのアップグレードを検討
- `config.yaml` で NewsAPI を一時的に無効化:
  ```yaml
  sources:
    - name: "NewsAPI"
      enabled: false
  ```

### 10.6 Markdown ファイルが見つからない（リアクションエラー）

**症状**: リアクションリンクをクリックすると「Article not found」と表示される

**解決策**:
- `knowledge_base/daily/` に対象日付の `YYYY-MM-DD_ai_news.md` が存在するか確認
- リアクションサーバーが起動しているか確認
- `config.yaml` の `knowledge_base.daily_dir` パスが正しいか確認

### 10.7 テストが失敗する

**症状**: `pytest` 実行時にテストが失敗する

**解決策**:
```bash
# 仮想環境がアクティベートされているか確認
which python

# PYTHONPATH を設定して実行
PYTHONPATH=. python -m pytest tests/ -v

# 特定のテストファイルのみ実行
PYTHONPATH=. python -m pytest tests/test_utils.py -v
```

### 10.8 ポート競合

**症状**: リアクションサーバー起動時に「Address already in use」と表示される

**解決策**:
```bash
# 使用中のポートを確認
lsof -i :8080

# 別のポートを config.yaml で設定
feedback_server:
  port: 8321
```

### 10.9 文字化け

**症状**: メールやログで日本語が文字化けする

**解決策**:
- ターミナルの文字コードが UTF-8 であることを確認
- `.env` ファイルが UTF-8 で保存されていることを確認
- `config.yaml` が UTF-8 で保存されていることを確認

### 10.10 Claude API のレート制限 / コストに関する注意

- Claude API の利用には費用が発生します。月額コスト目安: 約 $5-15（3件/日の場合）
- レート制限エラーが発生した場合は、リトライ機構により指数バックオフで自動対応します
- コストを抑えるには `config.yaml` の `claude.model` でより低コストなモデルを指定できます

---

## 付録: ディレクトリ構成

```
ai-news-bot/
  config.yaml              # アプリケーション設定
  .env                     # 秘匿情報（API キー等）※ gitignore 対象
  .env.example             # .env のテンプレート
  requirements.txt         # Python 依存パッケージ
  setup.sh                 # セットアップスクリプト
  venv/                    # Python 仮想環境 ※ gitignore 対象
  credentials/             # OAuth2 認証情報 ※ gitignore 対象
    credentials.json       # Google OAuth2 クライアント認証情報
    gmail_token.json       # Gmail API トークン（自動生成）
  src/                     # ソースコード
    main.py                # エントリポイント
    collector/             # ニュース収集モジュール
    writer/                # コンテンツ生成モジュール
    delivery/              # 配信モジュール
    feedback/              # リアクションサーバー
    knowledge/             # ナレッジベース管理
    utils/                 # 共通ユーティリティ
  knowledge_base/          # ナレッジベースストレージ
    daily/                 # 日次レポート + 候補 JSON
    monthly/               # 月次サマリー
  logs/                    # ログファイル
  tests/                   # テストコード
  scripts/                 # 運用スクリプト
    run_once.sh            # 手動実行スクリプト
    install_cron.sh        # cron 設定スクリプト
  docs/                    # ドキュメント
```
