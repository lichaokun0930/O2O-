# Panel AI 快速开始指南

## 🎯 什么是Panel AI?

Panel AI是O2O门店数据分析看板v2.0的**智能分析增强系统**，将AI分析能力植入到每个看板Panel中：

- **4个专项AI**: KPI、分类、价格带、促销各自独立分析
- **1个主AI**: 汇总各Panel洞察，识别跨看板关联问题
- **数据驱动**: AI必须先检查数据有效性，避免分析0值
- **可执行建议**: 每个洞察都给出明确的行动方案

---

## ⚡ 5分钟快速上手

### Step 1: 检查环境
```powershell
# 确保已安装依赖
cd "D:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析"
.\.venv\Scripts\python.exe -c "from ai_panel_analyzers import KPIPanelAnalyzer; print('✅ 环境OK')"
```

### Step 2: 启动看板
```powershell
# 方式1: 直接运行
.\.venv\Scripts\python.exe dashboard_v2.py

# 方式2: 使用快捷脚本
.\启动Dashboard_带AI.bat
```

### Step 3: 打开浏览器
```
本机访问: http://localhost:8055
局域网访问: http://119.188.71.47:8055
```

### Step 4: 使用Panel AI

#### 🔷 KPI看板AI (推荐第一次使用)
1. 在**核心KPI指标**区域找到 `🤖 AI智能分析 - KPI看板` 按钮 (蓝色)
2. 点击按钮
3. 等待3-5秒，展开查看分析结果
4. 阅读: ✅数据检查 → 📊逐项诊断 → 🎯综合建议

#### 🔷 分类看板AI
1. 滚动到**美团一级分类分析**区域
2. 点击 `🤖 AI智能分析 - 分类看板` 按钮 (绿色)
3. 查看TOP分类分析和问题分类识别

#### 🔷 价格带看板AI
1. 滚动到**价格带分析**区域
2. 点击 `🤖 AI智能分析 - 价格带看板` 按钮 (黄色)
3. 查看主力价格带和定价策略建议

#### 🔷 促销看板AI
1. 滚动到**促销强度分析**区域
2. 点击 `🤖 AI智能分析 - 促销看板` 按钮 (红色)
3. 查看促销效果评估和优化建议

#### 🔷 主AI综合诊断 (高级)
1. 滚动到页面底部 `🧠 主AI综合洞察` 区域
2. 点击 `生成综合诊断报告` 按钮 (白色大按钮)
3. 等待10-15秒，查看跨Panel关联分析

---

## 📊 输出解读

### KPI Panel AI输出结构
```
✅ 数据有效性检查
   - 列出所有KPI的有效性状态

📊 逐项KPI诊断
   1. 总SKU数: 判断 + 建议
   2. 动销SKU数: 判断 + 建议
   ...
   11. 滞销率: 判断 + 建议

🎯 综合评分与建议
   - 整体健康度评分 (0-100)
   - 优先级行动清单
```

### Master AI输出结构
```
🧠 综合诊断
   - 整合4个Panel的核心发现

🔗 关联问题识别
   - 问题1: 现象 → 影响 → 建议
   - 问题2: 现象 → 影响 → 建议
   ...

🎯 优先级行动清单
   1. ⚡ 立即: XXX
   2. 📅 本周: XXX
   3. 📆 本月: XXX
```

---

## 🎨 UI识别指南

### 按钮颜色编码
- **蓝色** = KPI看板AI
- **绿色** = 分类看板AI
- **黄色** = 价格带看板AI
- **红色** = 促销看板AI
- **白色 (紫色背景)** = 主AI综合诊断

### 洞察展示
- **展开/折叠**: 点击按钮自动展开，再次点击折叠
- **加载动画**: Cube旋转动画表示AI正在思考
- **Markdown渲染**: 支持emoji、粗体、列表、表格

---

## ⚙️ 高级用法

### 分类筛选后分析
1. 使用顶部的**分类筛选器**选择特定分类 (如: 饮料、休闲食品)
2. 点击Panel AI按钮
3. AI将只分析筛选后的数据

### 多次分析对比
1. 第一次分析: 全部分类
2. 记录关键发现
3. 筛选特定分类后再次分析
4. 对比差异，深入挖掘

### 导出分析结果
1. 展开AI分析结果
2. 全选文本 (Ctrl+A)
3. 复制 (Ctrl+C)
4. 粘贴到Word/Excel/Markdown编辑器

---

## 🔧 故障排查

### Q1: 点击按钮无反应
**原因**: 可能没有加载数据  
**解决**: 确保页面顶部显示"✅ 数据加载成功"

### Q2: 分析结果为空
**原因**: API密钥未配置或无效  
**解决**: 
```powershell
# 设置API密钥
$env:ZHIPU_API_KEY = "your_zhipu_api_key"
python dashboard_v2.py
```

### Q3: 分析时间过长 (>30秒)
**原因**: 网络延迟或API限流  
**解决**: 
1. 检查网络连接
2. 等待片刻再试
3. 查看控制台错误信息

### Q4: 报错"未定义KPIPanelAnalyzer"
**原因**: ai_panel_analyzers.py未正确导入  
**解决**: 
```powershell
# 验证模块
python -c "from ai_panel_analyzers import KPIPanelAnalyzer; print('OK')"
```

---

## 🧪 测试模式 (不启动Dashboard)

如需快速测试AI功能，无需启动完整Dashboard:

```powershell
# 运行快速测试脚本
.\.venv\Scripts\python.exe test_panel_ai_quick.py

# 选择测试模式
1. 测试单个Panel AI (KPI)
2. 测试单个Panel AI (分类)
3. 测试单个Panel AI (价格带)
4. 测试单个Panel AI (促销)
5. 测试所有Panel AI + 主AI (推荐)
6. 仅测试主AI
```

---

## 📚 进阶学习

### 自定义Prompt
编辑 `ai_panel_analyzers.py` 中的 `_build_prompt()` 方法:
```python
def _build_prompt(self, data: dict) -> str:
    prompt = f"""
    你是XXX分析师 (修改角色定位)
    ...
    【分析重点】(修改分析框架)
    1. XXX
    2. XXX
    """
    return prompt
```

### 调整API模型
编辑 `ai_panel_analyzers.py` 第17行:
```python
DEFAULT_MODEL = "glm-4-flash"  # 更快但质量稍低
# DEFAULT_MODEL = "glm-4-plus"  # 更强但稍慢
```

### 添加新Panel
1. 在 `ai_panel_analyzers.py` 创建新Analyzer类
2. 在 `dashboard_v2.py` 添加UI组件
3. 创建对应的回调函数

---

## 🎓 推荐工作流

### 场景1: 日常巡检 (每日)
1. 打开Dashboard
2. 点击**KPI看板AI** → 查看整体健康度
3. 如发现异常指标 → 点击对应Panel AI深入分析

### 场景2: 周度复盘 (每周)
1. 点击所有Panel AI，收集各看板洞察
2. 点击**主AI综合诊断** → 识别跨看板问题
3. 导出分析结果，制作周报

### 场景3: 专项优化 (按需)
1. 使用分类筛选器 → 选择目标分类 (如: 饮料)
2. 点击**分类看板AI** → 获得专项建议
3. 点击**价格带看板AI** → 评估定价策略
4. 点击**促销看板AI** → 优化促销方案

---

## 💡 最佳实践

### ✅ DO (推荐做法)
- ✅ 先分析整体 (全部分类) → 再分析局部 (单个分类)
- ✅ 先看Panel AI → 再看主AI (主AI需要Panel上下文)
- ✅ 记录每次分析的关键发现，建立历史对比
- ✅ 结合业务实际情况理解AI建议，不盲目执行

### ❌ DON'T (避免做法)
- ❌ 不要在数据未加载时点击AI按钮
- ❌ 不要期待AI分析0值数据 (AI会拒绝分析无效数据)
- ❌ 不要忽略"数据有效性检查"部分
- ❌ 不要连续快速点击按钮 (API有限流)

---

## 🚀 下一步

- 📖 阅读 `Panel_AI集成完成报告_v1.0.md` 了解架构细节
- 🔧 编辑 `ai_panel_analyzers.py` 自定义分析逻辑
- 📊 尝试不同分类筛选组合，探索更多洞察
- 💬 反馈问题和建议，持续改进

---

**祝你使用愉快！🎉**

如有问题，请查看:
- 集成报告: `Panel_AI集成完成报告_v1.0.md`
- 测试脚本: `test_panel_ai_integration.py`
- 快速测试: `test_panel_ai_quick.py`
