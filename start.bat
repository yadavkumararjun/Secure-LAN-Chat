@echo off
title Secure LAN Chat Server
echo ==============================================================================
echo  SECURE LAN CHAT & FILE SHARING SYSTEM - Server Launcher
echo ==============================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ and run 'setup.bat' first.
    echo.
    pause
    exit /b 1
)

echo Starting Secure LAN Chat Server...
echo Press Ctrl+C anytime to stop the server cleanly.
echo.

python run_server.py

if errorlevel 1 (
    echo.
    echo [NOTICE] If the server failed to start, run 'setup.bat' first to install packages.
    pause
)
