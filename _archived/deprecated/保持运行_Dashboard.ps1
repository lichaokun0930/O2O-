# Dashboard 守护脚本 - 简化版
# 确保 Dashboard 持续运行，崩溃时自动重启

$CheckInterval = 10  # 检查间隔（秒）

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Dashboard 守护进程" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "监控间隔: ${CheckInterval}秒" -ForegroundColor Yellow
Write-Host "按 Ctrl+C 停止`n" -ForegroundColor Yellow

$restartCount = 0

while ($true) {
    # 检查端口是否在监听
    $portListening = Get-NetTCPConnection -LocalPort 8055 -State Listen -ErrorAction SilentlyContinue
    
    if (-not $portListening) {
        $restartCount++
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ⚠️  Dashboard 未运行，准备重启 (第 ${restartCount} 次)" -ForegroundColor Yellow
        
        # 清理旧进程
        Stop-Process -Name python -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        
        # 启动 Dashboard
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] 🚀 启动 Dashboard..." -ForegroundColor Green
        
        cd "D:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析"
        Start-Process -FilePath "D:\办公\Python\python.exe" -ArgumentList "dashboard_v2.py" -NoNewWindow
        
        Start-Sleep -Seconds 5
        
        # 验证启动
        $portListening = Get-NetTCPConnection -LocalPort 8055 -State Listen -ErrorAction SilentlyContinue
        if ($portListening) {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✅ Dashboard 启动成功" -ForegroundColor Green
            Write-Host "   📊 http://localhost:8055" -ForegroundColor Cyan
            Write-Host "   🌐 https://2bn637md7241.vicp.fun" -ForegroundColor Cyan
            Write-Host ""
        } else {
            Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ❌ 启动失败，10秒后重试" -ForegroundColor Red
            Write-Host ""
        }
    } else {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ✅ Dashboard 运行正常" -ForegroundColor Gray
    }
    
    Start-Sleep -Seconds $CheckInterval
}
