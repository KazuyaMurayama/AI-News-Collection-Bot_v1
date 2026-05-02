#!/usr/bin/env bash
# ============================================================
# uninstall_cron.sh - AI News Collector Bot cron 削除スクリプト
#
# install_cron.sh で登録された cron ジョブを削除する。
# ============================================================

set -euo pipefail

CRON_MARKER="# ai-news-bot-daily"

echo "========================================="
echo "AI News Collector Bot - cron 削除"
echo "========================================="

EXISTING_CRON=$(crontab -l 2>/dev/null || true)

if echo "${EXISTING_CRON}" | grep -qF "${CRON_MARKER}"; then
    # マーカー付きのジョブを除去
    NEW_CRON=$(echo "${EXISTING_CRON}" | grep -vF "${CRON_MARKER}")
    echo "${NEW_CRON}" | sed '/^$/d' | crontab - 2>/dev/null || crontab -r 2>/dev/null || true
    echo "[OK] cron ジョブを削除しました。"
else
    echo "[INFO] AI News Bot の cron ジョブは登録されていません。"
fi

echo ""
echo "--- 現在の crontab ---"
crontab -l 2>/dev/null || echo "(crontab is empty)"
echo ""
echo "削除完了。"
