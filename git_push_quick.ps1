# ===================================
# Git 快速推送脚本 (精简版)
# ===================================

$ErrorActionPreference = "Stop"

# 获取提交信息（可选参数）
param(
    [string]$Message = ""
)

# 如果没有提供消息，使用默认消息
if ([string]::IsNullOrWhiteSpace($Message)) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Message = "更新代码 - $timestamp"
}

Write-Host "🚀 开始推送..." -ForegroundColor Cyan

# 添加所有文件
git add .
Write-Host "✅ 文件已添加" -ForegroundColor Green

# 提交
$commitResult = git commit -m "$Message" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 提交完成: $Message" -ForegroundColor Green
} elseif ($commitResult -match "nothing to commit") {
    Write-Host "ℹ️  没有需要提交的变更" -ForegroundColor Yellow
} else {
    Write-Host "❌ 提交失败: $commitResult" -ForegroundColor Red
    pause
    exit 1
}

# 推送
$branch = git branch --show-current
$pushResult = git push origin $branch 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 推送成功到 $branch 分支!" -ForegroundColor Green
} else {
    Write-Host "❌ 推送失败: $pushResult" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "完成! 按任意键退出..." -ForegroundColor Yellow
pause
