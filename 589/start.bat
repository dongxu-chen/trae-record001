@echo off
chcp 65001
echo ========================================
echo    比价达人 - 商品比价导购平台
echo ========================================
echo.

echo [1/3] 检查后端依赖...
cd backend
pip install -r requirements.txt -q
echo 后端依赖检查完成
echo.

echo [2/3] 初始化数据库...
python -m scripts.init_db
echo 数据库初始化完成
echo.

echo [3/3] 生成模拟数据...
python -m scripts.mock_data
echo 模拟数据生成完成
echo.

echo ========================================
echo  启动服务中...
echo ========================================
echo.

echo 正在启动后端API服务 (端口: 8000)...
start "后端API服务" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo 正在启动前端开发服务 (端口: 5173)...
start "前端开发服务" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo  ✅ 服务启动完成！
echo.
echo  前端地址: http://localhost:5173
echo  后端API: http://localhost:8000
echo  API文档: http://localhost:8000/docs
echo ========================================
echo.
echo 按任意键关闭此窗口（服务将继续运行）...
pause >nul
