@echo off
REM ============================================================
REM run_daily.bat - AI News Collector Bot 実行バッチファイル
REM
REM Windows 環境で仮想環境を有効化して main.py を実行する。
REM タスクスケジューラからの自動実行にも手動実行にも対応。
REM ============================================================

setlocal enabledelayedexpansion

REM --- プロジェクトルートの特定 ---
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo =========================================
echo AI News Collector Bot - 実行
echo =========================================
echo プロジェクトルート: %PROJECT_ROOT%
echo 実行日時: %date% %time%
echo.

REM --- ログディレクトリの作成 ---
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

REM --- 仮想環境の検出とアクティベート ---
set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"

if exist "%VENV_ACTIVATE%" (
    echo [INFO] 仮想環境を有効化しています...
    call "%VENV_ACTIVATE%"
    set "PYTHON_BIN=python"
) else (
    echo [WARN] 仮想環境が見つかりません。システムのPythonを使用します。
    set "PYTHON_BIN=python"
)

REM --- 実行 ---
cd /d "%PROJECT_ROOT%"
set "PYTHONPATH=%PROJECT_ROOT%"

echo [INFO] パイプラインを実行中...
echo.

%PYTHON_BIN% -m src.main %*

set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE% equ 0 (
    echo [OK] 実行が正常に完了しました。
) else (
    echo [ERROR] 実行がエラーコード %EXIT_CODE% で終了しました。
)

endlocal
exit /b %EXIT_CODE%
