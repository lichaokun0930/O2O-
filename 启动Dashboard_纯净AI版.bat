@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo   🚀 启动纯净版AI Dashboard（无业务基因，只用GLM-4-Plus）
echo ============================================================
echo.
echo 📌 说明：
echo    - 已切换到纯净版AI分析器
echo    - 移除了所有复杂的业务基因和向量检索
echo    - 只使用GLM-4-Plus的基础调用
echo    - 分析内容更简洁、直接
echo.
echo 🔧 正在启动...
echo.

cd /d "%~dp0"

REM 检查虚拟环境
if exist ".venv\Scripts\python.exe" (
    echo ✅ 检测到虚拟环境
    .venv\Scripts\python.exe dashboard_v2.py
) else (
    echo ⚠️ 未检测到虚拟环境，使用系统Python
    python dashboard_v2.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Dashboard启动失败！
    echo 请检查：
    echo   1. Python环境是否正确
    echo   2. 依赖包是否安装（pip install -r requirements_dashboard.txt）
    echo   3. ZHIPU_API_KEY环境变量是否设置
    echo.
    pause
) else (
    echo.
    echo ✅ Dashboard已关闭
)
