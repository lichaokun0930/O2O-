# Gradio Dashboard Launcher
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Gradio Dashboard Launcher" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Green

# Stop existing Python processes
Write-Host "Stopping existing processes..." -ForegroundColor Yellow
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Set location
Set-Location "D:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析"

Write-Host "Starting Gradio application..." -ForegroundColor Green
Write-Host "`nAccess at: http://localhost:7880`n" -ForegroundColor Cyan

# Start application
& "D:\办公\Python\python.exe" gradio_demo_working.py

Write-Host "`nApplication stopped." -ForegroundColor Yellow
pause
