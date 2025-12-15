# 启动Dashboard（开发模式 - 支持热重载）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  O2O Dashboard v2.0 (开发模式)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "功能特性:" -ForegroundColor Yellow
Write-Host "  ✅ 热重载 (代码修改后自动刷新)" -ForegroundColor Green
Write-Host "  ✅ ECharts图表组件" -ForegroundColor Green
Write-Host "  ✅ 数据缓存" -ForegroundColor Green
Write-Host ""
Write-Host "💡 提示: 修改代码后，浏览器会自动刷新" -ForegroundColor Magenta
Write-Host "💡 如果没有自动刷新，请手动刷新浏览器(F5)" -ForegroundColor Magenta
Write-Host ""

# 激活虚拟环境
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "激活虚拟环境..." -ForegroundColor Yellow
    & .\.venv\Scripts\Activate.ps1
}

# 设置环境变量启用热重载
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "1"

Write-Host "正在启动（热重载模式）..." -ForegroundColor Yellow
Write-Host ""

python dashboard_v2.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "发生错误！" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "查看日志: logs/dashboard.log" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "按回车键退出"
