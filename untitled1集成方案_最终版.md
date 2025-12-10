# untitled1.py模块化集成方案 - 真实需求版

## 📋 需求理解

### 当前架构
```
untitled1.py（分析引擎）
    ↓ 生成
竞对分析报告_v3.4_FINAL.xlsx（数据源）
    ↓ 读取
dashboard_v2.py（可视化看板）
```

### 集成目标
在Dashboard中直接集成untitled1.py，实现：
1. ✅ 上传原始Excel → 自动分析 → 生成报告 → 刷新看板
2. ✅ 支持多门店分析与切换
3. ✅ 无需手动运行untitled1.py

---

## 🏗️ 模块化集成架构

### 方案一：轻量级集成（推荐）⭐

在Dashboard中添加"快速分析"按钮：

```
Dashboard界面：
├── 现有：上传Excel文件区 → 加载已生成报告
└── 新增：原始数据上传区 → 触发untitled1分析
    ├── 上传原始数据文件
    ├── 输入门店名称
    ├── 点击"开始分析"按钮
    ├── 显示分析进度
    ├── 分析完成后自动刷新看板
    └── 支持多门店切换
```

### 实现要点

#### 1. 添加原始数据上传区
```python
# 在现有文件上传区旁边添加
dbc.Row([
    dbc.Col([
        html.Label("📊 方式1：加载已生成报告"),
        dcc.Upload(id='upload-data', ...)  # 现有
    ], width=6),
    dbc.Col([
        html.Label("🔬 方式2：上传原始数据直接分析"),
        dcc.Upload(
            id='upload-raw-data',
            children=html.Div([
                '上传门店原始数据（CSV/Excel）',
                html.Br(),
                html.Small('将自动运行untitled1分析引擎')
            ]),
            style={...}
        ),
        dcc.Input(
            id='store-name-input',
            placeholder='输入门店名称',
            style={'width': '100%', 'marginTop': '10px'}
        ),
        html.Button(
            '🚀 开始分析',
            id='btn-run-analysis',
            style={...}
        ),
        html.Div(id='analysis-status')
    ], width=6)
])
```

#### 2. 分析回调函数
```python
@app.callback(
    [Output('analysis-status', 'children'),
     Output('upload-trigger', 'data')],  # 触发刷新
    Input('btn-run-analysis', 'n_clicks'),
    [State('upload-raw-data', 'contents'),
     State('upload-raw-data', 'filename'),
     State('store-name-input', 'value')]
)
def run_untitled1_analysis(n_clicks, contents, filename, store_name):
    \"\"\"运行untitled1分析引擎\"\"\"
    if not n_clicks or not contents or not store_name:
        return "请上传文件并输入门店名称", dash.no_update
    
    try:
        # 1. 保存上传的原始文件
        import base64
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        temp_input = f"./temp/{filename}"
        Path('./temp').mkdir(exist_ok=True)
        with open(temp_input, 'wb') as f:
            f.write(decoded)
        
        # 2. 调用untitled1分析
        from store_analyzer import get_store_analyzer
        analyzer = get_store_analyzer()
        
        # 显示进度
        status_msg = html.Div([
            html.I(className="fas fa-spinner fa-spin"),
            " 正在分析中，请稍候..."
        ])
        
        # 执行分析
        results = analyzer.analyze_file(temp_input, store_name)
        
        if not results:
            return dbc.Alert("分析失败，请检查文件格式", color="danger"), dash.no_update
        
        # 3. 导出为标准报告格式
        output_path = f"./reports/{store_name}_分析报告.xlsx"
        analyzer.export_report([store_name], output_path)
        
        # 4. 更新全局DataLoader
        global loader
        loader = DataLoader(output_path)
        
        # 5. 返回成功提示并触发刷新
        success_msg = dbc.Alert([
            html.I(className="fas fa-check-circle"),
            f" 分析完成！门店【{store_name}】报告已生成"
        ], color="success")
        
        return success_msg, datetime.now().timestamp()  # 触发刷新
        
    except Exception as e:
        error_msg = dbc.Alert(f"分析失败: {str(e)}", color="danger")
        return error_msg, dash.no_update
```

#### 3. 多门店支持
```python
# 添加门店管理器
class StoreManager:
    def __init__(self):
        self.stores = {}  # {store_name: report_path}
        self.current_store = None
    
    def add_store(self, name, report_path):
        self.stores[name] = report_path
    
    def get_store_list(self):
        return list(self.stores.keys())
    
    def switch_store(self, name):
        if name in self.stores:
            self.current_store = name
            return DataLoader(self.stores[name])
        return None

# 全局实例
store_manager = StoreManager()

# 门店切换下拉框
dcc.Dropdown(
    id='store-selector',
    options=[],  # 动态更新
    placeholder='选择门店查看',
    style={'width': '200px'}
)

# 切换回调
@app.callback(
    Output('upload-trigger', 'data'),
    Input('store-selector', 'value')
)
def switch_store(store_name):
    global loader
    loader = store_manager.switch_store(store_name)
    return datetime.now().timestamp()
```

---

## 📂 文件修改清单

### 1. dashboard_v2.py
**位置1**: 导入模块（顶部）
```python
from store_analyzer import get_store_analyzer
from pathlib import Path
```

**位置2**: 添加StoreManager类（DataLoader后面）
```python
class StoreManager:
    # ... (如上代码)
```

**位置3**: 修改UI布局（文件上传区）
```python
# 在现有upload-data旁边添加upload-raw-data
# 添加store-name-input
# 添加btn-run-analysis
# 添加analysis-status
```

**位置4**: 添加分析回调（所有回调函数区域）
```python
@app.callback(...)
def run_untitled1_analysis(...):
    # ... (如上代码)
```

**位置5**: 添加门店切换回调
```python
@app.callback(...)
def switch_store(...):
    # ... (如上代码)
```

**位置6**: 更新门店列表（在分析成功后）
```python
@app.callback(
    Output('store-selector', 'options'),
    Input('upload-trigger', 'data')
)
def update_store_list(trigger):
    return [{'label': name, 'value': name} 
            for name in store_manager.get_store_list()]
```

### 2. store_analyzer.py
✅ 已完成，无需修改

### 3. untitled1.py
✅ 无需修改，通过store_analyzer间接调用

---

## 🚀 实施步骤

### Step 1: 添加UI组件（20分钟）
- 原始数据上传区
- 门店名称输入框
- 分析按钮
- 进度显示区

### Step 2: 添加StoreManager（10分钟）
- 创建门店管理类
- 全局实例初始化

### Step 3: 添加分析回调（30分钟）
- 文件上传处理
- 调用untitled1分析
- 更新DataLoader
- 刷新看板

### Step 4: 添加门店切换（15分钟）
- 门店选择器
- 切换回调
- 自动刷新

### Step 5: 测试（15分钟）
- 上传原始数据测试
- 多门店切换测试
- 报告生成验证

**总计: 约1.5小时**

---

## 💡 核心优势

1. **无缝集成** - Dashboard直接调用untitled1引擎
2. **自动化流程** - 上传→分析→展示一气呵成
3. **多门店支持** - 可分析多个门店并切换查看
4. **保持兼容** - 仍支持加载已生成报告
5. **代码复用** - 100%复用untitled1逻辑

---

## ⚠️ 注意事项

### 性能考虑
- untitled1分析可能耗时1-3分钟
- 建议添加进度条或Loading动画
- 考虑异步执行（可选）

### 文件管理
- 临时文件存储在`./temp/`
- 生成报告存储在`./reports/`
- 定期清理临时文件

### 错误处理
- 文件格式校验
- 分析失败提示
- 网络异常处理

---

是否开始实施？我将按步骤修改dashboard_v2.py。
