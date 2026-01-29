@echo off
echo Stopping any running server instances...
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /IM python.exe /T 2>nul

echo.
echo Starting IFC Monthly Briefing Server...
echo Please refresh your browser (localhost:8001) after the server starts.
echo.

cd /d "%~dp0backend"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
pause
