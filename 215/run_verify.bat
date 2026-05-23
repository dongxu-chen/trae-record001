@echo off
echo Running MD simulation verification...
echo.
cd /d "%~dp0"
python verify.py
pause
