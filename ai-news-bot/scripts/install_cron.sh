#!/usr/bin/env bash
# ============================================================
# install_cron.sh - AI News Collector Bot cron 設定スクリプト
#
# 毎朝 6:00 (JST) に main.py を実行する cron ジョブを登録する。
# - 既存の同一ジョブとの重複チェック
# - ログ出力先: logs/cron.log
# ============================================================

set -euo pipefail

# --- プロジェクトルートの特定 ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# --- 設定 ---
PYTHON_BIN="${PROJECT_ROOT}/venv/bin/python"
MAIN_SCRIPT="${PROJECT_ROOT}/src/main.py"
LOG_DIR="${PROJECT_ROOT}/logs"
CRON_LOG="${LOG_DIR}/cron.log"
CRON_MARKER="# ai-news-bot-daily"

echo "========================================="
echo "AI News Collector Bot - cron インストール"
echo "========================================="
echo "プロジェクトルート: ${PROJECT_ROOT}"
echo ""

# --- Python 実行環境のチェック ---
if [ ! -f "${PYTHON_BIN}" ]; then
    echo "[WARN] 仮想環境の Python が見つかりません: ${PYTHON_BIN}"
    echo "       システムの python3 を使用します。"
    PYTHON_BIN="$(command -v python3 2>/dev/null || command -v python 2>/dev/null)"
    if [ -z "${PYTHON_BIN}" ]; then
        echo "[ERROR] Python が見つかりません。インストールしてください。"
        exit 1
    fi
fi
echo "Python: ${PYTHON_BIN}"

# --- main.py の存在チェック ---
if [ ! -f "${MAIN_SCRIPT}" ]; then
    echo "[ERROR] main.py が見つかりません: ${MAIN_SCRIPT}"
    exit 1
fi

# --- ログディレクトリの作成 ---
mkdir -p "${LOG_DIR}"
echo "ログディレクトリ: ${LOG_DIR}"

# --- cron ジョブの定義 ---
CRON_JOB="0 6 * * * TZ=Asia/Tokyo cd ${PROJECT_ROOT} && PYTHONPATH=${PROJECT_ROOT} ${PYTHON_BIN} -m src.main >> ${CRON_LOG} 2>&1 ${CRON_MARKER}"

# --- 既存ジョブとの重複チェック ---
EXISTING_CRON=$(crontab -l 2>/dev/null || true)

if echo "${EXISTING_CRON}" | grep -qF "${CRON_MARKER}"; then
    echo ""
    echo "[INFO] 既存の cron ジョブが見つかりました。置き換えます。"
    # マーカー付きの既存ジョブを除去
    EXISTING_CRON=$(echo "${EXISTING_CRON}" | grep -vF "${CRON_MARKER}")
fi

# --- cron ジョブの登録 ---
NEW_CRON="${EXISTING_CRON}
${CRON_JOB}"

# 空行の重複を除去して登録
echo "${NEW_CRON}" | sed '/^$/d' | crontab -

echo ""
echo "[OK] cron ジョブを登録しました:"
echo "     ${CRON_JOB}"
echo ""
echo "スケジュール: 毎日 06:00 (JST)"
echo "ログ出力先:   ${CRON_LOG}"
echo ""

# --- 実行権限の付与 ---
chmod +x "${MAIN_SCRIPT}" 2>/dev/null || true
chmod +x "${SCRIPT_DIR}/run_once.sh" 2>/dev/null || true

echo "--- 現在の crontab ---"
crontab -l 2>/dev/null || echo "(crontab is empty)"
echo ""
echo "インストール完了。"
