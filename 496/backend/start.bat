@echo off
echo ========================================
echo 限流配置推荐工具 - 后端启动脚本
echo ========================================
echo.

where mvn >nul 2>nul
if %errorlevel% equ 0 (
    echo 检测到Maven已安装
    echo 正在编译并启动后端服务...
    echo.
    mvn spring-boot:run
) else (
    echo [警告] 未检测到Maven，请先安装Maven 3.6+
    echo.
    echo 下载地址: https://maven.apache.org/download.cgi
    echo 安装后请重启终端
)

pause
