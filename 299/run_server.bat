@echo off
cd /d "%~dp0"
echo Starting AQI Forecast Visualization Server...
echo.
cd backend
python app.py
pause
