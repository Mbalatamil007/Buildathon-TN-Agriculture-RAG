@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
"%~dp0venv\Scripts\python.exe" "%~dp0refresh.py" >> "%~dp0logs\refresh.log" 2>&1
exit /b %errorlevel%
