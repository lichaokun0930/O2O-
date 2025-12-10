@echo off
chcp 65001 >nul
color 0A
cls

echo.
echo ========================================
echo    Dashboard 响应式优化启动器
echo ========================================
echo.

:: 停止旧进程
echo [1/3] 停止旧进程...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul
echo     ✓ 已停止旧进程
echo.

:: 启动Dashboard
echo [2/3] 启动Dashboard...
cd /d "%~dp0"
start "O2O Dashboard" /MIN "D:\办公\Python\python.exe" dashboard_v2.py
timeout /t 3 /nobreak >nul
echo     ✓ Dashboard已启动
echo.

:: 显示访问信息
echo [3/3] 访问地址:
echo.
echo     📊 本地访问: http://localhost:8055
echo     🌐 外网访问: https://2bn637md7241.vicp.fun
echo.
echo ========================================
echo    Dashboard 已后台运行
echo ========================================
echo.
echo     💡 提示:
echo        - 测试响应式: 双击 "测试响应式.html"
echo        - 查看文档: 打开 "响应式优化说明.md"
echo        - F12打开开发者工具查看效果
echo.

pause
