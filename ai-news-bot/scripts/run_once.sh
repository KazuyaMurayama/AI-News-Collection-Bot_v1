#!/usr/bin/env bash
# ============================================================
# run_once.sh - AI News Collector Bot 手動実行スクリプト
#
# 仮想環境を有効化して main.py を1回実行する。
# 追加の引数はそのまま main.py に渡される。
#
# 使用例:
#   ./scripts/run_once.sh                  # 今日の日付で実行
#   ./scripts/run_once.sh --dry-run        # 配信なしで実行
#   ./scripts/run_once.sh --date 2026-02-20
#   ./scripts/run_once.sh --server         # リアクションサーバー起動
# ============================================================

set -euo pipefail

# --- プロジェクトルートの特定 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "========================================="
echo "AI News Collector Bot - 手動実行"
echo "========================================="
echo "プロジェクトルート: ${PROJECT_ROOT}"
echo ""

# --- 仮想環境の検出とアクティベート ---
VENV_DIR="${PROJECT_ROOT}/venv"
ACTIVATE_SCRIPT="${VENV_DIR}/bin/activate"

if [ -d "${VENV_DIR}" ] && [ -f "${ACTIVATE_SCRIPT}" ]; then
    echo "[INFO] 仮想環境を検出しました: ${VENV_DIR}"
    # shellcheck disable=SC1091
    source "${ACTIVATE_SCRIPT}"
    echo "[INFO] 仮想環境を有効化しました"
    PYTHON_BIN="$(command -v python)"
else
    echo "[WARN] 仮想環境が見つかりません: ${VENV_DIR}"
    echo "       システムの Python を使用します。"
    PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
    if [ -z "${PYTHON_BIN}" ]; then
        echo "[ERROR] Python が見つかりません。インストールしてください。"
        exit 1
    fi
fi

echo "Python: ${PYTHON_BIN} ($(${PYTHON_BIN} --version 2>&1))"
echo ""

# --- main.py の存在チェック ---
MAIN_SCRIPT="${PROJECT_ROOT}/src/main.py"
if [ ! -f "${MAIN_SCRIPT}" ]; then
    echo "[ERROR] main.py が見つかりません: ${MAIN_SCRIPT}"
    exit 1
fi

# --- プロジェクトルートに移動して実行 ---
cd "${PROJECT_ROOT}"

echo "実行コマンド: ${PYTHON_BIN} ${MAIN_SCRIPT} $*"
echo "-----------------------------------------"
echo ""

"${PYTHON_BIN}" "${MAIN_SCRIPT}" "$@"

EXIT_CODE=$?

echo ""
echo "-----------------------------------------"
if [ ${EXIT_CODE} -eq 0 ]; then
    echo "[OK] 実行が正常に完了しました。"
else
    echo "[ERROR] 実行がエラーコード ${EXIT_CODE} で終了しました。"
fi

exit ${EXIT_CODE}
