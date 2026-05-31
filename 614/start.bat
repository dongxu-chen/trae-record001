@echo off
echo ========================================
echo   汽车油耗预测系统 V3.0 - 启动中
echo ========================================
echo.
echo [V3.0升级特性]
echo   - 行程油耗记录与加油数据校准
echo   - 油耗异常检测与告警
echo   - 车辆健康与故障码影响分析
echo.
echo 正在启动 Streamlit 应用...
echo.
streamlit run app.py --server.port 8501
echo.
pause
