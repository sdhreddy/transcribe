@echo off
REM One-time script to save API key for future use
echo ========================================
echo SAVE API KEY FOR FUTURE USE
echo ========================================
echo.

REM Check if override.yaml exists
if not exist app\transcribe\override.yaml (
    echo ERROR: app\transcribe\override.yaml not found!
    echo Please create it first with your API key
    pause
    exit /b 1
)

REM Check if API key is set
findstr /C:"api_key:" app\transcribe\override.yaml | findstr /V /C:"null" | findstr /V /C:"YOUR_API_KEY" >nul
if %errorlevel% neq 0 (
    echo ERROR: No valid API key found in override.yaml!
    echo Please add your API key first:
    echo.
    echo OpenAI:
    echo   api_key: your-actual-api-key-here
    echo.
    pause
    exit /b 1
)

REM Create backup
echo Found API key in override.yaml
echo Creating permanent backup...
copy /Y app\transcribe\override.yaml override.yaml.backup
echo.
echo SUCCESS! API key saved to: override.yaml.backup
echo.
echo This file will be used to restore your API key after git pulls.
echo Keep this file safe and don't commit it to git!
echo.
echo From now on, use: git_pull_preserve_key.bat
echo Instead of: git pull
echo.
pause