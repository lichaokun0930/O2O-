# -*- coding: utf-8 -*-
"""
AI密钥配置脚本(PowerShell版本)
"""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   GLM-4 AI分析 - API密钥配置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "请输入你的智谱AI API密钥:" -ForegroundColor Yellow
Write-Host "(在 https://open.bigmodel.cn 获取)" -ForegroundColor Gray
Write-Host ""

$apiKey = Read-Host "API密钥"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host ""
    Write-Host "❌ 未输入API密钥,退出配置" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit
}

Write-Host ""
Write-Host "正在设置环境变量..." -ForegroundColor Yellow

try {
    # 设置用户级环境变量(永久生效)
    [System.Environment]::SetEnvironmentVariable("ZHIPU_API_KEY", $apiKey, "User")
    
    # 同时设置当前会话的环境变量(立即生效)
    $env:ZHIPU_API_KEY = $apiKey
    
    Write-Host ""
    Write-Host "✅ API密钥已成功保存!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 重要提示:" -ForegroundColor Cyan
    Write-Host "   1. 当前PowerShell窗口已可直接使用AI功能" -ForegroundColor White
    Write-Host "   2. 其他新打开的窗口需要重启后生效" -ForegroundColor White
    Write-Host "   3. API密钥已安全保存到用户环境变量" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 现在可以运行Dashboard并使用AI智能分析了!" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "❌ 设置失败: $_" -ForegroundColor Red
    Write-Host ""
}

Read-Host "按回车键退出"
