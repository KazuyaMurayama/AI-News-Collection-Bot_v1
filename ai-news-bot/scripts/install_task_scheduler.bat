@echo off
REM ============================================================
REM install_task_scheduler.bat
REM
REM Register a daily 06:00 task in Windows Task Scheduler.
REM Run this as Administrator.
REM ============================================================

setlocal enabledelayedexpansion

echo =========================================
echo AI News Collector Bot - Task Scheduler Setup
echo =========================================
echo.

REM --- Admin check ---
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Administrator privileges required.
    echo         Right-click this file and select
    echo         "Run as administrator"
    echo.
    pause
    exit /b 1
)

REM --- Project root ---
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

set "TASK_NAME=AI_News_Collector_Bot"
set "BAT_PATH=%PROJECT_ROOT%\scripts\run_daily.bat"

echo Project Root: %PROJECT_ROOT%
echo Batch File:   %BAT_PATH%
echo Task Name:    %TASK_NAME%
echo.

REM --- Check run_daily.bat exists ---
if not exist "%BAT_PATH%" (
    echo [ERROR] run_daily.bat not found: %BAT_PATH%
    pause
    exit /b 1
)

REM --- Remove existing task ---
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] Removing existing task...
    schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
)

REM --- Create task (daily at 06:00) ---
schtasks /Create /TN "%TASK_NAME%" /TR "\"%BAT_PATH%\"" /SC DAILY /ST 06:00 /RL HIGHEST /F

if %ERRORLEVEL% equ 0 (
    echo.
    echo =========================================
    echo [OK] Task registered successfully!
    echo =========================================
    echo.
    echo   Task Name:  %TASK_NAME%
    echo   Schedule:   Daily at 06:00
    echo   Action:     %BAT_PATH%
    echo.
    echo To verify:
    echo   1. Press Windows key, search "Task Scheduler"
    echo   2. Look for "%TASK_NAME%" in Task Scheduler Library
    echo.
    echo Note:
    echo   - PC must be powered on and logged in
    echo   - Will NOT run during sleep mode
    echo.
) else (
    echo.
    echo [ERROR] Failed to register task.
    echo         Make sure you are running as Administrator.
)

pause
endlocal
