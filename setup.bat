@echo off
echo ===================================================
echo  GeoRank SEO - Dependency Installer
echo ===================================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10 or higher from https://python.org
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment (.venv)...
python -m venv .venv

echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [3/3] Upgrading pip and installing all dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ===================================================
echo  Installation completed successfully!
echo  Run 'run.bat' to start the application.
echo ===================================================
pause
