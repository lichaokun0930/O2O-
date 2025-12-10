@echo off
chcp 65001 > nul
title O2O门店数据分析看板 v2.2 - 静默启动

echo.
echo ========================================
echo   O2O门店数据分析看板 v2.2
echo   静默模式启动（已抑制控制台警告）
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查虚拟环境...
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在！
    echo 请先运行: python -m venv .venv
    pause
    exit /b 1
)

echo [2/3] 检查数据文件...
if not exist "reports\竞对分析报告_v3.4_FINAL.xlsx" (
    echo [警告] 主数据文件不存在！
)

echo [3/3] 启动Dashboard...
echo.
echo ✅ 访问地址:
echo    本地: http://localhost:8055
echo    局域网: http://119.188.71.47:8055
echo    外网: https://2bn637md7241.vicp.fun
echo.
echo 💡 提示: 浏览器控制台的React警告已被抑制
echo 💡 按 Ctrl+C 可停止服务
echo.

REM 2>&1 重定向stderr到stdout，然后通过findstr过滤掉不需要的警告
.\.venv\Scripts\python.exe dashboard_v2.py 2>&1 | findstr /V /C:"componentWillMount" /C:"componentWillReceiveProps" /C:"React DevTools"

pause
