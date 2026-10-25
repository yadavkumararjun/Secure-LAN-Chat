@echo off
title Secure LAN Chat - One-Time Setup
echo ==============================================================================
echo  SECURE LAN CHAT & FILE SHARING SYSTEM - College Lab Setup
echo ==============================================================================
echo.
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH!
    echo Please install Python 3.10 or higher from https://python.org
    echo Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed.
echo.
echo Installing Python dependencies from backend/requirements.txt...
python -m pip install -r backend/requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install Python dependencies. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo ==============================================================================
echo  [SUCCESS] College Lab Setup Complete!
echo  You can now double-click 'start.bat' to launch the LAN chat server anytime.
echo ==============================================================================
echo.
pause
