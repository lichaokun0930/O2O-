@echo off
chcp 65001 >nul
title O2O Dashboard - 基础模式

echo ╔══════════════════════════════════════════════════════════╗
echo ║     O2O门店数据分析看板 - 基础模式                       ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 📊 当前模式: 基础GLM分析
echo   ⚡ 启动速度: 快速 (约3秒)
echo   📝 知识注入: 固定3000字符全量业务知识
echo   🎯 适用场景: 日常查看、快速分析
echo   🔧 特点: 标准版,保留扩展性
echo.
echo 💡 对比其他版本:
echo   - 纯GLM版: 极速启动,无向量检索依赖 (启动Dashboard_纯GLM版.bat)
echo   - 基础版 (本版本): 标准模式,平衡性能与扩展
echo   - 增强版: AI智能检索,精准分析 (启动Dashboard_AI增强版.bat)
echo.

REM 确保标准模式(不启用向量检索,不强制纯GLM)
set ENABLE_VECTOR_RETRIEVAL=0
set USE_PURE_GLM=0
set ZHIPU_API_KEY=9f6f4134b7854fff87297a183a6dd0f9.ntVxfTOqYgmr7dCQ

cd /d "%~dp0"
.\.venv\Scripts\python.exe dashboard_v2.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 启动失败,请检查错误信息
    pause
)
