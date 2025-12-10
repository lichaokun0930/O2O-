@echo off
chcp 65001 >nul
title O2O门店数据分析看板 v2.0 - Gradio版
color 0A

echo.
echo ========================================================================
echo   O2O门店数据分析看板 v2.0 - Gradio版
echo ========================================================================
echo.
echo   🚀 正在启动 Gradio Dashboard...
echo   📊 数据源: ./reports/竞对分析报告_v3.4_FINAL.xlsx
echo   🌐 访问地址: http://localhost:7860
echo.
echo ========================================================================
echo.

cd /d "%~dp0"
"D:\办公\Python\python.exe" gradio_dashboard_full_v2.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 启动失败！错误代码: %ERRORLEVEL%
    echo.
    pause
) else (
    echo.
    echo ✅ Dashboard已关闭
    echo.
    pause
)
