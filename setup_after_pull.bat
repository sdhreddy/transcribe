@echo off
REM Automated setup script after git pull
echo ========================================
echo POST-PULL SETUP SCRIPT
echo ========================================
echo.

REM 1. Check if we have a backup of override.yaml
if exist override.yaml.backup (
    echo Found API key backup!
    copy /Y override.yaml.backup app\transcribe\override.yaml
    echo Restored API key to override.yaml
) else (
    echo No API key backup found.
    echo Please create override.yaml.backup with your API key
)

REM 2. Create backup if override.yaml exists but no backup
if exist app\transcribe\override.yaml (
    if not exist override.yaml.backup (
        echo Creating backup of current override.yaml...
        copy app\transcribe\override.yaml override.yaml.backup
        echo Backup created: override.yaml.backup
    )
)

REM 3. Verify API key is set
echo.
echo Checking API key...
findstr /C:"api_key:" app\transcribe\override.yaml | findstr /V /C:"null" | findstr /V /C:"YOUR_API_KEY" >nul
if %errorlevel% equ 0 (
    echo [OK] API key is set in override.yaml
) else (
    echo [WARNING] API key not found or invalid!
    echo.
    echo Please update app\transcribe\override.yaml with:
    echo OpenAI:
    echo   api_key: your-actual-api-key-here
    echo.
    pause
)

REM 4. Run any other setup needed
echo.
echo Setup complete!
echo.
echo To test audio: python test_windows_audio_direct.py
echo To run app: python transcribe.py
echo.
pause