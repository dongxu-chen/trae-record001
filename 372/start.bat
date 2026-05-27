@echo off
echo Starting Image Segmentation Annotation Tool...
echo.

echo [1/2] Starting FastAPI backend server...
start "Backend Server" cmd /k "cd server && python main.py"

timeout /t 3 /nobreak > nul

echo.
echo [2/2] Starting React dev server...
start "Frontend Server" cmd /k "cd client && npm run dev"

echo.
echo Both servers started!
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo.
pause
