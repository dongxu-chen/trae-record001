@echo off
echo ========================================
echo  SkyWalking 告警规则优化工具 - 依赖安装
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 安装后端Python依赖...
cd backend
echo.
echo 正在安装Python依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 后端依赖安装失败
    echo 请尝试手动运行: pip install -r backend/requirements.txt
    pause
    exit /b 1
)
echo 后端依赖安装完成!
echo.

cd ..

echo [2/2] 安装前端npm依赖...
cd frontend
echo.
echo 正在安装npm依赖，这可能需要几分钟...
echo 如果遇到权限问题，请关闭杀毒软件后重试
echo.
npm install --legacy-peer-deps
if errorlevel 1 (
    echo.
    echo 警告: 前端依赖安装遇到问题
    echo 请尝试以下方法:
    echo 1. 关闭杀毒软件后重试
    echo 2. 手动删除 node_modules 和 package-lock.json 后重试
    echo 3. 使用 yarn 安装: yarn install
    echo 4. 使用国内镜像: npm config set registry https://registry.npmmirror.com
    echo.
    pause
    exit /b 1
)
echo 前端依赖安装完成!
echo.

cd ..

echo ========================================
echo  所有依赖安装完成!
echo ========================================
echo.
echo 下一步:
echo 1. 启动后端: 双击 start_backend.bat
echo 2. 启动前端: 双击 start_frontend.bat
echo 3. 访问应用: http://localhost:3000
echo.
pause
