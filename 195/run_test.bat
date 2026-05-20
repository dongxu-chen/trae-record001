@echo off
chcp 65001
cd /d "%~dp0"
echo Running test_imports.py...
python test_imports.py
pause
