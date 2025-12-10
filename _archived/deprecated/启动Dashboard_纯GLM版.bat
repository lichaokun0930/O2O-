@echo off
chcp 65001 >nul
title O2O Dashboard - 纯GLM-4.6版本

echo ╔══════════════════════════════════════════════════════════╗
echo ║     O2O门店数据分析看板 - 纯GLM-4.6版本                  ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 📊 当前模式: 纯GLM-4.6分析
echo   ⚡ 启动速度: 极速 (约2秒)
echo   📝 知识注入: 完整3000字符业务知识库
echo   🎯 适用场景: 最纯净版本,无任何额外依赖
echo   🔧 特点: 不加载transformers等重型库
echo.
echo 💡 对比其他版本:
echo   - 纯GLM版 (本版本): 最快,无向量检索依赖
echo   - 基础版 (启动Dashboard.bat): 标准版,保留扩展性
echo   - 增强版 (启动Dashboard_AI增强版.bat): 智能检索,精准分析
echo.

REM 设置环境变量
set ZHIPU_API_KEY=9f6f4134b7854fff87297a183a6dd0f9.ntVxfTOqYgmr7dCQ
set USE_PURE_GLM=1

echo 🚀 正在启动纯GLM版Dashboard...
echo.

cd /d "%~dp0"
.\.venv\Scripts\python.exe dashboard_pure_glm.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ 启动失败,请检查错误信息
    pause
)
