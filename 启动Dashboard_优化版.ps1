# PowerShell 启动脚本 - 支持中文
# 使用方法: 右键 -> 使用PowerShell运行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  O2O门店数据分析看板 v2.1 (优化版)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "优化内容:" -ForegroundColor Yellow
Write-Host "  ✅ 删除AI分析模块" -ForegroundColor Green
Write-Host "  ✅ 数据缓存机制 (提升5-10倍加载速度)" -ForegroundColor Green
Write-Host "  ✅ 规范化日志系统" -ForegroundColor Green
Write-Host "  ✅ 修复硬编码列索引" -ForegroundColor Green
Write-Host ""
Write-Host "正在启动..." -ForegroundColor Yellow
Write-Host ""

# 启动Dashboard
python dashboard_v2_optimized.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "发生错误！请查看日志: logs/dashboard.log" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
