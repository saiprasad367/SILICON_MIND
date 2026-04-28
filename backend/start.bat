@echo off
echo ============================================================
echo  FPGA AI Pilot - Backend Startup
echo ============================================================

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Create venv if not exists
if not exist "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

:: Activate
call venv\Scripts\activate.bat

:: Install dependencies
echo [INFO] Installing Python dependencies...
pip install -q -r requirements.txt

:: Run
echo [INFO] Starting FPGA AI Pilot backend on http://localhost:5000
python app.py
