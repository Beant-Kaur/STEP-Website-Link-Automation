@echo off
title Kajabi One-Time MFA Login Helper
cd /d "%~dp0"
echo ===================================================
echo   Launching Kajabi One-Time MFA Login Helper
echo ===================================================
echo.
python kajabi\login.py
pause
