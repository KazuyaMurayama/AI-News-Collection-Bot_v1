# AI News Collector Bot

毎朝6:00（JST）に自動実行され、国内外の先進的な生成AI活用事例を3件収集し、ストーリーテリング形式でまとめて配信するシステムです。

## 主な機能

- **自動ニュース収集**: TechCrunch, VentureBeat, The Verge, Hacker News, arXiv, ITmedia, Publickey 等から生成AI関連記事を自動収集
- **ストーリーテリング変換**: Claude API を活用し、STAR法・ヒーローズジャーニー・Before/After/Bridge・PAS の4つのフレームワークから最適なものを選択して記事を生成
- **スマート選定**: 先進性・意外性・実用性・日本企業関連性・鮮度を基準に AI がスコアリング、上位3件を選定
- **マルチチャネル配信**: Gmail（HTML形式）+ LINE Notify（オプション）
- **リアクション機能**: メール内のボタンでフィードバック（素晴らしい / 良い / 微妙 / 後で読む）を送信
- **ナレッジベース**: Markdown ファイルとして蓄積、タグ・全文検索対応
- **月次サマリー**: 高評価記事やトレンド分析を自動生成

## クイックスタート

### 1. セットアップ
```bash
git clone <repository-url>
cd ai-news-bot
chmod +x setup.sh
./setup.sh
```

### 2. 環境変数の設定
```bash
cp .env.example .env
# .env を編集してAPIキーを設定
```

### 3. 設定ファイルの編集
```bash
# config.yaml を編集（配信先メールアドレス等）
vi config.yaml
```

### 4. 手動実行（テスト）
```bash
./scripts/run_once.sh
# または
./scripts/run_once.sh --dry-run  # 配信せずMarkdown生成のみ
```

### 5. 定時実行の設定
```bash
./scripts/install_cron.sh
```

## ディレクトリ構成

```
ai-news-bot/
├── config.yaml              # システム設定
├── .env                     # APIキー（要作成）
├── .env.example             # 環境変数テンプレート
├── requirements.txt         # Python依存パッケージ
├── setup.sh                 # セットアップスクリプト
├── credentials/             # OAuth認証情報
├── src/
│   ├── main.py              # メインオーケストレーター
│   ├── collector/           # ニュース収集モジュール
│   │   ├── rss_collector.py # RSS収集
│   │   ├── web_scraper.py   # Webスクレイピング
│   │   ├── news_api.py      # NewsAPI / Hacker News
│   │   └── selector.py      # AI記事選定（Claudeスコアリング）
│   ├── writer/              # コンテンツ生成モジュール
│   │   ├── storyteller.py   # ストーリーテリング変換
│   │   ├── markdown_gen.py  # Markdown生成
│   │   └── templates/       # テンプレート
│   ├── delivery/            # 配信モジュール
│   │   ├── gmail_sender.py  # Gmail配信
│   │   ├── line_sender.py   # LINE配信
│   │   └── html_converter.py# HTML変換
│   ├── feedback/            # リアクション処理
│   │   ├── api_server.py    # FastAPIサーバー
│   │   └── updater.py       # MDファイル更新
│   ├── knowledge/           # ナレッジベース管理
│   │   ├── search.py        # 検索機能
│   │   ├── tagger.py        # 自動タグ付け
│   │   └── summarizer.py    # 月次サマリー
│   └── utils/               # ユーティリティ
│       ├── config.py        # 設定管理
│       ├── logger.py        # ログ管理
│       └── retry.py         # リトライ機能
├── knowledge_base/
│   ├── daily/               # 日次ニュース
│   └── monthly/             # 月次サマリー
├── logs/                    # ログファイル
├── tests/                   # テストスイート
├── docs/                    # ドキュメント
└── scripts/                 # 運用スクリプト
    ├── install_cron.sh      # cron設定
    └── run_once.sh          # 手動実行
```

## 必要なAPIキー

| サービス | 必須 | 用途 |
|----------|------|------|
| Anthropic (Claude API) | 必須 | 記事選定・コンテンツ生成 |
| Gmail API (OAuth2) | 必須 | メール配信 |
| NewsAPI.org | 推奨 | ニュース収集 |
| LINE Notify | オプション | LINE配信 |

## テスト実行

```bash
cd ai-news-bot
source venv/bin/activate
PYTHONPATH=. python -m pytest tests/ -v
```

## ドキュメント

- [要件定義書](docs/requirements.md)
- [アーキテクチャ設計書](docs/architecture.md)
- [セットアップガイド](docs/setup_guide.md)
- [テストレポート](docs/test_report.md)
- [最終報告書](docs/final_report.md)

## リアクションサーバー

メール内のリアクションボタンからフィードバックを受け付ける FastAPI サーバーを起動します。

```bash
python -m src.main --server
```

## 主な設定項目（config.yaml）

- `collection.num_stories`: 収集する記事数（デフォルト: 3）
- `collection.sources`: 情報ソース一覧
- `delivery.gmail.recipients`: 配信先メールアドレス
- `delivery.line.enabled`: LINE配信の有効/無効
- `feedback_server.port`: リアクションサーバーのポート（デフォルト: 8080）
- `claude.model`: 使用するClaudeモデル（デフォルト: claude-sonnet-4-20250514）
- `logging.level`: ログレベル（デフォルト: INFO）
- `retry.max_attempts`: リトライ最大回数（デフォルト: 3）

## 動作環境

- Python 3.11 以上
- macOS / Linux（Windows WSL2 も対応）
- インターネット接続

## ライセンス

MIT License

## 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成
