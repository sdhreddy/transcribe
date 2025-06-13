@echo off
echo ========================================
echo Voice Discrimination Testing Suite
echo ========================================
echo.

REM Check if virtual environment is activated
if "%VIRTUAL_ENV%"=="" (
    echo Activating virtual environment...
    call venv\Scripts\activate
)

REM Check for my_voice.npy
if not exist "my_voice.npy" (
    echo ERROR: Voice profile my_voice.npy not found!
    echo Please run: python scripts\make_voiceprint.py --record
    pause
    exit /b 1
)

REM Check for voice_recordings directory
if not exist "voice_recordings" (
    echo ERROR: voice_recordings directory not found!
    echo Please create the directory and add test audio files
    pause
    exit /b 1
)

echo Running voice discrimination tests...
echo.

REM Run the test suite
python tests\voice_discrimination\run_voice_tests.py

echo.
echo ========================================
echo To tune the threshold, run:
echo python tests\voice_discrimination\tune_voice_threshold.py --plot
echo ========================================
echo.

pause