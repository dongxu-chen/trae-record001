@echo off
echo ========================================
echo   导入示例数据
echo ========================================
echo.

cd /d "%~dp0backend"

if exist "venv" (
    call venv\Scripts\activate
)

echo 确保后端服务已启动...
echo.

python sample_data.py

echo.
echo 示例数据导入完成！
pause
