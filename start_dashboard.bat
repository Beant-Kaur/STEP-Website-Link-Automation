@echo off
title STEP ESG Compliance Dashboard
cd /d "%~dp0"
echo ===================================================
echo   Starting STEP ESG Compliance Dashboard Server
echo ===================================================
echo.
python dashboard\server.py --port 8080 --open
pause
