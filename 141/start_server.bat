@echo off
echo ========================================
echo  参数化保险定价引擎 - 启动服务
echo ========================================
echo.
echo 正在启动 FastAPI 服务器...
echo API 文档地址: http://localhost:8000/docs
echo.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
