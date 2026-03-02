@echo off
REM ============================================================
REM install_task_scheduler.bat
REM
REM Windows タスクスケジューラに毎朝6:00実行のタスクを登録する。
REM 管理者権限で実行してください。
REM ============================================================

setlocal enabledelayedexpansion

echo =========================================
echo AI News Collector Bot - タスクスケジューラ設定
echo =========================================
echo.

REM --- 管理者権限チェック ---
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 管理者権限が必要です。
    echo         このファイルを右クリックして
    echo         「管理者として実行」を選んでください。
    echo.
    pause
    exit /b 1
)

REM --- プロジェクトルートの特定 ---
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

set "TASK_NAME=AI_News_Collector_Bot"
set "BAT_PATH=%PROJECT_ROOT%\scripts\run_daily.bat"

echo プロジェクトルート: %PROJECT_ROOT%
echo バッチファイル: %BAT_PATH%
echo タスク名: %TASK_NAME%
echo.

REM --- バッチファイルの存在チェック ---
if not exist "%BAT_PATH%" (
    echo [ERROR] run_daily.bat が見つかりません: %BAT_PATH%
    pause
    exit /b 1
)

REM --- 既存タスクの削除（重複防止） ---
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] 既存のタスクを削除しています...
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
)

REM --- タスクの作成（毎日06:00 JST） ---
schtasks /Create ^
    /TN "%TASK_NAME%" ^
    /TR "\"%BAT_PATH%\"" ^
    /SC DAILY ^
    /ST 06:00 ^
    /RL HIGHEST ^
    /F

if %ERRORLEVEL% equ 0 (
    echo.
    echo =========================================
    echo [OK] タスクスケジューラに登録しました！
    echo =========================================
    echo.
    echo   タスク名:   %TASK_NAME%
    echo   実行時刻:   毎日 06:00
    echo   実行内容:   %BAT_PATH%
    echo.
    echo 確認方法:
    echo   1. Windows キーを押して「タスクスケジューラ」と検索
    echo   2. タスクスケジューラライブラリに
    echo      「%TASK_NAME%」があることを確認
    echo.
    echo 注意:
    echo   - PCがスリープ中は実行されません
    echo   - PCの電源が入っていて、ログインした状態が必要です
    echo.
) else (
    echo.
    echo [ERROR] タスクの登録に失敗しました。
    echo         管理者権限で実行しているか確認してください。
)

pause
endlocal
