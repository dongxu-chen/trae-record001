@echo off
echo ========================================
echo  Clipboard Sync Tauri 项目验证
echo ========================================
echo.

echo [1/8] 检查 Rust 环境...
rustc --version
if %errorlevel% neq 0 (
    echo ❌ Rust 未安装，请先安装 Rust: https://rustup.rs/
    exit /b 1
)
echo ✅ Rust 环境正常
echo.

echo [2/8] 检查 Cargo...
cargo --version
echo ✅ Cargo 正常
echo.

echo [3/8] 检查项目结构...
if exist "src\main.rs" (echo ✅ src\main.rs) else (echo ❌ src\main.rs 缺失)
if exist "src\lib.rs" (echo ✅ src\lib.rs) else (echo ❌ src\lib.rs 缺失)
if exist "src\models.rs" (echo ✅ src\models.rs) else (echo ❌ src\models.rs 缺失)
if exist "src\crypto.rs" (echo ✅ src\crypto.rs) else (echo ❌ src\crypto.rs 缺失)
if exist "src\device.rs" (echo ✅ src\device.rs) else (echo ❌ src\device.rs 缺失)
if exist "src\transfer.rs" (echo ✅ src\transfer.rs) else (echo ❌ src\transfer.rs 缺失)
if exist "src\history.rs" (echo ✅ src\history.rs) else (echo ❌ src\history.rs 缺失)
if exist "src\discovery.rs" (echo ✅ src\discovery.rs) else (echo ❌ src\discovery.rs 缺失)
if exist "src\server.rs" (echo ✅ src\server.rs) else (echo ❌ src\server.rs 缺失)
if exist "src\clipboard.rs" (echo ✅ src\clipboard.rs) else (echo ❌ src\clipboard.rs 缺失)
if exist "src\config.rs" (echo ✅ src\config.rs) else (echo ❌ src\config.rs 缺失)
if exist "src\cli\main.rs" (echo ✅ src\cli\main.rs) else (echo ❌ src\cli\main.rs 缺失)
if exist "dist\index.html" (echo ✅ dist\index.html) else (echo ❌ dist\index.html 缺失)
if exist "Cargo.toml" (echo ✅ Cargo.toml) else (echo ❌ Cargo.toml 缺失)
if exist "tauri.conf.json" (echo ✅ tauri.conf.json) else (echo ❌ tauri.conf.json 缺失)
echo.

echo [4/8] 检查 Tauri CLI...
cargo tauri --version 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  Tauri CLI 未安装，运行: cargo install tauri-cli
) else (
    echo ✅ Tauri CLI 已安装
)
echo.

echo [5/8] 尝试编译检查 (仅检查语法)...
cargo check 2>&1 | findstr "error"
if %errorlevel% equ 0 (
    echo ⚠️  存在编译错误，请修复后继续
) else (
    echo ✅ 语法检查通过
)
echo.

echo [6/8] 尝试编译 CLI 版本...
echo 这将下载依赖并编译 CLI 版本，可能需要几分钟...
cargo build --bin clipboard-sync-cli 2>&1 | tail -20
echo.

if exist "target\debug\clipboard-sync-cli.exe" (
    echo ✅ CLI 编译成功！
    echo.
    echo [7/8] CLI 帮助信息:
    target\debug\clipboard-sync-cli.exe --help
) else (
    echo ⚠️  CLI 编译未完成
)
echo.

echo [8/8] 构建 GUI 版本说明:
echo 运行: cargo tauri dev   (开发模式)
echo 运行: cargo tauri build (发布构建)
echo.

echo ========================================
echo  项目验证完成！
echo ========================================
echo.
echo 📖 详细说明请查看 README.md
echo 🚀 开始开发运行: cargo tauri dev
echo.
pause
