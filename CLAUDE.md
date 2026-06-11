# AI News Collection Bot v1 — Claude Code 運用ルール

AI関連の最新ニュース・論文を自動収集し、要約・タグ付けして配信するボットシステム。Claude API で高精度な日本語要約を生成し、定期的に関係者へ配信。

> **本ファイルは VSCode版 / Web版 Claude Code（claude.ai）の両方で、本リポジトリの単独完結ガイドです。**
> Web版はグローバル `~/.claude/CLAUDE.md` を参照しません。本リポの運用に必要な全ルールをこの1ファイルに集約しています（他リポ・グローバルとの重複は完結性のため許容）。

---

## 1. セッション開始手順（毎回・最初に実行）

セッション開始時、次の順で必ず読み込んでから作業を始める：

1. **本ファイル（CLAUDE.md）** — 前提制約・実行ルール
2. **`tasks.md`** — セッション間引継ぎタスク（次にやること・優先順位）
3. **`FILE_INDEX.md`** — ファイル構成の索引

> 編集前に、ユーザー発話のキーワードを `FILE_INDEX.md` と照合してから対象ファイルを特定する（推測で着手しない）。

---

## 2. 関連リポジトリ

| リポ | 役割 |
|---|---|
| [KazuyaMurayama/AI-News-Collection-Bot_v2](https://github.com/KazuyaMurayama/AI-News-Collection-Bot_v2) | v2 改良版 |
| [KazuyaMurayama/personal-brand-publisher_v1](https://github.com/KazuyaMurayama/personal-brand-publisher_v1) | コンテンツ自動発信（配信先候補） |

---

## 3. 開発者情報・命名ルール

| 種別 | 表記 | 用途 |
|---|---|---|
| **システム識別子（変更不可）** | `KazuyaMurayama` | GitHub ユーザー名 / URL / `@KazuyaMurayama` |
| **システム識別子（変更不可）** | `kazuya.murayama.21@gmail.com` | git `user.email` / 連絡先 |
| **表記名（人間として記載する場合）** | **男座員也（Kazuya Oza / おざ かずや）** | ドキュメント本文の著者名 / コミット message 中の自己言及 |

- ドキュメント本文等で開発者名を**人間として**記載する際は **男座員也 / Kazuya Oza** を使用。
- 「Murayama」「村山」「Otokoza」「おとこざ」を**表記名**として誤用しない（システム識別子 `KazuyaMurayama` の出現は許容）。

---

## 4. ツール実行ルール

- **確認不要・即実行**。「Allow〜?」「Should I…?」等の事前確認文を出力しない。即実行 → 事後報告。
- 長時間処理は積極的にバックグラウンド実行する。
- ファイル操作（編集・検索・読み込み）は専用ツール（Edit/Write/Read/Grep/Glob）を直接使用する。
- **機密情報**: Claude API キー・配信先トークン等は `.env` のみ保管、コミット禁止。
- **例外（事前確認必須）**: main への `git push --force`、`gh repo delete`、その他の不可逆・破壊的操作。

---

## 5. ブランチ管理

- **既定: main へ直接コミット**。ブランチ作成はユーザーが明示指示した場合のみ。
- ブランチを作成した場合（Web版が自動生成した `claude/*` ブランチも含む）、回答完了前に必ず `main` へマージ → ブランチ削除 → push まで完了させる。
  - 手順: `git checkout main; git pull; git merge <branch> --no-ff; git push origin main; git branch -d <branch>`
- 「完了 = main にマージ済み＆push済み」。ブランチにファイルを残したまま回答を終えない。

---

## 6. ファイル保存ルール

- 生成物・スクリプト・中間ファイルはすべて**本リポジトリ内**に保存する。
- `C:\Users\user\Desktop` への出力は禁止（ユーザーが明示した場合のみ例外）。
- 一時スクリプトも本リポ内に作成し、作業後に削除またはコミットする。ログ・コミットメッセージ等の一時ファイルを無断で作らない。

---

## 7. 成果物報告ルール（毎回必須）

ファイルを1つでも作成・更新・push したら、**すべての**成果物を次の3列表で報告する。例外なし。

| 成果物 | 説明 | リンク |
|---|---|---|
| file.py | 1行説明 | [開く](https://github.com/KazuyaMurayama/AI-News-Collection-Bot_v1/blob/main/path/to/file.py) |

**厳守事項**
1. 必ず Markdownリンク `[表示名](URL)` 形式。plain text URL 禁止。
2. `/blob/<実ブランチ>/<実パス>` 形式。リポトップ URL 禁止。
3. **報告前に URL 存在確認**: `gh api repos/KazuyaMurayama/AI-News-Collection-Bot_v1/contents/PATH?ref=main` でステータス200確認。
4. ブランチ名は推測せず `git rev-parse --abbrev-ref HEAD` で実値取得。
5. **push 完了後にのみ URL 生成**。未push ファイルは絶対パス＋「（ローカル）」と明記し、push可否を Next Action に添える。
6. 404 を出したら即訂正版を提示し、原因を1行報告。

---

## 8. ドキュメント命名・日付ルール（v2.0 / 2026-06-03 改訂）

### ファイル名
- 基本形 `<TOPIC>_YYYYMMDD.md`（**サフィックス・ハイフンなし**）。例: `NEWS_REPORT_20260603.md`
- 同日中の追加更新は `-v2`、`-v3`（例: `NEWS_REPORT_20260603-v2.md`）。
- 日付が変わったら v サフィックスをリセット（例: 翌日1回目 `NEWS_REPORT_20260604.md`）。

### 表記の区別
- **ファイル名**: ハイフン**なし** `YYYYMMDD`（例: `20260603`）。
- **本文中の日付**: ハイフン**あり** `YYYY-MM-DD`（例: `2026-06-03`）。

### H1直下の日付メタデータ
レポート系 .md 新規作成時は H1直下に必ず記載し、更新時は **最終更新日のみ** 当日付に書き換える（作成日は固定）：
```
作成日: YYYY-MM-DD
最終更新日: YYYY-MM-DD
```

### 対象外（日付サフィックスを入れない）
README / CLAUDE.md / FILE_INDEX / file_index / tasks.md / CHANGELOG / LICENSE / SPEC.md / `CURRENT_*.md` / パイプライン自動生成ファイル（`outputs/*.md` 等）。

### 旧形式（廃止・新規禁止）
- ❌ `2026-06-03_<TOPIC>.md`（プレフィックス・ハイフン） / ❌ `<TOPIC>_2026-06-03.md`（サフィックス・ハイフン）
- ✅ `<TOPIC>_20260603.md`（現行ルール）

---

## 9. モデル使い分け

- **メイン: Claude Fable 5（`claude-fable-5`）** — 計画・中〜高難易度の実装/分析・全体指揮。
- **実行フェーズ（定型実装・ファイル編集・テスト実行）**: サブエージェントを `model: "sonnet"` で起動して委譲。
- ※難易度ベースの自動メイン切替は不可。Fable の自動切替は安全性ブロック時の Opus 4.8 フォールバックのみ。工程別の使い分けはサブエージェント委譲で行う。

---

## 10. Skill 起動ルール

該当シーンでは、本リポ `.claude/skills/<name>/SKILL.md` を読んでから作業を開始する（**本リポに実在する skill のみ掲載**）。

| トリガー | スキル |
|---|---|
| 新機能・設計の検討開始 | `.claude/skills/sp-brainstorming/SKILL.md` |
| 計画立案 | `.claude/skills/sp-writing-plans/SKILL.md` |
| 計画に沿った実行 | `.claude/skills/sp-executing-plans/SKILL.md` |
| 図表生成（レポート） | `.claude/skills/mermaid-agents365/SKILL.md` |
| 成果物の納品・コミット前チェック | `.claude/skills/sp-verification-before-completion/SKILL.md` |

---

## 11. 回答スタイル

- 日本語で回答する。
- 回答末尾に「**Next Action:**」でユーザーの次アクションを具体的に推奨する。迷う場面は「**推奨:**」で明示する。

---

## 12. コンテキスト管理（自動圧縮対策 / Compact Instructions）

Claude Code はコンテキスト利用率が高まると自動でテキスト要約圧縮（auto-compact, 約83.5%目安）を行う。圧縮で重要情報を失わないため以下を守る。

### 圧縮時に必ず保持する情報（`/compact` 実行・自動圧縮時に要約へ残す）
- 本リポ/タスクの目的・前提制約・現行の意思決定
- 進行中タスクと未解決課題（`tasks.md` の最新状態）
- 正典ファイル・最新成果物への参照（例: SPEC / `CURRENT_*.md` / 最新レポート）
- ファイルスコープ・モジュール境界・命名規則
- 直近のエラー・制約・回避策

### 圧縮の影響を受けない永続層（外部メモリ）に状態を書き出す
- `tasks.md`（次にやること・進捗。セッション終了時に必ず更新）
- `file_index.md` / `FILE_INDEX.md`（索引）、`session.json`（あれば進捗）
- 確定した結論・成果はレポート `.md` に保存（会話履歴に依存させない）

### 運用ルール
- 重い調査・実装はサブエージェントに委譲し、親には要約のみ戻す（コンテキスト分離）
- 利用率が高まったら警告を待たず能動的に `/compact <保持指示>` を実行。別タスクへ移る際は `/clear`（CLAUDE.md・tasks.md は残る）
- ※潜在空間ベクトル圧縮（Codex方式）は公開APIの制約上、本ハーネスでは実装不可。テキスト要約＋外部メモリで代替する
