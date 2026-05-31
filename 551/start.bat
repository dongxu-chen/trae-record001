@echo off
echo ========================================
echo 实时语音转文字字幕系统 - 启动中
echo ========================================
echo.

echo [1/3] 启动Python语音识别服务...
start "Python Speech Recognition" cmd /k "cd backend-python && python speech_recognizer.py"
timeout /t 2 /nobreak > nul
echo Python语音识别服务已启动！
echo.

echo [2/3] 启动Node.js WebSocket服务器...
start "Node.js WebSocket Server" cmd /k "cd backend-node && npm start"
timeout /t 2 /nobreak > nul
echo Node.js WebSocket服务器已启动！
echo.

echo [3/3] 启动React前端...
start "React Frontend" cmd /k "cd frontend && npm start"
echo React前端已启动！
echo.

echo ========================================
echo 系统启动完成！
echo ========================================
echo.
echo 服务地址：
echo - Python WebSocket: ws://localhost:8765
echo - Node.js Server:   ws://localhost:3001
echo - React Frontend:   http://localhost:3000
echo.
echo 请在浏览器中打开 http://localhost:3000 查看字幕
echo.
echo 注意：请确保麦克风已连接并授权
echo.
pause
