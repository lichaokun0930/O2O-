# O2O门店数据分析看板

## 📊 概述
基于现有的数据分析结果构建的可视化看板，使用 Dash + Plotly 框架开发，提供直观的门店数据展示和分析功能。

## 🚀 快速开始

### 方法一：一键启动（推荐）
双击运行 `start_dashboard.bat`，脚本会自动：
- 检查依赖环境
- 安装必要的Python包
- 运行数据分析（如需要）
- 启动看板服务

### 方法二：手动启动
```bash
# 1. 安装依赖
pip install -r requirements_dashboard.txt

# 2. 确保有数据报告（如果没有，先运行）
python untitled1.py

# 3. 启动看板
python dashboard.py
```

### 访问地址
看板启动后访问：http://localhost:8052

## 📈 功能特性

### 核心KPI展示
- **总SKU数**: 门店商品总数（含多规格）
- **动销SKU数**: 有销售记录的商品数量
- **动销率**: 动销商品占比
- **总销售额**: 门店总营收

### 可视化分析
1. **分类表现热力图**
   - 展示美团一级分类的多维度表现
   - 包含SKU数量、动销率、月售占比等指标

2. **商品角色分析饼图**
   - 引流品、利润品、形象品、劣势品分布
   - 基于价格带和销量的智能分类

3. **价格带分布分析**
   - 双轴图展示SKU数量和销售额分布
   - 直观了解不同价格段的表现

4. **详细数据表格**
   - 美团一级分类的详细指标数据
   - 支持分页浏览和数据筛选

## 🔧 技术架构

### 核心组件
- **DataLoader**: 数据加载器，负责从Excel读取和预处理数据
- **DashboardComponents**: 组件生成器，创建各种图表和UI元素
- **Dash App**: 主应用框架，处理路由和交互

### 数据流
```
Excel报告 → DataLoader → 数据预处理 → Plotly图表 → Dash布局 → Web展示
```

### 文件结构
```
├── dashboard.py                 # 主看板应用
├── requirements_dashboard.txt   # 依赖包列表
├── start_dashboard.bat         # 一键启动脚本
├── untitled1.py               # 数据分析脚本
└── reports/                   # Excel报告目录
    └── 竞对分析报告_v3.4_FINAL.xlsx
```

## 📝 配置说明

### 数据源配置
看板会自动查找以下数据源（按优先级）：
1. `reports/` 目录下最新的 `.xlsx` 文件
2. 默认路径：`./reports/竞对分析报告_v3.4_FINAL.xlsx`

### 端口配置
默认端口：8052
如需修改，编辑 `dashboard.py` 中的：
```python
app.run_server(debug=True, host='localhost', port=8052)
```

## 🛠️ 自定义开发

### 添加新的图表组件
1. 在 `DashboardComponents` 类中添加静态方法
2. 在 `create_layout()` 函数中引用新组件
3. 如需交互功能，添加对应的 callback

### 扩展数据源
在 `DataLoader` 类中添加新的数据读取方法：
```python
def get_custom_analysis(self):
    return pd.read_excel(self.excel_path, sheet_name='自定义分析')
```

### 样式定制
- 使用 Bootstrap 主题：修改 `external_stylesheets`
- 自定义CSS：添加 `assets/` 目录和CSS文件
- 颜色配置：修改各图表组件中的 `color_discrete_map`

## 🐛 故障排除

### 常见问题
1. **"未找到数据文件"**
   - 确保已运行 `untitled1.py` 生成Excel报告
   - 检查 `reports/` 目录是否存在

2. **"数据格式不匹配"**
   - 检查Excel中的sheet名称是否正确
   - 确认数据列名与代码中的期望一致

3. **依赖包安装失败**
   - 检查网络连接
   - 尝试使用国内镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements_dashboard.txt`

### 调试模式
看板运行在调试模式下，代码修改会自动重载。如需关闭：
```python
app.run_server(debug=False, host='localhost', port=8052)
```

## 🔮 后续优化计划

### 短期优化
- [ ] 添加数据刷新按钮
- [ ] 支持多门店对比分析
- [ ] 添加数据筛选器
- [ ] 优化移动端显示

### 中期优化
- [ ] 集成ECharts组件
- [ ] 添加数据导出功能
- [ ] 实现用户权限管理
- [ ] 支持实时数据更新

### 长期规划
- [ ] 集成预测分析模型
- [ ] 添加告警和通知功能
- [ ] 支持自定义看板配置
- [ ] 云端部署和访问

## 📞 技术支持
如有问题或建议，请参考：
- 代码注释和文档
- Dash官方文档：https://dash.plotly.com/
- Plotly图表文档：https://plotly.com/python/