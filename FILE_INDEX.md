# FILE_INDEX — AI-News-Collection-Bot_v1

> ⚠️ このファイルは自動生成です。手動編集は次回更新で上書きされます。

| 項目 | 値 |
|---|---|
| リポジトリ | KazuyaMurayama/AI-News-Collection-Bot_v1 |
| ブランチ | main |
| 総ファイル数 | 63 |
| 最終更新 | 2026-05-02 |
| 管理者 | 男座員也（Kazuya Oza） |

---

## カテゴリ別サマリー

| カテゴリ | ファイル数 |
|---|---|
| Documentation | 13 |
| Code | 40 |
| Data | 2 |
| Asset | 1 |
| Config | 4 |
| Other | 3 |

---

## ディレクトリ構成

```
.
├── .github/
│   └── workflows/
│       └── daily-news.yml
├── ai-news-bot/
│   ├── docs/
│   │   ├── architecture.md
│   │   ├── final_report.md
│   │   ├── requirements.md
│   │   ├── setup_guide.md
│   │   └── test_report.md
│   ├── scripts/
│   │   ├── install_cron.sh
│   │   ├── install_task_scheduler.bat
│   │   ├── run_daily.bat
│   │   ├── run_once.sh
│   │   └── uninstall_cron.sh
│   ├── src/
│   │   ├── collector/
│   │   │   ├── __init__.py
│   │   │   ├── news_api.py
│   │   │   ├── prefilter.py
│   │   │   ├── rss_collector.py
│   │   │   ├── selector.py
│   │   │   └── web_scraper.py
│   │   ├── delivery/
│   │   │   ├── __init__.py
│   │   │   ├── gmail_sender.py
│   │   │   ├── html_converter.py
│   │   │   └── line_sender.py
│   │   ├── feedback/
│   │   │   ├── __init__.py
│   │   │   ├── api_server.py
│   │   │   ├── email_processor.py
│   │   │   └── updater.py
│   │   ├── knowledge/
│   │   │   ├── __init__.py
│   │   │   ├── search.py
│   │   │   ├── summarizer.py
│   │   │   └── tagger.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── logger.py
│   │   │   ├── quality_checker.py
│   │   │   └── retry.py
│   │   ├── writer/
│   │   │   ├── templates/
│   │   │   │   ... (2 items)
│   │   │   ├── __init__.py
│   │   │   ├── markdown_gen.py
│   │   │   └── storyteller.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_collector.py
│   │   ├── test_delivery.py
│   │   ├── test_feedback.py
│   │   ├── test_integration.py
│   │   ├── test_utils.py
│   │   └── test_writer.py
│   ├── .env.example
│   ├── .gitignore
│   ├── config.yaml
│   ├── README.md
│   ├── requirements.txt
│   └── setup.sh
├── .gitignore
├── AI_News_Collector_Bot_Presentation.pptx
├── CLAUDE.md
├── FILE_INDEX.md
├── generate_pptx.py
├── README.md
├── tasks.md
├── Timeout_Prevention.md
└── v2_project_prompt.md
```

---

## ファイル詳細

### Documentation (13件)

| ファイル | サイズ | 説明 |
|---|---|---|
| `ai-news-bot/docs/architecture.md` | 36.7 KB | Markdown ドキュメント |
| `ai-news-bot/docs/final_report.md` | 20.5 KB | Markdown ドキュメント |
| `ai-news-bot/docs/requirements.md` | 32.7 KB | Markdown ドキュメント |
| `ai-news-bot/docs/setup_guide.md` | 24.0 KB | Markdown ドキュメント |
| `ai-news-bot/docs/test_report.md` | 19.2 KB | Markdown ドキュメント |
| `ai-news-bot/README.md` | 6.0 KB | リポジトリ概要・セットアップ手順 |
| `ai-news-bot/src/writer/templates/daily_template.md` | 227 B | Markdown ドキュメント |
| `CLAUDE.md` | 1.3 KB | Claude Code プロジェクト設定・命名ルール |
| `FILE_INDEX.md` | 2.7 KB | （このファイル）全ファイルインデックス |
| `README.md` | 2.1 KB | リポジトリ概要・セットアップ手順 |
| `tasks.md` | 1.2 KB | タスク管理・セッション履歴 |
| `Timeout_Prevention.md` | 4.9 KB | タイムアウト対策ガイド |
| `v2_project_prompt.md` | 22.2 KB | Markdown ドキュメント |

### Code (40件)

| ファイル | サイズ | 説明 |
|---|---|---|
| `ai-news-bot/scripts/install_cron.sh` | 2.8 KB | シェルスクリプト |
| `ai-news-bot/scripts/run_once.sh` | 2.5 KB | シェルスクリプト |
| `ai-news-bot/scripts/uninstall_cron.sh` | 1.0 KB | シェルスクリプト |
| `ai-news-bot/setup.sh` | 4.0 KB | シェルスクリプト |
| `ai-news-bot/src/__init__.py` | - | Python スクリプト |
| `ai-news-bot/src/collector/__init__.py` | 5.8 KB | Python スクリプト |
| `ai-news-bot/src/collector/news_api.py` | 8.5 KB | Python スクリプト |
| `ai-news-bot/src/collector/prefilter.py` | 4.7 KB | Python スクリプト |
| `ai-news-bot/src/collector/rss_collector.py` | 6.9 KB | Python スクリプト |
| `ai-news-bot/src/collector/selector.py` | 16.6 KB | Python スクリプト |
| `ai-news-bot/src/collector/web_scraper.py` | 10.6 KB | Python スクリプト |
| `ai-news-bot/src/delivery/__init__.py` | 680 B | Python スクリプト |
| `ai-news-bot/src/delivery/gmail_sender.py` | 16.4 KB | Python スクリプト |
| `ai-news-bot/src/delivery/html_converter.py` | 9.1 KB | Python スクリプト |
| `ai-news-bot/src/delivery/line_sender.py` | 7.1 KB | Python スクリプト |
| `ai-news-bot/src/feedback/__init__.py` | 760 B | Python スクリプト |
| `ai-news-bot/src/feedback/api_server.py` | 17.6 KB | Python スクリプト |
| `ai-news-bot/src/feedback/email_processor.py` | 6.1 KB | Python スクリプト |
| `ai-news-bot/src/feedback/updater.py` | 7.1 KB | Python スクリプト |
| `ai-news-bot/src/knowledge/__init__.py` | 846 B | Python スクリプト |
| `ai-news-bot/src/knowledge/search.py` | 8.7 KB | Python スクリプト |
| `ai-news-bot/src/knowledge/summarizer.py` | 14.6 KB | Python スクリプト |
| `ai-news-bot/src/knowledge/tagger.py` | 8.2 KB | Python スクリプト |
| `ai-news-bot/src/main.py` | 18.4 KB | Python スクリプト |
| `ai-news-bot/src/utils/__init__.py` | - | Python スクリプト |
| `ai-news-bot/src/utils/config.py` | 12.6 KB | Python スクリプト |
| `ai-news-bot/src/utils/logger.py` | 5.1 KB | Python スクリプト |
| `ai-news-bot/src/utils/quality_checker.py` | 10.9 KB | Python スクリプト |
| `ai-news-bot/src/utils/retry.py` | 5.7 KB | Python スクリプト |
| `ai-news-bot/src/writer/__init__.py` | 714 B | Python スクリプト |
| `ai-news-bot/src/writer/markdown_gen.py` | 8.2 KB | Python スクリプト |
| `ai-news-bot/src/writer/storyteller.py` | 21.2 KB | Python スクリプト |
| `ai-news-bot/tests/__init__.py` | - | Python スクリプト |
| `ai-news-bot/tests/test_collector.py` | 31.1 KB | Python スクリプト |
| `ai-news-bot/tests/test_delivery.py` | 19.2 KB | Python スクリプト |
| `ai-news-bot/tests/test_feedback.py` | 22.0 KB | Python スクリプト |
| `ai-news-bot/tests/test_integration.py` | 45.2 KB | Python スクリプト |
| `ai-news-bot/tests/test_utils.py` | 19.4 KB | Python スクリプト |
| `ai-news-bot/tests/test_writer.py` | 26.0 KB | Python スクリプト |
| `generate_pptx.py` | 46.1 KB | Python スクリプト |

### Data (2件)

| ファイル | サイズ | 説明 |
|---|---|---|
| `.github/workflows/daily-news.yml` | 3.8 KB | GitHub Actions ワークフロー |
| `ai-news-bot/config.yaml` | 4.7 KB | YAML 設定 |

### Asset (1件)

| ファイル | サイズ | 説明 |
|---|---|---|
| `AI_News_Collector_Bot_Presentation.pptx` | 59.8 KB | PowerPoint プレゼンテーション |

### Config (4件)

| ファイル | サイズ | 説明 |
|---|---|---|
| `.gitignore` | 377 B | Git 除外設定 |
| `ai-news-bot/.env.example` | 1.1 KB | 環境変数テンプレート |
| `ai-news-bot/.gitignore` | 660 B | Git 除外設定 |
| `ai-news-bot/requirements.txt` | 707 B | Python 依存パッケージリスト |

### Other (3件)

| ファイル | サイズ | 説明 |
|---|---|---|
| `ai-news-bot/scripts/install_task_scheduler.bat` | 2.2 KB | ファイル |
| `ai-news-bot/scripts/run_daily.bat` | 1.4 KB | ファイル |
| `ai-news-bot/src/writer/templates/email_template.html` | 11.7 KB | ファイル |

---

_自動生成: 2026-05-02 | 管理者: 男座員也（Kazuya Oza）_
