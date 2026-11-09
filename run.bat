@echo off
TITLE AI Invoice Processing & Internal Purchase Record System
COLOR 0A

echo =======================================================================
echo     AI INVOICE PROCESSING & INTERNAL PURCHASE RECORD APPLICATION
echo =======================================================================
echo.

REM Verify Python Installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please download and install Python from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking environment & dependencies...
if not exist "venv" (
    echo Creating Python virtual environment (venv)...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [2/3] Installing / Updating required packages...
pip install --prefer-binary -r requirements.txt

echo.
echo [3/3] Launching Streamlit Application...
echo The app will open in your default browser at http://localhost:8501
echo Press Ctrl+C in this terminal to stop the server.
echo =======================================================================
echo.

streamlit run app.py

pause
