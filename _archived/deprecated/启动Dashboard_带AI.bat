@echo off
chcp 65001 >nul
echo ========================================
echo    启动Dashboard(带AI智能分析)
echo ========================================
echo.

:: 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo ❌ 虚拟环境不存在
    echo 请先创建虚拟环境
    pause
    exit /b
)

:: 检查zhipuai库
.\.venv\Scripts\python.exe -c "import zhipuai" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 📦 正在安装zhipuai库...
    .\.venv\Scripts\pip.exe install zhipuai
    echo.
)

:: 检查API密钥
.\.venv\Scripts\python.exe -c "import os; exit(0 if os.getenv('ZHIPU_API_KEY') else 1)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️  检测到未配置ZHIPU_API_KEY环境变量
    echo.
    echo 💡 提示:
    echo    1. AI智能分析功能需要API密钥
    echo    2. 可以稍后运行"设置AI密钥.bat"进行配置
    echo    3. 现在先启动Dashboard,其他功能正常可用
    echo.
    choice /C YN /M "是否现在配置API密钥"
    if %ERRORLEVEL% EQU 1 (
        call 设置AI密钥.bat
    )
    echo.
)

echo 🚀 启动Dashboard...
echo.
.\.venv\Scripts\python.exe dashboard_v2.py

pause
