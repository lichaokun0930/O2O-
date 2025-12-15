@echo off
chcp 65001 >nul
echo ========================================
echo   安装Dashboard依赖包
echo ========================================
echo.
echo 正在安装依赖，请稍候...
echo.

pip install -r requirements_dashboard.txt

echo.
echo ========================================
if %ERRORLEVEL% EQU 0 (
    echo ✅ 依赖安装成功！
    echo.
    echo 现在可以运行:
    echo   python dashboard_v2_optimized.py
) else (
    echo ❌ 依赖安装失败
    echo.
    echo 请检查网络连接或手动安装:
    echo   pip install dash pandas plotly numpy openpyxl
)
echo ========================================
echo.
pause
