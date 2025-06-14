@echo off
echo Installing PyAudio for Windows...
echo.

REM Check if pipwin is installed
pip show pipwin >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing pipwin...
    pip install pipwin
)

echo.
echo Installing PyAudio using pipwin...
pipwin install pyaudio

echo.
echo PyAudio installation complete!
pause