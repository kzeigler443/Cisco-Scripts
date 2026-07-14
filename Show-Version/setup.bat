@echo off
echo ============================================================
echo  Show Version - Environment Setup
echo ============================================================
echo.

REM Check that Python is installed and accessible
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found. Please install Python 3.7 or higher
    echo and make sure it is added to your system PATH.
    echo.
    echo Download Python at: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Show which Python version will be used
echo Python found:
python --version
echo.

REM Create the virtual environment only if it doesn't already exist
if exist netmiko_env (
    echo Virtual environment already exists, skipping creation.
) else (
    echo Creating virtual environment...
    python -m venv netmiko_env
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Done.
)
echo.

REM Activate the virtual environment and install dependencies
echo Installing dependencies from requirements.txt...
call netmiko_env\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete.
echo ============================================================
echo.
echo To run the script, open a terminal in this folder and run:
echo.
echo     .\netmiko_env\Scripts\activate
echo     python show_version.py
echo.
pause
