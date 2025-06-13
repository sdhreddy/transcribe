@echo off
REM Automatic log synchronization script for Windows/WSL integration
REM This script syncs logs between Windows and WSL environments

echo ========================================
echo Transcribe Log Synchronization Tool
echo ========================================
echo.

REM Set paths - adjust these based on your setup
set WINDOWS_LOG_DIR=%~dp0monitoring_logs
set WSL_LOG_DIR=\\wsl$\Ubuntu\home\sdhre\transcribe\monitoring_logs
set SHARED_LOG_DIR=%~dp0shared_logs
set WSL_SHARED_DIR=\\wsl$\Ubuntu\home\sdhre\transcribe\shared_logs

REM Create directories if they don't exist
if not exist "%WINDOWS_LOG_DIR%" mkdir "%WINDOWS_LOG_DIR%"
if not exist "%SHARED_LOG_DIR%" mkdir "%SHARED_LOG_DIR%"

REM Function to sync logs
:sync_loop
echo [%date% %time%] Syncing logs...

REM Copy from WSL to Windows shared directory
if exist "%WSL_LOG_DIR%" (
    echo Copying WSL logs to shared directory...
    xcopy "%WSL_LOG_DIR%\*.log" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
    xcopy "%WSL_LOG_DIR%\*.json" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
    xcopy "%WSL_LOG_DIR%\*.jsonl" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
    xcopy "%WSL_SHARED_DIR%\*.jsonl" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
    xcopy "%WSL_SHARED_DIR%\*.html" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
)

REM Copy from Windows monitoring_logs to shared directory
if exist "%WINDOWS_LOG_DIR%" (
    echo Copying Windows logs to shared directory...
    xcopy "%WINDOWS_LOG_DIR%\*.log" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
    xcopy "%WINDOWS_LOG_DIR%\*.json" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
    xcopy "%WINDOWS_LOG_DIR%\*.jsonl" "%SHARED_LOG_DIR%\" /Y /D /Q >nul 2>&1
)

REM Copy diagnostics directory if it exists
if exist "%~dp0diagnostics" (
    echo Copying diagnostics...
    xcopy "%~dp0diagnostics\*.*" "%SHARED_LOG_DIR%\diagnostics\" /Y /D /Q /S >nul 2>&1
)

REM Show latest files
echo.
echo Latest log files in shared directory:
echo -------------------------------------
dir "%SHARED_LOG_DIR%\*.log" /B /O-D 2>nul | head -5
dir "%SHARED_LOG_DIR%\*.json" /B /O-D 2>nul | head -5
dir "%SHARED_LOG_DIR%\*.jsonl" /B /O-D 2>nul | head -5
dir "%SHARED_LOG_DIR%\*.html" /B /O-D 2>nul | head -5

REM Wait 5 seconds before next sync
timeout /t 5 /nobreak >nul

REM Continue syncing
goto sync_loop

:end
pause