@echo off
chcp 65001 >nul
echo ==========================================
echo     视频超分辨率重建系统 - Web界面
echo ==========================================
echo.

echo 正在启动Streamlit服务...
echo 请在浏览器中打开显示的地址
echo.

streamlit run app.py --server.port 8501 --server.address 0.0.0.0

pause
