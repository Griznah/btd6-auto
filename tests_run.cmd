@echo off
REM Run overlay.py unit tests using pytest (Windows only)
setlocal
set PYTHONPATH=%~dp0
pytest -v tests\
endlocal
