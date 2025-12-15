# 门店对比分析功能设计文档

## 概述

本文档描述了门店对比分析功能的技术设计方案。该功能通过在现有单店看板中添加"对比模式"，允许用户选择竞对门店，并在卡片内展示对比视图，帮助用户快速识别经营差距。

设计遵循以下原则：
- **最小侵入**：在现有架构上扩展，不破坏单店看板功能
- **渐进增强**：优先实现3个核心卡片，后续逐步扩展
- **性能优先**：使用缓存机制，避免重复加载数据
- **用户友好**：平滑过渡，清晰的视觉反馈

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Dashboard Layout                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │  对比模式控制栏                                    │  │
│  │  [对比模式: OFF/ON]  [选择竞对: Dropdown]         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  卡片1: 核心指标概览                               │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ 单店视图 / 对比视图 (动态切换)               │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  卡片2: 一级分类动销分析                           │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │ 单店视图 / 对比视图 (动态切换)               │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ... (其他卡片)                                         │
└─────────────────────────────────────────────────────────┘
```

### 数据流设计

```
用户操作                Dash回调                数据处理
   │                      │                       │
   ├─ 开启对比模式 ────→  │                       │
   │                      ├─ 更新UI状态 ────────→ │
   │                      │   (启用竞对选择器)     │
   │                      │                       │
   ├─ 选择竞对门店 ────→  │                       │
   │                      ├─ 加载竞对数据 ──────→ │
   │                      │                       ├─ 检查缓存
   │                      │                       ├─ 读取Excel
   │                      │                       ├─ 解析数据
   │                      │                       └─ 返回数据
   │                      │ ←─────────────────────┘
   │                      ├─ 存储到Store组件
   │                      │
   │                      ├─ 触发卡片更新 ──────→ │
   │                      │                       ├─ 获取本店数据
   │                      │                       ├─ 获取竞对数据
   │                      │                       ├─ 生成对比图表
   │                      │                       ├─ 生成差异分析
   │                      │                       └─ 返回对比视图
   │                      │ ←─────────────────────┘
   │ ←─ 显示对比视图 ────┘
```

### 状态管理

使用Dash的`dcc.Store`组件管理全局状态：

```python
# 对比模式状态
dcc.Store(id='comparison-mode', data='off')  # 'off' | 'on'

# 选中的竞对门店
dcc.Store(id='selected-competitor', data=None)  # 门店名称

# 竞对数据缓存
dcc.Store(id='competitor-data-cache', data={})  # {kpi: {...}, category: [...], ...}

# 对比视图状态（每个卡片）
dcc.Store(id='card-view-mode', data={
    'kpi': 'single',           # 'single' | 'comparison'
    'category': 'single',
    'multispec': 'single'
})
```

## 组件设计

### 1. 对比模式控制栏组件

**组件名称**: `ComparisonModeControl`

**功能**: 提供对比模式开关和竞对选择器

**布局**:
```python
html.Div([
    dbc.Row([
        dbc.Col([
            html.Label("对比模式:", style={'fontWeight': '600', 'marginRight': '10px'}),
            dbc.Switch(
                id='comparison-mode-switch',
                value=False,
                label="OFF",
                style={'display': 'inline-block'}
            )
        ], width=3),
        
        dbc.Col([
            html.Label("选择竞对:", style={'fontWeight': '600', 'marginRight': '10px'}),
            dcc.Dropdown(
                id='competitor-selector',
                options=[],  # 动态加载已上传的门店
                value=None,
                placeholder="请选择竞对门店",
                disabled=True,  # 初始禁用
                style={'width': '300px'}
            )
        ], width=6)
    ], align='center', style={'padding': '15px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
], id='comparison-control-bar', style={'marginBottom': '20px'})
```

**回调逻辑**:
```python
@app.callback(
    [Output('competitor-selector', 'disabled'),
     Output('competitor-selector', 'options'),
     Output('comparison-mode-switch', 'label')],
    Input('comparison-mode-switch', 'value')
)
def update_comparison_control(mode_on):
    """更新对比模式控制栏状态"""
    if mode_on:
        # 获取已上传的门店列表（排除当前门店）
        options = get_uploaded_stores_except_current()
        return False, options, "ON"
    else:
        return True, [], "OFF"
```

### 2. 对比数据加载器

**组件名称**: `ComparisonDataLoader`

**功能**: 加载和缓存竞对门店数据

**实现**:
```python
class ComparisonDataLoader:
    """对比数据加载器"""
    
    def __init__(self):
        self.cache = {}  # {store_name: DataLoader}
    
    def load_competitor_data(self, store_name):
        """加载竞对数据（带缓存）"""
        # 检查缓存
        if store_name in self.cache:
            logger.info(f"✅ 使用缓存的竞对数据: {store_name}")
            return self.cache[store_name]
        
        # 获取门店报告路径
        report_path = store_manager.get_report_path(store_name)
        if not report_path or not Path(report_path).exists():
            logger.error(f"❌ 竞对报告不存在: {store_name}")
            return None
        
        # 加载数据
        logger.info(f"📂 加载竞对数据: {store_name}")
        data_loader = DataLoader(report_path, use_cache=True)
        
        # 缓存数据
        self.cache[store_name] = data_loader
        return data_loader
    
    def clear_cache(self, store_name=None):
        """清除缓存"""
        if store_name:
            self.cache.pop(store_name, None)
        else:
            self.cache.clear()

# 全局实例
comparison_loader = ComparisonDataLoader()
```

**回调逻辑**:
```python
@app.callback(
    Output('competitor-data-cache', 'data'),
    Input('competitor-selector', 'value'),
    prevent_initial_call=True
)
def load_competitor_data(competitor_name):
    """加载竞对数据"""
    if not competitor_name:
        return {}
    
    # 加载数据
    data_loader = comparison_loader.load_competitor_data(competitor_name)
    if not data_loader:
        return {}
    
    # 提取关键数据
    return {
        'kpi': data_loader.get_kpi_summary(),
        'category': data_loader.get_category_analysis().to_dict('records'),
        'price': data_loader.get_price_analysis().to_dict('records'),
        'role': data_loader.get_role_analysis().to_dict('records')
    }
```

### 3. 对比图表生成器

**组件名称**: `ComparisonChartBuilder`

**功能**: 生成各种对比图表

**实现**:
```python
class ComparisonChartBuilder:
    """对比图表生成器"""
    
    @staticmethod
    def create_grouped_bar_chart(own_data, competitor_data, x_col, y_col, title):
        """创建分组柱状图"""
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # 本店数据
        fig.add_trace(go.Bar(
            name='本店',
            x=own_data[x_col],
            y=own_data[y_col],
            marker_color='#3498db',
            text=own_data[y_col],
            textposition='outside'
        ))
        
        # 竞对数据
        fig.add_trace(go.Bar(
            name='竞对',
            x=competitor_data[x_col],
            y=competitor_data[y_col],
            marker_color='#e74c3c',
            text=competitor_data[y_col],
            textposition='outside'
        ))
        
        fig.update_layout(
            title=title,
            barmode='group',
            xaxis_title=x_col,
            yaxis_title=y_col,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_mirror_bar_chart(own_data, competitor_data, category_col, value_col, title):
        """创建镜像柱状图"""
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # 本店数据（负值，显示在左侧）
        fig.add_trace(go.Bar(
            name='本店',
            y=own_data[category_col],
            x=-own_data[value_col],  # 负值
            orientation='h',
            marker_color='#3498db',
            text=own_data[value_col],
            textposition='outside',
            hovertemplate='%{y}: %{text}<extra></extra>'
        ))
        
        # 竞对数据（正值，显示在右侧）
        fig.add_trace(go.Bar(
            name='竞对',
            y=competitor_data[category_col],
            x=competitor_data[value_col],
            orientation='h',
            marker_color='#e74c3c',
            text=competitor_data[value_col],
            textposition='outside',
            hovertemplate='%{y}: %{text}<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            barmode='overlay',
            xaxis=dict(
                title=value_col,
                tickvals=[-30, -20, -10, 0, 10, 20, 30],
                ticktext=['30', '20', '10', '0', '10', '20', '30']
            ),
            yaxis_title=category_col,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=500
        )
        
        return fig
    
    @staticmethod
    def create_stacked_comparison_bar(own_data, competitor_data, title):
        """创建堆叠对比柱状图"""
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        # 本店堆叠条
        fig.add_trace(go.Bar(
            name='本店-单规格',
            y=['本店'],
            x=[own_data['single_spec_pct']],
            orientation='h',
            marker_color='#3498db',
            text=[f"{own_data['single_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='本店-多规格',
            y=['本店'],
            x=[own_data['multi_spec_pct']],
            orientation='h',
            marker_color='#5dade2',
            text=[f"{own_data['multi_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        # 竞对堆叠条
        fig.add_trace(go.Bar(
            name='竞对-单规格',
            y=['竞对'],
            x=[competitor_data['single_spec_pct']],
            orientation='h',
            marker_color='#e74c3c',
            text=[f"{competitor_data['single_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='竞对-多规格',
            y=['竞对'],
            x=[competitor_data['multi_spec_pct']],
            orientation='h',
            marker_color='#ec7063',
            text=[f"{competitor_data['multi_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        fig.update_layout(
            title=title,
            barmode='stack',
            xaxis=dict(title='占比', tickformat='.0%'),
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=200
        )
        
        return fig
    
    @staticmethod
    def create_radar_chart(own_kpi, competitor_kpi, metrics):
        """创建雷达图"""
        import plotly.graph_objects as go
        
        # 归一化数据（0-100）
        own_values = []
        competitor_values = []
        
        for metric in metrics:
            own_val = own_kpi.get(metric, 0)
            comp_val = competitor_kpi.get(metric, 0)
            max_val = max(own_val, comp_val) or 1
            
            own_values.append((own_val / max_val) * 100)
            competitor_values.append((comp_val / max_val) * 100)
        
        fig = go.Figure()
        
        # 本店雷达
        fig.add_trace(go.Scatterpolar(
            r=own_values,
            theta=metrics,
            fill='toself',
            name='本店',
            line_color='#3498db'
        ))
        
        # 竞对雷达
        fig.add_trace(go.Scatterpolar(
            r=competitor_values,
            theta=metrics,
            fill='toself',
            name='竞对',
            line_color='#e74c3c'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=400
        )
        
        return fig

# 全局实例
chart_builder = ComparisonChartBuilder()
```

### 4. 差异分析生成器

**组件名称**: `DifferenceAnalyzer`

**功能**: 自动生成差异分析洞察

**实现**:
```python
class DifferenceAnalyzer:
    """差异分析生成器"""
    
    @staticmethod
    def analyze_kpi_differences(own_kpi, competitor_kpi):
        """分析KPI差异"""
        insights = []
        
        # 定义关键指标
        key_metrics = [
            {'key': '总销售额(去重后)', 'name': '销售额', 'format': 'currency', 'higher_is_better': True},
            {'key': '总SKU数(去重后)', 'name': 'SKU数', 'format': 'number', 'higher_is_better': True},
            {'key': '动销率', 'name': '动销率', 'format': 'percent', 'higher_is_better': True},
            {'key': '平均毛利率', 'name': '毛利率', 'format': 'percent', 'higher_is_better': True}
        ]
        
        for metric in key_metrics:
            own_val = own_kpi.get(metric['key'], 0)
            comp_val = competitor_kpi.get(metric['key'], 0)
            
            if comp_val == 0:
                continue
            
            diff = own_val - comp_val
            diff_pct = (diff / comp_val) * 100
            
            # 只有竞对领先时才生成洞察
            if comp_val > own_val:
                if metric['format'] == 'currency':
                    insight_text = f"竞对的{metric['name']}比本店高 ¥{abs(diff):,.0f}（{abs(diff_pct):.1f}%）"
                elif metric['format'] == 'percent':
                    insight_text = f"竞对的{metric['name']}比本店高 {abs(diff):.1%}（{abs(diff_pct):.1f}%）"
                else:
                    insight_text = f"竞对的{metric['name']}比本店多 {abs(diff):,.0f}个（{abs(diff_pct):.1f}%）"
                
                insights.append({
                    'icon': '⚠️',
                    'text': insight_text,
                    'level': 'warning'
                })
        
        return insights[:3]  # 最多返回3条
    
    @staticmethod
    def analyze_category_differences(own_category, competitor_category):
        """分析分类差异"""
        insights = []
        
        # 转换为DataFrame
        own_df = pd.DataFrame(own_category)
        comp_df = pd.DataFrame(competitor_category)
        
        if own_df.empty or comp_df.empty:
            return insights
        
        # 假设第一列是分类名，第二列是SKU数
        category_col = own_df.columns[0]
        sku_col = own_df.columns[1] if len(own_df.columns) > 1 else None
        
        if not sku_col:
            return insights
        
        # 合并数据
        merged = pd.merge(
            own_df[[category_col, sku_col]],
            comp_df[[category_col, sku_col]],
            on=category_col,
            how='outer',
            suffixes=('_own', '_comp')
        ).fillna(0)
        
        # 计算差异
        merged['diff'] = merged[f'{sku_col}_comp'] - merged[f'{sku_col}_own']
        merged['diff_pct'] = (merged['diff'] / merged[f'{sku_col}_comp']) * 100
        
        # 找出竞对领先的分类
        competitor_leading = merged[merged['diff'] > 0].nlargest(3, 'diff')
        
        for _, row in competitor_leading.iterrows():
            category = row[category_col]
            own_sku = row[f'{sku_col}_own']
            comp_sku = row[f'{sku_col}_comp']
            
            if comp_sku > 0:
                ratio = comp_sku / own_sku if own_sku > 0 else float('inf')
                if ratio == float('inf'):
                    insight_text = f"竞对在"{category}"有{comp_sku:.0f}个SKU，本店为0"
                else:
                    insight_text = f"竞对在"{category}"的SKU数是本店的{ratio:.1f}倍（{comp_sku:.0f} vs {own_sku:.0f}）"
                
                insights.append({
                    'icon': '📊',
                    'text': insight_text,
                    'level': 'info'
                })
        
        return insights[:3]
    
    @staticmethod
    def generate_recommendations(insights):
        """生成改进建议"""
        recommendations = []
        
        for insight in insights:
            text = insight['text']
            
            # 基于洞察生成建议
            if 'SKU数' in text or 'SKU' in text:
                recommendations.append({
                    'icon': '💡',
                    'text': '建议：增加该分类的商品数量，提升品类丰富度',
                    'level': 'success'
                })
            elif '动销率' in text:
                recommendations.append({
                    'icon': '💡',
                    'text': '建议：优化滞销商品，提升整体动销率',
                    'level': 'success'
                })
            elif '销售额' in text:
                recommendations.append({
                    'icon': '💡',
                    'text': '建议：加大促销力度，提升销售额',
                    'level': 'success'
                })
        
        return recommendations[:2]  # 最多返回2条建议

# 全局实例
analyzer = DifferenceAnalyzer()
```

## 数据模型

### 对比数据结构

```python
# 本店数据（从当前DataLoader获取）
own_data = {
    'kpi': {
        '总销售额(去重后)': 500000,
        '总SKU数(去重后)': 120,
        '动销率': 0.65,
        '平均毛利率': 0.32,
        ...
    },
    'category': [
        {'分类': '服饰鞋包', 'SKU数': 10, '动销率': 0.65, '销售额': 50000},
        {'分类': '食品饮料', 'SKU数': 45, '动销率': 0.78, '销售额': 120000},
        ...
    ],
    'price': [...],
    'role': [...]
}

# 竞对数据（从ComparisonDataLoader获取）
competitor_data = {
    'kpi': {
        '总销售额(去重后)': 680000,
        '总SKU数(去重后)': 180,
        '动销率': 0.72,
        '平均毛利率': 0.28,
        ...
    },
    'category': [
        {'分类': '服饰鞋包', 'SKU数': 20, '动销率': 0.72, '销售额': 80000},
        {'分类': '食品饮料', 'SKU数': 38, '动销率': 0.70, '销售额': 150000},
        ...
    ],
    'price': [...],
    'role': [...]
}
```

## 错误处理

### 错误场景与处理策略

| 错误场景 | 处理策略 |
|---------|---------|
| 竞对报告不存在 | 显示错误提示，禁用对比模式 |
| 竞对数据加载失败 | 显示错误提示，保持单店视图 |
| 竞对数据格式不匹配 | 显示警告，跳过不匹配的字段 |
| 图表渲染失败 | 显示"图表加载失败"，记录错误日志 |
| 差异分析生成失败 | 跳过差异分析，只显示图表 |

### 错误日志

```python
# 使用现有的logger系统
logger.error(f"❌ 竞对数据加载失败: {competitor_name}, 错误: {e}")
logger.warning(f"⚠️ 竞对数据字段缺失: {missing_fields}")
logger.info(f"✅ 对比视图渲染成功: {card_name}")
```

## 测试策略

### 单元测试

测试核心功能模块：

```python
# test_comparison_data_loader.py
def test_load_competitor_data():
    """测试竞对数据加载"""
    loader = ComparisonDataLoader()
    data = loader.load_competitor_data('竞对门店A')
    assert data is not None
    assert 'kpi' in data
    assert 'category' in data

def test_cache_mechanism():
    """测试缓存机制"""
    loader = ComparisonDataLoader()
    data1 = loader.load_competitor_data('竞对门店A')
    data2 = loader.load_competitor_data('竞对门店A')
    assert data1 is data2  # 应该返回同一个对象

# test_comparison_chart_builder.py
def test_create_grouped_bar_chart():
    """测试分组柱状图生成"""
    own_data = pd.DataFrame({'分类': ['A', 'B'], 'SKU数': [10, 20]})
    comp_data = pd.DataFrame({'分类': ['A', 'B'], 'SKU数': [15, 25]})
    fig = chart_builder.create_grouped_bar_chart(own_data, comp_data, '分类', 'SKU数', '测试')
    assert fig is not None
    assert len(fig.data) == 2  # 两条trace

# test_difference_analyzer.py
def test_analyze_kpi_differences():
    """测试KPI差异分析"""
    own_kpi = {'总销售额(去重后)': 500000, '总SKU数(去重后)': 120}
    comp_kpi = {'总销售额(去重后)': 680000, '总SKU数(去重后)': 180}
    insights = analyzer.analyze_kpi_differences(own_kpi, comp_kpi)
    assert len(insights) > 0
    assert '竞对' in insights[0]['text']
```

### 集成测试

测试完整的对比流程：

```python
# test_comparison_integration.py
def test_comparison_mode_workflow():
    """测试对比模式完整流程"""
    # 1. 开启对比模式
    # 2. 选择竞对门店
    # 3. 加载竞对数据
    # 4. 渲染对比视图
    # 5. 生成差异分析
    # 6. 关闭对比模式
    pass
```

### 性能测试

测试数据加载和渲染性能：

```python
# test_comparison_performance.py
def test_data_loading_performance():
    """测试数据加载性能"""
    import time
    start = time.time()
    loader = ComparisonDataLoader()
    data = loader.load_competitor_data('竞对门店A')
    elapsed = time.time() - start
    assert elapsed < 2.0  # 应该在2秒内完成

def test_chart_rendering_performance():
    """测试图表渲染性能"""
    import time
    start = time.time()
    fig = chart_builder.create_grouped_bar_chart(own_data, comp_data, '分类', 'SKU数', '测试')
    elapsed = time.time() - start
    assert elapsed < 0.5  # 应该在0.5秒内完成
```



## 正确性属性

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: 对比模式状态一致性
*For any* Dashboard state, when comparison mode is OFF, the competitor selector should be disabled, and when comparison mode is ON, the competitor selector should be enabled.
**Validates: Requirements 1.2, 1.3**

### Property 2: 对比模式切换的可逆性（Round Trip）
*For any* Dashboard state, enabling comparison mode then disabling it should restore the original single-store view state.
**Validates: Requirements 1.5**

### Property 3: 竞对数据加载触发
*For any* valid competitor store selection, the Dashboard should trigger data loading and switch all supported cards to comparison view.
**Validates: Requirements 1.4**

### Property 4: 核心指标对比完整性
*For any* comparison view of KPI card, the display should include all four core metrics (sales, SKU count, turnover rate, margin rate) with own-store value, competitor value, difference value, and difference percentage.
**Validates: Requirements 2.2, 2.3**

### Property 5: 指标差异视觉反馈规则
*For any* KPI metric, if own-store value < competitor value, the Dashboard should display a red color or down arrow indicator; if own-store value > competitor value, the Dashboard should display a green color or up arrow indicator.
**Validates: Requirements 2.4, 2.5**

### Property 6: 雷达图双曲线渲染
*For any* comparison view with valid KPI data, the radar chart should contain exactly two data curves (one for own-store, one for competitor) with different colors and a legend.
**Validates: Requirements 2.6**

### Property 7: 差异分析自动生成
*For any* comparison view, the Dashboard should automatically generate difference analysis insights when competitor metrics exceed own-store metrics.
**Validates: Requirements 2.7, 5.1, 5.2**

### Property 8: 分组柱状图双系列渲染
*For any* category comparison data, the grouped bar chart should contain exactly two data series (own-store and competitor) displayed side-by-side with different colors and a legend.
**Validates: Requirements 3.2, 3.4, 7.1**

### Property 9: 镜像柱状图布局规则
*For any* category comparison data, the mirror bar chart should display own-store data on the left side (negative values) and competitor data on the right side (positive values) with a zero baseline in the middle.
**Validates: Requirements 3.3, 4.2, 7.2**

### Property 10: 分类级差异识别
*For any* category where competitor metric > own-store metric, the Dashboard should generate a difference insight indicating the gap and improvement suggestions.
**Validates: Requirements 3.6**

### Property 11: 堆叠图结构完整性
*For any* multi-spec comparison data, the stacked comparison bar chart should display two components (single-spec and multi-spec) for both own-store and competitor, with percentages shown.
**Validates: Requirements 4.3, 7.3**

### Property 12: 差异洞察数量限制
*For any* difference analysis that generates more than 3 insights, the Dashboard should display only the top 3 most important insights.
**Validates: Requirements 5.5**

### Property 13: 差异洞察格式规范
*For any* difference insight containing numerical values, the Dashboard should format it in a readable pattern like "Competitor's SKU count is 2x of own-store (20 vs 10)".
**Validates: Requirements 5.6**

### Property 14: 竞对数据缓存机制
*For any* competitor store, loading its data twice should result in the second load retrieving from cache rather than re-reading the Excel file.
**Validates: Requirements 6.2**

### Property 15: 缓存更新一致性
*For any* competitor store switch operation, the Dashboard should clear the old competitor's cache and load the new competitor's data.
**Validates: Requirements 6.5**

### Property 16: 滚动位置保持
*For any* comparison mode toggle operation, the Dashboard should maintain the current page scroll position after the view transition.
**Validates: Requirements 8.2**

### Property 17: 增量更新机制
*For any* competitor store switch operation, the Dashboard should only update comparison data without re-rendering the entire page layout.
**Validates: Requirements 8.3**

### Property 18: 固定控制栏定位
*For any* page scroll operation in comparison mode, the comparison control bar (mode switch and competitor selector) should remain fixed at the top of the viewport.
**Validates: Requirements 8.5**

## 实现计划

### 阶段1：基础架构（第1-2周）

#### 任务1.1：创建对比模式控制栏
- 添加对比模式开关（Switch组件）
- 添加竞对选择器（Dropdown组件）
- 实现控制栏的固定定位
- 实现开关状态与选择器禁用/启用的联动
- _Validates: Requirements 1.1, 1.2, 1.3_

#### 任务1.2：实现对比数据加载器
- 创建`ComparisonDataLoader`类
- 实现`load_competitor_data`方法
- 实现缓存机制（内存缓存）
- 实现缓存清除功能
- _Validates: Requirements 6.1, 6.2, 6.5_

#### 任务1.3：实现状态管理
- 添加`dcc.Store`组件存储对比模式状态
- 添加`dcc.Store`组件存储选中的竞对门店
- 添加`dcc.Store`组件缓存竞对数据
- 实现状态更新回调
- _Validates: Requirements 1.4_

#### 任务1.4：实现错误处理机制
- 处理竞对报告不存在的情况
- 处理数据加载失败的情况
- 处理数据格式不匹配的情况
- 添加错误日志记录
- _Validates: Requirements 6.3_

### 阶段2：核心卡片对比功能（第3-4周）

#### 任务2.1：实现核心指标概览对比
- 创建对比卡片组件（4个核心指标）
- 实现指标差异计算
- 实现视觉反馈（红色/绿色，箭头）
- 创建雷达图生成函数
- 实现差异分析生成
- _Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

#### 任务2.1.1：编写Property测试 - 指标对比完整性
- **Property 4: 核心指标对比完整性**
- **Validates: Requirements 2.2, 2.3**

#### 任务2.1.2：编写Property测试 - 视觉反馈规则
- **Property 5: 指标差异视觉反馈规则**
- **Validates: Requirements 2.4, 2.5**

#### 任务2.1.3：编写Property测试 - 雷达图渲染
- **Property 6: 雷达图双曲线渲染**
- **Validates: Requirements 2.6**

#### 任务2.2：实现一级分类动销分析对比
- 创建分组柱状图生成函数（动销率）
- 创建镜像柱状图生成函数（SKU数量）
- 创建分组柱状图生成函数（销售额）
- 实现分类级差异分析
- 集成到卡片回调中
- _Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

#### 任务2.2.1：编写Property测试 - 分组柱状图渲染
- **Property 8: 分组柱状图双系列渲染**
- **Validates: Requirements 3.2, 3.4**

#### 任务2.2.2：编写Property测试 - 镜像柱状图布局
- **Property 9: 镜像柱状图布局规则**
- **Validates: Requirements 3.3**

#### 任务2.2.3：编写Property测试 - 分类差异识别
- **Property 10: 分类级差异识别**
- **Validates: Requirements 3.6**

#### 任务2.3：实现多规格商品供给分析对比
- 创建镜像柱状图生成函数（多规格SKU数量）
- 创建堆叠对比柱状图生成函数（占比）
- 实现多规格结构差异分析
- 集成到卡片回调中
- _Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

#### 任务2.3.1：编写Property测试 - 堆叠图结构
- **Property 11: 堆叠图结构完整性**
- **Validates: Requirements 4.3**

### 阶段3：差异分析引擎（第5周）

#### 任务3.1：实现差异分析生成器
- 创建`DifferenceAnalyzer`类
- 实现KPI差异分析方法
- 实现分类差异分析方法
- 实现改进建议生成方法
- _Validates: Requirements 5.1, 5.2, 5.3, 5.4_

#### 任务3.2：实现洞察格式化和限制
- 实现洞察数量限制（最多3条）
- 实现洞察格式化规则
- 实现洞察优先级排序
- _Validates: Requirements 5.5, 5.6_

#### 任务3.2.1：编写Property测试 - 洞察数量限制
- **Property 12: 差异洞察数量限制**
- **Validates: Requirements 5.5**

#### 任务3.2.2：编写Property测试 - 洞察格式规范
- **Property 13: 差异洞察格式规范**
- **Validates: Requirements 5.6**

### 阶段4：交互优化和测试（第6周）

#### 任务4.1：优化视图切换体验
- 实现平滑过渡动画
- 实现滚动位置保持
- 实现增量更新机制
- _Validates: Requirements 8.1, 8.2, 8.3_

#### 任务4.1.1：编写Property测试 - 滚动位置保持
- **Property 16: 滚动位置保持**
- **Validates: Requirements 8.2**

#### 任务4.1.2：编写Property测试 - 增量更新
- **Property 17: 增量更新机制**
- **Validates: Requirements 8.3**

#### 任务4.2：实现加载状态反馈
- 添加加载动画组件
- 实现加载超时检测（2秒）
- 实现进度提示
- _Validates: Requirements 6.4, 8.4_

#### 任务4.3：集成测试和性能优化
- 编写集成测试用例
- 测试完整对比流程
- 优化数据加载性能
- 优化图表渲染性能
- _Validates: All requirements_

#### 任务4.4：Checkpoint - 确保所有测试通过
- 确保所有Property测试通过
- 确保所有集成测试通过
- 确保性能测试通过
- 如有问题，向用户报告

### 阶段5：文档和部署（第7周）

#### 任务5.1：编写用户文档
- 编写功能使用指南
- 编写常见问题解答
- 录制演示视频

#### 任务5.2：代码审查和优化
- 代码审查
- 性能优化
- 安全检查

#### 任务5.3：部署和验收
- 部署到生产环境
- 用户验收测试
- 收集反馈

## 附录

### A. 图表库选择

使用Plotly作为图表库，原因：
- ✅ 已在项目中使用
- ✅ 支持所有需要的图表类型
- ✅ 交互性强
- ✅ 性能良好

### B. 性能指标

| 指标 | 目标值 | 测量方法 |
|-----|-------|---------|
| 竞对数据加载时间 | < 2秒 | 计时器 |
| 图表渲染时间 | < 0.5秒 | 计时器 |
| 缓存命中率 | > 90% | 日志统计 |
| 视图切换时间 | < 0.3秒 | 计时器 |

### C. 兼容性

| 浏览器 | 最低版本 |
|-------|---------|
| Chrome | 90+ |
| Firefox | 88+ |
| Edge | 90+ |
| Safari | 14+ |

### D. 依赖项

无需新增依赖，使用现有的：
- Dash
- Plotly
- Pandas
- NumPy
