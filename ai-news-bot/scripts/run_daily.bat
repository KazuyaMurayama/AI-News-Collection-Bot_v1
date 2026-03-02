@echo off
REM ============================================================
REM run_daily.bat - AI News Collector Bot runner for Windows
REM
REM Activates venv and runs main.py.
REM Used by Task Scheduler for daily automatic execution.
REM ============================================================

setlocal enabledelayedexpansion

REM --- Project root ---
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo =========================================
echo AI News Collector Bot - Running
echo =========================================
echo Project Root: %PROJECT_ROOT%
echo Date/Time:    %date% %time%
echo.

REM --- Create logs directory ---
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"

REM --- Activate venv ---
set "VENV_ACTIVATE=%PROJECT_ROOT%\venv\Scripts\activate.bat"

if exist "%VENV_ACTIVATE%" (
    echo [INFO] Activating virtual environment...
    call "%VENV_ACTIVATE%"
    set "PYTHON_BIN=python"
) else (
    echo [WARN] venv not found. Using system Python.
    set "PYTHON_BIN=python"
)

REM --- Run pipeline ---
cd /d "%PROJECT_ROOT%"
set "PYTHONPATH=%PROJECT_ROOT%"

echo [INFO] Running pipeline...
echo.

%PYTHON_BIN% -m src.main %*

set "EXIT_CODE=%ERRORLEVEL%"

echo.
if %EXIT_CODE% equ 0 (
    echo [OK] Completed successfully.
) else (
    echo [ERROR] Exited with code %EXIT_CODE%.
)

endlocal
exit /b %EXIT_CODE%
