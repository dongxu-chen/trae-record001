@echo off
echo ========================================
echo   信息抽取标注工具 - 启动脚本
echo ========================================
echo.

echo [1/3] 检查Node.js环境...
node --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Node.js，请先安装Node.js
    pause
    exit /b 1
)

echo.
echo [2/3] 安装后端依赖...
cd backend
if not exist "node_modules" (
    npm install
) else (
    echo 后端依赖已安装
)

echo.
echo [3/3] 安装前端依赖...
cd ..\frontend
if not exist "node_modules" (
    npm install
) else (
    echo 前端依赖已安装
)

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo 请按以下步骤启动服务：
echo.
echo 1. 新开一个终端，启动后端:
echo    cd backend
echo    npm start
echo.
echo 2. 再新开一个终端，启动前端:
echo    cd frontend
echo    npm start
echo.
echo 3. 确保MongoDB服务已启动
echo.
echo 访问地址: http://localhost:3000
echo.
pause
