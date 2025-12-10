@echo off
chcp 65001 >nul
echo ========================================
echo   Git 自动推送
echo ========================================
echo.

REM 运行PowerShell脚本
powershell -ExecutionPolicy Bypass -File "%~dp0git_push.ps1"

echo.
pause
