# AI News Collection Bot v1 — AIニュース自動収集・配信ボット

> AI関連の最新ニュース・論文を自動収集し、要約・タグ付けして配信するボットシステムです。

## 📋 概要

AI関連の最新ニュース・論文を自動収集し、要約・タグ付けして配信するボットシステムです。Claude APIで高精度な日本語要約を生成し、定期的に関係者へ配信します。

## ✨ 主な機能

- AI/MLニュースの自動スクレイピング
- Claude APIによる日本語要約生成
- キーワードフィルタリング
- 定期実行スケジューリング
- 配信ログ管理

## 🛠️ 技術スタック

| カテゴリ | 技術・ライブラリ |
|----------|----------------|
| 言語 | Python 3.10+ |
| AI要約 | Claude API |
| スクレイピング | requests, BeautifulSoup |
| スケジューリング | schedule |

## 🚀 セットアップ

### 前提条件

- Python 3.9 以上
- APIキー（Claude / OpenAI 等）を `.env` ファイルに設定

### インストール

```bash
git clone https://github.com/KazuyaMurayama/AI-News-Collection-Bot_v1.git
cd AI-News-Collection-Bot_v1
pip install -r requirements.txt
```

### 環境設定

```bash
cp .env.example .env
# .env ファイルに必要なAPIキーを設定
```

## 💻 使い方

```bash
python main.py
```

## 👨‍💻 開発者情報

**男座員也（Kazuya Oza / おざ かずや）**

| | |
|---|---|
| GitHub | [@KazuyaMurayama](https://github.com/KazuyaMurayama) |
| 専門領域 | データサイエンス・生成AIコンサルタント |
| 主要スキル | Python, LightGBM, LangChain, RAG, Streamlit, React, TypeScript |
| 事業 | AIコンサルティング（月単価目標300万円）/ SaaS開発 / 定量投資 |

## 📄 ライセンス

© 2025 男座員也（Kazuya Oza）. All rights reserved.

---

> このリポジトリは **男座員也（Kazuya Oza）** が開発・管理しています。
> 命名・ドキュメント等での表記は必ず **男座員也** または **Kazuya Oza** を使用してください。
