# AI News Collector Bot 要件定義書

| 項目 | 内容 |
|------|------|
| ドキュメントID | REQ-AINCB-001 |
| バージョン | 1.0.0 |
| 作成日 | 2026-02-25 |
| ステータス | ドラフト |

---

## 1. プロジェクト概要

### 1.1 システム名

AI News Collector Bot

### 1.2 目的

生成AI活用事例を国内外のメディアから自動収集し、ストーリーテリング手法を用いて読みやすい記事形式に変換したうえで、メール（Gmail）およびLINEで配信し、ローカルナレッジベースとして蓄積・検索可能にするシステム。

### 1.3 背景

生成AIの活用事例は日々増加しており、最新動向を効率的に把握することがビジネス上の意思決定に不可欠である。しかし、複数のメディアを毎日巡回して情報を収集・整理する作業には多大な時間がかかる。本システムはこの情報収集・整理・蓄積のプロセスを自動化し、読者が短時間で質の高いインサイトを得られる環境を提供する。

### 1.4 対象ユーザー

- 生成AIの最新動向を追いたいビジネスパーソン
- AI戦略の立案に携わるプロダクトマネージャー・経営企画担当者
- 技術トレンドを把握したいエンジニア・リサーチャー

### 1.5 スコープ

本システムは以下を対象範囲とする。

- ニュースの自動収集（RSS / スクレイピング / API）
- LLMによるコンテンツ生成（要約・ストーリーテリング）
- Markdownファイルとしての永続化
- Gmail / LINE による配信
- リアクション収集とフィードバックループ
- ナレッジベースとしての検索・閲覧

以下は対象範囲外とする。

- Web UIダッシュボード（将来拡張として検討）
- 複数ユーザーの権限管理
- クラウドデプロイ（ローカル実行を前提とする）

---

## 2. 用語定義

| 用語 | 定義 |
|------|------|
| ストーリーテリングフレームワーク | ニュース記事を読みやすい物語構造に変換するための文章構成手法の総称。本システムではSTAR法、ヒーローズジャーニー簡易版、Before/After/Bridge、PASの4種を採用する |
| STAR法 | Situation（状況）→ Task（課題）→ Action（行動）→ Result（成果）の順に展開するフレームワーク |
| ヒーローズジャーニー簡易版 | 課題 → 試練 → 解決 → 変革の流れで事例を物語化するフレームワーク |
| Before/After/Bridge | 導入前の状態 → 導入後の状態 → その橋渡し（どうやって変わったか）を示すフレームワーク |
| PAS | Problem（問題提起）→ Agitation（問題の深刻さを強調）→ Solution（解決策の提示）の順に展開するフレームワーク |
| ナレッジベース | 収集・生成したニュース記事をMarkdownファイルとして蓄積するローカルディレクトリ群 |
| YAML Frontmatter | Markdownファイル冒頭に `---` で囲んで記述するメタデータ領域。日付・タグ・リアクション等の構造化データを保持する |
| リアクション | 配信されたニュースに対する読者のフィードバック。4段階評価（素晴らしい / 良い / 微妙 / 後で読む）で記録する |
| Today's Insight | その日のニュース全体を俯瞰した編集者的な気づき・示唆をまとめたセクション |
| Daily Digest | 毎朝配信される3記事 + Today's Insightのまとめ |
| Monthly Summary | 月次で自動生成される統計・トレンド分析レポート |
| cron | Unix系OSにおける時刻指定タスクスケジューラ。本システムの定時実行に使用する |

---

## 3. 機能要件

### 3.1 FR-001: ニュース収集機能

#### 3.1.1 概要

国内外のメディアから生成AI活用事例を自動収集する。

#### 3.1.2 詳細仕様

| 項目 | 仕様 |
|------|------|
| 実行タイミング | 毎朝 06:00 JST（cron または APScheduler による定時実行） |
| 収集件数 | 3件 / 日（設定ファイルで変更可能） |
| 手動実行 | CLIコマンドによる任意タイミングでの実行をサポート |

#### 3.1.3 情報ソースと取得方式

| ソース | 取得方式 | 優先度 |
|--------|----------|--------|
| TechCrunch | RSS | Must |
| VentureBeat | RSS | Must |
| The Verge (AI セクション) | RSS | Should |
| Hacker News | API (HN Algolia API) | Must |
| AI関連サブReddit (r/MachineLearning, r/artificial 等) | Reddit API / RSS | Should |
| 日経クロステック | RSSまたはWebスクレイピング | Must |
| ITmedia (AI+ セクション) | RSS | Must |
| Publickey | RSS | Should |
| arXiv (cs.AI / cs.CL) | arXiv API | Should |
| Hugging Face Blog | RSS | Could |
| NewsAPI | REST API | Should |

#### 3.1.4 記事選定基準

収集した候補記事群から、以下の基準に基づきLLMが上位3件を選定する。

| 基準 | 重み | 説明 |
|------|------|------|
| 先進性 | 30% | 技術的に新しいアプローチ、未踏の領域への応用であるか |
| 意外性 | 20% | 読者が「こんな使い方があるのか」と感じる驚きがあるか |
| 実用性 | 25% | すぐにビジネスで応用できる具体性があるか |
| 日本企業への適用可能性 | 25% | 日本の産業構造・商慣行において応用しやすいか |

#### 3.1.5 収集データ構造

各記事について以下の情報を取得する。

```
- title: 元記事のタイトル
- url: 元記事のURL
- source: メディア名
- published_at: 公開日時 (ISO 8601)
- raw_content: 記事本文（取得可能な範囲）
- language: 言語コード (en / ja)
- relevance_score: 選定基準に基づくスコア (0.0-1.0)
```

#### 3.1.6 中間データ保存

- 収集した全候補記事を中間JSONファイルとして保存する
- 保存先: `./knowledge_base/daily/YYYY-MM-DD_candidates.json`
- 選定のトレーサビリティ確保とデバッグに使用する

---

### 3.2 FR-002: コンテンツ生成機能

#### 3.2.1 概要

収集した記事をLLMを用いてストーリーテリング形式に変換し、日本語の読みやすい記事を生成する。

#### 3.2.2 詳細仕様

| 項目 | 仕様 |
|------|------|
| 使用LLM | OpenAI GPT-4o（設定ファイルで変更可能。Claude API等も対応可） |
| 文字数 | 各事例 800～1,200文字（日本語） |
| 言語 | 日本語（英語ソースは翻訳・意訳） |

#### 3.2.3 ストーリーテリングフレームワーク

LLMが事例の内容に応じて以下の4つから最適なフレームワークを自動選択する。

| フレームワーク | 適用場面 | 構成 |
|---------------|----------|------|
| STAR法 | 企業の具体的プロジェクト事例 | Situation → Task → Action → Result |
| ヒーローズジャーニー簡易版 | 困難を乗り越えた変革事例 | 課題 → 試練 → 解決 → 変革 |
| Before/After/Bridge | ビフォーアフターが明確な導入事例 | 導入前 → 導入後 → 橋渡し |
| PAS | 業界課題に対するソリューション提案 | Problem → Agitation → Solution |

#### 3.2.4 生成コンテンツの必須要素

各記事に以下の要素を必ず含める。

1. **タイトル**: 読者の好奇心を刺激する形式とする
   - 疑問形（例: 「なぜ○○はAIで売上を3倍にできたのか？」）
   - 数字入り（例: 「生成AIで業務時間を40%削減した3つの秘訣」）
   - いずれかの形式をLLMが事例に応じて選択
2. **使用フレームワーク名の明示**: 記事冒頭にバッジとして表示
3. **本文**: 選択されたフレームワークに従った構造化された記事
4. **「なぜこれが重要か」セクション**: 業界全体への影響・意義を解説
5. **「日本企業への示唆」セクション**: 日本市場における具体的な応用可能性を提示
6. **元記事リンク**: ソースURLへの参照

#### 3.2.5 Today's Insightセクション

3件のニュースを俯瞰し、以下を含むインサイトを生成する。

- 3件に共通するトレンドや示唆
- 今日のニュースから読み取れる生成AI業界の方向性
- 読者への問いかけ（思考を促すクローズ）

---

### 3.3 FR-003: Markdown出力機能

#### 3.3.1 概要

生成したコンテンツをMarkdownファイルとしてローカルナレッジベースに保存する。

#### 3.3.2 ファイル仕様

| 項目 | 仕様 |
|------|------|
| ファイル名 | `YYYY-MM-DD_ai_news.md` |
| 保存先 | `./knowledge_base/daily/` |
| エンコーディング | UTF-8 |
| 改行コード | LF |

#### 3.3.3 YAML Frontmatter仕様

```yaml
---
date: "2026-02-25"
generation_timestamp: "2026-02-25T06:05:32+09:00"
tags:
  - 生成AI
  - LLM
  - (記事内容に応じた自動タグ)
stories:
  - id: 1
    title: "記事タイトル"
    source: "メディア名"
    source_url: "https://..."
    framework: "STAR"
    tags:
      - タグ1
      - タグ2
    reactions:
      excellent: 0
      good: 0
      so_so: 0
      read_later: 0
  - id: 2
    title: "..."
    source: "..."
    source_url: "..."
    framework: "..."
    tags: [...]
    reactions:
      excellent: 0
      good: 0
      so_so: 0
      read_later: 0
  - id: 3
    title: "..."
    source: "..."
    source_url: "..."
    framework: "..."
    tags: [...]
    reactions:
      excellent: 0
      good: 0
      so_so: 0
      read_later: 0
total_reactions:
  excellent: 0
  good: 0
  so_so: 0
  read_later: 0
---
```

#### 3.3.4 本文構造

```markdown
# AI News Daily - YYYY年MM月DD日

## Story 1: [タイトル]

> **フレームワーク**: STAR法 | **ソース**: TechCrunch

(本文 800-1200文字)

### なぜこれが重要か

(解説)

### 日本企業への示唆

(解説)

📰 [元記事を読む](URL)

---

## Story 2: [タイトル]
(同上の構造)

---

## Story 3: [タイトル]
(同上の構造)

---

## Today's Insight

(3件を俯瞰したインサイト)
```

---

### 3.4 FR-004: 配信機能（Gmail）

#### 3.4.1 概要

生成したMarkdownコンテンツをHTML形式に変換し、Gmailで配信する。

#### 3.4.2 詳細仕様

| 項目 | 仕様 |
|------|------|
| 使用API | Gmail API (google-api-python-client) |
| 認証方式 | OAuth 2.0 (初回: ブラウザ認証フロー → トークンファイル保存、以降: リフレッシュトークンによる自動認証) |
| メール形式 | HTML（Markdownから変換） |
| 送信先 | 設定ファイル (config.yaml) で管理するメーリングリスト |
| 送信タイミング | ニュース生成完了直後（06:00 JST以降） |
| 件名フォーマット | `[AI News] YYYY/MM/DD - {Story1のタイトル} 他2件` |

#### 3.4.3 HTMLメールテンプレート

- レスポンシブデザイン対応（モバイル閲覧を考慮）
- ダークモード対応
- Jinja2テンプレートエンジンを使用
- 各ニュースの末尾にリアクションリンクを配置

#### 3.4.4 リアクションリンク仕様

各ニュースの末尾に以下の4つのリアクションリンクを配置する。

| リアクション | 表示 | リンク形式 |
|-------------|------|-----------|
| 素晴らしい | ⭐ 素晴らしい | `http://localhost:{PORT}/api/reaction/{date}/{story_id}/excellent` |
| 良い | 👍 良い | `http://localhost:{PORT}/api/reaction/{date}/{story_id}/good` |
| 微妙 | 🤔 微妙 | `http://localhost:{PORT}/api/reaction/{date}/{story_id}/so_so` |
| 後で読む | 📌 後で読む | `http://localhost:{PORT}/api/reaction/{date}/{story_id}/read_later` |

ポート番号はconfig.yamlで設定可能（デフォルト: 8321）。

---

### 3.5 FR-005: 配信機能（LINE）[オプション]

#### 3.5.1 概要

LINE Notifyを通じてニュースの要約をテキスト形式で配信する。

#### 3.5.2 詳細仕様

| 項目 | 仕様 |
|------|------|
| 使用API | LINE Notify API |
| 認証 | Bearer Token |
| メッセージ形式 | テキスト（1,000文字以内） |
| 送信タイミング | Gmail配信と同時 |

#### 3.5.3 メッセージフォーマット

```
🤖 AI News Daily - YYYY/MM/DD

📰 Story 1: {タイトル}
{50文字要約}
🔗 {URL}

📰 Story 2: {タイトル}
{50文字要約}
🔗 {URL}

📰 Story 3: {タイトル}
{50文字要約}
🔗 {URL}

💡 Today's Insight:
{100文字要約}
```

#### 3.5.4 補足

- 詳細はGmailメールへ誘導する
- LINE Notifyサービス終了の可能性を考慮し、LINE Messaging APIへの移行パスを設計に含める

---

### 3.6 FR-006: リアクション・蓄積機能

#### 3.6.1 概要

メール内のリアクションリンクからのフィードバックを受信し、対応するMarkdownファイルのFrontmatterを更新する。あわせてタグの自動付与と月次サマリーの生成を行う。

#### 3.6.2 APIサーバー仕様

| 項目 | 仕様 |
|------|------|
| フレームワーク | FastAPI |
| ホスト | localhost |
| ポート | 8321（設定変更可能） |
| 起動方式 | バックグラウンドプロセス（systemdまたはnohup） |

#### 3.6.3 エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/reaction/{date}/{story_id}/{type}` | リアクション受信。ブラウザリダイレクトで「ありがとう」ページを表示 |
| GET | `/api/stories/{date}` | 指定日のニュース一覧取得 |
| GET | `/api/stories/{date}/{story_id}` | 指定ニュースの詳細取得 |
| GET | `/api/search?q={query}&tag={tag}&min_rating={n}` | ナレッジベース検索 |
| GET | `/api/summary/{year}/{month}` | 月次サマリー取得 |
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/stats` | 蓄積統計情報 |

#### 3.6.4 リアクション受信処理フロー

```
1. GET /api/reaction/{date}/{story_id}/{type} を受信
2. {date} に対応するMarkdownファイルを特定
   → ./knowledge_base/daily/YYYY-MM-DD_ai_news.md
3. python-frontmatterライブラリでYAML Frontmatterをパース
4. 該当story_idのreactions.{type}をインクリメント
5. total_reactionsも更新
6. Frontmatterを書き戻し
7. リダイレクト → サンクスページ（HTMLレスポンス）
```

#### 3.6.5 自動タグ付与

記事生成時にLLMが内容に基づいて以下のカテゴリからタグを自動付与する。

| カテゴリ | タグ例 |
|----------|--------|
| 技術領域 | LLM, 画像生成, 音声AI, マルチモーダル, RAG, Agent |
| 業種 | 製造, 金融, 医療, 小売, 教育, メディア |
| 活用タイプ | 業務効率化, 顧客体験向上, 新規事業, コスト削減, 創造支援 |
| 規模 | スタートアップ, 大企業, 中小企業 |

#### 3.6.6 月次サマリー自動生成

| 項目 | 仕様 |
|------|------|
| 生成タイミング | 毎月1日 06:30 JST |
| 保存先 | `./knowledge_base/monthly/YYYY-MM_summary.md` |
| 内容 | 月間のトップ記事（高評価Top5）、頻出タグ集計、リアクション統計、カテゴリ別トレンド分析、月次インサイト |

---

### 3.7 FR-007: ナレッジベース検索機能

#### 3.7.1 概要

蓄積されたMarkdownファイルをタグ・全文・評価で検索する。CLIおよびAPIの2つのインターフェースを提供する。

#### 3.7.2 検索方式

| 検索種別 | 方式 | 説明 |
|---------|------|------|
| タグベース検索 | YAML Frontmatterのtagsフィールドを対象 | 指定タグに一致する記事を返却 |
| 全文検索 | Markdown本文をプレーンテキスト化して検索 | キーワードに一致する記事を返却 |
| 高評価フィルタリング | reactions合計値でソート | excellent + good の合計が閾値以上の記事を返却 |

#### 3.7.3 検索APIパラメータ

| パラメータ | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| q | string | No | 全文検索キーワード |
| tag | string | No | タグ名（カンマ区切りで複数指定可） |
| min_rating | int | No | 最低リアクション数（excellent + good の合計） |
| date_from | string | No | 検索開始日 (YYYY-MM-DD) |
| date_to | string | No | 検索終了日 (YYYY-MM-DD) |
| sort | string | No | ソート順（date_desc / date_asc / rating_desc）。デフォルト: date_desc |
| limit | int | No | 返却件数上限。デフォルト: 20 |
| offset | int | No | ページネーションオフセット。デフォルト: 0 |

#### 3.7.4 レスポンス形式

```json
{
  "total": 42,
  "offset": 0,
  "limit": 20,
  "results": [
    {
      "date": "2026-02-25",
      "story_id": 1,
      "title": "記事タイトル",
      "source": "TechCrunch",
      "framework": "STAR",
      "tags": ["LLM", "製造", "業務効率化"],
      "reactions": {
        "excellent": 3,
        "good": 5,
        "so_so": 0,
        "read_later": 2
      },
      "excerpt": "本文の冒頭200文字..."
    }
  ]
}
```

---

## 4. 非機能要件

### 4.1 NFR-001: 実行環境

| 項目 | 仕様 |
|------|------|
| 言語 | Python 3.11以上 |
| パッケージ管理 | pip (requirements.txt) または Poetry |
| OS | macOS / Linux（Windows WSL2も対象） |
| 実行形態 | ローカルマシン上でのバッチ実行 + 常駐APIサーバー |

### 4.2 NFR-002: 依存ライブラリ方針

依存ライブラリは最小限に抑える。以下を主要ライブラリとして想定する。

| ライブラリ | 用途 |
|-----------|------|
| feedparser | RSS解析 |
| httpx | HTTP通信 |
| beautifulsoup4 | HTMLパース・スクレイピング |
| openai | LLM API呼び出し |
| pyyaml | YAML操作 |
| python-frontmatter | Markdownのfrontmatter操作 |
| fastapi | APIサーバー |
| uvicorn | ASGIサーバー |
| google-api-python-client | Gmail API |
| google-auth-oauthlib | OAuth2認証 |
| markdown | Markdown → HTML変換 |
| jinja2 | HTMLメールテンプレート |
| python-dotenv | 環境変数管理 |
| apscheduler | タスクスケジューリング（オプション） |

### 4.3 NFR-003: エラーハンドリング・リトライ

| 項目 | 仕様 |
|------|------|
| リトライ回数 | 最大3回（設定変更可能） |
| リトライ間隔 | Exponential backoff (1秒 → 2秒 → 4秒) |
| リトライ対象 | HTTP 429, 500, 502, 503, 504、ネットワークタイムアウト |
| エラー通知 | 全リトライ失敗時にログ出力 + メール通知（設定で有効/無効を切替） |
| 部分失敗 | 3件中1件のソース取得失敗時は残り2件で続行。全件失敗時のみ処理中断 |

### 4.4 NFR-004: ログ

| 項目 | 仕様 |
|------|------|
| 保存先 | `./logs/` |
| ファイル名 | `YYYY-MM-DD.log` |
| フォーマット | `[YYYY-MM-DD HH:MM:SS] [LEVEL] [MODULE] MESSAGE` |
| ログレベル | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| ローテーション | 日次ローテーション、30日間保持 |
| デフォルトレベル | INFO（設定ファイルで変更可能） |

### 4.5 NFR-005: 設定管理

#### config.yaml

```yaml
# config.yaml
collection:
  schedule_time: "06:00"
  timezone: "Asia/Tokyo"
  num_stories: 3
  sources:
    - name: "TechCrunch"
      type: "rss"
      url: "https://techcrunch.com/category/artificial-intelligence/feed/"
      enabled: true
    - name: "VentureBeat"
      type: "rss"
      url: "https://venturebeat.com/category/ai/feed/"
      enabled: true
    # ... (他ソース)

generation:
  llm_model: "gpt-4o"
  max_tokens: 4096
  temperature: 0.7
  language: "ja"
  min_chars: 800
  max_chars: 1200

output:
  knowledge_base_dir: "./knowledge_base/daily/"
  monthly_summary_dir: "./knowledge_base/monthly/"

delivery:
  gmail:
    enabled: true
    recipients:
      - "user@example.com"
    subject_template: "[AI News] {date} - {headline}"
  line:
    enabled: false
    # LINE Notify token is stored in .env

api_server:
  host: "127.0.0.1"
  port: 8321

logging:
  level: "INFO"
  dir: "./logs/"
  retention_days: 30

retry:
  max_attempts: 3
  backoff_base: 1
  backoff_multiplier: 2
```

#### .envファイル

```
OPENAI_API_KEY=sk-...
GMAIL_CREDENTIALS_PATH=./credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=./credentials/gmail_token.json
LINE_NOTIFY_TOKEN=...
NEWS_API_KEY=...
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
```

### 4.6 NFR-006: セキュリティ

| 項目 | 仕様 |
|------|------|
| APIキー管理 | .envファイルで管理し、.gitignoreに追加 |
| OAuth認証情報 | ./credentials/ディレクトリに保存し、.gitignoreに追加 |
| APIサーバー | localhostのみバインド（外部アクセス不可） |
| 入力バリデーション | FastAPIのPydanticモデルによる入力検証 |

### 4.7 NFR-007: パフォーマンス

| 項目 | 目標値 |
|------|--------|
| ニュース収集～配信完了 | 10分以内 |
| APIサーバー応答時間 | 500ms以内（検索含む） |
| Markdownファイル読み込み | 1ファイルあたり100ms以内 |
| API呼び出し | 各外部APIのレート制限を遵守 |

---

## 5. システム境界・外部インターフェース

### 5.1 システム構成図

```
┌──────────────────────────────────────────────────────────────┐
│                    AI News Collector Bot                      │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │  Collector   │→│  Generator   │→│  Markdown Writer      │ │
│  │  Module      │  │  Module      │  │  Module              │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬───────────┘ │
│         │                │                      │            │
│         ↓                ↓                      ↓            │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │  RSS / API / │  │  OpenAI     │  │  Knowledge Base       │ │
│  │  Scraping    │  │  API        │  │  (./knowledge_base/)  │ │
│  └─────────────┘  └─────────────┘  └──────────┬───────────┘ │
│                                                 │            │
│  ┌─────────────┐  ┌─────────────┐               │            │
│  │  Gmail       │  │  LINE       │               │            │
│  │  Delivery    │  │  Delivery   │               │            │
│  └──────┬──────┘  └──────┬──────┘               │            │
│         │                │                       │            │
│  ┌──────────────────────────────────────────────────────────┐│
│  │           FastAPI Server (localhost:8321)                 ││
│  │  /api/reaction  /api/search  /api/summary  /api/health   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 5.2 外部インターフェース一覧

| IF-ID | 外部システム | 方向 | プロトコル | 認証方式 | 用途 |
|-------|-------------|------|-----------|---------|------|
| IF-001 | TechCrunch / VentureBeat 等 | 受信 | HTTPS (RSS) | なし | ニュース記事の取得 |
| IF-002 | Hacker News API | 受信 | HTTPS (REST) | なし | ニュース記事の取得 |
| IF-003 | Reddit API | 受信 | HTTPS (REST) | OAuth2 | AI関連投稿の取得 |
| IF-004 | NewsAPI | 受信 | HTTPS (REST) | API Key | ニュース記事の検索・取得 |
| IF-005 | arXiv API | 受信 | HTTPS (REST) | なし | 論文情報の取得 |
| IF-006 | OpenAI API | 双方向 | HTTPS (REST) | API Key | コンテンツ生成（LLM） |
| IF-007 | Gmail API | 送信 | HTTPS (REST) | OAuth 2.0 | メール配信 |
| IF-008 | LINE Notify API | 送信 | HTTPS (REST) | Bearer Token | LINE配信 |
| IF-009 | ローカルファイルシステム | 双方向 | ファイルI/O | なし | ナレッジベースの読み書き |

---

## 6. データ要件

### 6.1 ディレクトリ構成

```
./
├── config.yaml                  # システム設定
├── .env                         # APIキー等の秘匿情報
├── credentials/                 # OAuth認証情報
│   ├── gmail_credentials.json
│   └── gmail_token.json
├── knowledge_base/              # ナレッジベース
│   ├── daily/                   # 日次ニュース
│   │   ├── 2026-02-25_ai_news.md
│   │   ├── 2026-02-25_candidates.json
│   │   └── ...
│   └── monthly/                 # 月次サマリー
│       ├── 2026-01_summary.md
│       └── ...
├── logs/                        # ログファイル
│   ├── 2026-02-25.log
│   └── ...
├── templates/                   # メールHTMLテンプレート
│   ├── email_base.html
│   └── thanks.html
└── src/                         # ソースコード
    ├── collector/               # ニュース収集モジュール
    ├── generator/               # コンテンツ生成モジュール
    ├── writer/                  # Markdown出力モジュール
    ├── delivery/                # 配信モジュール（Gmail / LINE）
    ├── api/                     # FastAPI サーバー
    ├── search/                  # 検索モジュール
    └── utils/                   # 共通ユーティリティ
```

### 6.2 データ保持期間

| データ種別 | 保持期間 | 備考 |
|-----------|---------|------|
| 日次ニュースMD | 無期限 | ナレッジベースとして永続保持 |
| 候補記事JSON | 無期限 | トレーサビリティのため保持 |
| 月次サマリーMD | 無期限 | ナレッジベースとして永続保持 |
| ログファイル | 30日 | 自動ローテーションにより削除 |
| OAuth トークン | 有効期限切れまで | 自動リフレッシュ |

### 6.3 バックアップ

- ナレッジベースディレクトリはGit管理を推奨（.mdファイルおよび.jsonファイル）
- .envおよびcredentials/はバックアップ対象外（Gitに含めない）

---

## 7. 制約事項

| ID | 制約内容 | 理由 |
|----|---------|------|
| C-001 | ローカル実行を前提とする。クラウドデプロイは対象外 | 個人利用を想定し、インフラコストを最小化するため |
| C-002 | LLM APIの利用料金が発生する | コンテンツ生成に必須。月額コスト見積もり: 約$5-15（3件/日想定） |
| C-003 | Gmail APIにはGoogleアカウントとOAuth同意画面の設定が必要 | Google Cloud Consoleでのプロジェクト作成・API有効化が前提 |
| C-004 | LINE Notify APIはサービス終了の可能性がある | 代替手段（LINE Messaging API）への移行パスを考慮する |
| C-005 | Webスクレイピングは対象サイトの利用規約・robots.txtに従う | 過度なリクエストの抑止、法的リスクの回避が必要 |
| C-006 | リアクション機能はローカルネットワーク内でのみ動作 | APIサーバーがlocalhostにバインドされるため（外部公開時はngrok/cloudflare tunnel等を別途構成） |
| C-007 | arXiv論文は要旨（Abstract）のみを対象とする | 全文PDFの処理は計算コスト・ライセンスの観点から対象外 |
| C-008 | Gmail APIの送信制限（1日500通） | Google Workspaceの場合は2,000通まで |
| C-009 | NewsAPI無料プランの制限（1日100リクエスト） | 有料プラン契約で緩和可能 |
| C-010 | 一部サイトはペイウォール等でコンテンツ取得不可の場合がある | 取得失敗時は他ソースで補完する |

---

## 8. 前提条件

| ID | 前提条件 |
|----|---------|
| A-001 | Python 3.11以上がインストールされていること |
| A-002 | OpenAI APIキー（またはその他LLM APIキー）が取得済みであること |
| A-003 | Google Cloud Consoleでプロジェクトを作成し、Gmail APIが有効化されていること |
| A-004 | OAuth同意画面が構成済みであり、credentials.jsonが取得済みであること |
| A-005 | LINE配信を利用する場合、LINE Notifyトークンが取得済みであること |
| A-006 | インターネット接続が利用可能であること |
| A-007 | 実行マシンにcron（またはsystemd timer / APScheduler）が利用可能であること（定時実行の場合） |
| A-008 | NewsAPI利用の場合、APIキーが取得済みであること |
| A-009 | Reddit API利用の場合、Reddit Appが作成済みでClient ID / Secretが取得済みであること |

---

## 9. 優先度（MoSCoW法）

### Must（必須）

これがなければシステムとして成立しない機能。MVP（最小実行可能プロダクト）の範囲。

| ID | 機能 | 対応する機能要件 |
|----|------|----------------|
| M-001 | RSSによるニュース収集（国内外各1ソース以上） | FR-001 |
| M-002 | LLMによるストーリーテリング形式の記事生成 | FR-002 |
| M-003 | ストーリーテリングフレームワークの適用（4種から自動選択） | FR-002 |
| M-004 | Markdownファイル出力（YAML Frontmatter付き） | FR-003 |
| M-005 | Gmail配信（HTML形式） | FR-004 |
| M-006 | config.yamlによる設定管理 | NFR-005 |
| M-007 | .envによるAPIキー管理 | NFR-005 |
| M-008 | 基本的なエラーハンドリングとログ出力 | NFR-003, NFR-004 |

### Should（重要）

なくても動作するが、ユーザー体験を大きく向上させる機能。MVP後の第2フェーズで実装。

| ID | 機能 | 対応する機能要件 |
|----|------|----------------|
| S-001 | リアクション機能（FastAPIサーバー + Frontmatter更新） | FR-006 |
| S-002 | メール内リアクションリンク | FR-004 |
| S-003 | タグ自動付与 | FR-006 |
| S-004 | ナレッジベース検索（タグ・全文・評価） | FR-007 |
| S-005 | 全ソースの統合（Hacker News, Reddit, arXiv, NewsAPI等） | FR-001 |
| S-006 | Webスクレイピングによる収集 | FR-001 |
| S-007 | リトライ機構（Exponential backoff） | NFR-003 |

### Could（あると良い）

時間とリソースに余裕があれば実装する機能。

| ID | 機能 | 対応する機能要件 |
|----|------|----------------|
| C-001 | LINE Notify配信 | FR-005 |
| C-002 | 月次サマリー自動生成 | FR-006 |
| C-003 | ダークモード対応HTMLメール | FR-004 |
| C-004 | 高評価記事フィルタリング | FR-007 |
| C-005 | 蓄積統計情報API | FR-006 |

### Won't（今回は対象外）

本バージョンでは対象外とし、将来の拡張として記録する。

| ID | 機能 | 備考 |
|----|------|------|
| W-001 | Web UIダッシュボード | 将来的にStreamlit等での実装を検討 |
| W-002 | 複数ユーザー対応・権限管理 | 個人利用を前提とするため |
| W-003 | クラウドデプロイ（AWS/GCP） | ローカル実行で十分な規模を想定 |
| W-004 | Slack / Teams連携 | 配信チャネルの拡張として将来検討 |
| W-005 | 記事の自動分類・クラスタリング（ベクトルDB） | RAG連携として将来検討 |
| W-006 | 多言語対応（英語版配信） | 日本語読者を主要ターゲットとするため |
| W-007 | ユーザーの好み学習による記事選定最適化 | リアクションデータ蓄積後に検討 |

---

## 付録A: 開発マイルストーン（参考）

| フェーズ | 内容 | 含まれる機能ID | 目安期間 |
|---------|------|---------------|---------|
| Phase 1 (MVP) | Must項目の実装・動作確認 | M-001 ～ M-008 | 2週間 |
| Phase 2 | Should項目の実装 | S-001 ～ S-007 | 2週間 |
| Phase 3 | Could項目の実装 | C-001 ～ C-005 | 1週間 |
| 継続運用 | フィードバックに基づく改善 | - | 随時 |

## 付録B: 変更履歴

| 日付 | バージョン | 変更者 | 変更内容 |
|------|-----------|--------|---------|
| 2026-02-25 | 1.0.0 | - | 初版作成 |
