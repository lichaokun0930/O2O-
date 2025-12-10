@echo off
chcp 65001 >nul
echo ========================================
echo 🚀 向量检索预热工具
echo ========================================
echo.
echo 📝 说明:
echo   - 首次启用需下载模型(约420MB, 5-10分钟)
echo   - 后续启动即可使用向量检索(3秒内)
echo   - 模型会永久缓存,无需重复下载
echo.
echo ⏳ 开始预热向量检索模块...
echo.

cd /d "%~dp0"
.\.venv\Scripts\python.exe -c "from ai_knowledge_retriever import get_knowledge_retriever; retriever = get_knowledge_retriever(); print('\n✅ 向量检索预热成功!'); print('💡 现在可以在 ai_analyzer.py 中设置 VECTOR_RETRIEVAL_ENABLED = True')"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo ✅ 预热完成!
    echo ========================================
    echo.
    echo 📋 下一步:
    echo   1. 打开 ai_analyzer.py
    echo   2. 找到第16行: VECTOR_RETRIEVAL_ENABLED = False
    echo   3. 改为: VECTOR_RETRIEVAL_ENABLED = True
    echo   4. 保存文件,重启Dashboard即可
    echo.
) else (
    echo.
    echo ❌ 预热失败,请检查网络连接
    echo.
)

pause
