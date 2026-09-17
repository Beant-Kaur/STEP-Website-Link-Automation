@echo off
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
set "PROJECT_DIR=%PROJECT_ROOT%step_esg_pipeline"
cd /d "%PROJECT_DIR%"

set "PORT=8080"
set "REPORT=report.json"

where wt.exe >nul 2>&1
if %errorlevel% equ 0 (
    start "STEP ESG - Backend" wt.exe new-tab -d "%PROJECT_DIR%" python dashboard\server.py --port %PORT% --report %REPORT%
) else (
    start "STEP ESG - Backend" cmd /c "cd /d "%PROJECT_DIR%" && python dashboard\server.py --port %PORT% --report %REPORT%"
)

timeout /t 3 /nobreak >nul

set "HEALTHY=0"
for /l %%i in (1,1,20) do (
    powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:%PORT%/api/status' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if !errorlevel! equ 0 (
        set "HEALTHY=1"
        goto :ready
    )
    timeout /t 1 /nobreak >nul
)

:ready
if %HEALTHY%==1 (
    start "STEP ESG - Dashboard" http://localhost:%PORT%/dashboard/?report=%REPORT%
) else (
    echo.
    echo Server did not start correctly.
    echo Open http://localhost:%PORT%/dashboard/?report=%REPORT% manually after checking the backend window.
    pause
)

endlocal
