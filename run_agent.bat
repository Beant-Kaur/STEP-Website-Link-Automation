@echo off
title STEP ESG AI Audit Agent
cd /d "%~dp0"
echo ===================================================
echo   Running STEP ESG AI Audit Agent Pipeline
echo ===================================================
echo.
python agent\step_agent.py --all
pause
