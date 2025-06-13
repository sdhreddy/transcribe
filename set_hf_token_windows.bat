@echo off
echo Setting HuggingFace token for voice discrimination feature...
echo.
echo You need a HuggingFace token to use the voice discrimination feature.
echo Get your token from: https://huggingface.co/settings/tokens
echo.
set /p HF_TOKEN="Enter your HuggingFace token: "
echo %HF_TOKEN% > "%USERPROFILE%\huggingface_token.txt"
setx HF_TOKEN "%HF_TOKEN%"
echo.
echo Token saved to %USERPROFILE%\huggingface_token.txt
echo Token also set as environment variable HF_TOKEN
echo.
echo You can now use the voice enrollment script:
echo python scripts\make_voiceprint.py --record
echo.
pause