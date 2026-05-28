@echo off
echo 正在启动数据库连接池优化工具后端服务...
echo.

mvn spring-boot:run

if %errorlevel% neq 0 (
    echo.
    echo 启动失败，请检查 Maven 和 Java 环境
    pause
)
