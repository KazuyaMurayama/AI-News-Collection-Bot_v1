# FILE_INDEX.md — AI-News-Collection-Bot_v1

> **新セッション開始時に必ずこのファイルを読む。**
> ファイル追加・削除・移動時は必ずこのファイルを更新すること。
> 最終更新: 2026-04-30

## 概要
AIニュース自動収集・配信ボット v1。v2同等機能＋PPTXプレゼン資料・アーキテクチャ・要件定義・テストレポート付き。

**スタック:** Python, HTML, Shell Script, PowerPoint

---

## 📋 最初に読むべきファイル

| 優先度 | ファイル | 内容 |
|---|---|---|
| ★★★ | `ai-news-bot/src/main.py` | メインエントリポイント |
| ★★★ | `ai-news-bot/docs/final_report.md` | 最終報告書 |
| ★★ | `ai-news-bot/docs/architecture.md` | アーキテクチャ設計 |
| ★★ | `AI_News_Collector_Bot_Presentation.pptx` | プレゼン資料 |
| ★★ | `ai-news-bot/config.yaml` | 設定ファイル |

---

## 🗂️ ディレクトリ構造

```
AI-News-Collection-Bot_v1/
├── generate_pptx.py
├── AI_News_Collector_Bot_Presentation.pptx
└── ai-news-bot/
    ├── config.yaml
    ├── requirements.txt
    ├── setup.sh
    ├── docs/
    │   ├── architecture.md
    │   ├── requirements.md
    │   ├── setup_guide.md
    │   ├── test_report.md
    │   └── final_report.md      ← 最終報告書
    ├── src/
    │   ├── main.py
    │   ├── collector/
    │   ├── delivery/
    │   ├── writer/
    │   ├── knowledge/
    │   ├── feedback/
    │   └── utils/
    ├── tests/
    └── scripts/
```

---

## 📑 全ファイル一覧

| パス | 種別 | 説明 |
|---|---|---|
| `generate_pptx.py` | Python | PPTXプレゼン生成スクリプト |
| `AI_News_Collector_Bot_Presentation.pptx` | 資料 | プレゼンテーション資料 |
| `ai-news-bot/src/main.py` | Python | メインエントリポイント |
| `ai-news-bot/docs/architecture.md` | ドキュメント | アーキテクチャ設計 |
| `ai-news-bot/docs/requirements.md` | ドキュメント | 要件定義 |
| `ai-news-bot/docs/setup_guide.md` | ドキュメント | セットアップガイド |
| `ai-news-bot/docs/test_report.md` | ドキュメント | テストレポート |
| `ai-news-bot/docs/final_report.md` | ドキュメント | 最終報告書 |
| `ai-news-bot/config.yaml` | 設定 | システム設定 |
| `ai-news-bot/requirements.txt` | 設定 | Python依存関係 |

---

## 🔖 ファイル更新ルール

1. 新ファイル追加時: 該当セクションに1行追加
2. ファイル削除・移動時: 該当行を削除または更新
3. 更新後: `git add FILE_INDEX.md && git commit -m "docs: FILE_INDEX.md更新"`
