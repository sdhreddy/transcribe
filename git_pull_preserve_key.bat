@echo off
REM Script to pull changes while preserving API key
echo ========================================
echo GIT PULL WITH API KEY PRESERVATION
echo ========================================
echo.

REM 1. First, backup current override.yaml if it exists
if exist app\transcribe\override.yaml (
    echo Backing up current API key...
    copy /Y app\transcribe\override.yaml override.yaml.backup
    echo Backup saved to: override.yaml.backup
) else (
    echo No override.yaml found to backup
)

REM 2. Stash any local changes
echo.
echo Stashing local changes...
git stash

REM 3. Pull latest changes
echo.
echo Pulling latest changes from GitHub...
git pull origin disc-clean

REM 4. Restore API key
if exist override.yaml.backup (
    echo.
    echo Restoring API key...
    copy /Y override.yaml.backup app\transcribe\override.yaml
    echo API key restored!
) else (
    echo.
    echo WARNING: No API key backup found!
    echo You'll need to manually add your API key to app\transcribe\override.yaml
)

REM 5. Show API key status
echo.
echo Checking API key status...
findstr /C:"api_key:" app\transcribe\override.yaml 2>nul | findstr /V /C:"null" | findstr /V /C:"YOUR_API_KEY" >nul
if %errorlevel% equ 0 (
    echo [SUCCESS] API key is set and ready!
) else (
    echo [WARNING] API key not found or invalid!
    echo Please update app\transcribe\override.yaml
)

echo.
echo ========================================
echo Pull complete! 
echo To test: python test_windows_audio_direct.py
echo To run: python transcribe.py
echo ========================================
pause