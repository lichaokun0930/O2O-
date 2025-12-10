# Git自动推送脚本
# 仓库: https://github.com/lichaokun0930/O2O-.git

$ErrorActionPreference = "Stop"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "  Git推送脚本" "Cyan"
Write-ColorOutput "  时间: $timestamp" "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

# 查找Git根目录
$current = Get-Location
$found = $false
while ($true) {
    if (Test-Path (Join-Path $current ".git")) {
        Set-Location $current
        Write-ColorOutput "Git根目录: $current" "Cyan"
        $found = $true
        break
    }
    $parent = Split-Path $current -Parent
    if (-not $parent -or $parent -eq $current) {
        break
    }
    $current = $parent
}

if (-not $found) {
    Write-ColorOutput "错误: 未找到Git仓库" "Red"
    pause
    exit 1
}
Write-Host ""

# 检查状态
Write-ColorOutput "检查Git状态..." "Yellow"
$status = git status --porcelain
if ($status) {
    Write-ColorOutput "检测到文件变更:" "Green"
    git status --short
} else {
    Write-ColorOutput "没有检测到文件变更" "Yellow"
    $continue = Read-Host "是否继续? (y/n)"
    if ($continue -ne "y") {
        exit 0
    }
}
Write-Host ""

# 添加文件
Write-ColorOutput "添加文件..." "Yellow"
$addResult = git add . 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "文件添加成功" "Green"
} else {
    Write-ColorOutput "添加失败: $addResult" "Red"
    pause
    exit 1
}
Write-Host ""

# 获取提交信息
Write-ColorOutput "请输入提交信息 (留空使用默认):" "Yellow"
$commitMessage = Read-Host "提交信息"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "更新代码 - $timestamp"
    Write-ColorOutput "使用默认信息: $commitMessage" "Cyan"
}
Write-Host ""

# 提交
Write-ColorOutput "提交变更..." "Yellow"
$commitResult = git commit -m "$commitMessage" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "提交成功" "Green"
} elseif ($commitResult -match "nothing to commit") {
    Write-ColorOutput "没有需要提交的变更" "Yellow"
} else {
    Write-ColorOutput "提交失败: $commitResult" "Red"
    pause
    exit 1
}
Write-Host ""

# 获取当前分支
$currentBranch = git branch --show-current
Write-ColorOutput "当前分支: $currentBranch" "Cyan"
Write-Host ""

# 推送
Write-ColorOutput "推送到远程仓库..." "Yellow"
$pushResult = git push origin $currentBranch 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "推送成功!" "Green"
} else {
    Write-ColorOutput "推送失败: $pushResult" "Red"
    Write-Host ""
    Write-ColorOutput "可能原因:" "Yellow"
    Write-ColorOutput "1. 网络问题" "White"
    Write-ColorOutput "2. 未配置远程仓库" "White"
    Write-ColorOutput "3. 认证失败" "White"
    Write-Host ""
    Write-ColorOutput "尝试添加远程仓库..." "Yellow"
    $remoteResult = git remote add origin https://github.com/lichaokun0930/O2O-.git 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "远程仓库已添加，请重新运行" "Green"
    } else {
        Write-ColorOutput "远程仓库可能已存在" "Yellow"
    }
    pause
    exit 1
}

Write-Host ""
Write-ColorOutput "========================================" "Green"
Write-ColorOutput "  推送完成!" "Green"
Write-ColorOutput "========================================" "Green"
Write-Host ""

Write-ColorOutput "最近提交:" "Cyan"
git log --oneline -5

Write-Host ""
pause
