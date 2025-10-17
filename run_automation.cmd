@echo off
SET ENV_NAME=btd6env

REM Create the virtual environment if it doesn't exist
IF NOT EXIST "%ENV_NAME%\Scripts\activate.bat" (
    echo Creating virtual environment: %ENV_NAME%
    python -m venv "%ENV_NAME%"
)

REM Activate the virtual environment
call "%ENV_NAME%\Scripts\activate.bat"

REM Install dependencies from requirements.txt
echo Installing dependencies...
pip install -r requirements.txt -q

REM Run the BTD6 automation bot
echo Starting BTD6 Automation Bot...
python main.py