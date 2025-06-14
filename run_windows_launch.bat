@echo off
REM Windows launch script for transcribe with proper debugging

echo ========================================
echo Streaming TTS Launcher for Windows
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "app\transcribe\main.py" (
    echo ERROR: Please run this from the transcribe root directory
    echo Current directory: %CD%
    exit /b 1
)

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first
    exit /b 1
)

REM Check API key
if not exist "app\transcribe\override.yaml" (
    echo WARNING: override.yaml not found
    echo Please create app\transcribe\override.yaml with your API key
    pause
)

echo.
echo Starting transcribe...
echo Look for [TTS Debug] messages in the console
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

REM Run from correct directory with proper output
cd app\transcribe
python main.py 2>&1
cd ..\..