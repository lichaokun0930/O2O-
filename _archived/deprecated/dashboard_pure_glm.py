# -*- coding: utf-8 -*-
"""
O2O门店数据分析看板 v2.0 - 智能自适应版本
基于Dash + Plotly构建的可视化数据看板，具备智能面积识别功能

运行方式：
    python dashboard_v2.py

功能：
- 智能面积识别，自动调整图表尺寸
- 自适应布局系统
- 高质量数据可视化
- 交互式数据探索
"""

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ALL
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
import os
from datetime import datetime
import base64
import io

# AI分析相关导入
from ai_analyzer import get_ai_analyzer
from ai_business_context import get_business_context, get_kpi_definitions

# PDF生成相关库
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from PIL import Image

# 全局配置
DEFAULT_REPORT_PATH = "./reports/竞对分析报告_v3.4_FINAL.xlsx"
APP_TITLE = "O2O门店数据分析看板 v2.0"

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
            # 支持文件路径或BytesIO对象
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
            
            if len(sheet_names) > 6:
                # 第七个sheet通常是详细SKU报告(去重后)
                self.data['sku_details'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[6])
            
            # 填充缺失的数据
            for key in ['kpi', 'category_l1', 'role_analysis', 'price_analysis', 'sku_details']:
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
            
            # 根据实际Excel列顺序映射
            # A:门店 B:总SKU数(含规格) C:单规格SPU数 D:单规格SKU数 E:多规格SKU总数 
            # F:总SKU数(去重后) G:动销SKU数 H:滞销SKU数 I:总销售额(去重后) J:动销率 K:唯一多规格商品数
            for i, col in enumerate(kpi_df.columns):
                value = row.iloc[i] if i < len(row) else 0
                if i == 0:  # 门店
                    summary['门店'] = value
                elif i == 1:  # 总SKU数(含规格)
                    summary['总SKU数(含规格)'] = value
                elif i == 4:  # 多规格SKU总数
                    summary['多规格SKU总数'] = value
                elif i == 6:  # 动销SKU数
                    summary['动销SKU数'] = value
                elif i == 7:  # 滞销SKU数
                    summary['滞销SKU数'] = value
                elif i == 8:  # 总销售额(去重后)
                    summary['总销售额(去重后)'] = value
                elif i == 9:  # 动销率
                    summary['动销率'] = value
                elif i == 10:  # 唯一多规格商品数
                    summary['唯一多规格商品数'] = value
            
            # 从美团一级分类详细指标中获取门店爆品数和平均折扣
            if not self.data['category_l1'].empty:
                category_df = self.data['category_l1']
                # X列(索引23): 美团一级分类爆品sku数
                if len(category_df.columns) > 23:
                    summary['门店爆品数'] = category_df.iloc[:, 23].sum()
                # Y列(索引24): 美团一级分类折扣
                if len(category_df.columns) > 24:
                    # 过滤掉非数值，计算平均值
                    discount_col = pd.to_numeric(category_df.iloc[:, 24], errors='coerce')
                    summary['门店平均折扣'] = discount_col.mean()
            
            # ========== 新增指标计算 ==========
            # 从SKU详细数据计算新指标
            if not self.data['sku_details'].empty:
                sku_df = self.data['sku_details']
                
                # 1. 平均SKU单价 (B列-售价的平均值)
                if len(sku_df.columns) > 1:
                    price_col = pd.to_numeric(sku_df.iloc[:, 1], errors='coerce')
                    summary['平均SKU单价'] = price_col.mean()
                
                # 2. 高价值SKU占比 (售价>50元的SKU数 / 总SKU数)
                if len(sku_df.columns) > 1 and '总SKU数(去重后)' in summary:
                    high_value_count = (pd.to_numeric(sku_df.iloc[:, 1], errors='coerce') > 50).sum()
                    total_skus = summary['总SKU数(去重后)']
                    summary['高价值SKU占比'] = (high_value_count / total_skus) if total_skus > 0 else 0
                
                # 3. 爆款集中度 (TOP10商品销售额 / 总销售额)
                if len(sku_df.columns) > 2 and '总销售额(去重后)' in summary:
                    # 计算每个SKU的销售额 = 售价(B列) × 月售(C列)
                    price_col = pd.to_numeric(sku_df.iloc[:, 1], errors='coerce').fillna(0)
                    sales_col = pd.to_numeric(sku_df.iloc[:, 2], errors='coerce').fillna(0)
                    sku_df_temp = sku_df.copy()
                    sku_df_temp['revenue'] = price_col * sales_col
                    
                    # TOP10销售额
                    top10_revenue = sku_df_temp.nlargest(10, 'revenue')['revenue'].sum()
                    total_revenue = summary['总销售额(去重后)']
                    summary['爆款集中度'] = (top10_revenue / total_revenue) if total_revenue > 0 else 0
            
            # 5. 促销强度 (折扣商品数 / 动销SKU数)
            if not self.data['category_l1'].empty and '动销SKU数' in summary:
                category_df = self.data['category_l1']
                # W列(索引22): 美团一级分类折扣sku数
                if len(category_df.columns) > 22:
                    total_discount_skus = pd.to_numeric(category_df.iloc[:, 22], errors='coerce').sum()
                    active_skus = summary['动销SKU数']
                    summary['促销强度'] = (total_discount_skus / active_skus) if active_skus > 0 else 0
            
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
            return 900, 600
        
        rows = len(data)
        cols = len(data.columns) if hasattr(data, 'columns') else 1
        
        # 智能尺寸计算
        base_width = 900
        base_height = max(600, rows * 30 + 200)  # 每行30px + 边距
        
        # 最大限制
        max_width = 1400
        max_height = 900
        
        width = min(base_width, max_width)
        height = min(base_height, max_height)
        
        return width, height
    
    @staticmethod
    def calculate_pie_dimensions(categories):
        """计算饼图最优尺寸"""
        num_categories = len(categories) if categories else 4
        
        # 根据分类数量调整尺寸
        if num_categories <= 4:
            return 700, 700
        elif num_categories <= 8:
            return 800, 800
        else:
            return 900, 900
    
    @staticmethod
    def calculate_bar_dimensions(data_length):
        """计算柱状图最优尺寸"""
        base_height = 600
        if data_length > 10:
            base_height = 700
        if data_length > 15:
            base_height = 800
        
        return 1000, base_height


class DashboardComponents:
    """仪表板组件类 - 提供智能自适应的图表组件"""
    
    @staticmethod
    def create_insights_panel(insights):
        """创建洞察面板"""
        if not insights:
            return None
        
        insight_items = []
        for insight in insights:
            # 兼容两种格式：{icon, text} 或 {title, content}
            icon = insight.get('icon', '💡')
            title = insight.get('title', '')
            content = insight.get('content', '')
            text = insight.get('text', '')
            level = insight.get('level', 'info')  # success, warning, danger, info
            
            # 优先使用 title+content，其次使用 text
            display_text = f"{title}" if title else text
            if content and title:
                display_text = f"{title}: {content}"
            elif content:
                display_text = content
            
            color_map = {
                'success': 'success',
                'warning': 'warning', 
                'danger': 'danger',
                'info': 'info',
                'primary': 'primary'
            }
            
            insight_items.append(
                html.Div([
                    html.Span(icon, className="me-2", style={'fontSize': '1.2rem'}),
                    html.Span(display_text, className="fw-normal")
                ], className=f"alert alert-{color_map.get(level, 'info')} mb-2 py-2 px-3 d-flex align-items-center",
                   style={'fontSize': '0.9rem'})
            )
        
        return html.Div([
            html.H6("🔍 关键洞察", className="mb-3 fw-bold"),
            html.Div(insight_items)
        ], className="mt-3 p-3", style={'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
    
    @staticmethod
    def create_kpi_cards(kpi_data):
        """创建智能KPI卡片组件"""
        if not kpi_data:
            return html.Div("暂无KPI数据", className="text-center text-muted p-4")
        
        # KPI卡片配置 - 13个核心指标（原9个 + 新增4个）
        kpi_configs = [
            {
                'key': '总SKU数(含规格)', 'title': '总SKU数(含规格)', 'icon': '📦', 'color': 'primary',
                'definition': '所有商品规格的总数量，包括多规格商品的各个子SKU。用于衡量商品丰富度。'
            },
            {
                'key': '多规格SKU总数', 'title': '多规格SKU总数', 'icon': '🧩', 'color': 'secondary',
                'definition': '同一商品拥有多个规格选项的SKU数量。例如：可乐(300ml/500ml/1L)算3个多规格SKU。'
            },
            {
                'key': '动销SKU数', 'title': '动销SKU数', 'icon': '📈', 'color': 'success',
                'definition': '有实际销量的商品数量（月售>0）。反映门店商品的活跃程度。'
            },
            {
                'key': '滞销SKU数', 'title': '滞销SKU数', 'icon': '📉', 'color': 'danger',
                'definition': '月销量为0的商品数量。滞销商品占用库存资源，建议及时优化。'
            },
            {
                'key': '总销售额(去重后)', 'title': '总销售额(去重后)', 'icon': '💰', 'color': 'warning', 'format': 'currency',
                'definition': '门店当期总销售收入，已去除多规格商品的重复计算。用于评估门店整体营收能力。'
            },
            {
                'key': '动销率', 'title': '动销率', 'icon': '💹', 'color': 'info', 'format': 'percent',
                'definition': '动销SKU数 ÷ 总SKU数。反映商品周转效率，建议保持在60%以上。'
            },
            {
                'key': '唯一多规格商品数', 'title': '唯一多规格商品数', 'icon': '🔀', 'color': 'dark',
                'definition': '去重后的多规格商品种类数。例如：可乐有3个规格，但只算1个唯一商品。'
            },
            {
                'key': '门店爆品数', 'title': '门店爆品数', 'icon': '🔥', 'color': 'danger',
                'definition': '月销量超过10的热销商品数量。爆品驱动门店销售增长。'
            },
            {
                'key': '门店平均折扣', 'title': '门店平均折扣', 'icon': '🏷️', 'color': 'success', 'format': 'discount',
                'definition': '门店所有商品的平均折扣力度（售价÷原价）。7.8折表示平均优惠22%。'
            },
            {
                'key': '平均SKU单价', 'title': '平均SKU单价', 'icon': '🔖', 'color': 'info', 'format': 'currency',
                'definition': '门店商品的平均售价。反映门店价格定位：高单价=高端定位，低单价=大众定位。'
            },
            {
                'key': '高价值SKU占比', 'title': '高价值SKU占比(>50元)', 'icon': '💎', 'color': 'primary', 'format': 'percent',
                'definition': '售价超过50元的商品占比。高价值商品占比高说明门店盈利能力强。'
            },
            {
                'key': '促销强度', 'title': '促销强度', 'icon': '📊', 'color': 'success', 'format': 'percent',
                'definition': '参与促销活动的商品比例。高促销强度可提升销量但会影响利润率。'
            },
            {
                'key': '爆款集中度', 'title': '爆款集中度(TOP10)', 'icon': '🚀', 'color': 'danger', 'format': 'percent',
                'definition': 'TOP10爆款商品的销售额占比。过高(>60%)说明依赖爆款，需优化长尾商品。'
            }
        ]
        
        cards = []
        for idx, config in enumerate(kpi_configs):
            key = config['key']
            if key in kpi_data:
                value = kpi_data[key]
                
                # 格式化数值
                if config.get('format') == 'percent':
                    formatted_value = f"{value:.1%}" if isinstance(value, (int, float)) else str(value)
                elif config.get('format') == 'currency':
                    formatted_value = f"¥{value:,.0f}" if isinstance(value, (int, float)) else str(value)
                elif config.get('format') == 'discount':
                    formatted_value = f"{value:.1f}折" if isinstance(value, (int, float)) else str(value)
                else:
                    formatted_value = f"{value:,}" if isinstance(value, (int, float)) else str(value)
                
                card = dbc.Card([
                    dbc.CardBody([
                        # 右上角问号图标
                        html.Div([
                            html.I(
                                className="bi bi-question-circle",
                                id={'type': 'kpi-help', 'index': idx},
                                style={
                                    'position': 'absolute',
                                    'top': '8px',
                                    'right': '8px',
                                    'fontSize': '1.1rem',
                                    'cursor': 'pointer',
                                    'color': '#6c757d',
                                    'opacity': '0.7',
                                    'transition': 'all 0.2s'
                                }
                                # 移除 n_clicks 初始化，避免触发初始回调
                            ),
                        ]),
                        # 卡片主体内容
                        html.Div([
                            html.Div(config['icon'], 
                                    style={'fontSize': '2.5rem', 'marginBottom': '0.5rem'},
                                    className="text-center"),
                            html.H4(formatted_value, 
                                   className="mb-1 text-center",
                                   style={'fontWeight': 'bold', 'fontSize': '1.5rem'}),
                            html.P(config['title'], 
                                  className="text-muted mb-0 text-center",
                                  style={'fontSize': '0.85rem', 'lineHeight': '1.2'})
                        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})
                    ], style={'padding': '1rem', 'position': 'relative'})
                ], color=config['color'], outline=True, className="h-100", style={'minHeight': '150px'})
                
                # 直接使用内联样式确保6列布局
                cards.append(dbc.Col(card, style={'flex': '0 0 16.666667%', 'maxWidth': '16.666667%'}, className="mb-3"))
        
        return dbc.Row(cards, style={'display': 'flex', 'flexWrap': 'wrap'})
    
    @staticmethod
    def create_category_heatmap(category_data):
        """创建智能自适应的分类热力图"""
        if category_data.empty:
            return dcc.Graph(figure=px.scatter(title="暂无分类数据"), style={'height': '600px'})
        
        print(f"🔥 热力图数据维度: {category_data.shape}")
        print(f"🔥 数据列名: {category_data.columns.tolist()[:5]}...")  # 只显示前5个
        print(f"🔥 数据预览: \n{category_data.head(3)}")
        
        # 智能选择最重要的指标
        numeric_cols = category_data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return dcc.Graph(figure=px.scatter(title="数值列不足"), style={'height': '600px'})
        
        # 优先级排序选择指标
        priority_map = {
            '动销率': 100, 'sku数': 90, '销售额': 85, '占比': 80, 
            '折扣': 75, '活动': 70, '库存': 65
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
            heatmap_data = category_data[selected_cols].copy()
            heatmap_data.index = [f"分类{i+1}" for i in range(len(heatmap_data))]
        
        if heatmap_data.empty:
            return dcc.Graph(figure=px.scatter(title="数据为空"), style={'height': '600px'})
        
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
            if len(clean_name) > 12:
                clean_name = clean_name[:12] + '...'
            clean_cols.append(clean_name)
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_normalized.values.T,
            x=heatmap_data.index,
            y=clean_cols,
            colorscale='RdYlBu_r',
            text=heatmap_data.values.T,
            texttemplate="%{text:.1f}",
            textfont={"size": 11, "color": "black"},
            hoverongaps=False,
            hovertemplate='<b>%{y}</b><br>%{x}: %{z}<extra></extra>',
            colorbar=dict(title=dict(text="数值范围", font=dict(size=12)))
        ))
        
        # 优化布局
        fig.update_layout(
            title={
                'text': "🔥 美团一级分类表现热力图",
                'x': 0.5,
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            width=chart_width,
            height=chart_height,
            margin=dict(l=150, r=80, t=80, b=80),
            xaxis={
                'tickangle': 45,
                'tickfont': {'size': 10}
            },
            yaxis={
                'tickfont': {'size': 11}
            },
            font=dict(size=11),
            paper_bgcolor='white',
            plot_bgcolor='white',
            autosize=False
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': f'{chart_height}px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False,
                'responsive': True
            }
        )
    
    @staticmethod
    def create_role_pie_chart(role_data):
        """创建智能自适应的商品角色饼图"""
        if role_data.empty:
            # 创建示例数据
            labels = ['引流品', '利润品', '形象品', '劣势品']
            values = [30, 40, 20, 10]
        else:
            print(f"🎭 角色数据维度: {role_data.shape}")
            
            # 智能数据提取
            if 'role' in role_data.columns and 'count' in role_data.columns:
                labels = role_data['role'].tolist()
                values = role_data['count'].tolist()
            elif len(role_data.columns) >= 2:
                labels = role_data.iloc[:, 0].tolist()
                values = role_data.iloc[:, 1].tolist()
            else:
                labels = ['引流品', '利润品', '形象品', '劣势品']
                values = [30, 40, 20, 10]
        
        # 计算智能尺寸
        chart_width, chart_height = SmartLayoutManager.calculate_pie_dimensions(labels)
        
        # 预定义角色和颜色
        role_colors = {
            '引流品': '#FF6B6B', '利润品': '#4ECDC4', '形象品': '#45B7D1', '劣势品': '#96CEB4',
            '0': '#FFD93D', '1': '#6BCF7F', '2': '#4D96FF', '3': '#9B59B6'
        }
        
        # 获取颜色
        colors = [role_colors.get(str(label), f'hsl({i*360//len(labels)}, 70%, 60%)') 
                 for i, label in enumerate(labels)]
        
        # 创建饼图
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # 空心饼图，更美观
            marker=dict(
                colors=colors,
                line=dict(color='white', width=3)
            ),
            textinfo='label+percent+value',
            textposition='auto',
            textfont=dict(size=14),
            hovertemplate='<b>%{label}</b><br>' +
                         '数量: %{value}<br>' +
                         '占比: %{percent}<br>' +
                         '<extra></extra>'
        )])
        
        # 优化布局
        fig.update_layout(
            title={
                'text': "🎭 商品角色分布",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            width=chart_width,
            height=chart_height,
            margin=dict(l=80, r=120, t=100, b=80),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(size=14)
            ),
            font=dict(size=14),
            paper_bgcolor='white'
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': f'{chart_height}px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False,
                'responsive': True
            }
        )
    
    @staticmethod
    def create_category_sales_analysis(category_data):
        """创建一级分类动销分析图表"""
        if category_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无分类数据"), style={'height': '700px'})
        
        print(f"📊 分类数据维度: {category_data.shape}")
        print(f"📊 列名: {category_data.columns.tolist()}")
        
        # 提取关键列：A=一级分类, E=去重SKU数, F=动销SKU数, G=动销率
        category_col = category_data.iloc[:, 0]  # A列：一级分类
        total_sku_col = category_data.iloc[:, 4]  # E列：去重SKU数
        active_sku_col = category_data.iloc[:, 5]  # F列：动销SKU数
        active_rate_col = category_data.iloc[:, 6]  # G列：动销率
        
        # 创建双Y轴图表
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加SKU总数柱状图（浅蓝色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=total_sku_col,
                name="分类SKU总数",
                marker_color='lightblue',
                opacity=0.7,
                text=[int(val) if pd.notna(val) else 0 for val in total_sku_col],
                textposition='outside',
                textfont=dict(size=10),
                hovertemplate='SKU总数: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加动销SKU数柱状图（深蓝色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=active_sku_col,
                name="动销SKU数",
                marker_color='#1f77b4',
                opacity=0.9,
                text=[int(val) if pd.notna(val) else 0 for val in active_sku_col],
                textposition='outside',
                textfont=dict(size=10),
                hovertemplate='动销SKU数: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加动销率折线图（红色）
        formatted_rate = []
        for val in active_rate_col:
            if pd.notna(val):
                formatted_rate.append(f'{val*100:.1f}%')
            else:
                formatted_rate.append('0%')
        
        fig.add_trace(
            go.Scatter(
                x=category_col,
                y=active_rate_col * 100,  # 转换为百分比
                mode='lines+markers+text',
                name="动销率",
                line=dict(color='red', width=3),
                marker=dict(size=8, color='red'),
                text=formatted_rate,
                textposition='top center',
                textfont=dict(size=10, color='red', family='Arial Black'),
                hovertemplate='动销率: %{text}<extra></extra>'
            ),
            secondary_y=True,
        )
        
        # 优化布局
        fig.update_xaxes(
            title_text="一级分类",
            tickangle=45,
            tickfont=dict(size=11),
            title_font=dict(size=14)
        )
        fig.update_yaxes(
            title_text="SKU数量",
            secondary_y=False,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',
            separatethousands=True
        )
        fig.update_yaxes(
            title_text="动销率 (%)",
            secondary_y=True,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            range=[0, 100]  # 动销率范围0-100%
        )
        
        fig.update_layout(
            title={
                'text': "📊 一级分类动销分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=700,
            margin=dict(l=80, r=80, t=100, b=150),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            ),
            font=dict(size=12),
            hovermode='x',
            paper_bgcolor='white',
            plot_bgcolor='white',
            bargap=0.15,
            bargroupgap=0.1
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_category_sales_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                id='category-sales-graph',  # 【新增】添加ID用于监听点击事件
                figure=fig,
                style={'height': '700px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def create_multispec_supply_analysis(category_data):
        """创建多规格商品供给分析图表"""
        if category_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无分类数据"), style={'height': '700px'})
        
        print(f"🔀 多规格供给数据维度: {category_data.shape}")
        
        # 提取关键列：A=一级分类, B=总SKU数, C=多规格SKU数
        category_col = category_data.iloc[:, 0]  # A列：一级分类
        total_sku_col = category_data.iloc[:, 1]  # B列：总SKU数
        multispec_sku_col = category_data.iloc[:, 2]  # C列：多规格SKU数
        
        # 计算单规格SKU数和多规格占比
        single_sku_col = total_sku_col - multispec_sku_col
        multispec_ratio = (multispec_sku_col / total_sku_col * 100).fillna(0)
        
        # 创建双Y轴图表
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加单规格SKU柱状图（底部，浅灰色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=single_sku_col,
                name="单规格SKU",
                marker_color='lightgray',
                opacity=0.8,
                text=[int(val) if pd.notna(val) else 0 for val in single_sku_col],
                textposition='inside',
                textfont=dict(size=9),
                hovertemplate='单规格SKU: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加多规格SKU柱状图（顶部，橙色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=multispec_sku_col,
                name="多规格SKU",
                marker_color='#ff7f0e',
                opacity=0.9,
                text=[int(val) if pd.notna(val) else 0 for val in multispec_sku_col],
                textposition='inside',
                textfont=dict(size=9, color='white'),
                hovertemplate='多规格SKU: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加多规格占比折线图（蓝色）
        formatted_ratio = []
        for val in multispec_ratio:
            if pd.notna(val):
                formatted_ratio.append(f'{val:.1f}%')
            else:
                formatted_ratio.append('0%')
        
        fig.add_trace(
            go.Scatter(
                x=category_col,
                y=multispec_ratio,
                mode='lines+markers+text',
                name="多规格占比",
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8, color='#1f77b4'),
                text=formatted_ratio,
                textposition='top center',
                textfont=dict(size=10, color='#1f77b4', family='Arial Black'),
                hovertemplate='多规格占比: %{text}<extra></extra>'
            ),
            secondary_y=True,
        )
        
        # 优化布局
        fig.update_xaxes(
            title_text="一级分类",
            tickangle=45,
            tickfont=dict(size=11),
            title_font=dict(size=14)
        )
        fig.update_yaxes(
            title_text="SKU数量",
            secondary_y=False,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',
            separatethousands=True
        )
        fig.update_yaxes(
            title_text="多规格占比 (%)",
            secondary_y=True,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            range=[0, 100]
        )
        
        fig.update_layout(
            title={
                'text': "🔀 多规格商品供给分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=700,
            margin=dict(l=80, r=80, t=100, b=150),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            ),
            font=dict(size=12),
            hovermode='x',
            paper_bgcolor='white',
            plot_bgcolor='white',
            barmode='stack',  # 堆叠模式
            bargap=0.2
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_multispec_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '700px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_kpi_insights(kpi_data):
        """生成KPI数据洞察"""
        insights = []
        
        if '动销率' in kpi_data:
            rate = kpi_data['动销率']
            if rate >= 0.7:
                insights.append({'icon': '🎯', 'text': f'动销率达到 {rate:.1%},库存周转健康', 'level': 'success'})
            elif rate >= 0.5:
                insights.append({'icon': '⚠️', 'text': f'动销率为 {rate:.1%},建议优化滞销商品', 'level': 'warning'})
            else:
                insights.append({'icon': '🚨', 'text': f'动销率仅 {rate:.1%},需清理滞销品', 'level': 'danger'})
        
        if '多规格SKU总数' in kpi_data and '总SKU数(含规格)' in kpi_data:
            total = kpi_data['总SKU数(含规格)']
            multi = kpi_data['多规格SKU总数']
            if total > 0:
                ratio = multi / total
                if ratio >= 0.3:
                    insights.append({'icon': '🧩', 'text': f'多规格商品占比 {ratio:.1%},供给结构丰富', 'level': 'info'})
                elif ratio < 0.15:
                    insights.append({'icon': '📦', 'text': f'多规格商品仅占 {ratio:.1%},可丰富规格选择', 'level': 'info'})
        
        if '总销售额(去重后)' in kpi_data and '总SKU数(含规格)' in kpi_data:
            revenue = kpi_data['总销售额(去重后)']
            sku_count = kpi_data['总SKU数(含规格)']
            if sku_count > 0:
                avg_revenue = revenue / sku_count
                if avg_revenue > 100:
                    insights.append({'icon': '💰', 'text': f'单SKU均销售额 ¥{avg_revenue:.0f},坪效优秀', 'level': 'success'})
        
        return insights
    
    @staticmethod
    def generate_price_insights(price_data):
        """生成价格带洞察"""
        insights = []
        
        if price_data.empty:
            return insights
        
        # 计算总销售额和各价格带占比
        cols = price_data.columns.tolist()
        if len(cols) < 3:
            return insights
            
        total_revenue = price_data.iloc[:, 2].sum()
        price_data_copy = price_data.copy()
        price_data_copy['revenue_pct'] = price_data_copy.iloc[:, 2] / total_revenue
        
        # 找出主力价格带
        max_revenue_idx = price_data_copy['revenue_pct'].idxmax()
        max_price_band = price_data_copy.iloc[max_revenue_idx, 0]
        max_revenue_pct = price_data_copy.iloc[max_revenue_idx]['revenue_pct']
        
        insights.append({
            'icon': '🎯',
            'text': f'主力价格带:{max_price_band},贡献 {max_revenue_pct:.1%} 销售额',
            'level': 'primary'
        })
        
        # 分析SKU数量分布
        max_sku_idx = price_data_copy.iloc[:, 1].idxmax()
        max_sku_band = price_data_copy.iloc[max_sku_idx, 0]
        if max_sku_band != max_price_band:
            insights.append({
                'icon': '📊',
                'text': f'SKU最集中在 {max_sku_band},但销售额主要来自 {max_price_band}',
                'level': 'info'
            })
        
        # 分析高价格带表现
        high_price_bands = price_data_copy[price_data_copy.iloc[:, 0].str.contains('100|以上|200', na=False)]
        if not high_price_bands.empty:
            high_revenue_pct = high_price_bands['revenue_pct'].sum()
            if high_revenue_pct > 0.2:
                insights.append({
                    'icon': '💎',
                    'text': f'高价位商品(≥100元)贡献 {high_revenue_pct:.1%} 销售额,形象品运营良好',
                    'level': 'success'
                })
            elif high_revenue_pct < 0.05:
                insights.append({
                    'icon': '📈',
                    'text': f'高价位商品占比仅 {high_revenue_pct:.1%},可提升形象品供给',
                    'level': 'warning'
                })
        
        return insights
    
    @staticmethod
    def generate_category_sales_insights(category_data):
        """生成品类动销洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 分析动销率分布
        sales_rate_col = category_data.iloc[:, 6]  # G列：动销率
        high_sales = category_data[sales_rate_col >= 0.7]
        low_sales = category_data[sales_rate_col < 0.3]
        
        if len(high_sales) > 0:
            top_categories = high_sales.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '🌟',
                'text': f'动销优秀品类:{", ".join(top_categories)}(动销率≥70%)',
                'level': 'success'
            })
        
        if len(low_sales) > 0:
            bottom_categories = low_sales.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '⚠️',
                'text': f'动销较弱品类:{", ".join(bottom_categories)}(动销率<30%),需优化',
                'level': 'warning'
            })
        
        # 分析SKU效率
        total_sku = category_data.iloc[:, 4].sum()  # E列：总SKU
        active_sku = category_data.iloc[:, 5].sum()  # F列：动销SKU
        overall_rate = active_sku / total_sku if total_sku > 0 else 0
        
        insights.append({
            'icon': '📊',
            'text': f'整体动销率 {overall_rate:.1%},活跃SKU {int(active_sku)}/{int(total_sku)}',
            'level': 'info'
        })
        
        return insights
    
    @staticmethod
    def generate_multispec_insights(category_data):
        """生成多规格供给洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 计算多规格占比
        category_data_copy = category_data.copy()
        total_sku = category_data_copy.iloc[:, 1]  # B列：总SKU
        multispec_sku = category_data_copy.iloc[:, 2]  # C列：多规格SKU
        category_data_copy['multispec_ratio'] = multispec_sku / total_sku
        
        # 高多规格品类（>50%）
        high_multispec = category_data_copy[category_data_copy['multispec_ratio'] > 0.5]
        if len(high_multispec) > 0:
            high_cats = high_multispec.iloc[:, 0].tolist()
            insights.append({
                'icon': '🎨',
                'text': f'高多规格品类(>50%):{", ".join(high_cats)} → 供给丰富',
                'level': 'success'
            })
        
        # 低多规格品类（<15%）
        low_multispec = category_data_copy[category_data_copy['multispec_ratio'] < 0.15]
        if len(low_multispec) > 0:
            low_cats = low_multispec.iloc[:, 0].tolist()
            insights.append({
                'icon': '📦',
                'text': f'低多规格品类(<15%):{", ".join(low_cats)} → 供给相对单一',
                'level': 'warning'
            })
        
        # 中等多规格品类（20-40%）
        mid_multispec = category_data_copy[
            (category_data_copy['multispec_ratio'] >= 0.2) & 
            (category_data_copy['multispec_ratio'] <= 0.4)
        ]
        if len(mid_multispec) > 0:
            mid_cats = mid_multispec.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '🔧',
                'text': f'中等多规格品类(20-40%):{", ".join(mid_cats)} → 有优化空间',
                'level': 'info'
            })
        
        # 整体统计
        total_multispec = multispec_sku.sum()
        total_all = total_sku.sum()
        overall_ratio = total_multispec / total_all if total_all > 0 else 0
        insights.append({
            'icon': '📊',
            'text': f'门店整体多规格占比 {overall_ratio:.1%},多规格SKU {int(total_multispec)}/{int(total_all)}',
            'level': 'primary'
        })
        
        return insights
    
    @staticmethod
    def create_discount_analysis(category_data):
        """创建折扣商品分析图表"""
        if category_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无分类数据"), style={'height': '700px'})
        
        print(f"💸 折扣数据维度: {category_data.shape}")
        
        # 提取关键列：
        # A列(索引0)：一级分类
        # W列(索引22)：美团一级分类折扣sku数
        # K列(索引10)：美团一级分类活动SKU占比(类内) - 不使用，改为自己计算
        # S列(索引18)：售价销售额 - 作为折扣销售额
        
        category_col = category_data.iloc[:, 0]  # A列：一级分类
        discount_sku_col = category_data.iloc[:, 22]  # W列：折扣SKU数
        total_sku_col = category_data.iloc[:, 1]  # B列：总SKU数
        discount_revenue_col = category_data.iloc[:, 18]  # S列：售价销售额（折扣销售额）
        
        # 计算折扣SKU占比（折扣SKU / 总SKU）
        discount_ratio = (discount_sku_col / total_sku_col * 100).fillna(0)
        
        print(f"💸 使用列: 分类={category_col.name}, 折扣SKU数=W列(索引22), 折扣销售额=S列(索引18)")
        
        # 创建双Y轴图表
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加折扣SKU数量柱状图（深橙色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=discount_sku_col,
                name="折扣SKU数量",
                marker_color='#ff7f0e',
                opacity=0.8,
                text=[int(val) if pd.notna(val) else 0 for val in discount_sku_col],
                textposition='outside',
                textfont=dict(size=10),
                hovertemplate='折扣SKU数: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加折扣销售额折线图（红色）
        formatted_revenue = []
        for val in discount_revenue_col:
            if pd.notna(val):
                formatted_revenue.append(f'{val:,.0f}')
            else:
                formatted_revenue.append('0')
        
        fig.add_trace(
            go.Scatter(
                x=category_col,
                y=discount_revenue_col,
                mode='lines+markers+text',
                name="折扣销售额",
                line=dict(color='red', width=3, dash='dot'),
                marker=dict(size=8, color='red', symbol='diamond'),
                text=formatted_revenue,
                textposition='bottom center',
                textfont=dict(size=9, color='red', family='Arial Black'),
                hovertemplate='折扣销售额: ¥%{text}<extra></extra>'
            ),
            secondary_y=True,
        )
        
        # 优化布局
        fig.update_xaxes(
            title_text="一级分类",
            tickangle=45,
            tickfont=dict(size=11),
            title_font=dict(size=14)
        )
        fig.update_yaxes(
            title_text="折扣SKU数量",
            secondary_y=False,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',
            separatethousands=True
        )
        fig.update_yaxes(
            title_text="折扣销售额 (¥)",
            secondary_y=True,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',
            separatethousands=True
        )
        
        fig.update_layout(
            title={
                'text': "💸 折扣商品供给与销售分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=700,
            margin=dict(l=80, r=80, t=100, b=150),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            ),
            font=dict(size=12),
            hovermode='x',
            paper_bgcolor='white',
            plot_bgcolor='white',
            bargap=0.2
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_discount_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '700px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_discount_insights(category_data):
        """生成折扣商品洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 计算折扣占比
        category_data_copy = category_data.copy()
        total_sku = category_data_copy.iloc[:, 1]  # B列：总SKU
        discount_sku = category_data_copy.iloc[:, 22]  # W列：折扣SKU
        discount_revenue = category_data_copy.iloc[:, 18]  # S列：折扣销售额
        
        category_data_copy['discount_ratio'] = discount_sku / total_sku
        category_data_copy['discount_revenue'] = discount_revenue
        
        # 高折扣占比品类（>30%）
        high_discount = category_data_copy[category_data_copy['discount_ratio'] > 0.3]
        if len(high_discount) > 0:
            high_cats = high_discount.iloc[:, 0].tolist()
            avg_ratio = high_discount['discount_ratio'].mean()
            insights.append({
                'icon': '🔥',
                'text': f'高折扣占比品类(>30%):{", ".join(high_cats)} → 促销力度大',
                'level': 'warning'
            })
        
        # 找出折扣销售额TOP3品类
        top_revenue_cats = category_data_copy.nlargest(3, 'discount_revenue')
        if len(top_revenue_cats) > 0:
            top_cats = top_revenue_cats.iloc[:, 0].tolist()
            top_revenue_sum = top_revenue_cats['discount_revenue'].sum()
            insights.append({
                'icon': '💰',
                'text': f'折扣销售额TOP3:{", ".join(top_cats)},合计¥{top_revenue_sum:,.0f}',
                'level': 'success'
            })
        
        # 折扣投入产出分析：高折扣占比但低销售额的品类
        category_data_copy['sku_efficiency'] = category_data_copy['discount_revenue'] / (discount_sku + 1)  # 避免除零
        low_efficiency = category_data_copy[
            (category_data_copy['discount_ratio'] > 0.2) & 
            (category_data_copy['sku_efficiency'] < category_data_copy['sku_efficiency'].median())
        ]
        
        if len(low_efficiency) > 0:
            low_eff_cats = low_efficiency.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '⚠️',
                'text': f'折扣效率待优化:{", ".join(low_eff_cats)} → 折扣多但销售额相对低',
                'level': 'warning'
            })
        
        # 整体统计
        total_discount_sku = discount_sku.sum()
        total_all_sku = total_sku.sum()
        overall_ratio = total_discount_sku / total_all_sku if total_all_sku > 0 else 0
        total_discount_revenue = discount_revenue.sum()
        
        insights.append({
            'icon': '📊',
            'text': f'门店整体折扣占比 {overall_ratio:.1%},折扣销售额¥{total_discount_revenue:,.0f}',
            'level': 'primary'
        })
        
        return insights
    
    @staticmethod
    def create_discount_heatmap(category_data):
        """创建折扣渗透率热力图"""
        if category_data.empty:
            return dcc.Graph(figure=px.imshow([[0]], title="暂无数据"), style={'height': '600px'})
        
        print(f"🔥 折扣热力图数据维度: {category_data.shape}")
        
        # 提取数据
        categories = category_data.iloc[:, 0].tolist()  # A列：一级分类
        total_sku = category_data.iloc[:, 1]  # B列：总SKU（含多规格）
        dedup_sku = category_data.iloc[:, 4]  # E列：去重SKU数（口径同动销率）
        discount_sku = category_data.iloc[:, 22]  # W列：折扣SKU
        total_revenue = category_data.iloc[:, 18]  # S列：售价销售额
        active_sku = category_data.iloc[:, 5]  # F列：动销SKU数
        
        # 计算三个不同维度的指标
        # 1. 折扣SKU占比 - 反映折扣力度
        discount_sku_ratio = (discount_sku / total_sku * 100).fillna(0)
        # 2. 动销率 - 反映商品活跃度
        sales_rate = (active_sku / total_sku * 100).fillna(0)
        # 3. SKU平均销售额 - 反映每个SKU的销售贡献（使用去重后的SKU数计算）
        avg_revenue_per_sku = (total_revenue / dedup_sku).fillna(0)
        
        # 构建热力图数据矩阵
        heatmap_data = [
            discount_sku_ratio.tolist(),
            sales_rate.tolist(),
            avg_revenue_per_sku.tolist()
        ]
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=categories,
            y=['折扣SKU占比(%)', '动销率(%)', 'SKU平均销售额(¥)'],
            colorscale=[
                [0, '#f7fbff'],
                [0.2, '#deebf7'],
                [0.4, '#9ecae1'],
                [0.6, '#4292c6'],
                [0.8, '#2171b5'],
                [1, '#08519c']
            ],
            text=[[f'{val:.1f}' if i < 2 else f'{val:.0f}' for val in row] for i, row in enumerate(heatmap_data)],
            texttemplate='%{text}',
            textfont={"size": 10},
            hovertemplate='%{y}<br>%{x}<br>数值: %{z:.1f}<extra></extra>',
            colorbar=dict(
                title="数值",
                tickmode="linear",
                tick0=0,
                dtick=20
            )
        ))
        
        fig.update_layout(
            title={
                'text': "🔥 折扣渗透率热力图分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            xaxis=dict(
                title="一级分类",
                tickangle=45,
                tickfont=dict(size=11)
            ),
            yaxis=dict(
                title="分析维度",
                tickfont=dict(size=12)
            ),
            height=500,
            margin=dict(l=150, r=100, t=100, b=150),
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_heatmap_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '500px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_heatmap_insights(category_data):
        """生成热力图洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 计算指标
        total_sku = category_data.iloc[:, 1]
        discount_sku = category_data.iloc[:, 22]
        discount_sku_ratio = (discount_sku / total_sku * 100).fillna(0)
        
        # 高渗透品类（>50%）
        high_penetration = category_data[discount_sku_ratio > 50]
        if len(high_penetration) > 0:
            high_cats = high_penetration.iloc[:, 0].tolist()
            insights.append({
                'icon': '🔥',
                'text': f'高渗透品类(>50%):{", ".join(high_cats)} → 促销策略激进',
                'level': 'danger'
            })
        
        # 中等渗透品类（30-50%）
        mid_penetration = category_data[(discount_sku_ratio >= 30) & (discount_sku_ratio <= 50)]
        if len(mid_penetration) > 0:
            mid_cats = mid_penetration.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '⚖️',
                'text': f'中等渗透品类(30-50%):{", ".join(mid_cats)} → 折扣策略均衡',
                'level': 'warning'
            })
        
        # 低渗透品类（<20%）
        low_penetration = category_data[discount_sku_ratio < 20]
        if len(low_penetration) > 0:
            low_cats = low_penetration.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '🎯',
                'text': f'低渗透品类(<20%):{", ".join(low_cats)} → 保持原价策略',
                'level': 'success'
            })
        
        # 整体统计
        avg_ratio = discount_sku_ratio.mean()
        insights.append({
            'icon': '📊',
            'text': f'门店平均折扣渗透率 {avg_ratio:.1f}%',
            'level': 'primary'
        })
        
        return insights
    
    @staticmethod
    def create_price_distribution(price_data):
        """创建智能自适应的价格带分布图"""
        if price_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无价格带数据"), style={'height': '600px'})
        
        print(f"💰 价格带数据维度: {price_data.shape}")
        print(f"💰 列名: {price_data.columns.tolist()}")
        
        # 注意：第一列Unnamed:0已在DataLoader中被删除，所以索引要减1
        # 现在：0=price_band, 1=SKU数量, 2=销售额, 3=销售额占比, 4=SKU占比
        cols = price_data.columns.tolist()
        price_col = cols[0] if len(cols) > 0 else None  # price_band
        sku_col = cols[1] if len(cols) > 1 else None    # SKU数量
        revenue_col = cols[2] if len(cols) > 2 else None  # 销售额
        
        print(f"💰 使用列: 价格带={price_col}, SKU={sku_col}, 销售额={revenue_col}")
        
        # 创建双轴图
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加动销SKU数量柱状图
        if sku_col and sku_col in price_data.columns:
            fig.add_trace(
                go.Bar(
                    x=price_data[price_col],
                    y=price_data[sku_col],
                    name="动销SKU数量",
                    marker_color='lightblue',
                    opacity=0.8,
                    text=[int(val) if pd.notna(val) else 0 for val in price_data[sku_col]],
                    textposition='outside',
                    textfont=dict(size=12),
                    hovertemplate='动销SKU数量: %{text}<extra></extra>'
                ),
                secondary_y=False,
            )
        
        # 添加销售额折线图
        if revenue_col and revenue_col in price_data.columns:
            # 格式化销售额：显示为千分位格式，无小数点
            formatted_text = []
            for val in price_data[revenue_col]:
                if pd.notna(val):
                    formatted_text.append(f'{val:,.0f}')  # 千分位，0位小数
                else:
                    formatted_text.append('0')
            
            fig.add_trace(
                go.Scatter(
                    x=price_data[price_col],
                    y=price_data[revenue_col],
                    mode='lines+markers+text',
                    name="销售额",
                    line=dict(color='red', width=3),
                    marker=dict(size=10, color='red'),
                    text=formatted_text,
                    textposition='top center',
                    textfont=dict(size=11, color='red', family='Arial Black'),
                    hovertemplate='销售额: ¥%{text}<extra></extra>'
                ),
                secondary_y=True,
            )
        
        # 优化布局
        fig.update_xaxes(
            title_text="价格带",
            tickangle=45,
            tickfont=dict(size=12),
            title_font=dict(size=14)
        )
        fig.update_yaxes(
            title_text="动销SKU数量",
            secondary_y=False,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',  # 千分位格式，不使用K
            separatethousands=True
        )
        fig.update_yaxes(
            title_text="销售额 (¥)",
            secondary_y=True,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',  # 千分位格式
            separatethousands=True
        )
        
        fig.update_layout(
            title={
                'text': "💰 价格带分布分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=600,  # 固定高度
            margin=dict(l=80, r=80, t=100, b=120),  # 减小左右边距
            showlegend=True,
            legend=dict(
                orientation="h",  # 水平布局
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            ),
            font=dict(size=12),
            hovermode='x',  # 改为x模式，避免重复显示价格带
            paper_bgcolor='white',
            plot_bgcolor='white',
            bargap=0.2  # 柱间距
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_price_insights(price_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '600px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def create_sales_bubble_chart(category_data):
        """创建分类销量与销售额气泡图"""
        if category_data.empty:
            return dcc.Graph(figure=px.scatter(title="暂无数据"), style={'height': '700px'})
        
        print(f"🫧 气泡图数据维度: {category_data.shape}")
        
        # 提取数据
        categories = category_data.iloc[:, 0]  # A列：一级分类
        total_sku = category_data.iloc[:, 1]  # B列：总SKU
        dedup_sku = category_data.iloc[:, 4]  # E列：去重SKU
        active_rate = category_data.iloc[:, 6] * 100  # G列：动销率（转为百分比）
        monthly_sales = category_data.iloc[:, 15]  # P列：月售
        total_revenue = category_data.iloc[:, 18]  # S列：售价销售额
        discount_sku = category_data.iloc[:, 22]  # W列：折扣SKU数
        
        # 计算折扣占比 (折扣SKU数 / 去重SKU数 * 100%)
        discount_ratio = (discount_sku / dedup_sku * 100).fillna(0)
        
        # 创建气泡图
        fig = go.Figure()
        
        # 使用折扣占比作为颜色(数值越大=折扣商品越多=颜色越深)
        colors = discount_ratio.tolist()
        
        fig.add_trace(go.Scatter(
            x=monthly_sales,
            y=total_revenue,
            mode='markers',
            marker=dict(
                size=active_rate * 0.8,  # 气泡大小根据动销率
                color=colors,  # 颜色根据折扣占比
                colorscale='RdYlGn_r',  # 红黄绿反向(红=高折扣占比,绿=低折扣占比)
                showscale=True,
                colorbar=dict(
                    title=dict(
                        text="折扣占比<br>(%)",
                        side="right"
                    ),
                    tickmode="linear",
                    tick0=0,
                    dtick=20  # 每20%显示一个刻度
                ),
                line=dict(width=2, color='white'),
                opacity=0.8,
                sizemode='diameter',
                sizemin=4
            ),
            text=categories,
            customdata=np.column_stack((
                dedup_sku,
                active_rate,
                discount_sku,
                discount_ratio
            )),
            hovertemplate=(
                '<b>%{text}</b><br>' +
                '月售: %{x:,}件<br>' +
                '销售额: ¥%{y:,.0f}<br>' +
                '去重SKU: %{customdata[0]}个<br>' +
                '动销率: %{customdata[1]:.1f}%<br>' +
                '折扣SKU数: %{customdata[2]}个<br>' +
                '折扣占比: %{customdata[3]:.1f}%' +
                '<extra></extra>'
            ),
            name='分类'
        ))
        
        # 添加参考线
        avg_sales = monthly_sales.mean()
        avg_revenue = total_revenue.mean()
        
        fig.add_hline(y=avg_revenue, line_dash="dash", line_color="gray", opacity=0.5,
                     annotation_text=f"平均销售额: ¥{avg_revenue:,.0f}", 
                     annotation_position="right")
        fig.add_vline(x=avg_sales, line_dash="dash", line_color="gray", opacity=0.5,
                     annotation_text=f"平均月售: {avg_sales:,.0f}件", 
                     annotation_position="top")
        
        fig.update_layout(
            title={
                'text': "📊 分类销量与销售额对比分析<br><sub>气泡大小=动销率 | 颜色=折扣力度(红=高价/低折扣,绿=低价/高折扣)</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            xaxis=dict(
                title="月售数量（件）",
                gridcolor='lightgray',
                showgrid=True,
                zeroline=False,
                tickfont=dict(size=12)
            ),
            yaxis=dict(
                title="售价销售额（元）",
                gridcolor='lightgray',
                showgrid=True,
                zeroline=False,
                tickfont=dict(size=12)
            ),
            height=700,
            margin=dict(l=100, r=150, t=120, b=80),
            paper_bgcolor='white',
            plot_bgcolor='#f8f9fa',
            hovermode='closest',
            showlegend=False
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_bubble_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '700px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_bubble_insights(category_data):
        """生成气泡图洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 提取数据
        categories = category_data.iloc[:, 0]
        monthly_sales = category_data.iloc[:, 15]
        total_revenue = category_data.iloc[:, 18]
        active_rate = category_data.iloc[:, 6] * 100
        
        # 计算平均值
        avg_sales = monthly_sales.mean()
        avg_revenue = total_revenue.mean()
        
        # 分类为四象限
        high_sales_high_revenue = category_data[
            (monthly_sales > avg_sales) & (total_revenue > avg_revenue)
        ]
        high_sales_low_revenue = category_data[
            (monthly_sales > avg_sales) & (total_revenue <= avg_revenue)
        ]
        low_sales_high_revenue = category_data[
            (monthly_sales <= avg_sales) & (total_revenue > avg_revenue)
        ]
        
        # 明星品类（高销量+高销售额）
        if len(high_sales_high_revenue) > 0:
            star_cats = high_sales_high_revenue.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '⭐',
                'text': f"明星品类（高销量+高销售额）: {', '.join(star_cats)}",
                'level': 'success'
            })
        
        # 走量品类（高销量+低销售额）
        if len(high_sales_low_revenue) > 0:
            volume_cats = high_sales_low_revenue.iloc[:, 0].head(2).tolist()
            insights.append({
                'icon': '📦',
                'text': f"走量品类（薄利多销）: {', '.join(volume_cats)}",
                'level': 'info'
            })
        
        # 高客单品类（低销量+高销售额）
        if len(low_sales_high_revenue) > 0:
            premium_cats = low_sales_high_revenue.iloc[:, 0].head(2).tolist()
            insights.append({
                'icon': '💎',
                'text': f"高客单品类（少而精）: {', '.join(premium_cats)}",
                'level': 'primary'
            })
        
        # 动销率最高的品类
        top_active = category_data.nlargest(1, category_data.columns[6])
        if len(top_active) > 0:
            cat_name = top_active.iloc[0, 0]
            rate = top_active.iloc[0, 6] * 100
            insights.append({
                'icon': '🚀',
                'text': f"最高动销率: {cat_name}（{rate:.1f}%）",
                'level': 'success'
            })
        
        return insights
    
    @staticmethod
    def create_sales_treemap(category_data):
        """创建分类销量树状图"""
        if category_data.empty:
            return dcc.Graph(figure=px.treemap(title="暂无数据"), style={'height': '700px'})
        
        print(f"🌳 树状图数据维度: {category_data.shape}")
        
        # 提取数据并转换为数值类型，自动处理异常
        categories = category_data.iloc[:, 0].astype(str)  # A列：一级分类（确保为字符串）
        monthly_sales = pd.to_numeric(category_data.iloc[:, 15], errors='coerce').fillna(0)  # P列：月售
        sales_ratio = pd.to_numeric(category_data.iloc[:, 16], errors='coerce').fillna(0) * 100  # Q列：月售占比
        total_revenue = pd.to_numeric(category_data.iloc[:, 18], errors='coerce').fillna(0)  # S列：售价销售额
        
        # 创建数据框
        treemap_df = pd.DataFrame({
            '分类': categories,
            '月售': monthly_sales,
            '月售占比': sales_ratio,
            '销售额': total_revenue
        })
        
        # 过滤掉无效数据（月售为0或负数的分类）
        treemap_df = treemap_df[treemap_df['月售'] > 0]
        
        if treemap_df.empty:
            return dcc.Graph(figure=px.treemap(title="暂无有效数据"), style={'height': '700px'})
        
        # 按月售降序排列
        treemap_df = treemap_df.sort_values('月售', ascending=False)
        
        # 创建树状图
        fig = px.treemap(
            treemap_df,
            path=['分类'],
            values='月售',
            color='月售占比',
            color_continuous_scale='Blues',
            hover_data={
                '月售': ':,',
                '销售额': ':,.0f',
                '月售占比': ':.1f'
            },
            custom_data=['销售额', '月售占比']
        )
        
        # 更新文本显示
        fig.update_traces(
            textposition='middle center',
            texttemplate='<b>%{label}</b><br>%{value:,}件<br>%{customdata[1]:.1f}%',
            hovertemplate=(
                '<b>%{label}</b><br>' +
                '月售: %{value:,}件<br>' +
                '销售额: ¥%{customdata[0]:,.0f}<br>' +
                '月售占比: %{customdata[1]:.1f}%' +
                '<extra></extra>'
            ),
            marker=dict(
                line=dict(width=2, color='white'),
                cornerradius=5
            )
        )
        
        fig.update_layout(
            title={
                'text': "🌳 分类月售贡献树状图<br><sub>面积=月售数量 | 颜色深度=月售占比</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=700,
            margin=dict(l=10, r=10, t=100, b=10),
            paper_bgcolor='white',
            coloraxis_colorbar=dict(
                title=dict(
                    text="月售占比(%)",
                    side="right"
                ),
                ticksuffix="%",
                tickmode="linear",
                tick0=0,
                dtick=5
            )
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': '700px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False,
                'responsive': True
            }
        )
    
    @staticmethod
    def generate_treemap_insights(category_df):
        """生成树状图洞察"""
        insights = []
        
        if category_df.empty or len(category_df.columns) < 17:
            return insights
        
        # 提取数据
        treemap_df = pd.DataFrame({
            '分类': category_df.iloc[:, 0],  # A列
            '月售': category_df.iloc[:, 15],  # P列
            '月售占比': category_df.iloc[:, 16] * 100  # Q列（转为百分比）
        }).sort_values('月售', ascending=False)
        
        # TOP3品类
        top3 = treemap_df.head(3)
        top3_names = top3['分类'].tolist()
        top3_ratio = top3['月售占比'].sum()
        
        insights.append({
            'title': '🏆 TOP3品类贡献',
            'content': f"{', '.join(top3_names)}这三个品类合计贡献了{top3_ratio:.1f}%的销量",
            'level': 'success'
        })
        
        # 80%销量贡献品类数
        cumsum = treemap_df['月售占比'].cumsum()
        pareto_80 = len(cumsum[cumsum <= 80])
        total_cats = len(treemap_df)
        
        insights.append({
            'title': '📊 帕累托法则验证',
            'content': f"{pareto_80}个品类（占总品类的{pareto_80/total_cats*100:.0f}%）贡献了80%的销量，符合二八定律" if pareto_80 <= total_cats * 0.3 else f"{pareto_80}个品类（占{pareto_80/total_cats*100:.0f}%）才达到80%销量，说明销售较为分散",
            'level': 'primary' if pareto_80 <= total_cats * 0.3 else 'warning'
        })
        
        # 长尾品类
        bottom_5 = treemap_df.tail(5)
        bottom_ratio = bottom_5['月售占比'].sum()
        bottom_names = ', '.join(bottom_5['分类'].head(3).tolist())
        
        insights.append({
            'title': '📉 长尾品类识别',
            'content': f"末尾5个品类（如{bottom_names}等）仅占{bottom_ratio:.1f}%的销量，建议评估其优化或精简的必要性",
            'level': 'warning'
        })
        
        # 销量最大的单个品类
        top1 = treemap_df.iloc[0]
        insights.append({
            'title': '👑 销量冠军',
            'content': f"{top1['分类']}以{top1['月售']:,.0f}件的月售占据{top1['月售占比']:.1f}%的份额，是门店销量支柱",
            'level': 'success'
        })
        
        return insights
    
    @staticmethod
    def create_inventory_health_chart(category_df):
        """创建库存健康看板
        
        包含:
        1. 0库存率TOP10分类柱状图
        2. 库存预警高亮卡片
        3. 库存健康度概览
        """
        if category_df.empty or len(category_df.columns) < 14:
            return html.Div("库存数据不可用", className="alert alert-warning")
        
        # 提取数据: M列(索引12)=0库存数, N列(索引13)=0库存率, A列=分类名
        df = category_df.copy()
        df.columns = [f'col_{i}' for i in range(len(df.columns))]
        
        # 准备数据（0库存率从小数转为百分比）
        inventory_data = pd.DataFrame({
            '分类': df['col_0'],
            '0库存数': pd.to_numeric(df['col_12'], errors='coerce').fillna(0),
            '0库存率': pd.to_numeric(df['col_13'], errors='coerce').fillna(0) * 100  # 转为百分比
        })
        
        # 过滤掉无效数据
        inventory_data = inventory_data[inventory_data['0库存率'] > 0]
        
        # 按0库存率排序，取TOP10
        top10_zero_stock = inventory_data.nlargest(10, '0库存率')
        
        # 计算整体统计
        total_zero_stock = inventory_data['0库存数'].sum()
        avg_zero_stock_rate = inventory_data['0库存率'].mean()
        high_risk_count = len(inventory_data[inventory_data['0库存率'] > 30])  # 0库存率>30%为高风险
        
        # 1. 创建TOP10柱状图
        fig_bar = go.Figure()
        
        # 根据风险等级分配颜色
        colors = ['#e74c3c' if rate > 30 else '#f39c12' if rate > 15 else '#3498db' 
                  for rate in top10_zero_stock['0库存率']]
        
        fig_bar.add_trace(go.Bar(
            x=top10_zero_stock['0库存率'],
            y=top10_zero_stock['分类'],
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=[f"{rate:.1f}%<br>({int(count)}件)" 
                  for rate, count in zip(top10_zero_stock['0库存率'], top10_zero_stock['0库存数'])],
            textposition='outside',
            textfont=dict(size=11),  # 调整文本字体大小
            hovertemplate='<b>%{y}</b><br>0库存率: %{x:.1f}%<br>0库存数: %{customdata}件<br><extra></extra>',
            customdata=top10_zero_stock['0库存数']  # 添加自定义数据用于悬停
        ))
        
        fig_bar.update_layout(
            title=dict(
                text='<b>0库存率TOP10分类</b><br><sub>红色=高风险(>30%) | 橙色=中风险(15-30%) | 蓝色=低风险(<15%)</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='0库存率 (%)',
            yaxis_title='',
            height=500,
            margin=dict(l=200, r=120, t=100, b=80),  # 左边距从150增加到200，右边距从100增加到120
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            hovermode='y unified',
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                range=[0, max(top10_zero_stock['0库存率']) * 1.2]
            ),
            yaxis=dict(
                tickmode='linear',
                tickfont=dict(size=12),  # 调整y轴标签字体大小
                automargin=True  # 自动调整边距以容纳标签
            )
        )
        
        # 添加风险阈值参考线
        fig_bar.add_vline(x=30, line_dash="dash", line_color="red", opacity=0.5,
                         annotation_text="高风险线", annotation_position="top right")
        fig_bar.add_vline(x=15, line_dash="dash", line_color="orange", opacity=0.5,
                         annotation_text="中风险线", annotation_position="top right")
        
        # 2. 创建库存健康度雷达图
        # 计算各维度得分 (满分100)
        radar_metrics = {
            '低库存率': max(0, 100 - avg_zero_stock_rate * 2),  # 0库存率越低越好
            '风险分类数': max(0, 100 - high_risk_count * 10),  # 高风险分类越少越好
            '库存均衡度': 100 - inventory_data['0库存率'].std() if len(inventory_data) > 1 else 50,
            '整体库存健康': max(0, 100 - avg_zero_stock_rate * 3)
        }
        
        fig_radar = go.Figure()
        
        fig_radar.add_trace(go.Scatterpolar(
            r=list(radar_metrics.values()),
            theta=list(radar_metrics.keys()),
            fill='toself',
            fillcolor='rgba(52, 152, 219, 0.3)',
            line=dict(color='#3498db', width=2),
            marker=dict(size=8, color='#3498db'),
            name='当前状态'
        ))
        
        # 添加理想状态参考线
        fig_radar.add_trace(go.Scatterpolar(
            r=[90, 90, 90, 90],
            theta=list(radar_metrics.keys()),
            line=dict(color='rgba(46, 204, 113, 0.5)', dash='dash', width=2),
            name='理想标准'
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    showticklabels=True,
                    ticks='outside',
                    gridcolor='rgba(0,0,0,0.1)'
                ),
                bgcolor='rgba(248,249,250,0.5)'
            ),
            title=dict(
                text='<b>库存健康度评分</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            showlegend=True,
            height=450,
            margin=dict(t=80, b=40),
            paper_bgcolor='white'
        )
        
        # 3. 创建预警卡片
        alert_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{total_zero_stock:.0f}", className="text-danger mb-0"),
                        html.P("总0库存商品数", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{avg_zero_stock_rate:.1f}%", 
                               className="text-warning mb-0" if avg_zero_stock_rate < 20 else "text-danger mb-0"),
                        html.P("平均0库存率", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{high_risk_count}", className="text-danger mb-0"),
                        html.P("高风险分类(>30%)", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(
                            "健康" if avg_zero_stock_rate < 10 else "预警" if avg_zero_stock_rate < 20 else "严重",
                            className="text-success mb-0" if avg_zero_stock_rate < 10 else "text-warning mb-0" if avg_zero_stock_rate < 20 else "text-danger mb-0"
                        ),
                        html.P("库存状态", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3)
        ], className="mb-4")
        
        # 组合所有组件
        return html.Div([
            alert_cards,
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
                ], width=7),
                dbc.Col([
                    dcc.Graph(figure=fig_radar, config={'displayModeBar': False})
                ], width=5)
            ])
        ])
    
    @staticmethod
    def generate_inventory_insights(category_df):
        """生成库存健康智能洞察"""
        if category_df.empty or len(category_df.columns) < 14:
            return []
        
        insights = []
        
        # 提取数据（0库存率从小数转为百分比）
        df = category_df.copy()
        df.columns = [f'col_{i}' for i in range(len(df.columns))]
        
        inventory_data = pd.DataFrame({
            '分类': df['col_0'],
            '0库存数': pd.to_numeric(df['col_12'], errors='coerce').fillna(0),
            '0库存率': pd.to_numeric(df['col_13'], errors='coerce').fillna(0) * 100  # 转为百分比
        })
        
        inventory_data = inventory_data[inventory_data['0库存率'] > 0]
        
        if len(inventory_data) == 0:
            insights.append({
                'title': '🎉 库存表现优秀',
                'content': '所有分类库存充足,无0库存问题',
                'level': 'success'
            })
            return insights
        
        # 1. 高风险分类警告
        high_risk = inventory_data[inventory_data['0库存率'] > 30]
        if len(high_risk) > 0:
            top_risk = high_risk.nlargest(3, '0库存率')
            risk_list = ", ".join([f"{row['分类']}({row['0库存率']:.1f}%)" 
                                   for _, row in top_risk.iterrows()])
            insights.append({
                'title': '🚨 高风险分类警告',
                'content': f"发现{len(high_risk)}个高风险分类(0库存率>30%),TOP3: {risk_list}。建议立即补货以避免失销。",
                'level': 'danger'
            })
        else:
            # 如果没有高风险，给予正面反馈
            insights.append({
                'title': '✅ 无高风险分类',
                'content': '所有分类的0库存率均低于30%，库存风险控制良好。',
                'level': 'success'
            })
        
        # 2. 整体库存健康度评估
        avg_rate = inventory_data['0库存率'].mean()
        total_zero = inventory_data['0库存数'].sum()
        
        if avg_rate < 10:
            health_status = "优秀"
            health_level = 'success'
        elif avg_rate < 20:
            health_status = "良好"
            health_level = 'info'
        elif avg_rate < 30:
            health_status = "需改进"
            health_level = 'warning'
        else:
            health_status = "严重"
            health_level = 'danger'
        
        insights.append({
            'title': f'📊 库存健康度: {health_status}',
            'content': f"全店平均0库存率为{avg_rate:.1f}%,共有{total_zero:.0f}个SKU处于0库存状态。" +
                      ("表现优秀,请继续保持!" if avg_rate < 10 else 
                       "需要关注库存补充效率。" if avg_rate < 20 else
                       "建议优化供应链管理和库存预警机制。"),
            'level': health_level
        })
        
        # 3. 库存不均衡提示
        std_rate = inventory_data['0库存率'].std()
        if std_rate > 20:
            max_cat = inventory_data.loc[inventory_data['0库存率'].idxmax()]
            min_cat = inventory_data.loc[inventory_data['0库存率'].idxmin()]
            insights.append({
                'title': '⚖️ 库存分布不均衡',
                'content': f"各分类0库存率波动较大(标准差{std_rate:.1f}%)。最高: {max_cat['分类']}({max_cat['0库存率']:.1f}%)," +
                          f"最低: {min_cat['分类']}({min_cat['0库存率']:.1f}%)。建议平衡各分类库存配置。",
                'level': 'warning'
            })
        
        # 4. 长尾分类改善建议
        medium_risk = inventory_data[(inventory_data['0库存率'] > 15) & (inventory_data['0库存率'] <= 30)]
        if len(medium_risk) > 0:
            insights.append({
                'title': '💡 改善建议',
                'content': f"发现{len(medium_risk)}个中风险分类(0库存率15-30%),建议优先优化这些分类的库存周转," +
                          "可通过增加补货频次或调整安全库存量来降低0库存率。",
                'level': 'info'
            })
        
        # 5. 最需要关注的TOP3分类
        if len(inventory_data) > 0:
            top3_problem = inventory_data.nlargest(3, '0库存率')
            top3_list = ", ".join([f"{row['分类']}({row['0库存率']:.1f}%)" 
                                   for _, row in top3_problem.iterrows()])
            insights.append({
                'title': '🔍 重点关注分类',
                'content': f"0库存率最高的TOP3分类: {top3_list}。建议优先检查这些分类的补货策略和销售预测准确性。",
                'level': 'warning'
            })
        
        return insights
    
    @staticmethod
    def create_promotion_effectiveness_analysis(category_df):
        """创建促销效能分析
        
        包含:
        1. 促销渗透率对比柱状图（活动SKU vs 非活动SKU）
        2. 促销商品销售贡献分析
        3. 分类促销效能排名
        """
        if category_df.empty or len(category_df.columns) < 11:
            return html.Div("促销数据不可用", className="alert alert-warning")
        
        # 提取数据并确保数据类型正确
        df = category_df.copy()
        
        # 计算活动商品数量和占比
        activity_去重SKU = pd.to_numeric(df.iloc[:, 8], errors='coerce').fillna(0)  # I列：活动去重SKU数
        dedup_SKU = pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0)  # E列：去重SKU数
        activity_ratio = (activity_去重SKU / dedup_SKU * 100).fillna(0).clip(upper=100)
        
        # 计算折扣力度作为促销强度指标 (Y列：折扣,值越小折扣越大)
        discount_level = pd.to_numeric(df.iloc[:, 24], errors='coerce').fillna(10)  # Y列：折扣(例如3.5折)
        # 将折扣力度转换为促销强度: 10折=0%强度, 1折=90%强度
        promo_intensity = ((10 - discount_level) / 9 * 100).clip(lower=0, upper=100)
        
        promo_data = pd.DataFrame({
            '分类': df.iloc[:, 0].astype(str),  # A列
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0).astype(int),  # B列
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0).astype(int),  # E列
            '活动去重SKU数': activity_去重SKU.astype(int),  # I列
            '活动sku数': pd.to_numeric(df.iloc[:, 9], errors='coerce').fillna(0).astype(int),  # J列
            '活动占比': activity_ratio,  # 活动商品占比(%)
            '折扣力度': discount_level,  # Y列：折扣(3.5折)
            '促销强度': promo_intensity,  # 促销强度(0-100%,越高促销越强)
            '销售额': pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0),  # S列
            '月售': pd.to_numeric(df.iloc[:, 15], errors='coerce').fillna(0).astype(int)  # P列
        })
        
        # 计算非活动SKU数
        promo_data['非活动SKU数'] = promo_data['去重SKU数'] - promo_data['活动去重SKU数']
        promo_data['非活动SKU数'] = promo_data['非活动SKU数'].clip(lower=0)
        
        # 过滤有效数据
        promo_data = promo_data[promo_data['去重SKU数'] > 0]
        
        # 按促销强度排序(原来按活动占比)
        promo_data_sorted = promo_data.sort_values('促销强度', ascending=True)
        
        # 1. 创建促销渗透率对比柱状图（横向堆叠）
        fig_bar = go.Figure()
        
        # 活动SKU
        fig_bar.add_trace(go.Bar(
            name='活动商品',
            y=promo_data_sorted['分类'].tolist(),
            x=promo_data_sorted['活动去重SKU数'].tolist(),
            orientation='h',
            marker=dict(color='#e74c3c', line=dict(color='rgba(0,0,0,0.2)', width=1)),
            text=[f"{int(x)}" for x in promo_data_sorted['活动去重SKU数']],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>活动商品: %{x}个<extra></extra>'
        ))
        
        # 非活动SKU
        fig_bar.add_trace(go.Bar(
            name='非活动商品',
            y=promo_data_sorted['分类'].tolist(),
            x=promo_data_sorted['非活动SKU数'].tolist(),
            orientation='h',
            marker=dict(color='#95a5a6', line=dict(color='rgba(0,0,0,0.2)', width=1)),
            text=[f"{int(x)}" for x in promo_data_sorted['非活动SKU数']],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>非活动商品: %{x}个<extra></extra>'
        ))
        
        fig_bar.update_layout(
            barmode='stack',
            title=dict(
                text='<b>各分类促销商品结构对比</b><br><sub>红色=活动商品 | 灰色=非活动商品</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='SKU数量',
            yaxis_title='',
            height=800,
            margin=dict(l=150, r=80, t=120, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            hovermode='y unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            )
        )
        
        # 2. 创建促销效能气泡图（促销强度 vs 销售额）
        fig_bubble = go.Figure()
        
        # 根据促销强度分配颜色 (强度越高=折扣越大=颜色越深)
        colors = ['#e74c3c' if intensity > 60 else '#f39c12' if intensity > 40 else '#2ecc71'
                  for intensity in promo_data['促销强度'].tolist()]
        
        # 只对关键分类显示标签（避免重叠）
        # 选择促销强度极端值和销售额最高的分类显示标签
        top_sales = promo_data.nlargest(3, '销售额')['分类'].tolist()
        high_promo = promo_data.nlargest(3, '促销强度')['分类'].tolist()
        low_promo = promo_data.nsmallest(3, '促销强度')['分类'].tolist()
        show_label_cats = set(top_sales + high_promo + low_promo)
        
        text_labels = [cat if cat in show_label_cats else '' for cat in promo_data['分类'].tolist()]
        
        fig_bubble.add_trace(go.Scatter(
            x=promo_data['促销强度'].tolist(),
            y=promo_data['销售额'].tolist(),
            mode='markers+text',
            marker=dict(
                size=(promo_data['月售'] / 80).tolist(),  # 调整气泡大小
                color=colors,
                line=dict(width=2, color='white'),
                sizemode='diameter',
                sizemin=8
            ),
            text=text_labels,
            textposition='top center',
            textfont=dict(size=10),
            hovertemplate=(
                '<b>%{customdata[0]}</b><br>' +
                '促销强度: %{x:.1f}%<br>' +
                '折扣力度: %{customdata[1]:.1f}折<br>' +
                '销售额: ¥%{y:,.0f}<br>' +
                '<extra></extra>'
            ),
            customdata=list(zip(promo_data['分类'].tolist(), promo_data['折扣力度'].tolist()))
        ))
        
        fig_bubble.update_layout(
            title=dict(
                text='<b>促销效能分析</b><br><sub>气泡大小=月售量 | 颜色=促销强度(红>60%, 橙40-60%, 绿<40%)</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='促销强度 (%)',
            yaxis_title='销售额 (¥)',
            height=500,
            margin=dict(l=80, r=50, t=100, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', range=[0, 105]),
            yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)')
        )
        
        # 添加参考线
        fig_bubble.add_hline(y=promo_data['销售额'].median(), line_dash="dash", 
                            line_color="gray", opacity=0.5,
                            annotation_text="销售额中位数", annotation_position="right")
        fig_bubble.add_vline(x=promo_data['促销强度'].mean(), line_dash="dash", 
                            line_color="gray", opacity=0.5,
                            annotation_text="平均促销强度", annotation_position="top")
        
        # 3. 创建TOP10促销强度排名
        top10_promo = promo_data.nlargest(10, '促销强度')
        
        fig_rank = go.Figure()
        
        fig_rank.add_trace(go.Bar(
            x=top10_promo['促销强度'].tolist(),
            y=top10_promo['分类'].tolist(),
            orientation='h',
            marker=dict(
                color=top10_promo['促销强度'].tolist(),
                colorscale='RdYlGn_r',  # 红黄绿反向(红=高促销强度)
                showscale=True,
                colorbar=dict(title=dict(text="促销<br>强度(%)", side="right")),
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=[f"{ratio:.1f}%" for ratio in top10_promo['促销强度'].tolist()],
            textposition='outside',
            customdata=top10_promo['折扣力度'].tolist(),
            hovertemplate='<b>%{y}</b><br>促销强度: %{x:.1f}%<br>折扣力度: %{customdata:.1f}折<extra></extra>'
        ))
        
        fig_rank.update_layout(
            title=dict(
                text='<b>促销力度TOP10分类</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='促销强度 (%)',
            yaxis_title='',
            height=500,
            margin=dict(l=150, r=100, t=80, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', range=[0, 105])
        )
        
        # 组合所有组件
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
                ], width=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_bubble, config={'displayModeBar': False})
                ], width=7),
                dbc.Col([
                    dcc.Graph(figure=fig_rank, config={'displayModeBar': False})
                ], width=5)
            ])
        ])
    
    @staticmethod
    def generate_promotion_insights(category_df):
        """生成促销效能智能洞察"""
        if category_df.empty or len(category_df.columns) < 11:
            return []
        
        insights = []
        
        # 提取数据
        df = category_df.copy()
        promo_data = pd.DataFrame({
            '分类': df.iloc[:, 0],
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0),  # B列：总SKU数（含多规格）
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0),
            '活动SKU数': pd.to_numeric(df.iloc[:, 8], errors='coerce').fillna(0),
            '活动占比': pd.to_numeric(df.iloc[:, 10], errors='coerce').fillna(0) * 100,
            '销售额': pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0)
        })
        
        promo_data = promo_data[promo_data['总SKU数'] > 0]
        
        if len(promo_data) == 0:
            return insights
        
        # 1. 整体促销渗透率（正确计算：活动SKU数 / 总SKU数含多规格）
        total_sku_all = promo_data['总SKU数'].sum()  # 总SKU数（含多规格）
        total_promo = promo_data['活动SKU数'].sum()
        overall_ratio = (total_promo / total_sku_all * 100) if total_sku_all > 0 else 0
        
        insights.append({
            'title': f'📊 整体促销渗透率: {overall_ratio:.1f}%',
            'content': f"全店总SKU数{total_sku_all:.0f}个（含多规格），其中活动商品{total_promo:.0f}个，促销渗透率{overall_ratio:.1f}%。" +
                      ("促销力度充足，能有效吸引消费者。" if overall_ratio > 70 else
                       "促销力度适中，建议根据季节和节日适度加强。" if overall_ratio > 40 else
                       "促销力度偏弱，建议增加促销商品数量以提升竞争力。"),
            'level': 'success' if overall_ratio > 70 else 'info' if overall_ratio > 40 else 'warning'
        })
        
        # 2. 促销不均衡分析
        high_promo = promo_data[promo_data['活动占比'] > 80]
        low_promo = promo_data[promo_data['活动占比'] < 30]
        
        if len(low_promo) > 0:
            low_list = ", ".join(low_promo.nsmallest(3, '活动占比')['分类'].tolist())
            insights.append({
                'title': '⚠️ 促销力度不足分类',
                'content': f"发现{len(low_promo)}个分类促销力度不足(<30%)，如: {low_list}。建议增加这些分类的促销商品，平衡促销策略。",
                'level': 'warning'
            })
        
        if len(high_promo) > 0:
            high_list = ", ".join(high_promo.nlargest(3, '活动占比')['分类'].tolist())
            insights.append({
                'title': '✨ 促销力度突出分类',
                'content': f"{len(high_promo)}个分类促销力度强(>80%)，如: {high_list}。这些分类将成为吸引客流的重点品类。",
                'level': 'success'
            })
        
        # 3. 促销效能评估（销售额 vs 促销占比）
        avg_promo_ratio = promo_data['活动占比'].mean()
        median_sales = promo_data['销售额'].median()
        
        # 识别高效促销分类（活动占比高且销售额高）
        efficient_promo = promo_data[
            (promo_data['活动占比'] > avg_promo_ratio) & 
            (promo_data['销售额'] > median_sales)
        ]
        
        if len(efficient_promo) > 0:
            efficient_list = ", ".join(efficient_promo.nlargest(3, '销售额')['分类'].tolist())
            insights.append({
                'title': '🎯 高效促销分类',
                'content': f"{len(efficient_promo)}个分类促销效果显著(活动占比>{avg_promo_ratio:.0f}% 且 销售额>中位数)，如: {efficient_list}。建议维持并优化这些分类的促销策略。",
                'level': 'success'
            })
        
        return insights
    
    @staticmethod
    def create_sku_structure_analysis(category_df):
        """创建SKU结构优化分析
        
        包含:
        1. SKU结构分布饼图
        2. 多规格管理效率分析
        3. SKU集中度分析
        """
        if category_df.empty or len(category_df.columns) < 15:
            return html.Div("SKU结构数据不可用", className="alert alert-warning")
        
        # 提取数据
        df = category_df.copy()
        
        sku_data = pd.DataFrame({
            '分类': df.iloc[:, 0],  # A列
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0),  # B列（含多规格）
            '多规格SKU数': pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0),  # C列
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0),  # E列
            'SKU占比': pd.to_numeric(df.iloc[:, 14], errors='coerce').fillna(0) * 100,  # O列（转百分比）
            '销售额': pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0)  # S列
        })
        
        # 计算单规格SKU数
        sku_data['单规格SKU数'] = sku_data['去重SKU数'] - (sku_data['多规格SKU数'] / 2)  # 简化估算
        sku_data['单规格SKU数'] = sku_data['单规格SKU数'].clip(lower=0)
        
        # 过滤有效数据
        sku_data = sku_data[sku_data['总SKU数'] > 0]
        
        # 1. 创建整体SKU结构饼图
        total_sku = sku_data['总SKU数'].sum()
        total_multi = sku_data['多规格SKU数'].sum()
        total_dedup = sku_data['去重SKU数'].sum()
        redundant_sku = total_sku - total_dedup
        
        fig_pie = go.Figure()
        
        fig_pie.add_trace(go.Pie(
            labels=['去重SKU', '多规格重复'],
            values=[total_dedup, redundant_sku],
            hole=0.4,
            marker=dict(colors=['#3498db', '#e74c3c']),
            textinfo='label+percent+value',
            texttemplate='<b>%{label}</b><br>%{value}个<br>(%{percent})',
            hovertemplate='<b>%{label}</b><br>数量: %{value}个<br>占比: %{percent}<extra></extra>'
        ))
        
        fig_pie.update_layout(
            title=dict(
                text=f'<b>全店SKU结构</b><br><sub>总SKU: {total_sku:.0f} | 去重后: {total_dedup:.0f} | 精简空间: {redundant_sku:.0f}</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            height=450,
            margin=dict(t=100, b=50),
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # 2. 创建SKU集中度分析（帕累托图）
        sku_data_sorted = sku_data.sort_values('SKU占比', ascending=False)
        sku_data_sorted['累计占比'] = sku_data_sorted['SKU占比'].cumsum()
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 柱状图：SKU占比
        fig_pareto.add_trace(
            go.Bar(
                x=sku_data_sorted['分类'],
                y=sku_data_sorted['SKU占比'],
                name='SKU占比',
                marker=dict(color='#3498db'),
                hovertemplate='<b>%{x}</b><br>SKU占比: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=False
        )
        
        # 折线图：累计占比
        fig_pareto.add_trace(
            go.Scatter(
                x=sku_data_sorted['分类'],
                y=sku_data_sorted['累计占比'],
                name='累计占比',
                mode='lines+markers',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=8),
                hovertemplate='<b>%{x}</b><br>累计占比: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True
        )
        
        # 添加80%参考线
        fig_pareto.add_hline(
            y=80, line_dash="dash", line_color="orange", opacity=0.5,
            annotation_text="80%基准线", annotation_position="right",
            secondary_y=True
        )
        
        fig_pareto.update_layout(
            title=dict(
                text='<b>SKU集中度分析（帕累托图）</b><br><sub>识别核心品类，优化SKU结构</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            height=550,
            margin=dict(l=80, r=80, t=120, b=180),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            hovermode='x unified',
            xaxis=dict(
                tickangle=-60,
                tickfont=dict(size=10)
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            )
        )
        
        fig_pareto.update_yaxes(title_text="SKU占比 (%)", secondary_y=False)
        fig_pareto.update_yaxes(title_text="累计占比 (%)", secondary_y=True, range=[0, 105])
        
        # 3. 创建多规格管理效率柱状图
        sku_data['多规格比例'] = (sku_data['多规格SKU数'] / sku_data['总SKU数'] * 100).fillna(0)
        top10_multi = sku_data.nlargest(10, '多规格比例')
        
        fig_multi = go.Figure()
        
        colors_multi = ['#e74c3c' if ratio > 50 else '#f39c12' if ratio > 30 else '#2ecc71' 
                        for ratio in top10_multi['多规格比例']]
        
        fig_multi.add_trace(go.Bar(
            x=top10_multi['多规格比例'],
            y=top10_multi['分类'],
            orientation='h',
            marker=dict(
                color=colors_multi,
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=[f"{ratio:.1f}%" for ratio in top10_multi['多规格比例']],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>多规格占比: %{x:.1f}%<extra></extra>'
        ))
        
        fig_multi.update_layout(
            title=dict(
                text='<b>多规格商品TOP10分类</b><br><sub>红色>50% | 橙色30-50% | 绿色<30%</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='多规格SKU占比 (%)',
            yaxis_title='',
            height=550,
            margin=dict(l=150, r=120, t=100, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', range=[0, max(top10_multi['多规格比例']) * 1.15])
        )
        
        # 组合所有组件
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_pie, config={'displayModeBar': False})
                ], width=5),
                dbc.Col([
                    dcc.Graph(figure=fig_multi, config={'displayModeBar': False})
                ], width=7)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_pareto, config={'displayModeBar': False})
                ], width=12)
            ])
        ])
    
    @staticmethod
    def generate_sku_structure_insights(category_df):
        """生成SKU结构优化智能洞察"""
        if category_df.empty or len(category_df.columns) < 15:
            return []
        
        insights = []
        
        # 提取数据
        df = category_df.copy()
        sku_data = pd.DataFrame({
            '分类': df.iloc[:, 0],
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0),
            '多规格SKU数': pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0),
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0),
            'SKU占比': pd.to_numeric(df.iloc[:, 14], errors='coerce').fillna(0) * 100
        })
        
        sku_data = sku_data[sku_data['总SKU数'] > 0]
        
        if len(sku_data) == 0:
            return insights
        
        # 1. SKU精简潜力
        total_sku = sku_data['总SKU数'].sum()
        total_dedup = sku_data['去重SKU数'].sum()
        redundant = total_sku - total_dedup
        redundant_ratio = (redundant / total_sku * 100) if total_sku > 0 else 0
        
        insights.append({
            'title': f'📦 SKU精简空间: {redundant:.0f}个',
            'content': f"全店共有{total_sku:.0f}个SKU(含多规格)，去重后为{total_dedup:.0f}个，存在{redundant:.0f}个({redundant_ratio:.1f}%)重复规格。" +
                      ("重复率偏高，建议评估多规格必要性，精简低效规格。" if redundant_ratio > 40 else
                       "多规格管理合理，建议持续优化。"),
            'level': 'warning' if redundant_ratio > 40 else 'success'
        })
        
        # 2. SKU集中度分析
        sku_data_sorted = sku_data.sort_values('SKU占比', ascending=False)
        sku_data_sorted['累计占比'] = sku_data_sorted['SKU占比'].cumsum()
        top_n_for_80 = len(sku_data_sorted[sku_data_sorted['累计占比'] <= 80])
        total_categories = len(sku_data)
        concentration_ratio = (top_n_for_80 / total_categories * 100) if total_categories > 0 else 0
        
        top_categories = ", ".join(sku_data_sorted.head(top_n_for_80)['分类'].tolist()[:5])
        
        insights.append({
            'title': f'📊 SKU集中度: {top_n_for_80}个分类占80%',
            'content': f"{top_n_for_80}个分类({concentration_ratio:.1f}%)的SKU数量占全店的80%，如: {top_categories}等。" +
                      ("SKU分布较为集中，核心品类明确。" if concentration_ratio < 40 else
                       "SKU分布较为分散，建议聚焦核心品类。"),
            'level': 'success' if concentration_ratio < 40 else 'info'
        })
        
        # 3. 多规格管理建议（优化版：区分合理多规格和过度复杂）
        sku_data['多规格比例'] = (sku_data['多规格SKU数'] / sku_data['总SKU数'] * 100).fillna(0)
        
        # 计算全店整体多规格比例
        total_multi_sku = sku_data['多规格SKU数'].sum()
        total_all_sku = sku_data['总SKU数'].sum()
        overall_multi_ratio = (total_multi_sku / total_all_sku * 100) if total_all_sku > 0 else 0
        
        # 合理多规格：占比30-60%，说明供给选择丰富
        reasonable_multi = sku_data[(sku_data['多规格比例'] >= 30) & (sku_data['多规格比例'] <= 60)]
        # 过度复杂：占比>70%，可能管理复杂度过高
        excessive_multi = sku_data[sku_data['多规格比例'] > 70]
        # 多规格不足：占比<15%，可丰富规格选择
        low_multi = sku_data[sku_data['多规格比例'] < 15]
        
        # 根据整体多规格比例给出全局评价
        if overall_multi_ratio >= 30 and overall_multi_ratio <= 50:
            insights.append({
                'title': '✅ 多规格供给结构优秀',
                'content': f"全店多规格SKU占比{overall_multi_ratio:.1f}%，处于合理区间(30-50%)。多规格商品丰富，能够满足不同用户的多元化需求，供给能力强。",
                'level': 'success'
            })
        elif overall_multi_ratio > 50 and overall_multi_ratio <= 65:
            insights.append({
                'title': '🎯 多规格供给充足',
                'content': f"全店多规格SKU占比{overall_multi_ratio:.1f}%，供给选择非常丰富。建议关注管理效率，确保多规格带来的用户价值大于管理成本。",
                'level': 'info'
            })
        elif overall_multi_ratio > 65:
            insights.append({
                'title': '⚠️ 多规格管理复杂度较高',
                'content': f"全店多规格SKU占比{overall_multi_ratio:.1f}%，虽然供给选择极其丰富，但管理复杂度较高。建议评估部分低效规格的必要性，平衡用户选择与运营效率。",
                'level': 'warning'
            })
        elif overall_multi_ratio < 20:
            insights.append({
                'title': '💡 多规格供给待提升',
                'content': f"全店多规格SKU占比仅{overall_multi_ratio:.1f}%，供给选择相对单一。建议在核心品类增加多规格选择(如不同容量、口味等)，提升用户满意度和客单价。",
                'level': 'info'
            })
        
        # 只有在存在过度复杂分类时才发出警告
        if len(excessive_multi) > 0:
            excessive_list = ", ".join(excessive_multi.nlargest(3, '多规格比例')['分类'].tolist())
            insights.append({
                'title': '⚠️ 个别分类多规格过度复杂',
                'content': f"{len(excessive_multi)}个分类多规格占比超70%，如: {excessive_list}。建议评估这些分类的规格合理性，避免过度细分导致管理复杂和用户选择困难。",
                'level': 'warning'
            })
        
        # 4. 长尾SKU优化
        low_sku = sku_data[sku_data['SKU占比'] < 2]  # 占比低于2%的分类
        if len(low_sku) > 0:
            insights.append({
                'title': '💡 长尾SKU优化建议',
                'content': f"发现{len(low_sku)}个长尾分类(SKU占比<2%)，总计{low_sku['总SKU数'].sum():.0f}个SKU。建议评估其必要性，考虑精简或整合以提升管理效率。",
                'level': 'info'
            })
        
        return insights
    
    # ========== 滞销商品诊断看板方法 ==========
    @staticmethod
    def create_unsold_analysis_kpis(unsold_df, total_skus):
        """创建滞销商品核心指标卡片"""
        if unsold_df.empty:
            return html.Div("恭喜！没有滞销商品🎉", 
                          className="alert alert-success text-center", 
                          style={'fontSize': '20px', 'fontWeight': 'bold'})
        
        # 🔧 关键修复：剔除0库存商品（0库存不应算滞销）
        stock_col = pd.to_numeric(unsold_df.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        unsold_df_filtered = unsold_df[stock_col > 0].copy()  # 只保留有库存的滞销商品
        
        if unsold_df_filtered.empty:
            return html.Div("恭喜！没有滞销商品（已排除0库存）🎉", 
                          className="alert alert-success text-center", 
                          style={'fontSize': '20px', 'fontWeight': 'bold'})
        
        # 计算核心指标（基于有库存的滞销商品）
        unsold_count = len(unsold_df_filtered)
        unsold_ratio = (unsold_count / total_skus * 100) if total_skus > 0 else 0
        
        # 计算库存总金额 = 原价 × 库存
        price_col = pd.to_numeric(unsold_df_filtered.iloc[:, 4], errors='coerce').fillna(0)  # E列:原价
        stock_col_filtered = pd.to_numeric(unsold_df_filtered.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        total_stock_value = (price_col * stock_col_filtered).sum()
        
        # 高价滞销品数量 (原价>50)
        high_price_unsold = (price_col > 50).sum()
        
        # 平均库存金额
        avg_stock_value = total_stock_value / unsold_count if unsold_count > 0 else 0
        
        kpi_configs = [
            {'value': unsold_count, 'label': '滞销SKU总数', 'icon': '📦', 'color': 'danger'},
            {'value': f"{unsold_ratio:.1f}%", 'label': '滞销商品占比', 'icon': '📉', 'color': 'warning'},
            {'value': f"¥{total_stock_value:,.0f}", 'label': '滞销库存总金额', 'icon': '💰', 'color': 'danger'},
            {'value': high_price_unsold, 'label': '高价滞销品(>50元)', 'icon': '💎', 'color': 'warning'},
            {'value': f"¥{avg_stock_value:,.0f}", 'label': '平均库存金额', 'icon': '📊', 'color': 'info'}
        ]
        
        cards = []
        for config in kpi_configs:
            card = dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div(config['icon'], style={'fontSize': '2.5rem', 'marginBottom': '0.5rem'}),
                        html.H3(config['value'], className="mb-1", style={'fontWeight': 'bold'}),
                        html.P(config['label'], className="text-muted mb-0", style={'fontSize': '0.9rem'})
                    ], className="text-center")
                ])
            ], color=config['color'], outline=True, className="h-100")
            cards.append(dbc.Col(card, style={'flex': '0 0 16.666667%', 'maxWidth': '16.666667%'}, className="mb-3"))
        
        return dbc.Row(cards, style={'display': 'flex', 'flexWrap': 'wrap'})
    
    @staticmethod
    def create_unsold_category_pie(unsold_df):
        """滞销分类分布饼图"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.pie(title="暂无滞销数据"), style={'height': '400px'})
        
        # 按一级分类统计
        category_counts = unsold_df.iloc[:, 3].value_counts().head(10)  # D列:一级分类
        
        fig = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="🍰 滞销分类分布TOP10",
            hole=0.4
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>滞销数量: %{value}<br>占比: %{percent}<extra></extra>'
        )
        
        fig.update_layout(
            height=400,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
        )
        
        return dcc.Graph(figure=fig, style={'height': '400px'})
    
    @staticmethod
    def create_unsold_price_distribution(unsold_df):
        """滞销价格带分布柱状图"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.bar(title="暂无数据"), style={'height': '400px'})
        
        # 定义价格带
        price_col = pd.to_numeric(unsold_df.iloc[:, 1], errors='coerce').fillna(0)  # B列:售价
        
        price_bands = [
            ('0-10元', (price_col >= 0) & (price_col < 10)),
            ('10-20元', (price_col >= 10) & (price_col < 20)),
            ('20-50元', (price_col >= 20) & (price_col < 50)),
            ('50-100元', (price_col >= 50) & (price_col < 100)),
            ('100+元', price_col >= 100)
        ]
        
        band_counts = {band: mask.sum() for band, mask in price_bands}
        
        fig = go.Figure([
            go.Bar(
                x=list(band_counts.keys()),
                y=list(band_counts.values()),
                marker=dict(
                    color=list(band_counts.values()),
                    colorscale='Reds',
                    showscale=False
                ),
                text=list(band_counts.values()),
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title="📊 滞销价格带分布",
            xaxis_title="价格带",
            yaxis_title="SKU数量",
            height=450,
            showlegend=False,
            margin=dict(t=80, b=60, l=60, r=40)
        )
        
        return dcc.Graph(figure=fig, style={'height': '450px'})
    
    @staticmethod
    def create_unsold_stock_bubble(unsold_df):
        """滞销库存压力气泡图"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.scatter(title="暂无数据"), style={'height': '500px'})
        
        # 准备数据
        df_plot = unsold_df.copy()
        df_plot['price'] = pd.to_numeric(df_plot.iloc[:, 4], errors='coerce').fillna(0)  # E列:原价
        df_plot['stock'] = pd.to_numeric(df_plot.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        df_plot['stock_value'] = df_plot['price'] * df_plot['stock']
        df_plot['category'] = df_plot.iloc[:, 3]  # D列:一级分类
        df_plot['product_name'] = df_plot.iloc[:, 0]  # A列:商品名称
        
        # 只显示TOP50高风险商品
        df_plot = df_plot.nlargest(50, 'stock_value')
        
        fig = px.scatter(
            df_plot,
            x='price',
            y='stock',
            size='stock_value',
            color='category',
            hover_data={'product_name': True, 'stock_value': ':,.0f'},
            title="🔴 滞销库存压力气泡图 (TOP50)",
            labels={'price': '原价(元)', 'stock': '库存数量', 'category': '一级分类'}
        )
        
        fig.update_traces(
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                         '原价: ¥%{x:.2f}<br>' +
                         '库存: %{y}<br>' +
                         '库存金额: ¥%{customdata[1]}<br>' +
                         '<extra></extra>'
        )
        
        fig.update_layout(
            height=500,
            xaxis_title="原价(元)",
            yaxis_title="库存数量",
            showlegend=True
        )
        
        return dcc.Graph(figure=fig, style={'height': '500px'})
    
    @staticmethod
    def create_unsold_discount_scatter(unsold_df):
        """滞销原因分析矩阵(折扣力度 vs 售价)"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.scatter(title="暂无数据"), style={'height': '400px'})
        
        # 准备数据
        df_plot = unsold_df.copy()
        df_plot['price'] = pd.to_numeric(df_plot.iloc[:, 1], errors='coerce').fillna(0)  # B列:售价
        df_plot['original_price'] = pd.to_numeric(df_plot.iloc[:, 4], errors='coerce').fillna(0)  # E列:原价
        
        # 计算折扣力度
        df_plot['discount_rate'] = ((df_plot['original_price'] - df_plot['price']) / df_plot['original_price'] * 100).fillna(0)
        df_plot['has_discount'] = df_plot['discount_rate'] > 0
        df_plot['product_name'] = df_plot.iloc[:, 0]
        
        # 标记折扣状态
        df_plot['discount_status'] = df_plot['has_discount'].map({True: '有折扣', False: '无折扣'})
        
        fig = px.scatter(
            df_plot,
            x='discount_rate',
            y='price',
            color='discount_status',
            hover_data={'product_name': True},
            title="🔍 滞销原因分析矩阵",
            labels={'discount_rate': '折扣力度(%)', 'price': '售价(元)', 'discount_status': '折扣状态'},
            color_discrete_map={'有折扣': '#28a745', '无折扣': '#dc3545'}
        )
        
        fig.update_traces(
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                         '售价: ¥%{y:.2f}<br>' +
                         '折扣力度: %{x:.1f}%<br>' +
                         '<extra></extra>'
        )
        
        fig.update_layout(height=400)
        
        return dcc.Graph(figure=fig, style={'height': '400px'})
    
    @staticmethod
    def create_unsold_top_table(unsold_df):
        """创建TOP20高风险滞销商品表格"""
        if unsold_df.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        # 准备数据
        df_table = unsold_df.copy()
        df_table['product_name'] = df_table.iloc[:, 0]  # A列
        df_table['category'] = df_table.iloc[:, 3]  # D列
        df_table['price'] = pd.to_numeric(df_table.iloc[:, 1], errors='coerce').fillna(0)  # B列
        df_table['original_price'] = pd.to_numeric(df_table.iloc[:, 4], errors='coerce').fillna(0)  # E列
        df_table['stock'] = pd.to_numeric(df_table.iloc[:, 5], errors='coerce').fillna(0)  # F列
        df_table['stock_value'] = df_table['original_price'] * df_table['stock']
        df_table['discount_rate'] = ((df_table['original_price'] - df_table['price']) / df_table['original_price'] * 100).fillna(0)
        
        # 按库存金额降序
        df_table = df_table.nlargest(20, 'stock_value')
        
        # 生成建议操作
        def get_suggestion(row):
            if row['stock_value'] > 500:
                return "🔥 建议清仓"
            elif row['discount_rate'] == 0:
                return "💰 建议促销"
            elif row['price'] < 20 and row['stock'] > 20:
                return "🗑️ 建议下架"
            else:
                return "📊 需要调研"
        
        df_table['suggestion'] = df_table.apply(get_suggestion, axis=1)
        
        # 构建表格
        table_data = []
        for idx, row in df_table.iterrows():
            table_data.append(html.Tr([
                html.Td(row['product_name'], style={'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                html.Td(row['category']),
                html.Td(f"¥{row['price']:.2f}"),
                html.Td(f"¥{row['original_price']:.2f}"),
                html.Td(f"{row['discount_rate']:.1f}%"),
                html.Td(str(int(row['stock']))),
                html.Td(f"¥{row['stock_value']:,.0f}", style={'fontWeight': 'bold', 'color': '#dc3545'}),
                html.Td(row['suggestion'], style={'fontWeight': 'bold'})
            ]))
        
        table = dbc.Table([
            html.Thead(html.Tr([
                html.Th("商品名称"),
                html.Th("一级分类"),
                html.Th("售价"),
                html.Th("原价"),
                html.Th("折扣力度"),
                html.Th("库存"),
                html.Th("库存金额"),
                html.Th("建议操作")
            ])),
            html.Tbody(table_data)
        ], bordered=True, hover=True, responsive=True, striped=True, size='sm')
        
        return table
    
    @staticmethod
    def generate_unsold_insights(unsold_df, total_skus):
        """生成滞销商品智能洞察"""
        if unsold_df.empty:
            return []
        
        insights = []
        
        # 1. 滞销率分析
        unsold_ratio = len(unsold_df) / total_skus * 100 if total_skus > 0 else 0
        if unsold_ratio > 30:
            insights.append({
                'title': '⚠️ 滞销率较高',
                'content': f"滞销率{unsold_ratio:.1f}%，建议重点检查SKU结构",
                'level': 'danger'
            })
        
        # 2. 分类分析
        category_counts = unsold_df.iloc[:, 3].value_counts()
        if len(category_counts) > 0:
            top_category = category_counts.index[0]
            top_count = category_counts.values[0]
            insights.append({
                'title': '📉 滞销分类TOP1',
                'content': f"{top_category}分类滞销最多({top_count}个)，建议重点关注",
                'level': 'warning'
            })
        
        # 3. 高价滞销品
        price_col = pd.to_numeric(unsold_df.iloc[:, 4], errors='coerce').fillna(0)
        high_price_count = (price_col > 100).sum()
        if high_price_count > 0:
            stock_col = pd.to_numeric(unsold_df.iloc[:, 5], errors='coerce').fillna(0)
            high_price_value = (price_col[price_col > 100] * stock_col[price_col > 100]).sum()
            insights.append({
                'title': '💰 高价滞销品警告',
                'content': f"{high_price_count}个高价滞销品(>100元)占用资金¥{high_price_value:,.0f}，建议加大促销",
                'level': 'danger'
            })
        
        # 4. 无折扣商品
        original_price_col = pd.to_numeric(unsold_df.iloc[:, 4], errors='coerce').fillna(0)
        sale_price_col = pd.to_numeric(unsold_df.iloc[:, 1], errors='coerce').fillna(0)
        no_discount_count = (original_price_col == sale_price_col).sum()
        if no_discount_count > 0:
            insights.append({
                'title': '🏷️ 无折扣建议',
                'content': f"{no_discount_count}个滞销商品无折扣，建议设置促销活动",
                'level': 'info'
            })
        
        # 5. 高库存警告
        stock_col = pd.to_numeric(unsold_df.iloc[:, 5], errors='coerce').fillna(0)
        high_stock_count = (stock_col > 50).sum()
        if high_stock_count > 0:
            insights.append({
                'title': '📦 高库存警告',
                'content': f"{high_stock_count}个商品库存>50且滞销，建议清仓处理",
                'level': 'warning'
            })
        
        # 格式化为展示组件
        formatted_insights = []
        for insight in insights:
            color_map = {
                'danger': 'danger',
                'warning': 'warning',
                'info': 'info',
                'success': 'success'
            }
            formatted_insights.append(
                dbc.Alert([
                    html.H5(insight['title'], className="alert-heading"),
                    html.P(insight['content'], className="mb-0")
                ], color=color_map.get(insight['level'], 'info'))
            )
        
        return html.Div(formatted_insights) if formatted_insights else html.Div()


# 初始化数据加载器
loader = DataLoader(DEFAULT_REPORT_PATH)

# 初始化Dash应用 - 使用国内CDN加速
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        'https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css',  # 国内CDN
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',  # 备用CDN1
        dbc.themes.BOOTSTRAP  # 原有CDN作为最后备份
    ],
    suppress_callback_exceptions=True  # 【修复】允许回调引用动态生成的组件ID
)
app.title = APP_TITLE

# 自定义CSS样式 - 添加多CDN备份
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no, maximum-scale=1, user-scalable=no">
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.11.1/font/bootstrap-icons.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
            /* 强制响应式布局 - 确保在CSS加载失败时也能正常显示 */
            * {
                box-sizing: border-box;
            }
            
            body {
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* Bootstrap Grid 备用系统 */
            .container, .container-fluid {
                width: 100%;
                padding-right: 15px;
                padding-left: 15px;
                margin-right: auto;
                margin-left: auto;
            }
            
            .row {
                display: flex;
                flex-wrap: wrap;
                margin-right: -15px;
                margin-left: -15px;
            }
            
            [class*="col-"] {
                position: relative;
                width: 100%;
                padding-right: 15px;
                padding-left: 15px;
            }
            
            /* 响应式列宽 - 完整Bootstrap 5规范 */
            .col-xs-12 { flex: 0 0 100%; max-width: 100%; }
            
            @media (min-width: 576px) {
                .col-sm-6 { flex: 0 0 50%; max-width: 50%; }
            }
            
            @media (min-width: 768px) {
                .col-md-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
            }
            
            @media (min-width: 992px) {
                .col-lg-3 { flex: 0 0 25%; max-width: 25%; }
                .col-lg-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
            }
            
            /* 固定列宽类 - Bootstrap标准 */
            .col-1 { flex: 0 0 8.333333%; max-width: 8.333333%; }
            .col-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
            .col-3 { flex: 0 0 25%; max-width: 25%; }
            .col-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
            .col-6 { flex: 0 0 50%; max-width: 50%; }
            .col-12 { flex: 0 0 100%; max-width: 100%; }
            
            @media (min-width: 1200px) {
                .col-xl-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
                .col-xl-3 { flex: 0 0 25%; max-width: 25%; }
            }
            
            @media (min-width: 1400px) {
                .col-xxl-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
            }
            
            /* 卡片样式优化 */
            .card {
                position: relative;
                display: flex;
                flex-direction: column;
                min-width: 0;
                word-wrap: break-word;
                background-color: #fff;
                background-clip: border-box;
                border: 1px solid rgba(0,0,0,.125);
                border-radius: 0.5rem;
                height: 100%;
                box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
            }
            
            /* 图表容器响应式 */
            .dash-graph, .js-plotly-plot {
                width: 100% !important;
                max-width: 100% !important;
            }
            
            /* 移动端优化 */
            @media (max-width: 575.98px) {
                body { font-size: 14px; }
                h1 { font-size: 1.5rem !important; }
                h2 { font-size: 1.3rem !important; }
                h3 { font-size: 1.1rem !important; }
                .section-title { font-size: 1.2rem; }
                .card-body { padding: 0.75rem; }
            }
            
            /* Card 样式备用 */
            .card {
                position: relative;
                display: flex;
                flex-direction: column;
                min-width: 0;
                word-wrap: break-word;
                background-color: #fff;
                background-clip: border-box;
                border: 1px solid rgba(0,0,0,.125);
                border-radius: 0.375rem;
                height: 100%;
            }
            
            .card-body {
                flex: 1 1 auto;
                padding: 1rem;
            }
            
            .h-100 {
                height: 100% !important;
            }
            
            .mb-3 {
                margin-bottom: 1rem !important;
            }
            
            .g-3 {
                gap: 1rem;
            }
            
            /* 容器响应式优化 */
            .main-container {
                padding: 20px;
                max-width: 100%;
                margin: 0 auto;
            }
            
            @media (max-width: 767.98px) {
                .main-container {
                    padding: 10px;
                }
            }
            
            /* 章节标题响应式 */
            .section-title {
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
                font-weight: bold;
            }
            .chart-section {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: 1px solid #e9ecef;
            }
            
            @media (max-width: 767.98px) {
                .chart-section {
                    padding: 15px;
                    margin-bottom: 20px;
                }
                .section-title {
                    font-size: 1.2rem;
                    margin-bottom: 20px;
                }
            }
            
            /* Plotly图表响应式 */
            .js-plotly-plot .plotly {
                width: 100% !important;
                height: auto !important;
            }
            
            .js-plotly-plot .plotly .main-svg {
                width: 100% !important;
            }
            
            /* PDF生成优化样式 */
            #pdf-export-status {
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
            }
            #pdf-export-status.generating {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffc107;
            }
            #pdf-export-status.success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #28a745;
            }
            #pdf-export-status.error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #dc3545;
            }
            
            /* KPI卡片问号图标hover效果 */
            .bi-question-circle:hover {
                opacity: 1 !important;
                color: #007bff !important;
                transform: scale(1.15);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# 应用布局
app.layout = html.Div([
    # 隐藏的Store组件用于触发所有图表更新
    dcc.Store(id='upload-trigger', data=0),
    dcc.Store(id='category-filter-state', data=[]),  # 存储选中的分类
    
    html.Div([
        # 标题区域
        html.Div([
            html.Div([
                html.H1("📊 O2O门店数据分析看板 v2.0", className="text-center mb-4", 
                       style={'color': '#2c3e50', 'fontWeight': 'bold', 'display': 'inline-block', 'width': '100%'}),
                html.Div([
                    html.Button(
                        "�️ 导出PNG图片", 
                        id="export-png-btn",
                        n_clicks=0,
                        style={
                            'position': 'absolute',
                            'right': '220px',
                            'top': '20px',
                            'padding': '12px 30px',
                            'backgroundColor': '#17a2b8',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '8px',
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'cursor': 'pointer',
                            'boxShadow': '0 4px 6px rgba(23, 162, 184, 0.3)',
                            'transition': 'all 0.3s ease'
                        },
                        title="导出当前看板为高清PNG图片"
                    ),
                    html.Button(
                        "�📄 下载PDF报告", 
                        id="export-pdf-btn",
                        n_clicks=0,
                        style={
                            'position': 'absolute',
                            'right': '30px',
                            'top': '20px',
                            'padding': '12px 30px',
                            'backgroundColor': '#28a745',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '8px',
                            'fontSize': '16px',
                            'fontWeight': 'bold',
                            'cursor': 'pointer',
                            'boxShadow': '0 4px 6px rgba(40, 167, 69, 0.3)',
                            'transition': 'all 0.3s ease'
                        },
                        title="一键生成并下载高质量PDF报告（包含所有图表和分析）"
                    ),
                    dcc.Download(id='download-pdf'),
                    dcc.Download(id='download-png'),
                    html.Div(id='pdf-export-status', style={'textAlign': 'right', 'marginTop': '70px', 'marginRight': '30px', 'fontSize': '13px', 'fontWeight': 'bold'}),
                    html.Div(id='png-export-status', style={'textAlign': 'right', 'marginTop': '95px', 'marginRight': '30px', 'fontSize': '13px', 'fontWeight': 'bold'})
                ], style={'position': 'relative'})
            ], style={'position': 'relative'}),
            html.P("智能自适应 · 数据驱动 · 一目了然", 
                  className="text-center text-muted mb-4")
        ]),
        
        # 文件上传和门店选择区域
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("📁 上传Excel文件:", style={'fontWeight': 'bold'}),
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            '拖拽文件到此处或 ',
                            html.A('点击选择文件', style={'color': '#007bff'})
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '2px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'borderColor': '#007bff',
                            'cursor': 'pointer'
                        },
                        multiple=False
                    ),
                    html.Div(id='upload-status', style={'marginTop': '10px', 'fontSize': '14px'})
                ], width=8),
                dbc.Col([
                    html.Label("🏪 选择门店:", style={'fontWeight': 'bold'}),
                    dcc.Dropdown(
                        id='store-selector',
                        options=[],
                        value=None,
                        placeholder="选择要查看的门店...",
                        style={'width': '100%'}
                    )
                ], width=4)
            ], className="mb-4")
        ], className="chart-section"),
        
        # 全局分类筛选器
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("🔍 一级分类筛选:", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                    dcc.Dropdown(
                        id='category-filter',
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="选择分类筛选(默认显示全部)...",
                        style={'width': '100%'}
                    ),
                    html.Div(id='filter-status', style={'marginTop': '5px', 'fontSize': '13px', 'color': '#666'})
                ], width=12)
            ])
        ], className="chart-section", style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'}),
        
        # KPI指标卡片
        html.Div([
            html.H2("🎯 核心指标概览", className="section-title"),
            html.Div(id="kpi-cards"),
            html.Div(id="kpi-insights"),
            # KPI指标说明Modal弹窗
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(id="kpi-modal-title")),
                dbc.ModalBody(id="kpi-modal-body"),
                dbc.ModalFooter(
                    dbc.Button("关闭", id="kpi-modal-close", className="ms-auto")
                ),
            ], id="kpi-modal", is_open=False, size="lg"),
            
            # 【新增】数据下钻Modal弹窗
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(id="drilldown-modal-title")),
                dbc.ModalBody(id="drilldown-modal-body", style={'maxHeight': '70vh', 'overflowY': 'auto'}),
                dbc.ModalFooter(
                    dbc.Button("关闭", id="drilldown-modal-close-btn", className="ms-auto")
                ),
            ], id="drilldown-modal", is_open=False, size="xl")  # xl = 超大尺寸
        ], className="chart-section"),
        
        # 一级分类动销分析
        html.Div([
            html.H2("📊 一级分类动销分析", className="section-title"),
            html.P("💡 提示：点击图表中的柱状图可查看该分类的详细SKU列表", 
                   className="text-muted", style={'fontSize': '0.9rem', 'fontStyle': 'italic'}),
            html.Div(id="category-sales-analysis")
        ], className="chart-section"),
        
        # 多规格商品供给分析
        html.Div([
            html.H2("🔀 多规格商品供给分析", className="section-title"),
            html.Div(id="multispec-supply-analysis")
        ], className="chart-section"),
        
        # 折扣商品分析
        html.Div([
            html.H2("💸 折扣商品供给与销售分析", className="section-title"),
            html.Div(id="discount-analysis")
        ], className="chart-section"),
        
        # 折扣渗透率热力图
        html.Div([
            html.H2("🔥 折扣渗透率热力图分析", className="section-title"),
            html.Div(id="discount-heatmap")
        ], className="chart-section"),
        
        # 价格带分析
        html.Div([
            html.H2("💰 价格带分布分析", className="section-title"),
            html.Div(id="price-distribution")
        ], className="chart-section"),
        
        # 销量与销售额气泡图
        html.Div([
            html.H2("🫧 分类销量与销售额对比分析", className="section-title"),
            html.Div(id="sales-bubble-chart")
        ], className="chart-section"),
        
        # 销量贡献树状图
        html.Div([
            html.H2("🌳 分类月售贡献树状图", className="section-title"),
            html.Div(id="sales-treemap")
        ], className="chart-section"),
        
        # 库存健康看板
        html.Div([
            html.H2("🏥 库存健康看板", className="section-title"),
            html.Div(id="inventory-health-analysis"),
            html.Div(id="inventory-insights", className="mt-3")
        ], className="chart-section"),
        
        # 促销效能分析
        html.Div([
            html.H2("🎯 促销效能分析", className="section-title"),
            html.Div(id="promotion-effectiveness-analysis"),
            html.Div(id="promotion-insights", className="mt-3")
        ], className="chart-section"),
        
        # SKU结构优化建议
        html.Div([
            html.H2("📊 SKU结构优化分析", className="section-title"),
            html.Div(id="sku-structure-analysis"),
            html.Div(id="sku-structure-insights", className="mt-3")
        ], className="chart-section"),
        
        # ========== 滞销商品诊断看板 ==========
        html.Div([
            html.H2("🚫 滞销商品诊断看板", className="section-title"),
            
            # 核心指标卡片
            html.Div(id="unsold-kpis", className="mb-4"),
            
            # 智能洞察面板
            html.Div(id="unsold-insights", className="mb-4"),
            
            # 第一行: 分类分布 + 价格带分布
            dbc.Row([
                dbc.Col(html.Div(id="unsold-category-pie"), width=6),
                dbc.Col(html.Div(id="unsold-price-distribution"), width=6)
            ], className="mb-4"),
            
            # 第二行: TOP20高风险滞销商品表格
            html.Div([
                html.H4("📄 TOP20高风险滞销商品详情", className="mb-3", 
                       style={'color': '#dc3545', 'fontWeight': 'bold'}),
                html.Div(id="unsold-top-table")
            ])
        ], className="chart-section"),
        
        # ========== AI智能分析 ==========
        html.Div([
            html.H2("🤖 AI智能分析", className="section-title"),
            html.P([
                "💡 ",
                html.Span("点击下方按钮,GLM-4大模型将对当前看板的所有数据进行全面分析,", 
                         style={'color': '#666'}),
                html.Br(),
                html.Span("提供业务洞察、策略建议和可执行的优化方案。", 
                         style={'color': '#666'})
            ], style={'fontSize': '0.95rem', 'marginBottom': '20px'}),
            
            # AI分析按钮
            html.Div([
                dbc.Button(
                    [
                        html.I(className="fas fa-brain me-2"),
                        "开始智能分析"
                    ],
                    id="ai-analyze-btn",
                    color="primary",
                    size="lg",
                    className="mb-3",
                    style={
                        'padding': '15px 40px',
                        'fontSize': '18px',
                        'fontWeight': 'bold',
                        'borderRadius': '10px',
                        'boxShadow': '0 4px 12px rgba(13, 110, 253, 0.3)',
                        'transition': 'all 0.3s ease'
                    }
                )
            ], style={'textAlign': 'center'}),
            
            # AI分析结果展示区(带加载动画)
            dcc.Loading(
                id="ai-loading",
                type="cube",  # 可选: default, graph, cube, circle, dot
                fullscreen=False,
                color="#ffffff",
                style={'marginTop': '25px'},
                children=[
                    html.Div(id="ai-analysis-result")
                ]
            )
            
        ], className="chart-section", style={
            'background': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'color': 'white',
            'borderRadius': '15px',
            'padding': '30px',
            'boxShadow': '0 10px 30px rgba(102, 126, 234, 0.3)'
        })
        
    ], className="main-container")
])

# ========== KPI指标说明Modal回调 ==========
# 为13个KPI指标创建统一的Modal弹窗回调
@app.callback(
    [Output('kpi-modal', 'is_open'),
     Output('kpi-modal-title', 'children'),
     Output('kpi-modal-body', 'children')],
    [Input({'type': 'kpi-help', 'index': ALL}, 'n_clicks'),
     Input('kpi-modal-close', 'n_clicks')],
    [State('kpi-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_kpi_modal(help_clicks, close_clicks, is_open):
    """处理KPI指标说明弹窗的打开和关闭"""
    ctx = dash.callback_context
    
    # 没有触发源，不做任何更新
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    # 获取触发的组件信息
    trigger = ctx.triggered[0]
    trigger_prop_id = trigger['prop_id']
    
    # 检查是否真的有按钮被点击（n_clicks 不为 None）
    if trigger['value'] is None:
        raise dash.exceptions.PreventUpdate
    
    # 关闭按钮
    if 'kpi-modal-close' in trigger_prop_id:
        return False, "", ""
    
    # 检查是否是KPI帮助按钮被点击
    if 'kpi-help' in trigger_prop_id:
        # 从prop_id中提取索引: {"index":0,"type":"kpi-help"}.n_clicks
        import json
        import re
        try:
            # 提取JSON部分 - 使用正则表达式更稳定
            match = re.search(r'\{[^}]+\}', trigger_prop_id)
            if match:
                json_str = match.group(0)
                trigger_id = json.loads(json_str)
                clicked_idx = trigger_id.get('index')
            else:
                raise dash.exceptions.PreventUpdate
        except Exception as e:
            print(f"解析trigger_id失败: {e}")
            raise dash.exceptions.PreventUpdate
        
        # KPI指标定义列表(与kpi_configs顺序一致)
        kpi_definitions = [
            {
                'title': '📦 总SKU数(含规格)',
                'content': '所有商品规格的总数量,包括多规格商品的各个子SKU。用于衡量商品丰富度。'
            },
            {
                'title': '🧩 多规格SKU总数',
                'content': '同一商品拥有多个规格选项的SKU数量。例如:可乐(300ml/500ml/1L)有3个多规格SKU。'
            },
            {
                'title': '📈 动销SKU数',
                'content': '有实际销量的商品数量(月售>0)。反映门店商品的活跃程度。'
            },
            {
                'title': '📉 滞销SKU数',
                'content': '月销量为0的商品数量。滞销商品占用库存资源,建议及时优化。'
            },
            {
                'title': '💰 总销售额(去重后)',
                'content': '门店当期总销售收入,已去除多规格商品的重复计算。用于评估门店整体营收能力。'
            },
            {
                'title': '💹 动销率',
                'content': '动销SKU数 ÷ 总SKU数。反映商品周转效率,建议保持在60%以上。'
            },
            {
                'title': '🔀 唯一多规格商品数',
                'content': '去重后的多规格商品种类数。例如:可乐有3个规格,但只算1个唯一商品。'
            },
            {
                'title': '🔥 门店爆品数',
                'content': '月销量超过10的热销商品数量。爆品驱动门店销售增长。'
            },
            {
                'title': '🏷️ 门店平均折扣',
                'content': '门店所有商品的平均折扣力度(售价÷原价)。7.8折表示平均优惠22%。'
            },
            {
                'title': '🔖 平均SKU单价',
                'content': '门店商品的平均售价。反映门店价格定位:高单价=高端定位,低单价=大众定位。'
            },
            {
                'title': '💎 高价值SKU占比(>50元)',
                'content': '售价超过50元的商品占比。高价值商品占比高说明门店盈利能力强。'
            },
            {
                'title': '📊 促销强度',
                'content': '参与促销活动的商品比例。高促销强度可提升销量但会影响利润率。'
            },
            {
                'title': '🚀 爆款集中度(TOP10)',
                'content': 'TOP10爆款商品的销售额占比。过高(>60%)说明依赖爆款,需优化长尾商品。'
            }
        ]
        
        if clicked_idx is not None and clicked_idx < len(kpi_definitions):
            kpi_info = kpi_definitions[clicked_idx]
            return True, kpi_info['title'], html.Div([
                html.P(kpi_info['content'], style={'fontSize': '16px', 'lineHeight': '1.8'}),
                html.Hr(),
                html.P("💡 提示: 该指标可帮助您了解门店当前运营状态,结合其他指标综合分析效果更佳。", 
                      style={'fontSize': '14px', 'color': '#6c757d', 'fontStyle': 'italic'})
            ])
    
    raise dash.exceptions.PreventUpdate

# 回调函数
@app.callback(
    [Output('store-selector', 'options'),
     Output('upload-status', 'children'),
     Output('upload-trigger', 'data')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')],
    prevent_initial_call=True
)
def update_store_options(contents, filename):
    """上传文件后更新门店选项和提示"""
    if contents is None:
        return [], html.Div(), 0
    
    try:
        import base64
        import io
        import time
        
        # 解析上传的文件
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # 读取Excel文件
        excel_file = pd.ExcelFile(io.BytesIO(decoded))
        sheet_names = excel_file.sheet_names
        
        if len(sheet_names) > 0:
            # 更新全局loader
            global loader
            loader = DataLoader(io.BytesIO(decoded))
            
            # 提取文件名（不含路径）
            display_filename = filename if filename else "未知文件"
            
            # 返回成功提示，包含文件名信息
            timestamp = int(time.time())
            success_msg = html.Div([
                html.Div([
                    html.I(className="bi bi-check-circle-fill", style={'marginRight': '8px'}),
                    html.Span("文件上传成功！", style={'fontWeight': 'bold'})
                ], style={'color': '#28a745', 'fontSize': '16px', 'marginBottom': '8px'}),
                html.Div([
                    html.Span("📄 当前分析文件: ", style={'color': '#6c757d', 'fontWeight': '500'}),
                    html.Span(display_filename, style={'color': '#007bff', 'fontWeight': 'bold'})
                ], style={'fontSize': '14px', 'marginBottom': '5px'}),
                html.Div([
                    html.Span(f"📊 包含 {len(sheet_names)} 个数据表", style={'color': '#6c757d', 'fontSize': '13px'})
                ])
            ], style={
                'padding': '12px 16px',
                'backgroundColor': '#d4edda',
                'border': '1px solid #c3e6cb',
                'borderRadius': '6px',
                'marginTop': '8px'
            })
            
            return [], success_msg, timestamp
        
        return [], html.Div("⚠️ 文件为空", style={'color': 'orange'}), 0
    except Exception as e:
        print(f"文件解析错误: {e}")
        error_msg = html.Div([
            html.I(className="bi bi-exclamation-triangle-fill", style={'color': '#dc3545', 'marginRight': '8px'}),
            f"文件上传失败: {str(e)}"
        ], style={'color': '#dc3545', 'padding': '10px', 'backgroundColor': '#f8d7da', 'border': '1px solid #f5c6cb', 'borderRadius': '5px', 'marginTop': '8px'})
        return [], error_msg, 0

# ========== 分类筛选器相关回调 ==========
@app.callback(
    [Output('category-filter', 'options'),
     Output('filter-status', 'children')],
    Input('upload-trigger', 'data')
)
def update_category_filter_options(upload_trigger):
    """上传文件后更新分类筛选器选项"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return [], html.Div("等待数据上传...", style={'color': '#999'})
        
        # 获取所有一级分类
        categories = sku_details.iloc[:, 3].dropna().unique().tolist()  # D列:一级分类
        categories = sorted([cat for cat in categories if cat])  # 排序并去除空值
        
        options = [{'label': cat, 'value': cat} for cat in categories]
        
        status_msg = html.Div([
            html.I(className="fas fa-info-circle", style={'marginRight': '5px'}),
            f"共 {len(categories)} 个分类可选 | 默认显示全部"
        ], style={'color': '#28a745'})
        
        return options, status_msg
    except Exception as e:
        print(f"分类筛选器选项更新错误: {e}")
        return [], html.Div("分类加载失败", style={'color': 'red'})

@app.callback(
    Output('category-filter-state', 'data'),
    Input('category-filter', 'value')
)
def update_category_filter_state(selected_categories):
    """更新分类筛选状态"""
    if not selected_categories:
        return []
    return selected_categories

@app.callback(
    [Output('kpi-cards', 'children'),
     Output('kpi-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('store-selector', 'value')]
)
def update_kpi_cards(upload_trigger, selected_store):
    """更新KPI卡片和洞察"""
    try:
        kpi_data = loader.get_kpi_summary()
        # 如果选择了门店，这里可以根据门店过滤数据
        # 当前版本假设单门店数据
        cards = DashboardComponents.create_kpi_cards(kpi_data)
        insights = DashboardComponents.generate_kpi_insights(kpi_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        return cards, insights_panel
    except Exception as e:
        print(f"KPI卡片更新错误: {e}")
        return html.Div("KPI数据加载失败"), html.Div()

@app.callback(
    Output('category-sales-analysis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_category_sales(upload_trigger, selected_categories):
    """更新一级分类动销分析"""
    try:
        category_data = loader.get_category_analysis()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]  # A列:一级分类
        
        return DashboardComponents.create_category_sales_analysis(category_data)
    except Exception as e:
        print(f"分类动销分析更新错误: {e}")
        return html.Div("分类动销数据加载失败")

@app.callback(
    Output('multispec-supply-analysis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_multispec_supply(upload_trigger, selected_categories):
    """更新多规格商品供给分析"""
    try:
        category_data = loader.get_category_analysis()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        return DashboardComponents.create_multispec_supply_analysis(category_data)
    except Exception as e:
        print(f"多规格供给分析更新错误: {e}")
        return html.Div("多规格供给数据加载失败")

@app.callback(
    Output('discount-analysis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_discount_analysis(upload_trigger, selected_categories):
    """更新折扣商品分析"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        return DashboardComponents.create_discount_analysis(category_data)
    except Exception as e:
        print(f"折扣分析更新错误: {e}")
        return html.Div("折扣数据加载失败")

@app.callback(
    Output('discount-heatmap', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_discount_heatmap(upload_trigger, selected_categories):
    """更新折扣渗透率热力图"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        return DashboardComponents.create_discount_heatmap(category_data)
    except Exception as e:
        print(f"折扣热力图更新错误: {e}")
        return html.Div("折扣热力图数据加载失败")

@app.callback(
    Output('price-distribution', 'children'),
    Input('upload-trigger', 'data')
)
def update_price_distribution(upload_trigger):
    """更新价格带分析"""
    try:
        price_data = loader.get_price_analysis()
        return DashboardComponents.create_price_distribution(price_data)
    except Exception as e:
        print(f"价格带分析更新错误: {e}")
        return html.Div("价格带数据加载失败")

@app.callback(
    Output('sales-bubble-chart', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_sales_bubble(upload_trigger, selected_categories):
    """更新销量与销售额气泡图"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        return DashboardComponents.create_sales_bubble_chart(category_data)
    except Exception as e:
        print(f"气泡图更新错误: {e}")
        return html.Div("气泡图数据加载失败")

@app.callback(
    Output('sales-treemap', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_sales_treemap(upload_trigger, selected_categories):
    """更新销量贡献树状图"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"🌳 树状图数据维度: {category_data.shape}")
        
        # 创建树状图
        treemap_chart = DashboardComponents.create_sales_treemap(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_treemap_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return html.Div([
            treemap_chart,
            insights_panel
        ])
    except Exception as e:
        import traceback
        print(f"树状图更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"树状图生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    [Output('inventory-health-analysis', 'children'),
     Output('inventory-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_inventory_health(upload_trigger, selected_categories):
    """更新库存健康看板"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"🏥 库存健康数据维度: {category_data.shape}")
        
        if category_data.empty:
            return html.Div("库存数据不可用", className="alert alert-warning"), html.Div()
        
        # 创建库存健康图表
        health_chart = DashboardComponents.create_inventory_health_chart(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_inventory_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return health_chart, insights_panel
    except Exception as e:
        import traceback
        print(f"库存健康分析更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"库存健康分析生成失败: {str(e)}", className="alert alert-danger"), html.Div()

@app.callback(
    [Output('promotion-effectiveness-analysis', 'children'),
     Output('promotion-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_promotion_effectiveness(upload_trigger, selected_categories):
    """更新促销效能分析"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"🎯 促销效能数据维度: {category_data.shape}")
        
        if category_data.empty:
            return html.Div("促销数据不可用", className="alert alert-warning"), html.Div()
        
        # 创建促销效能图表
        promo_chart = DashboardComponents.create_promotion_effectiveness_analysis(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_promotion_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return promo_chart, insights_panel
    except Exception as e:
        import traceback
        print(f"促销效能分析更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"促销效能分析生成失败: {str(e)}", className="alert alert-danger"), html.Div()

@app.callback(
    [Output('sku-structure-analysis', 'children'),
     Output('sku-structure-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_sku_structure(upload_trigger, selected_categories):
    """更新SKU结构优化分析"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"📊 SKU结构数据维度: {category_data.shape}")
        
        if category_data.empty:
            return html.Div("SKU结构数据不可用", className="alert alert-warning"), html.Div()
        
        # 创建SKU结构图表
        sku_chart = DashboardComponents.create_sku_structure_analysis(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_sku_structure_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return sku_chart, insights_panel
    except Exception as e:
        import traceback
        print(f"SKU结构分析更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"SKU结构分析生成失败: {str(e)}", className="alert alert-danger"), html.Div()

# ========== 滞销商品诊断看板回调函数 ==========
@app.callback(
    Output('unsold-kpis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_kpis(upload_trigger, selected_categories):
    """更新滞销商品核心指标"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("SKU详细数据不可用", className="alert alert-warning")
        
        # 筛选滞销商品 (月售=0 且 库存>0)
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)  # C列:月售
        stock_col = pd.to_numeric(sku_details.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        unsold_df = sku_details[(sales_col == 0) & (stock_col > 0)].copy()  # 🔧 剔除0库存
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]  # D列:一级分类
        
        total_skus = len(sku_details)
        
        print(f"🚫 滞销商品数量(有库存): {len(unsold_df)} / {total_skus}")
        
        return DashboardComponents.create_unsold_analysis_kpis(unsold_df, total_skus)
    except Exception as e:
        import traceback
        print(f"滞销KPI更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"滞销KPI生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    Output('unsold-insights', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_insights(upload_trigger, selected_categories):
    """更新滞销商品智能洞察"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div()
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        stock_col = pd.to_numeric(sku_details.iloc[:, 5], errors='coerce').fillna(0)
        unsold_df = sku_details[(sales_col == 0) & (stock_col > 0)].copy()  # 🔧 剔除0库存
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        total_skus = len(sku_details)
        
        return DashboardComponents.generate_unsold_insights(unsold_df, total_skus)
    except Exception as e:
        print(f"滞销洞察更新错误: {e}")
        return html.Div()

@app.callback(
    Output('unsold-category-pie', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_category_pie(upload_trigger, selected_categories):
    """更新滞销分类分布饼图"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        stock_col = pd.to_numeric(sku_details.iloc[:, 5], errors='coerce').fillna(0)
        unsold_df = sku_details[(sales_col == 0) & (stock_col > 0)].copy()  # 🔧 剔除0库存
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        return DashboardComponents.create_unsold_category_pie(unsold_df)
    except Exception as e:
        print(f"滞销分类饼图更新错误: {e}")
        return html.Div(f"图表生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    Output('unsold-price-distribution', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_price_distribution(upload_trigger, selected_categories):
    """更新滞销价格带分布"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        unsold_df = sku_details[sales_col == 0].copy()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        return DashboardComponents.create_unsold_price_distribution(unsold_df)
    except Exception as e:
        print(f"滞销价格分布更新错误: {e}")
        return html.Div(f"图表生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    Output('unsold-top-table', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_top_table(upload_trigger, selected_categories):
    """更新TOP20高风险滞销商品表格"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        unsold_df = sku_details[sales_col == 0].copy()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        return DashboardComponents.create_unsold_top_table(unsold_df)
    except Exception as e:
        print(f"滞销TOP表格更新错误: {e}")
        return html.Div(f"表格生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    [Output('download-png', 'data'),
     Output('png-export-status', 'children')],
    Input('export-png-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_to_png(n_clicks):
    """导出所有图表为PNG图片压缩包"""
    if n_clicks > 0:
        try:
            import zipfile
            import tempfile
            import shutil
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建图表列表（需要重新生成所有图表的figure对象）
            charts_to_export = []
            
            try:
                # 从loader获取数据
                category_df = loader.data.get('category_l1', pd.DataFrame())
                price_df = loader.data.get('price_analysis', pd.DataFrame())
                
                if not category_df.empty:
                    # 1. 分类月售柱状图
                    fig1 = px.bar(
                        category_df.head(15), 
                        x='一级分类', 
                        y='月售',
                        title='各分类月售TOP15'
                    )
                    charts_to_export.append(('01_分类月售分析.png', fig1))
                    
                    # 2. 多规格SKU对比图
                    if '美团一级分类多规格SKU数' in category_df.columns:
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(
                            name='多规格SKU',
                            x=category_df['一级分类'].head(10),
                            y=category_df['美团一级分类多规格SKU数'].head(10)
                        ))
                        fig2.update_layout(title='多规格商品分布TOP10')
                        charts_to_export.append(('02_多规格商品分析.png', fig2))
                    
                    # 3. 动销率对比图
                    if '美团一级分类动销率(类内)' in category_df.columns:
                        fig3 = px.bar(
                            category_df.head(15),
                            x='一级分类',
                            y='美团一级分类动销率(类内)',
                            title='各分类动销率对比TOP15'
                        )
                        charts_to_export.append(('03_动销率分析.png', fig3))
                
                if not price_df.empty and 'price_band' in price_df.columns:
                    # 4. 价格带分布图
                    fig4 = px.bar(
                        price_df,
                        x='price_band',
                        y='SKU数量',
                        title='价格带SKU分布'
                    )
                    charts_to_export.append(('04_价格带分析.png', fig4))
                
                # 导出所有图表为PNG
                exported_files = []
                for filename, fig in charts_to_export:
                    try:
                        img_path = os.path.join(temp_dir, filename)
                        fig.write_image(img_path, width=1200, height=800, scale=2)
                        exported_files.append(filename)
                    except Exception as e:
                        print(f"导出图表 {filename} 失败: {e}")
                        continue
                
                if len(exported_files) == 0:
                    raise Exception("没有图表可以导出，请确保已安装kaleido库")
                
                # 创建ZIP压缩包
                zip_filename = f"O2O看板图表_{timestamp}.zip"
                zip_path = os.path.join(temp_dir, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for filename in exported_files:
                        file_path = os.path.join(temp_dir, filename)
                        zipf.write(file_path, filename)
                
                # 读取ZIP文件
                with open(zip_path, 'rb') as f:
                    zip_bytes = f.read()
                
                # 清理临时文件
                shutil.rmtree(temp_dir)
                
                success_msg = html.Div([
                    html.Div(f"✅ 成功导出 {len(exported_files)} 张高清图表！", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(f"文件名: {zip_filename}", style={'fontSize': '12px'}),
                    html.Div(f"包含图表: {', '.join([f.replace('.png', '') for f in exported_files])}", 
                            style={'fontSize': '11px', 'marginTop': '5px', 'color': '#155724'})
                ], style={'color': '#155724', 'backgroundColor': '#d4edda', 
                         'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #28a745'})
                
                return dcc.send_bytes(zip_bytes, zip_filename), success_msg
                
            except ImportError as ie:
                # kaleido未安装
                error_msg = html.Div([
                    html.Div("⚠️ 需要安装图表导出库", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div("请在终端运行: pip install kaleido", style={'fontSize': '12px', 'marginTop': '5px'}),
                    html.Div("或使用浏览器截图: F12 → Ctrl+Shift+P → 输入'screenshot'", 
                            style={'fontSize': '11px', 'marginTop': '5px', 'color': '#856404'})
                ], style={'color': '#856404', 'backgroundColor': '#fff3cd', 
                         'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #ffc107'})
                return None, error_msg
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"PNG导出错误详情:\n{error_detail}")
            error_msg = html.Div(f"❌ 导出失败: {str(e)}", 
                                style={'color': '#721c24', 'backgroundColor': '#f8d7da', 
                                      'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #dc3545'})
            return None, error_msg
    
    return None, ""


@app.callback(
    [Output('download-pdf', 'data'),
     Output('pdf-export-status', 'children')],
    Input('export-pdf-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_to_pdf(n_clicks):
    """服务端生成高质量PDF报告"""
    if n_clicks > 0:
        try:
            # 从loader获取数据
            kpi_df = loader.data.get('kpi', pd.DataFrame())
            category_df = loader.data.get('category_l1', pd.DataFrame())
            price_df = loader.data.get('price_analysis', pd.DataFrame())
            
            # 生成PDF
            pdf_bytes = generate_dashboard_pdf(kpi_df, category_df, price_df)
            
            # 生成文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"O2O门店分析报告_{timestamp}.pdf"
            
            success_msg = html.Div(f"✅ PDF报告生成成功！文件名: {filename}", 
                                  style={'color': '#155724', 'backgroundColor': '#d4edda', 
                                        'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #28a745'})
            
            return dcc.send_bytes(pdf_bytes, filename), success_msg
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"PDF生成错误详情:\n{error_detail}")
            error_msg = html.Div(f"❌ PDF生成失败: {str(e)}", 
                                style={'color': '#721c24', 'backgroundColor': '#f8d7da', 
                                      'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #dc3545'})
            return None, error_msg
    
    return None, ""


def generate_dashboard_pdf(kpi_df, category_df, price_df):
    """生成完整的数据看板PDF报告"""
    # 创建PDF缓冲区
    buffer = io.BytesIO()
    
    # 使用横向A4纸张
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    
    # 注册中文字体（使用系统自带字体）
    try:
        # Windows系统字体路径（优先使用.ttf格式）
        font_paths = [
            "C:\\Windows\\Fonts\\simhei.ttf",   # 黑体（推荐）
            "C:\\Windows\\Fonts\\msyh.ttf",    # 微软雅黑
            "C:\\Windows\\Fonts\\simkai.ttf",  # 楷体
            "C:\\Windows\\Fonts\\simsun.ttc",  # 宋体
        ]
        
        font_registered = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('chinese', font_path))
                    c.setFont('chinese', 12)
                    font_registered = True
                    print(f"✅ 成功加载字体: {font_path}")
                    break
                except Exception as e:
                    print(f"⚠️ 字体加载失败 {font_path}: {e}")
                    continue
        
        if not font_registered:
            print("⚠️ 未找到中文字体，使用默认字体")
            c.setFont('Helvetica', 12)
    except Exception as e:
        print(f"字体注册错误: {e}")
        c.setFont('Helvetica', 12)
    
    page_num = 1
    
    # ===== 第1页：封面 =====
    draw_cover_page(c, page_width, page_height)
    c.showPage()
    page_num += 1
    
    # ===== 第2页：核心指标概览 =====
    try:
        c.setFont('chinese', 20)
        c.drawString(50, page_height - 50, "核心指标概览")
        
        # 绘制KPI卡片
        y_offset = page_height - 120
        if kpi_df is not None and not kpi_df.empty:
            draw_kpi_cards(c, kpi_df, 50, y_offset, page_width)
        else:
            c.setFont('chinese', 12)
            c.drawString(50, y_offset, "KPI数据不可用")
        
        c.setFont('chinese', 10)
        c.drawString(page_width - 100, 30, f"第 {page_num} 页")
        c.showPage()
        page_num += 1
    except Exception as e:
        print(f"KPI页面生成错误: {e}")
        import traceback
        print(traceback.format_exc())
    
    # ===== 第3页：数据摘要表格 =====
    try:
        c.setFont('chinese', 20)
        c.drawString(50, page_height - 50, "� 分类数据摘要")
        
        # 绘制摘要表格
        if category_data is not None and not category_data.empty:
            draw_summary_table(c, category_data, 50, page_height - 100, page_width - 100, page_num)
        
        c.setFont('chinese', 10)
        c.drawString(page_width - 100, 30, f"第 {page_num} 页")
        c.showPage()
        page_num += 1
    except Exception as e:
        print(f"摘要表格生成错误: {e}")
    
    # ===== 第4页：图表导出说明 =====
    try:
        c.setFont('chinese', 18)
        c.drawString(50, page_height - 50, "关于图表导出")
        
        c.setFont('chinese', 12)
        y_pos = page_height - 120
        
        notes = [
            "本PDF报告包含核心数据指标和摘要信息。",
            "",
            "完整的交互式图表（包括11个分析看板）请在浏览器中查看：",
            "- 分类月售分析",
            "- 多规格商品供给分析", 
            "- 折扣供给与销售分析",
            "- 价格带分布分析",
            "- 销售四维气泡图",
            "- 销售树状图",
            "- 库存健康看板",
            "- 促销效能分析",
            "- SKU结构优化建议",
            "",
            "如需导出特定图表，可在浏览器中右键点击图表，选择'保存图片'。",
            "",
            "本报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        for note in notes:
            c.drawString(80, y_pos, note)
            y_pos -= 25
        
        c.setFont('chinese', 10)
        c.drawString(page_width - 100, 30, f"第 {page_num} 页")
        c.showPage()
        page_num += 1
        
    except Exception as e:
        print(f"说明页生成错误: {e}")
    
    # 保存PDF
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def draw_summary_table(c, data, x, y, max_width, page_num):
    """绘制数据摘要表格"""
    try:
        c.setFont('chinese', 10)
    except:
        c.setFont('Helvetica', 10)
    
    # 选择关键列
    key_columns = ['一级分类', '美团一级分类sku数', '月售', '售价销售额', 
                   '美团一级分类动销率(类内)', '美团一级分类活动SKU占比(类内)',
                   '美团一级分类0库存率']
    
    # 筛选存在的列
    available_cols = [col for col in key_columns if col in data.columns]
    
    if not available_cols:
        c.drawString(x, y, "数据表格不可用")
        return
    
    # 表格参数
    row_height = 20
    col_width = max_width / len(available_cols)
    
    # 绘制表头
    c.setFillColor(colors.HexColor('#2c3e50'))
    c.rect(x, y - row_height, max_width, row_height, fill=1)
    
    c.setFillColor(colors.white)
    for idx, col in enumerate(available_cols):
        col_name = col.replace('美团一级分类', '')
        c.drawString(x + idx * col_width + 5, y - row_height + 5, col_name)
    
    # 绘制数据行（前10行）
    c.setFillColor(colors.black)
    for row_idx, (_, row) in enumerate(data.head(10).iterrows()):
        row_y = y - (row_idx + 2) * row_height
        
        # 交替行背景
        if row_idx % 2 == 0:
            c.setFillColor(colors.HexColor('#f8f9fa'))
            c.rect(x, row_y, max_width, row_height, fill=1)
        
        c.setFillColor(colors.black)
        for col_idx, col in enumerate(available_cols):
            value = row[col]
            
            # 格式化数值
            if isinstance(value, (int, float)):
                if '率' in col or '占比' in col:
                    display_value = f"{value:.1%}" if value < 1 else f"{value:.1f}%"
                elif '销售额' in col:
                    display_value = f"{int(value):,}"
                else:
                    display_value = f"{int(value)}" if value == int(value) else f"{value:.1f}"
            else:
                display_value = str(value)[:15]  # 限制长度
            
            c.drawString(x + col_idx * col_width + 5, row_y + 5, display_value)


def draw_cover_page(c, page_width, page_height):
    """绘制PDF封面"""
    try:
        c.setFont('chinese', 36)
    except:
        c.setFont('Helvetica-Bold', 36)
    
    # 标题
    title = "O2O门店数据分析报告"
    c.drawCentredString(page_width / 2, page_height - 150, title)
    
    # 副标题
    try:
        c.setFont('chinese', 18)
    except:
        c.setFont('Helvetica', 18)
    
    subtitle = "数据驱动 · 精准洞察 · 科学决策"
    c.drawCentredString(page_width / 2, page_height - 200, subtitle)
    
    # 生成时间
    try:
        c.setFont('chinese', 14)
    except:
        c.setFont('Helvetica', 14)
    
    report_date = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    c.drawCentredString(page_width / 2, page_height - 400, f"生成时间: {report_date}")
    
    # 页脚
    try:
        c.setFont('chinese', 10)
    except:
        c.setFont('Helvetica', 10)
    
    c.drawCentredString(page_width / 2, 50, "本报告由O2O门店数据分析看板自动生成")


def draw_kpi_cards(c, kpi_data, x, y, page_width):
    """在PDF中绘制KPI指标卡片"""
    try:
        c.setFont('chinese', 12)
    except:
        c.setFont('Helvetica', 12)
    
    # KPI列配置
    kpi_cols = [
        '总SKU数(含多规格)', '多规格SKU数', '多规格SPU数', '去重SKU数', 
        '动销SKU数', '动销率', '活动SKU数', '活动SKU占比', 
        '爆品SKU数', '折扣SKU数', '折扣'
    ]
    
    # 每行显示4个指标
    cards_per_row = 4
    card_width = (page_width - 100) / cards_per_row - 20
    card_height = 80
    
    for idx, col in enumerate(kpi_cols):
        if col not in kpi_data.columns:
            continue
            
        value = kpi_data[col].iloc[0] if not kpi_data[col].empty else "N/A"
        
        # 计算卡片位置
        row = idx // cards_per_row
        col_pos = idx % cards_per_row
        
        card_x = x + col_pos * (card_width + 20)
        card_y = y - row * (card_height + 20)
        
        # 绘制卡片边框
        c.setStrokeColor(colors.HexColor('#e9ecef'))
        c.setFillColor(colors.HexColor('#f8f9fa'))
        c.rect(card_x, card_y - card_height, card_width, card_height, fill=1)
        
        # 绘制标题
        c.setFillColor(colors.HexColor('#6c757d'))
        try:
            c.setFont('chinese', 10)
        except:
            c.setFont('Helvetica', 10)
        c.drawString(card_x + 10, card_y - 25, col)
        
        # 绘制数值
        c.setFillColor(colors.HexColor('#2c3e50'))
        try:
            c.setFont('chinese', 16)
        except:
            c.setFont('Helvetica-Bold', 16)
        
        # 格式化数值
        if isinstance(value, (int, float)):
            if '率' in col or '占比' in col or '折扣' in col:
                display_value = f"{value:.1%}" if value < 1 else f"{value:.1f}%"
            else:
                display_value = f"{int(value):,}"
        else:
            display_value = str(value)
        
        c.drawString(card_x + 10, card_y - 55, display_value)


def export_charts_to_pdf(c, chart_element, x, y, max_width, max_height):
    """将Dash图表元素导出为PDF图片"""
    try:
        # 由于Dash回调中的图表是动态生成的，我们需要重新创建图表
        # 这里使用占位符文本，实际实现中需要访问存储的图表数据
        
        try:
            c.setFont('chinese', 12)
        except:
            c.setFont('Helvetica', 12)
        
        c.setFillColor(colors.HexColor('#6c757d'))
        c.drawString(x, y, "图表区域（动态内容需在浏览器中查看）")
        
        # 绘制边框表示图表位置
        c.setStrokeColor(colors.HexColor('#dee2e6'))
        c.setFillColor(colors.white)
        c.rect(x, y - 300, max_width, 280, fill=0)
        
    except Exception as e:
        print(f"图表导出错误: {e}")
        try:
            c.setFont('chinese', 12)
        except:
            c.setFont('Helvetica', 12)
        c.setFillColor(colors.HexColor('#dc3545'))
        c.drawString(x, y, f"图表区域")


# ========== 数据下钻回调 ==========
@app.callback(
    [Output('drilldown-modal', 'is_open'),
     Output('drilldown-modal-title', 'children'),
     Output('drilldown-modal-body', 'children')],
    [Input('category-sales-graph', 'clickData'),
     Input('drilldown-modal-close-btn', 'n_clicks')],
    [State('drilldown-modal', 'is_open')],
    prevent_initial_call=True  # 防止初始加载时触发，因为graph是动态生成的
)
def handle_category_drilldown(clickData, n_clicks, is_open):
    """处理一级分类图表的点击下钻事件"""
    ctx = dash.callback_context
    
    # 如果点击关闭按钮，则关闭Modal
    if ctx.triggered and ctx.triggered[0]['prop_id'].split('.')[0] == 'drilldown-modal-close-btn':
        return False, "", ""

    # 如果有点击数据，则打开Modal并显示内容
    if clickData:
        try:
            # 1. 提取点击的分类名称
            clicked_category = clickData['points'][0]['x']
            
            # 2. 获取详细SKU数据
            sku_details_df = loader.data.get('sku_details', pd.DataFrame())
            
            if sku_details_df.empty:
                return True, f"分类: {clicked_category}", html.Div("无法加载详细SKU数据", className="alert alert-warning")

            # 3. 查找"一级分类"列
            category_col_name = None
            if '一级分类' in sku_details_df.columns:
                category_col_name = '一级分类'
            else:
                # 尝试从列名中找到包含"分类"的列
                for col in sku_details_df.columns:
                    if '分类' in str(col) and '一级' in str(col):
                        category_col_name = col
                        break

            if not category_col_name:
                return True, f"分类: {clicked_category}", html.Div(
                    f"在SKU明细表中未找到'一级分类'列。可用列：{', '.join(sku_details_df.columns[:5])}...", 
                    className="alert alert-danger"
                )

            # 4. 筛选属于该分类的SKU
            filtered_df = sku_details_df[sku_details_df[category_col_name] == clicked_category].copy()
            
            # 5. 创建要显示的表格
            if filtered_df.empty:
                table_content = html.Div(
                    f'在"{clicked_category}"分类下未找到任何SKU', 
                    className="alert alert-info"
                )
            else:
                # 选择性展示关键列
                display_cols = ['商品名称', '售价', '月售', '库存', '商品角色', '规格', '条码']
                existing_display_cols = [col for col in display_cols if col in filtered_df.columns]
                
                if not existing_display_cols:
                    # 如果预定义列都不存在，则显示前7列
                    existing_display_cols = filtered_df.columns[:7].tolist()
                
                # 格式化数值列
                display_df = filtered_df[existing_display_cols].copy()
                for col in ['售价', '月售', '库存']:
                    if col in display_df.columns:
                        display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
                
                if '售价' in display_df.columns:
                    display_df['售价'] = display_df['售价'].apply(lambda x: f'¥{x:,.2f}' if pd.notna(x) else '¥0.00')

                table_content = dbc.Table.from_dataframe(
                    display_df, 
                    striped=True, 
                    bordered=True, 
                    hover=True,
                    responsive=True,
                    className="align-middle text-center"
                )

            # 6. 设置Modal标题和内容，并打开
            modal_title = f"📊 下钻详情: {clicked_category} (共 {len(filtered_df)} 个SKU)"
            return True, modal_title, table_content
            
        except Exception as e:
            import traceback
            error_content = html.Div([
                html.H5("❌ 处理下钻数据时出错", className="text-danger"),
                html.Pre(f"{str(e)}\n\n{traceback.format_exc()}", style={'fontSize': '0.8rem'})
            ])
            return True, "发生错误", error_content

    return is_open, "", ""


# ========== AI智能分析Callback ==========
@app.callback(
    Output('ai-analysis-result', 'children'),
    [Input('ai-analyze-btn', 'n_clicks')],
    [State('upload-trigger', 'data'),
     State('category-filter', 'value')],
    prevent_initial_call=True
)
def run_ai_analysis(n_clicks, upload_trigger, selected_categories):
    """运行AI智能分析"""
    if not n_clicks:
        return ""
    
    try:
        # 1. 初始化AI分析器
        analyzer = get_ai_analyzer()
        
        if not analyzer or not analyzer.is_ready():
            return dbc.Alert([
                html.H5("❌ AI分析器未就绪", className="alert-heading"),
                html.Hr(),
                html.P([
                    "请检查以下配置:",
                    html.Ul([
                        html.Li("确保已安装zhipuai库: pip install zhipuai"),
                        html.Li("设置环境变量: ZHIPU_API_KEY=你的API密钥"),
                        html.Li([
                            "获取API密钥: ",
                            html.A("https://open.bigmodel.cn", 
                                  href="https://open.bigmodel.cn", 
                                  target="_blank",
                                  style={'color': '#007bff', 'textDecoration': 'underline'})
                        ])
                    ])
                ])
            ], color="danger", style={'backgroundColor': 'white', 'color': '#dc3545'})
        
        # 2. 收集Dashboard数据
        dashboard_data = collect_dashboard_data(selected_categories)
        
        # 3. 获取业务上下文
        business_context = get_business_context()
        
        # 4. 调用AI分析
        analysis_result = analyzer.analyze_dashboard_data(
            dashboard_data=dashboard_data,
            business_context=business_context
        )
        
        # 5. 格式化显示结果
        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="fas fa-lightbulb me-2", style={'color': '#ffc107'}),
                    html.Span("AI智能分析报告", style={'fontSize': '20px', 'fontWeight': 'bold'})
                ], style={'display': 'inline-block'}),
                html.Div([
                    html.I(className="fas fa-check-circle me-2", style={'color': '#28a745'}),
                    html.Span("分析完成", style={'fontSize': '14px', 'color': '#28a745'})
                ], style={'float': 'right', 'display': 'inline-block'})
            ], style={'backgroundColor': '#f8f9fa', 'color': '#2c3e50', 'padding': '15px 20px'}),
            dbc.CardBody([
                # 分析时间和元信息
                html.Div([
                    html.Div([
                        html.I(className="fas fa-clock me-2"),
                        html.Span(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
                                 style={'marginRight': '20px'}),
                        html.I(className="fas fa-robot me-2"),
                        html.Span(f"模型: GLM-4.6", style={'marginRight': '20px'}),
                        html.I(className="fas fa-layer-group me-2"),
                        html.Span(f"分析分类: {len(selected_categories) if selected_categories else '全部'}个")
                    ], style={'color': '#666', 'fontSize': '13px', 'marginBottom': '20px', 'padding': '10px', 
                             'backgroundColor': '#f8f9fa', 'borderRadius': '5px'})
                ]),
                
                # AI分析内容(支持Markdown格式)
                dcc.Markdown(
                    analysis_result,
                    style={
                        'fontSize': '15px',
                        'lineHeight': '1.8',
                        'color': '#333'
                    }
                )
            ], style={'backgroundColor': 'white', 'padding': '25px'})
        ], style={'boxShadow': '0 4px 12px rgba(0,0,0,0.1)', 'borderRadius': '10px'})
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        
        return dbc.Alert([
            html.H5("❌ AI分析过程中发生错误", className="alert-heading"),
            html.Hr(),
            html.P(str(e)),
            html.Details([
                html.Summary("查看详细错误信息"),
                html.Pre(error_detail, style={'fontSize': '0.85rem', 'backgroundColor': '#f8f9fa', 'padding': '10px'})
            ])
        ], color="danger", style={'backgroundColor': 'white', 'color': '#dc3545'})


def collect_dashboard_data(selected_categories=None):
    """收集Dashboard所有数据用于AI分析 - 深度版本"""
    
    # 获取当前加载的数据
    kpi_data = loader.data.get('kpi_data', pd.DataFrame())
    category_data = loader.data.get('category_data', pd.DataFrame())
    price_data = loader.data.get('price_data', pd.DataFrame())
    
    # 如果有分类筛选,应用筛选
    if selected_categories and len(selected_categories) > 0:
        if '一级分类' in category_data.columns:
            category_data = category_data[category_data['一级分类'].isin(selected_categories)]
    
    # ========== 1. 提取核心KPI ==========
    kpi_dict = {}
    if not kpi_data.empty and len(kpi_data) > 0:
        for col in kpi_data.columns:
            value = kpi_data[col].iloc[0]
            # 处理数值,转换百分比等
            if pd.notna(value):
                if isinstance(value, str) and '%' in value:
                    # 处理百分比字符串
                    try:
                        kpi_dict[col] = float(value.replace('%', ''))
                    except:
                        kpi_dict[col] = value
                else:
                    kpi_dict[col] = value
            else:
                kpi_dict[col] = 0
    
    # ========== 2. 分类数据深度提取 ==========
    category_summary = []
    if not category_data.empty:
        # 确保必要列存在
        required_cols = ['一级分类', '售价销售额']
        if all(col in category_data.columns for col in required_cols):
            # 按销售额排序,获取全部分类(不只是TOP10)
            sorted_cats = category_data.sort_values('售价销售额', ascending=False).copy()
            
            # 提取关键字段
            for idx, row in sorted_cats.iterrows():
                cat_info = {
                    '一级分类': row.get('一级分类', '未知'),
                    '售价销售额': row.get('售价销售额', 0),
                    '美团一级分类去重SKU数(口径同动销率)': row.get('美团一级分类去重SKU数(口径同动销率)', 0),
                    '美团一级分类动销率(类内)': row.get('美团一级分类动销率(类内)', 0),
                    '美团一级分类折扣': row.get('美团一级分类折扣', 10),
                }
                
                # 添加爆品/滞销数据(如果有)
                if '爆品数' in category_data.columns:
                    cat_info['爆品数'] = row.get('爆品数', 0)
                if '滞销数' in category_data.columns:
                    cat_info['滞销数'] = row.get('滞销数', 0)
                
                # 添加促销相关(如果有)
                if len(category_data.columns) > 24:  # Y列：折扣力度
                    discount_level = row.iloc[24] if pd.notna(row.iloc[24]) else 10
                    cat_info['折扣力度'] = discount_level
                    cat_info['促销强度'] = ((10 - discount_level) / 9 * 100) if discount_level < 10 else 0
                
                category_summary.append(cat_info)
    
    # ========== 3. 价格带数据提取 ==========
    price_summary = []
    if not price_data.empty and 'price_band' in price_data.columns:
        for idx, row in price_data.iterrows():
            price_info = {
                'price_band': row.get('price_band', '未知'),
                'SKU数量': row.get('SKU数量', 0),
                '销售额': row.get('销售额', 0),
                '销售额占比': row.get('销售额占比', 0)
            }
            price_summary.append(price_info)
    
    # ========== 4. 促销强度TOP分类 ==========
    promo_summary = []
    if category_summary:  # 已在category_summary中计算
        # 按促销强度排序
        promo_cats = sorted(
            [c for c in category_summary if '促销强度' in c],
            key=lambda x: x.get('促销强度', 0),
            reverse=True
        )[:10]
        
        for cat in promo_cats:
            promo_summary.append({
                '分类': cat.get('一级分类', '未知'),
                '促销强度': cat.get('促销强度', 0),
                '折扣力度': cat.get('折扣力度', 10)
            })
    
    # ========== 5. 计算衍生指标 ==========
    meta_info = {
        '总分类数': len(category_data),
        '筛选分类': selected_categories if selected_categories else '全部',
        '分析时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'TOP3销售额占比': 0,
        '健康分类数': 0,
        '问题分类数': 0
    }
    
    if category_summary:
        # TOP3集中度
        total_revenue = sum(c.get('售价销售额', 0) for c in category_summary)
        top3_revenue = sum(c.get('售价销售额', 0) for c in category_summary[:3])
        if total_revenue > 0:
            meta_info['TOP3销售额占比'] = (top3_revenue / total_revenue) * 100
        
        # 健康分类统计
        for cat in category_summary:
            moverate = cat.get('美团一级分类动销率(类内)', 0)
            if moverate >= 60:
                meta_info['健康分类数'] += 1
            else:
                meta_info['问题分类数'] += 1
    
    return {
        'kpi': kpi_dict,
        'category': category_summary,  # 全部分类,不只TOP10
        'price': price_summary,
        'promo': promo_summary,
        'meta': meta_info
    }


# 运行应用
if __name__ == '__main__':
    print("🚀 启动O2O门店数据分析看板...")
    print("📊 本机访问地址: http://localhost:8055")
    print("📊 局域网访问地址: http://119.188.71.47:8055")
    print("🌐 花生壳外网访问: https://2bn637md7241.vicp.fun")
    print("💡 提示: 使用0.0.0.0允许花生壳和局域网访问")
    # 使用0.0.0.0允许花生壳客户端访问
    app.run(debug=True, host='0.0.0.0', port=8055)