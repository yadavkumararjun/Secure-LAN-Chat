@echo off
setlocal
title Secure LAN Chat - Server Launcher

echo ==============================================================================
echo  Starting Secure LAN Chat & File Sharing Server
echo ==============================================================================
echo.

cd /d "%~dp0"

REM 1. Verify Python availability
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from python.org or the Microsoft Store.
    echo.
    pause
    exit /b 1
)

REM 2. Check if frontend build exists, offer to build if missing
if not exist "frontend\dist\index.html" (
    echo [INFO] Compiled frontend dist not found.
    echo Attempting to build frontend with npm...
    if exist "frontend\node_modules" (
        cd frontend
        call npm run build
        cd ..
    ) else (
        echo [WARNING] frontend\node_modules not found. Running npm install first...
        cd frontend
        call npm install
        call npm run build
        cd ..
    )
)

echo.
echo Launching server via Python...
python run_server.py

pause
