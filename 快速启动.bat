@echo off
chcp 65001 >nul
title O2O Dashboard - 端口 8055
color 0A

echo.
echo ========================================
echo    O2O 门店数据分析看板
echo ========================================
echo.
echo 正在启动 Dashboard...
echo.

cd /d "%~dp0"
"D:\办公\Python\python.exe" dashboard_v2.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo    启动失败！
    echo ========================================
    echo.
    pause
) else (
    echo.
    echo Dashboard 已停止运行
    pause
)
