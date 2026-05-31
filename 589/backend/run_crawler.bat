@echo off
chcp 65001
echo ========================================
echo    爬虫运行脚本
echo ========================================
echo.

echo 请选择要爬取的平台:
echo [1] 淘宝
echo [2] 京东
echo [3] 拼多多
echo [4] 苏宁
echo [5] 全部平台
echo [6] 生成模拟数据
echo [7] 退出
echo.

set /p choice=请输入选项 (1-7):

if "%choice%"=="1" goto taobao
if "%choice%"=="2" goto jd
if "%choice%"=="3" goto pdd
if "%choice%"=="4" goto suning
if "%choice%"=="5" goto all
if "%choice%"=="6" goto mock
if "%choice%"=="7" goto end

:taobao
echo.
echo 正在爬取淘宝数据...
python -m scripts.run_crawler --platform taobao --keyword "手机"
goto end

:jd
echo.
echo 正在爬取京东数据...
python -m scripts.run_crawler --platform jd --keyword "手机"
goto end

:pdd
echo.
echo 正在爬取拼多多数据...
python -m scripts.run_crawler --platform pdd --keyword "手机"
goto end

:suning
echo.
echo 正在爬取苏宁数据...
python -m scripts.run_crawler --platform suning --keyword "手机"
goto end

:all
echo.
echo 正在爬取全部平台数据...
python -m scripts.run_crawler --all --keyword "手机"
goto end

:mock
echo.
echo 正在生成模拟数据...
python -m scripts.mock_data
goto end

:end
echo.
echo ========================================
echo  操作完成！
echo ========================================
pause
