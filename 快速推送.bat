@echo off
chcp 65001 >nul
echo 🚀 快速推送到Git...
echo.

REM 运行快速推送脚本
powershell -ExecutionPolicy Bypass -File "%~dp0git_push_quick.ps1"
