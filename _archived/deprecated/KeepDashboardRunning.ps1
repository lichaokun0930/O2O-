# Dashboard Auto-Restart Script
# Keeps Dashboard running, auto-restarts if crashed

$CheckInterval = 10

Write-Host ""
Write-Host "========================================"
Write-Host "  Dashboard Guardian Process"
Write-Host "========================================"
Write-Host ""
Write-Host "Check interval: $CheckInterval seconds"
Write-Host "Press Ctrl+C to stop"
Write-Host ""

$restartCount = 0

while ($true) {
    $portListening = Get-NetTCPConnection -LocalPort 8050 -State Listen -ErrorAction SilentlyContinue
    
    if (-not $portListening) {
        $restartCount++
        $timestamp = Get-Date -Format 'HH:mm:ss'
        Write-Host "[$timestamp] WARNING: Dashboard not running, restarting (attempt $restartCount)" -ForegroundColor Yellow
        
        Stop-Process -Name python -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        
        Write-Host "[$timestamp] Starting Dashboard..." -ForegroundColor Green
        
        Set-Location "D:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析"
        Start-Process -FilePath "D:\办公\Python\python.exe" -ArgumentList "dashboard_v2.py" -NoNewWindow
        
        Start-Sleep -Seconds 5
        
        $portListening = Get-NetTCPConnection -LocalPort 8055 -State Listen -ErrorAction SilentlyContinue
        $timestamp = Get-Date -Format 'HH:mm:ss'
        if ($portListening) {
            Write-Host "[$timestamp] SUCCESS: Dashboard started" -ForegroundColor Green
            Write-Host "  Local: http://localhost:8055"
            Write-Host "  Online: https://2bn637md7241.vicp.fun"
            Write-Host ""
        } else {
            Write-Host "[$timestamp] FAILED: Will retry in 10 seconds" -ForegroundColor Red
            Write-Host ""
        }
    } else {
        $timestamp = Get-Date -Format 'HH:mm:ss'
        Write-Host "[$timestamp] Dashboard is running normally" -ForegroundColor Gray
    }
    
    Start-Sleep -Seconds $CheckInterval
}
