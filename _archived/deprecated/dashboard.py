# -*- coding: utf-8 -*-
"""
O2O门店数据分析看板 v1.0
基于Dash + Plotly构建的可视化数据看板

运行方式：
    python dashboard.py

功能：
- 读取Excel分析报告数据
- 展示核心KPI指标
- 可视化分类分析、价格带分析、商品角色分析
- 交互式数据探索
"""

import dash
from dash import dcc, html, Input, Output, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
import os
from datetime import datetime

# 全局配置
DEFAULT_REPORT_PATH = "./reports/竞对分析报告_v3.4_FINAL.xlsx"
APP_TITLE = "O2O门店数据分析看板"

class DataLoader:
    """数据加载器 - 负责从Excel报告中读取和预处理数据"""
    
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有sheet数据"""
        try:
            # 获取所有sheet名称
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            print(f"📊 可用的sheet: {sheet_names}")
            
            # 根据索引加载数据（避免编码问题）
            if len(sheet_names) > 0:
                # 第一个sheet通常是核心指标
                self.data['kpi'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[0])
            
            if len(sheet_names) > 2:
                # 第三个sheet通常是价格带分析
                self.data['price_analysis'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[2])
                # 清理价格带数据
                if not self.data['price_analysis'].empty and 'Unnamed' in str(self.data['price_analysis'].columns[0]):
                    self.data['price_analysis'] = self.data['price_analysis'].drop(self.data['price_analysis'].columns[0], axis=1)
            
            if len(sheet_names) > 4:
                # 第五个sheet通常是美团一级分类
                self.data['category_l1'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[4])
            
            if len(sheet_names) > 1:
                # 第二个sheet通常是商品角色分析
                self.data['role_analysis'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[1])
            
            # 填充缺失的数据
            for key in ['kpi', 'category_l1', 'role_analysis', 'price_analysis']:
                if key not in self.data:
                    self.data[key] = pd.DataFrame()
            
            print(f"✅ 数据加载成功: {self.excel_path}")
            print(f"📊 KPI数据: {self.data['kpi'].shape}")
            print(f"💰 价格带数据: {self.data['price_analysis'].shape}")
            print(f"🏪 分类数据: {self.data['category_l1'].shape}")
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            # 创建空数据框作为备用
            self.data = {
                'kpi': pd.DataFrame(),
                'category_l1': pd.DataFrame(),
                'role_analysis': pd.DataFrame(),
                'price_analysis': pd.DataFrame()
            }
    
    def get_kpi_summary(self):
        """获取KPI摘要数据"""
        if self.data['kpi'].empty:
            return {}
        
        kpi_df = self.data['kpi']
        if len(kpi_df) > 0:
            # 取第一行数据（单门店）
            row = kpi_df.iloc[0]
            summary = {}
            
            # 映射到标准化的字段名
            for i, col in enumerate(kpi_df.columns):
                value = row.iloc[i] if i < len(row) else 0
                if i == 0:  # 门店名
                    summary['门店'] = value
                elif i == 1:  # 总SKU数
                    summary['总SKU数'] = value
                elif i == 2:  # SPU数
                    summary['SPU数'] = value  
                elif i == 3:  # 动销SKU数
                    summary['动销SKU数'] = value
                elif i == 4:  # 滞销SKU数
                    summary['滞销SKU数'] = value
                elif i == 5:  # 动销率
                    summary['动销率'] = value
                elif i == 6:  # 平均价格
                    summary['平均价格'] = value
                elif i == 7:  # 经销SKU数
                    summary['经销SKU数'] = value
                elif i == 8:  # 经销率
                    summary['经销率'] = value
                elif i == 9:  # 销售额
                    summary['销售额'] = value
                elif i == 10: # 多规格商品数
                    summary['多规格商品数'] = value
            
            return summary
        return {}
    
    def get_category_analysis(self):
        """获取分类分析数据"""
        return self.data['category_l1']
    
    def get_role_analysis(self):
        """获取商品角色分析数据"""
        return self.data['role_analysis']
    
    def get_price_analysis(self):
        """获取价格带分析数据"""
        return self.data['price_analysis']

class SmartLayoutManager:
    """智能布局管理器 - 根据数据复杂度自动调整图表尺寸"""
    
    @staticmethod
    def calculate_heatmap_dimensions(data):
        """计算热力图最优尺寸"""
        if data.empty:
            return 800, 500
        
        # 根据数据维度计算尺寸
        rows = len(data)
        cols = len(data.columns) if hasattr(data, 'columns') else 1
        
        # 基本尺寸计算
        base_width = 800
        base_height = max(500, rows * 25 + 150)  # 每行25px + 边距
        
        # 最大限制
        max_width = 1200
        max_height = 800
        
        width = min(base_width, max_width)
        height = min(base_height, max_height)
        
        return width, height
    
    @staticmethod
    def calculate_pie_dimensions(categories):
        """计算饼图最优尺寸"""
        num_categories = len(categories) if categories else 4
        
        # 根据分类数量调整尺寸
        if num_categories <= 4:
            return 600, 600
        elif num_categories <= 8:
            return 700, 700
        else:
            return 800, 800
    
    @staticmethod
    def calculate_bar_dimensions(data_length):
        """计算柱状图最优尺寸"""
        base_height = 500
        if data_length > 10:
            base_height = 600
        if data_length > 15:
            base_height = 700
        
        return 900, base_height


class DashboardComponents:
    """仪表板组件类 - 提供智能自适应的图表组件"""
    
    @staticmethod
    def create_kpi_cards(kpi_data):
        """创建KPI卡片组件"""
        if not kpi_data:
            return html.Div("暂无KPI数据")
        
        # 定义KPI卡片配置
        kpi_configs = [
            {
                'key': '总SKU数(含规格)',
                'title': '总SKU数',
                'icon': 'fas fa-boxes'
            },
            {
                'key': '动销SKU数',
                'title': '动销SKU数',
                'icon': 'fas fa-chart-line'
            },
            {
                'key': '动销率',
                'title': '动销率',
                'icon': 'fas fa-percentage',
                'format': 'percent'
            },
            {
                'key': '总销售额(去重后)',
                'title': '总销售额',
                'icon': 'fas fa-yen-sign',
                'format': 'currency'
            }
        ]
        
        cards = []
        colors = ['#007bff', '#28a745', '#17a2b8', '#ffc107']
        
        for idx, config in enumerate(kpi_configs):
            if config['key'] in kpi_data:
                value = kpi_data[config['key']]
                
                # 格式化数值
                if config.get('format') == 'percent':
                    formatted_value = f"{value:.1%}"
                elif config.get('format') == 'currency':
                    formatted_value = f"¥{value:,.0f}"
                else:
                    formatted_value = f"{value:,.0f}"
                
                card = html.Div([
                    html.Div([
                        html.I(className=config['icon'] + " fa-lg"),
                        html.H5(formatted_value, style={'margin': '5px 0', 'fontWeight': 'bold'}),
                        html.P(config['title'], style={'margin': '0', 'fontSize': '0.9rem', 'color': '#6c757d'})
                    ], style={'textAlign': 'center'})
                ], style={
                    'backgroundColor': 'white',
                    'border': f'2px solid {colors[idx]}',
                    'borderRadius': '8px',
                    'padding': '15px',
                    'height': '100px',
                    'display': 'flex',
                    'alignItems': 'center',
                    'justifyContent': 'center',
                    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'transition': 'transform 0.2s'
                })
                
                cards.append(card)
        
        return html.Div([
            html.Div(cards, style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))',
                'gap': '15px',
                'width': '100%'
            })
        ])
    
    @staticmethod
    def create_category_heatmap(category_data):
        """创建智能自适应的分类热力图"""
        if category_data.empty:
            return dcc.Graph(figure=px.scatter(title="暂无分类数据"), style={'height': '400px'})
        
        print(f"热力图数据维度: {category_data.shape}")
        
        # 智能选择最重要的指标
        numeric_cols = category_data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return dcc.Graph(figure=px.scatter(title="数值列不足"), style={'height': '400px'})
        
        # 优先级排序选择指标
        priority_map = {
            '动销率': 100,
            'sku数': 90,
            '销售额': 85,
            '占比': 80,
            '折扣': 75,
            '活动': 70,
            '库存': 65
        }
        
        # 按优先级排序
        scored_cols = []
        for col in numeric_cols:
            score = 0
            for keyword, weight in priority_map.items():
                if keyword in str(col):
                    score += weight
            scored_cols.append((col, score))
        
        # 选择前6个最重要的指标
        scored_cols.sort(key=lambda x: x[1], reverse=True)
        selected_cols = [col for col, score in scored_cols[:6]]
        
        if not selected_cols:
            selected_cols = numeric_cols[:6]
        
        # 准备数据
        if category_data.columns[0] and category_data[category_data.columns[0]].dtype == 'object':
            heatmap_data = category_data.set_index(category_data.columns[0])[selected_cols]
        else:
            heatmap_data = category_data[selected_cols]
            heatmap_data.index = [f"分类{i+1}" for i in range(len(heatmap_data))]
        
        if heatmap_data.empty:
            return dcc.Graph(figure=px.scatter(title="数据为空"), style={'height': '400px'})
        
        # 计算智能尺寸
        chart_width, chart_height = SmartLayoutManager.calculate_heatmap_dimensions(heatmap_data)
        
        # 标准化数据
        max_vals = heatmap_data.max()
        max_vals = max_vals.replace(0, 1)
        heatmap_normalized = heatmap_data.div(max_vals)
        
        # 简化列名
        clean_cols = []
        for col in selected_cols:
            clean_name = str(col).replace('美团一级分类', '').replace('(类内)', '').replace('(跨类)', '')
            if len(clean_name) > 10:
                clean_name = clean_name[:10] + '...'
            clean_cols.append(clean_name)
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_normalized.values.T,
            x=heatmap_data.index,
            y=clean_cols,
            colorscale='RdYlBu_r',
            text=heatmap_data.values.T,
            texttemplate="%{text:.1f}",
            textfont={"size": 10, "color": "black"},
            hoverongaps=False,
            hovertemplate='<b>%{y}</b><br>%{x}: %{text}<extra></extra>',
            colorbar=dict(title="数值范围")
        ))
        
        # 优化布局
        fig.update_layout(
            title={
                'text': "🔥 美团一级分类表现热力图",
                'x': 0.5,
                'font': {'size': 18}
            },
            width=chart_width,
            height=chart_height,
            margin=dict(l=150, r=100, t=80, b=100),
            xaxis={
                'tickangle': 45,
                'tickfont': {'size': 10}
            },
            yaxis={
                'tickfont': {'size': 11}
            },
            font=dict(size=12)
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': f'{chart_height}px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False
            }
        )
    
    @staticmethod
    def create_role_pie_chart(role_data):
        """创建商品角色饼图"""
        if role_data.empty:
            return dcc.Graph(figure=px.pie(title="暂无角色数据"))
        
        # 重置索引以获取角色名称
        if role_data.index.nlevels > 1:
            # 多层索引情况，取第二层（角色）
            role_summary = role_data.groupby(level=1).sum()
        else:
            role_summary = role_data
        
        if 'SKU数量' not in role_summary.columns:
            return dcc.Graph(figure=px.pie(title="数据格式不匹配"))
        
        fig = px.pie(
            values=role_summary['SKU数量'],
            names=role_summary.index,
            title="商品角色分布",
            color_discrete_map={
                '引流品': '#FF6B6B',
                '利润品': '#4ECDC4', 
                '形象品': '#45B7D1',
                '劣势品': '#96CEB4'
            }
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            height=400,
            width=None,
            margin=dict(l=40, r=40, t=60, b=40),
            showlegend=True,
            autosize=True,
            font=dict(size=12)
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': '400px', 'width': '100%'},
            config={'displayModeBar': False, 'staticPlot': False}
        )
    
    @staticmethod
    def create_price_distribution(price_data):
        """创建智能自适应的价格带分布图"""
        if price_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无价格带数据"), style={'height': '500px'})
        
        print(f"价格带数据维度: {price_data.shape}")
        
        # 智能计算图表尺寸
        chart_width, chart_height = SmartLayoutManager.calculate_bar_dimensions(len(price_data))
        
        # 智能匹配列名
        cols = price_data.columns.tolist()
        price_col = cols[0] if cols else 'price_band'
        sku_col = None
        revenue_col = None
        
        for col in cols:
            col_lower = str(col).lower()
            if 'sku' in col_lower or '数量' in col:
                sku_col = col
            elif '销售' in col or '金额' in col or 'revenue' in col_lower:
                revenue_col = col
        
        # 如果找不到，使用默认索引
        if not sku_col and len(cols) > 1:
            sku_col = cols[1]
        if not revenue_col and len(cols) > 2:
            revenue_col = cols[2]
        
        # 创建双轴图
        fig = make_subplots(
            specs=[[{"secondary_y": True}]],
            subplot_titles=["💰 价格带分布分析"]
        )
        
        # 添加SKU数量柱状图
        if sku_col and sku_col in price_data.columns:
            fig.add_trace(
                go.Bar(
                    x=price_data[price_col],
                    y=price_data[sku_col],
                    name="SKU数量",
                    marker_color='lightblue',
                    opacity=0.8,
                    text=price_data[sku_col],
                    textposition='outside',
                    textfont=dict(size=10)
                ),
                secondary_y=False,
            )
        
        # 添加销售额折线图
        if revenue_col and revenue_col in price_data.columns:
            fig.add_trace(
                go.Scatter(
                    x=price_data[price_col],
                    y=price_data[revenue_col],
                    mode='lines+markers',
                    name="销售额",
                    line=dict(color='red', width=3),
                    marker=dict(size=8, color='red'),
                    text=[f'{val:.0f}' for val in price_data[revenue_col]],
                    textposition='top center',
                    textfont=dict(size=10)
                ),
                secondary_y=True,
            )
        
        # 优化布局
        fig.update_xaxes(
            title_text="价格带",
            tickangle=45,
            tickfont=dict(size=11)
        )
        fig.update_yaxes(
            title_text="SKU数量",
            secondary_y=False,
            tickfont=dict(size=11)
        )
        fig.update_yaxes(
            title_text="销售额",
            secondary_y=True,
            tickfont=dict(size=11)
        )
        
        fig.update_layout(
            title={
                'text': "💰 价格带分布分析",
                'x': 0.5,
                'font': {'size': 18}
            },
            width=chart_width,
            height=chart_height,
            margin=dict(l=80, r=80, t=100, b=80),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                font=dict(size=12)
            ),
            font=dict(size=12),
            hovermode='x unified'
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': f'{chart_height}px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False
            }
        )

# 初始化Dash应用
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = APP_TITLE

# 添加自定义CSS样式
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            html, body {
                min-height: 100vh;
                width: 100vw;
                overflow-x: hidden;
                overflow-y: auto;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f8f9fa;
            }
            #react-entry-point {
                min-height: 100vh;
                width: 100vw;
                overflow-x: hidden;
                display: flex;
                flex-direction: column;
            }
            .dashboard-grid {
                display: grid;
                grid-template-rows: auto 1fr;
                min-height: 100vh;
                width: 100vw;
                overflow-x: hidden;
            }
            .kpi-section {
                background-color: white;
                padding: 10px 15px;
                border-bottom: 2px solid #e9ecef;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                z-index: 1000;
            }
            .content-section {
                overflow-y: auto;
                overflow-x: hidden;
                padding: 15px;
                height: calc(100vh - 150px);
            }
            .chart-row {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 15px;
                margin-bottom: 15px;
                height: 320px;
            }
            .chart-container {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border: 1px solid #e9ecef;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            }
            .chart-title {
                color: #2c3e50;
                font-weight: 600;
                margin-bottom: 10px;
                border-bottom: 2px solid #3498db;
                padding-bottom: 5px;
                font-size: 1.1rem;
                flex-shrink: 0;
            }
            .chart-content {
                flex: 1;
                overflow: hidden;
                min-height: 0;
            }
            .kpi-card {
                height: 100px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .full-width-chart {
                grid-column: 1 / -1;
                height: 320px;
            }
            .table-container {
                grid-column: 1 / -1;
                height: 200px;
                overflow: hidden;
            }
            /* 确保Plotly图表不会溢出 */
            .js-plotly-plot {
                width: 100% !important;
                height: 100% !important;
                max-width: 100% !important;
                max-height: 100% !important;
            }
            .dash-table-container {
                height: 250px !important;
                overflow-y: auto !important;
            }
        </style>
    </head>
    <body>
        <div id="dashboard-wrapper">
            {%app_entry%}
        </div>
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // 强制禁用所有滚动
                document.body.style.overflow = 'hidden';
                document.documentElement.style.overflow = 'hidden';
                window.scrollTo(0, 0);
                
                // 监听任何可能导致滚动的事件
                window.addEventListener('scroll', function(e) {
                    window.scrollTo(0, 0);
                });
                
                // 禁用方向键滚动
                window.addEventListener('keydown', function(e) {
                    if([32, 33, 34, 35, 36, 37, 38, 39, 40].indexOf(e.keyCode) > -1) {
                        e.preventDefault();
                    }
                }, false);
            });
        </script>
    </body>
</html>
'''

# 全局数据加载器
data_loader = None

def init_data_loader():
    """初始化数据加载器"""
    global data_loader
    
    # 查找最新的报告文件
    reports_dir = Path("./reports")
    if reports_dir.exists():
        excel_files = list(reports_dir.glob("*.xlsx"))
        # 过滤掉锁文件
        excel_files = [f for f in excel_files if not f.name.startswith('~$')]
        
        if excel_files:
            # 按修改时间排序，取最新的
            latest_file = max(excel_files, key=lambda f: f.stat().st_mtime)
            data_loader = DataLoader(str(latest_file))
            return True
    
    # 回退到默认路径
    if Path(DEFAULT_REPORT_PATH).exists():
        data_loader = DataLoader(DEFAULT_REPORT_PATH)
        return True
    
    print("❌ 未找到Excel报告文件，请先运行数据分析脚本生成报告")
    return False

# 应用布局
def create_layout():
    """创建应用布局"""
    if not data_loader:
        return html.Div([
            dbc.Alert("未找到数据文件，请先运行数据分析脚本生成Excel报告", color="danger"),
            html.P("请确保reports目录下存在分析报告文件")
        ], className="main-container")
    
    kpi_data = data_loader.get_kpi_summary()
    category_data = data_loader.get_category_analysis()
    role_data = data_loader.get_role_analysis()
    price_data = data_loader.get_price_analysis()
    
    return html.Div([
        # 固定KPI区域
        html.Div([
            html.Div([
                html.H2(APP_TITLE, 
                       style={'color': '#2c3e50', 'fontWeight': '700', 'margin': '0 0 10px 0', 'fontSize': '1.5rem'}),
                DashboardComponents.create_kpi_cards(kpi_data)
            ], style={'maxWidth': '1200px', 'margin': '0 auto'})
        ], className="kpi-section"),
        
        # 主要内容区域
        html.Div([
            html.Div([
                # 第一行：热力图 + 饼图
                html.Div([
                    html.Div([
                        html.H4("分类表现热力图", className="chart-title"),
                        html.Div([
                            DashboardComponents.create_category_heatmap(category_data)
                        ], className="chart-content")
                    ], className="chart-container"),
                    html.Div([
                        html.H4("商品角色分析", className="chart-title"),
                        html.Div([
                            DashboardComponents.create_role_pie_chart(role_data)
                        ], className="chart-content")
                    ], className="chart-container")
                ], className="chart-row"),
                
                # 第二行：价格带分析
                html.Div([
                    html.Div([
                        html.H4("价格带分布分析", className="chart-title"),
                        html.Div([
                            DashboardComponents.create_price_distribution(price_data)
                        ], className="chart-content")
                    ], className="chart-container full-width-chart")
                ], style={'display': 'grid', 'gap': '15px', 'marginBottom': '15px'}),
                
                # 第三行：数据表格
                html.Div([
                    html.Div([
                        html.H4("美团一级分类详细数据", className="chart-title"),
                        html.Div(id="category-table", className="chart-content")
                    ], className="chart-container table-container")
                ], style={'display': 'grid', 'gap': '15px'})
                
            ], style={'maxWidth': '1200px', 'margin': '0 auto'})
        ], className="content-section")
    ], className="dashboard-grid")

@callback(
    Output('category-table', 'children'),
    Input('category-table', 'id')  # 触发器
)
def update_category_table(_):
    """更新分类数据表格"""
    if not data_loader:
        return html.Div("暂无数据")
    
    category_data = data_loader.get_category_analysis()
    if category_data.empty:
        return html.Div("暂无分类数据")
    
    # 选择关键列显示
    display_columns = [
        'l1_category', '美团一级分类sku数', '美团一级分类动销sku数', 
        '美团一级分类动销率(类内)', '月售', '美团一级分类月售占比'
    ]
    available_columns = [col for col in display_columns if col in category_data.columns]
    
    if not available_columns:
        return html.Div("数据格式不匹配")
    
    display_data = category_data[available_columns].round(4)
    
    return dash_table.DataTable(
        data=display_data.to_dict('records'),
        columns=[{"name": col, "id": col} for col in display_data.columns],
        style_cell={
            'textAlign': 'center', 
            'fontSize': 12, 
            'padding': '10px',
            'fontFamily': 'Arial, sans-serif'
        },
        style_header={
            'backgroundColor': '#3498db', 
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center'
        },
        style_data={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #dee2e6'
        },
        style_table={
            'height': '200px', 
            'overflowY': 'auto',
            'border': '1px solid #dee2e6',
            'borderRadius': '5px'
        },
        page_size=8,
        sort_action="native",
        filter_action="native"
    )

# 设置应用布局
if init_data_loader():
    app.layout = create_layout()
else:
    app.layout = html.Div([
        dbc.Alert([
            html.H4("数据文件未找到"),
            html.P("请先运行以下命令生成数据报告："),
            html.Code("python untitled1.py"),
            html.P("然后刷新此页面", className="mt-2")
        ], color="warning")
    ])

if __name__ == '__main__':
    print(f"🚀 启动{APP_TITLE}...")
    print("📊 访问地址: http://localhost:8052")
    app.run(debug=True, host='localhost', port=8052)