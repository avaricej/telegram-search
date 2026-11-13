@echo off
setlocal
cd /d "%~dp0"
if exist "dist\ChatScout\ChatScout.exe" (
    start "" "dist\ChatScout\ChatScout.exe"
    exit /b 0
)
if exist ".venv\Scripts\chat-scout.exe" (
    start "" ".venv\Scripts\chat-scout.exe"
    exit /b 0
)
echo Build not found. See README.md for setup instructions.
pause
