@echo off
TITLE Skate Contest - Control Server
color 0A

echo ===================================================
echo      SKATE CONTEST - REAL-TIME SCORING SYSTEM
echo ===================================================
echo.

echo [1/3] Checking dependencies...
:: Installs missing dependencies silently. Upgrade if needed.
pip install -r requirements.txt -q

echo.
echo [2/3] Retrieving Local IP Address for Judges...
:: Magic command to extract the IPv4 address on Windows
for /f "tokens=14" %%a in ('ipconfig ^| findstr IPv4') do set _IPAddress=%%a

echo.
echo ===================================================
echo   CONNECT YOUR DEVICES TO THE SAME WI-FI NETWORK
echo ===================================================
echo.
echo   [ Control Room ] : http://localhost:8000
echo   [ Judges Pad ]   : http://%_IPAddress%:8000/#/judge
echo   [ ScoreBoard ]   : http://%_IPAddress%:8000/#/board
echo.
echo ===================================================
echo.

echo [3/3] Starting the backend server...
cd backend

:: Wait 2 seconds to ensure the server starts, then open the browser
timeout /t 2 /nobreak > nul
start "" http://localhost:8000

:: Start Uvicorn.
:: --host 0.0.0.0 is CRUCIAL: it allows incoming LAN connections!
python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
