@echo off
echo Starting Nixie's Trading Bot...
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install/Update dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.template to .env and configure it.
    echo.
    pause
    exit /b 1
)

REM Create necessary directories
if not exist "data\" mkdir data
if not exist "logs\" mkdir logs
if not exist "models\" mkdir models

REM Run the bot
echo.
echo ================================
echo   STARTING TRADING BOT
echo ================================
echo.
python main.py

REM Keep window open if error occurs
if errorlevel 1 (
    echo.
    echo ERROR: Bot crashed! Check logs/nixie_bot.log for details.
    pause
)