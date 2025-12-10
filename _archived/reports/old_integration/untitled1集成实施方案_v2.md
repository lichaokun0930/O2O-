# 门店深度分析集成实施方案 v2.0（最小化改动）

## 🎯 调整后的集成策略

**核心理念**：不改变现有Dashboard结构，在底部添加新的"门店深度分析"区域

### 方案优势
- ✅ 不影响现有功能
- ✅ 最小化代码改动
- ✅ 可独立测试
- ✅ 快速上线

---

## 📐 UI布局设计

在现有Dashboard底部添加折叠面板：

```
现有Dashboard
├── 标题栏
├── 文件上传区（现有）
├── 门店选择器（现有）
├── KPI卡片（现有）
├── 分类分析图表（现有）
├── 价格带分析图表（现有）
├── 促销分析图表（现有）
├── 多规格分析图表（现有）
└── 【新增】门店深度分析区域 ⭐
    ├── 折叠标题："🔬 门店深度分析（多规格识别 + 商品角色）"
    └── 展开内容：
        ├── 文件上传区（独立于主上传）
        ├── 分析按钮 + 进度显示
        ├── 核心指标卡片组
        │   ├── SKU统计卡片
        │   ├── 多规格商品卡片
        │   ├── 动销情况卡片
        │   └── 商品角色卡片
        ├── 详细数据表格
        │   ├── 多规格商品明细
        │   └── 分类详细指标
        └── 导出按钮（Excel报告）
```

---

## 🔧 实施步骤

### Step 1: 添加核心组件（30分钟）

在`dashboard_v2.py`底部（现有图表下方）添加：

```python
# ==================== 门店深度分析区域 ====================

html.Div([
    # 折叠面板标题
    html.Div([
        html.Button(
            "🔬 门店深度分析（多规格识别 + 商品角色）",
            id="toggle-deep-analysis",
            n_clicks=0,
            style={...}
        )
    ]),
    
    # 折叠内容
    dbc.Collapse(
        id="deep-analysis-content",
        is_open=False,
        children=[
            # 独立文件上传
            dcc.Upload(
                id='upload-store-file',
                children=[...],
                style={...}
            ),
            
            # 分析按钮
            html.Button("开始分析", id="btn-start-analysis"),
            
            # 进度显示
            html.Div(id="analysis-progress"),
            
            # 结果展示区
            html.Div(id="deep-analysis-results")
        ]
    )
], className="mt-5", style={'borderTop': '2px solid #e0e0e0', 'paddingTop': '30px'})
```

### Step 2: 添加回调函数（1小时）

```python
# 1. 折叠面板切换
@app.callback(
    Output("deep-analysis-content", "is_open"),
    Input("toggle-deep-analysis", "n_clicks"),
    State("deep-analysis-content", "is_open")
)
def toggle_deep_analysis(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


# 2. 文件上传处理
@app.callback(
    Output("analysis-progress", "children"),
    Input("upload-store-file", "contents"),
    State("upload-store-file", "filename")
)
def handle_store_upload(contents, filename):
    if contents is None:
        return "请上传Excel文件"
    
    # 解析文件
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    # 保存临时文件
    temp_path = f"./temp/{filename}"
    with open(temp_path, 'wb') as f:
        f.write(decoded)
    
    return html.Div([
        html.I(className="fas fa-check-circle", style={'color': 'green'}),
        f" 文件已上传: {filename}"
    ])


# 3. 执行分析
@app.callback(
    Output("deep-analysis-results", "children"),
    Input("btn-start-analysis", "n_clicks"),
    State("upload-store-file", "filename")
)
def run_deep_analysis(n_clicks, filename):
    if not n_clicks or not filename:
        return html.Div()
    
    # 获取分析器
    from store_analyzer import get_store_analyzer
    analyzer = get_store_analyzer()
    
    # 执行分析
    temp_path = f"./temp/{filename}"
    store_name = Path(filename).stem
    
    results = analyzer.analyze_file(temp_path, store_name)
    
    if not results:
        return dbc.Alert("分析失败，请检查文件格式", color="danger")
    
    # 获取摘要
    summary = analyzer.get_summary(store_name)
    
    # 生成展示组件
    return html.Div([
        # KPI卡片组
        create_deep_analysis_kpi_cards(summary),
        
        # 多规格商品表格
        create_multispec_table(analyzer, store_name),
        
        # 导出按钮
        html.Button("下载Excel报告", id="btn-download-deep-report", 
                   className="btn btn-success mt-3")
    ])
```

### Step 3: 创建UI组件函数（30分钟）

```python
def create_deep_analysis_kpi_cards(summary):
    """创建核心指标卡片"""
    return dbc.Row([
        # SKU统计卡片
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📦 SKU统计"),
                dbc.CardBody([
                    html.H3(f"{summary['总SKU数']}个", 
                           style={'color': '#007bff'}),
                    html.Hr(),
                    html.P(f"单规格: {summary['单规格SKU数']}个"),
                    html.P(f"多规格商品: {summary['多规格商品数']}个"),
                    html.P(f"多规格SKU: {summary['多规格SKU总数']}个")
                ])
            ], className="shadow-sm")
        ], width=3),
        
        # 动销情况卡片
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📈 动销情况"),
                dbc.CardBody([
                    html.H3(f"{summary['动销率']:.1f}%", 
                           style={'color': '#28a745'}),
                    html.Hr(),
                    html.P(f"动销SKU: {summary['动销SKU数']}个"),
                    html.P(f"滞销SKU: {summary['滞销SKU数']}个")
                ])
            ], className="shadow-sm")
        ], width=3),
        
        # 商品角色卡片
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🎯 商品角色"),
                dbc.CardBody([
                    html.P(f"引流品: {summary['引流品数']}个", 
                          style={'color': '#17a2b8'}),
                    html.P(f"利润品: {summary['利润品数']}个", 
                          style={'color': '#ffc107'}),
                    html.P(f"形象品: {summary['形象品数']}个", 
                          style={'color': '#6f42c1'}),
                    html.P(f"劣势品: {summary['劣势品数']}个", 
                          style={'color': '#dc3545'})
                ])
            ], className="shadow-sm")
        ], width=3),
        
        # 销售数据卡片
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("💰 销售数据"),
                dbc.CardBody([
                    html.H3(f"¥{summary['总销售额']:,.0f}", 
                           style={'color': '#fd7e14'}),
                    html.Hr(),
                    html.P(f"总销量: {summary['总销量']:,.0f}"),
                    html.P(f"客单价: ¥{summary['客单价']:.2f}")
                ])
            ], className="shadow-sm")
        ], width=3)
    ], className="mb-4")


def create_multispec_table(analyzer, store_name):
    """创建多规格商品表格"""
    df = analyzer.get_multispec_products(store_name, limit=50)
    
    if df is None or df.empty:
        return html.Div("暂无多规格商品数据")
    
    return html.Div([
        html.H5("📋 多规格商品明细（TOP 50）", className="mt-4 mb-3"),
        dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[
                {'name': '商品名称', 'id': 'product_name'},
                {'name': '规格', 'id': '规格名称'},
                {'name': '售价', 'id': 'price'},
                {'name': '月售', 'id': 'monthly_sales'},
                {'name': '一级分类', 'id': 'l1_category'},
                {'name': '商品角色', 'id': 'product_role'}
            ],
            style_table={'overflowX': 'auto', 'maxHeight': '400px'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'borderBottom': '2px solid #dee2e6'
            },
            page_size=20,
            page_action='native',
            filter_action='native',
            sort_action='native'
        )
    ])
```

### Step 4: 添加导出功能（20分钟）

```python
@app.callback(
    Output("download-deep-report", "data"),
    Input("btn-download-deep-report", "n_clicks"),
    State("upload-store-file", "filename"),
    prevent_initial_call=True
)
def download_deep_report(n_clicks, filename):
    if not n_clicks:
        return None
    
    from store_analyzer import get_store_analyzer
    analyzer = get_store_analyzer()
    
    store_name = Path(filename).stem
    output_path = f"./reports/{store_name}_深度分析.xlsx"
    
    analyzer.export_report([store_name], output_path)
    
    return dcc.send_file(output_path)
```

---

## 📦 文件修改清单

### 新增文件
1. ✅ `store_analyzer.py` - 已完成
2. ⬜ `temp/` - 临时文件目录（需创建）

### 修改文件
1. ⬜ `dashboard_v2.py`
   - 添加导入: `from store_analyzer import get_store_analyzer`
   - 添加UI组件（约100行）
   - 添加回调函数（约150行）
   - 添加辅助函数（约80行）

**总计新增代码: ~330行**

---

## ⏱️ 预估时间

- Step 1: UI组件 - 30分钟
- Step 2: 回调函数 - 1小时
- Step 3: 展示组件 - 30分钟
- Step 4: 导出功能 - 20分钟
- **测试与调试** - 30分钟

**总计: 约3小时**

---

## 🎬 立即开始？

建议执行顺序：
1. 创建temp目录
2. 在dashboard_v2.py中添加UI组件
3. 添加基础回调函数
4. 测试基本流程
5. 优化UI和交互

是否开始实施？
