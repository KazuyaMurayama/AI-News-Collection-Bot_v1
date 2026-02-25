#!/usr/bin/env bash
# ============================================================
# AI News Collector Bot - セットアップスクリプト
# ============================================================
# 使用方法:
#   chmod +x setup.sh
#   ./setup.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
PYTHON_CMD="${PYTHON_CMD:-python3}"

echo "============================================================"
echo " AI News Collector Bot - セットアップ"
echo "============================================================"
echo ""

# --- Python バージョンチェック ---
echo "[1/5] Python バージョンを確認しています..."
if ! command -v "$PYTHON_CMD" &>/dev/null; then
    echo "エラー: $PYTHON_CMD が見つかりません。Python 3.11 以上をインストールしてください。"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$("$PYTHON_CMD" -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$("$PYTHON_CMD" -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]; }; then
    echo "エラー: Python 3.11 以上が必要です（現在: $PYTHON_VERSION）"
    exit 1
fi
echo "  Python $PYTHON_VERSION を使用します。"
echo ""

# --- 仮想環境の作成 ---
echo "[2/5] Python 仮想環境を作成しています..."
if [ -d "$VENV_DIR" ]; then
    echo "  既存の仮想環境が見つかりました。スキップします。"
else
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "  仮想環境を作成しました: $VENV_DIR/"
fi
echo ""

# --- 仮想環境をアクティベート ---
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# --- 依存パッケージのインストール ---
echo "[3/5] 依存パッケージをインストールしています..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "  依存パッケージのインストールが完了しました。"
echo ""

# --- ディレクトリ構造の作成 ---
echo "[4/5] ディレクトリ構造を作成しています..."
directories=(
    "knowledge_base/daily"
    "knowledge_base/monthly"
    "logs"
    "credentials"
    "src/collector"
    "src/writer"
    "src/writer/templates"
    "src/delivery"
    "src/feedback"
    "src/knowledge"
    "src/utils"
    "tests"
    "scripts"
    "docs"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  作成: $dir/"
    fi
done
echo "  ディレクトリ構造の準備が完了しました。"
echo ""

# --- .env ファイルのコピー ---
echo "[5/5] 環境変数ファイルを確認しています..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  .env.example を .env にコピーしました。"
        echo "  ※ .env ファイルを編集して API キーを設定してください。"
    else
        echo "  警告: .env.example が見つかりません。手動で .env を作成してください。"
    fi
else
    echo "  .env ファイルは既に存在します。スキップします。"
fi
echo ""

# --- 完了 ---
echo "============================================================"
echo " セットアップ完了!"
echo "============================================================"
echo ""
echo "次のステップ:"
echo "  1. .env ファイルを編集して API キーを設定してください"
echo "     vi .env"
echo ""
echo "  2. config.yaml を確認・カスタマイズしてください"
echo "     vi config.yaml"
echo ""
echo "  3. 仮想環境をアクティベートして実行してください"
echo "     source $VENV_DIR/bin/activate"
echo ""
echo "  4. テストを実行して動作確認してください"
echo "     pytest tests/"
echo ""
