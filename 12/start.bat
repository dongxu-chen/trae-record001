@echo off
echo Installing dependencies...
call npm install
echo.
echo Starting whiteboard server...
node server.js
pause
