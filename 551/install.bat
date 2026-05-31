@echo off
echo ========================================
echo 实时语音转文字字幕系统 - 环境安装
echo ========================================
echo.

echo [1/3] 安装Python依赖...
cd backend-python
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Python依赖安装失败，请检查pip是否正常工作
    pause
    exit /b 1
)
cd ..
echo Python依赖安装完成！
echo.

echo [2/3] 安装Node.js后端依赖...
cd backend-node
npm install
if %errorlevel% neq 0 (
    echo Node.js后端依赖安装失败，请检查npm是否正常工作
    pause
    exit /b 1
)
cd ..
echo Node.js后端依赖安装完成！
echo.

echo [3/3] 安装React前端依赖...
cd frontend
npm install
if %errorlevel% neq 0 (
    echo React前端依赖安装失败，请检查npm是否正常工作
    pause
    exit /b 1
)
cd ..
echo React前端依赖安装完成！
echo.

echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 运行 start.bat 启动系统
echo.
pause
