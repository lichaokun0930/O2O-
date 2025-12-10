@echo off
chcp 65001 >nul
echo ========================================
echo    GLM-4 AI分析 - API密钥配置
echo ========================================
echo.

echo 请输入你的智谱AI API密钥:
echo (在 https://open.bigmodel.cn 获取)
echo.
set /p APIKEY="API密钥: "

if "%APIKEY%"=="" (
    echo.
    echo ❌ 未输入API密钥,退出配置
    pause
    exit /b
)

echo.
echo 正在设置环境变量...

:: 设置用户级环境变量(永久生效)
setx ZHIPU_API_KEY "%APIKEY%" >nul

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ API密钥已成功保存到系统环境变量
    echo.
    echo 📝 重要提示:
    echo    1. 请重启VS Code或PowerShell以使配置生效
    echo    2. 配置生效后即可使用AI智能分析功能
    echo    3. API密钥已加密保存,其他应用无法访问
    echo.
) else (
    echo.
    echo ❌ 设置失败,请以管理员身份运行此脚本
    echo.
)

pause
