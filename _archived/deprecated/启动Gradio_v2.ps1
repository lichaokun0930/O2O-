# O2O门店数据分析看板 v2.0 - Gradio版 启动脚本
# 使用方式: .\启动Gradio_v2.ps1

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "O2O门店数据分析看板 v2.0 - Gradio版"

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  O2O门店数据分析看板 v2.0 - Gradio版" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  🚀 正在启动 Gradio Dashboard..." -ForegroundColor Yellow
Write-Host "  📊 数据源: ./reports/竞对分析报告_v3.4_FINAL.xlsx" -ForegroundColor Gray
Write-Host "  🌐 访问地址: " -NoNewline -ForegroundColor Gray
Write-Host "http://localhost:7860" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location -Path $PSScriptRoot

try {
    & "D:\办公\Python\python.exe" gradio_dashboard_full_v2.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Dashboard已正常关闭" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "❌ 启动失败！错误代码: $LASTEXITCODE" -ForegroundColor Red
    }
}
catch {
    Write-Host ""
    Write-Host "❌ 发生错误: $_" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
