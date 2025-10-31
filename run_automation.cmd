@echo off
SET ENV_NAME=.venv

REM Create the virtual environment if it doesn't exist
IF NOT EXIST "%ENV_NAME%\Scripts\activate.bat" (
    echo Creating virtual environment: %ENV_NAME%
    uv venv "%ENV_NAME%" --python 3.13
)

REM Activate the virtual environment
call "%ENV_NAME%\Scripts\activate.bat"

REM Install dependencies from requirements.txt
echo Installing dependencies...
uv sync

REM Run the BTD6 automation bot
echo Starting BTD6 Automation Bot...
echo %time%
python main.py
