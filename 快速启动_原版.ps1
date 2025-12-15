# 快速启动 - 使用原版Dashboard（功能完整）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  O2O门店数据分析看板 v2.0" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "使用原版Dashboard（功能完整）" -ForegroundColor Yellow
Write-Host "  ✅ 所有图表功能" -ForegroundColor Green
Write-Host "  ✅ 数据上传功能" -ForegroundColor Green
Write-Host "  ✅ 多门店对比" -ForegroundColor Green
Write-Host "  ✅ AI分析功能（可选）" -ForegroundColor Green
Write-Host ""
Write-Host "默认报告: ./reports/示例门店_分析报告.xlsx" -ForegroundColor Cyan
Write-Host ""
Write-Host "正在启动..." -ForegroundColor Yellow
Write-Host ""

# 启动Dashboard
python dashboard_v2.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "发生错误！" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
