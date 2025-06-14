@echo off
echo Installing Streaming TTS dependencies for Windows...
echo.

REM Check if pipwin is installed for PyAudio
echo Installing pipwin for Windows-specific packages...
pip install pipwin

echo.
echo Installing PyAudio via pipwin (Windows pre-built wheel)...
pipwin install pyaudio

echo.
echo Installing other dependencies...
pip install --upgrade openai gtts

echo.
echo Verifying installations...
python -c "import pyaudio; print('PyAudio version:', pyaudio.__version__)"
python -c "import openai; print('OpenAI version:', openai.__version__)"
python -c "import gtts; print('gTTS version:', gtts.__version__)"

echo.
echo Installation complete!
echo.
echo IMPORTANT: Make sure your OPENAI_API_KEY is set in override.yaml
echo.
pause