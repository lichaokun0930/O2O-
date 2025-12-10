# Git 推送脚本使用说明

## 📦 文件说明

本项目提供了多个Git推送脚本，方便快速推送代码到GitHub仓库。

### 文件列表

1. **Git推送.bat** - 完整版推送（双击运行）
2. **快速推送.bat** - 快速推送（双击运行）
3. **git_push.ps1** - 完整版PowerShell脚本
4. **git_push_quick.ps1** - 快速版PowerShell脚本

---

## 🚀 使用方法

### 方法一：双击运行（推荐）

#### 完整版推送
1. 双击 `Git推送.bat`
2. 查看文件变更状态
3. 输入提交信息（或按Enter使用默认信息）
4. 等待推送完成

#### 快速推送
1. 双击 `快速推送.bat`
2. 自动使用时间戳作为提交信息
3. 快速完成推送

### 方法二：命令行运行

#### PowerShell中运行完整版
```powershell
.\git_push.ps1
```

#### PowerShell中运行快速版
```powershell
.\git_push_quick.ps1
```

#### 快速推送带自定义消息
```powershell
.\git_push_quick.ps1 -Message "修复了对比分析的bug"
```

---

## 📋 功能特点

### 完整版 (git_push.ps1)
- ✅ 彩色输出，界面友好
- ✅ 检查Git状态
- ✅ 显示文件变更
- ✅ 自定义提交信息
- ✅ 错误处理和提示
- ✅ 显示最近提交记录
- ✅ 自动检测分支

### 快速版 (git_push_quick.ps1)
- ✅ 精简快速
- ✅ 一键推送
- ✅ 支持自定义消息参数
- ✅ 自动使用时间戳

---

## ⚠️ 注意事项

1. **首次使用前**，请确保已配置Git：
   ```bash
   git config --global user.name "你的名字"
   git config --global user.email "你的邮箱"
   ```

2. **如果远程仓库未配置**，脚本会自动尝试添加：
   ```bash
   git remote add origin https://github.com/lichaokun0930/O2O-.git
   ```

3. **权限问题**：如果遇到PowerShell执行策略限制，可以：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **认证问题**：如果推送时需要认证，建议配置：
   - GitHub Personal Access Token
   - SSH密钥
   - Git Credential Manager

---

## 🔧 常见问题

### Q1: 脚本无法运行？
**A:** 右键脚本 → 属性 → 解除锁定

### Q2: 提示"无法加载脚本"？
**A:** 以管理员身份运行PowerShell，执行：
```powershell
Set-ExecutionPolicy RemoteSigned
```

### Q3: 推送失败？
**A:** 检查：
- 网络连接
- GitHub认证信息
- 远程仓库地址是否正确
- 是否有推送权限

### Q4: 如何修改远程仓库地址？
**A:** 编辑脚本中的仓库地址，或手动执行：
```bash
git remote set-url origin 新的仓库地址
```

---

## 📚 相关命令

### 查看远程仓库
```bash
git remote -v
```

### 查看提交历史
```bash
git log --oneline -10
```

### 查看当前分支
```bash
git branch
```

### 切换分支
```bash
git checkout 分支名
```

---

## 🌟 仓库信息

- **仓库地址**: https://github.com/lichaokun0930/O2O-.git
- **默认分支**: master
- **项目**: O2O门店数据分析系统

---

## 📝 更新日志

- **2025-12-11**: 创建初始版本
  - 完整版推送脚本
  - 快速推送脚本
  - 批处理封装
  - 使用文档

---

## 💡 提示

- 建议在推送前先测试代码
- 重要更新建议写详细的提交信息
- 定期检查远程仓库同步状态
- 养成良好的Git使用习惯

---

**Happy Coding! 🚀**
