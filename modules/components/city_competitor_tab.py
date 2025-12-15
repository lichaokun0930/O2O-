# -*- coding: utf-8 -*-
"""
城市新增竞对分析TAB组件 - ECharts版本
"""

from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import dash_echarts
import pandas as pd
import logging

logger = logging.getLogger('dashboard')

DEFAULT_COMPETITOR_FILE = "城市新增竞对数据/新增竞对.xlsx"


def get_toolbox(chart_name: str) -> dict:
    """获取通用的ECharts工具栏配置（高清PNG下载）"""
    return {
        'show': True,
        'right': 15,
        'top': 5,
        'feature': {
            'saveAsImage': {
                'type': 'png',
                'pixelRatio': 4,  # 4倍分辨率，超高清
                'title': '下载高清图',
                'name': chart_name,
                'backgroundColor': '#fff',  # 白色背景
                'excludeComponents': ['toolbox']
            }
        }
    }


CHART_CARD_STYLE = {
    'backgroundColor': 'white',
    'padding': '15px',
    'borderRadius': '8px',
    'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
    'marginBottom': '15px'
}


def create_city_competitor_tab_layout():
    """创建城市新增竞对分析TAB布局"""
    return html.Div([
        dcc.Store(id='city-competitor-data-store'),
        dcc.Store(id='city-competitor-resize-trigger'),  # 用于触发图表resize
        
        # 标题
        html.Div([
            html.H4("📊 城市新增竞对分析", style={'marginBottom': '10px', 'color': '#2c3e50'}),
            html.P("分析各城市5km范围内的新增竞对情况", style={'color': '#7f8c8d', 'fontSize': '14px'})
        ], style={'marginBottom': '15px'}),
        
        # 概览卡片
        html.Div(id='city-competitor-overview-cards', style={'marginBottom': '20px'}),
        
        # 筛选器
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("🏙️ 城市:", style={'fontWeight': 'bold', 'fontSize': '13px'}),
                    dcc.Dropdown(id='city-competitor-city-filter', options=[], value=None,
                                placeholder="全部城市", clearable=True, style={'fontSize': '13px'})
                ], width=2),
                dbc.Col([
                    html.Label("🏪 商圈:", style={'fontWeight': 'bold', 'fontSize': '13px'}),
                    dcc.Dropdown(id='city-competitor-circle-filter',
                                options=[{'label': t, 'value': t} for t in ['强', '中', '弱']],
                                value=None, placeholder="全部", clearable=True, style={'fontSize': '13px'})
                ], width=2),
                dbc.Col([
                    html.Label("📍 区域:", style={'fontWeight': 'bold', 'fontSize': '13px'}),
                    dcc.Dropdown(id='city-competitor-region-filter',
                                options=[{'label': t, 'value': t} for t in ['市区', '县城']],
                                value=None, placeholder="全部", clearable=True, style={'fontSize': '13px'})
                ], width=2),
                dbc.Col([
                    html.Label("🔍 品牌:", style={'fontWeight': 'bold', 'fontSize': '13px'}),
                    dcc.Input(id='city-competitor-brand-search', type='text', placeholder="搜索品牌...",
                             style={'width': '100%', 'padding': '6px', 'borderRadius': '4px', 'border': '1px solid #ccc', 'fontSize': '13px'})
                ], width=3),
                dbc.Col([
                    html.Label(" ", style={'display': 'block'}),
                    dbc.Button("🔄 刷新", id='city-competitor-refresh-btn', color='primary', size='sm')
                ], width=1)
            ])
        ], style={'backgroundColor': '#f8f9fa', 'padding': '12px', 'borderRadius': '8px', 'marginBottom': '15px'}),
        
        # 第一行图表：城市分布 + 品牌TOP10
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("🏙️ 城市新增竞对分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-city-chart', option={}, style={'height': '350px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("🏆 新增竞对品牌TOP10", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-brand-chart', option={}, style={'height': '350px'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 第二行图表：商圈×区域 + 区域对比
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("📊 不同商圈的平均竞对数对比", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-circle-region-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("📍 市区vs县城竞对分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-region-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 新增：市区/县城商圈分布对比（门店维度）
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("🏙️ 市区门店商圈分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-urban-circle-chart', option={}, style={'height': '280px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("🏘️ 县城门店商圈分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-county-circle-chart', option={}, style={'height': '280px'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 新增：市区/县城新增竞对商圈分布对比
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("🏙️ 市区新增竞对商圈分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-urban-new-circle-chart', option={}, style={'height': '280px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("🏘️ 县城新增竞对商圈分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-county-new-circle-chart', option={}, style={'height': '280px'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 第三行图表：近15天新增分析 + SKU规模分布
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("📅 近15天新增竞对城市分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-new15-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("📦 竞对SKU规模分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-sku-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 第四行图表：商补率分布 + 品牌×城市热力图
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("💰 商补率分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-subsidy-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("🔥 TOP10品牌在主要城市的分布", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-heatmap-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 第五行：5km竞对分布 + 关键词
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("🎯 市区vs县城平均竞对数", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-5km-chart', option={}, style={'height': '300px'})
                ], style=CHART_CARD_STYLE)
            ], width=6),
            dbc.Col([
                html.Div([
                    html.H6("🏷️ 品牌特性关键词", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    html.Div(id='city-competitor-keywords', style={'height': '260px', 'overflowY': 'auto'})
                ], style=CHART_CARD_STYLE)
            ], width=6)
        ], style={'marginBottom': '15px'}),
        
        # 第六行：品牌扩张趋势
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("📈 品牌扩张趋势（市区vs县城）", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    dash_echarts.DashECharts(id='city-competitor-brand-expansion-chart', option={}, style={'height': '350px'})
                ], style=CHART_CARD_STYLE)
            ], width=12)
        ], style={'marginBottom': '15px'}),
        
        # 第七行：智能洞察分析
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H6("🧠 智能洞察分析", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
                    html.Div(id='city-competitor-insights')
                ], style=CHART_CARD_STYLE)
            ], width=12)
        ], style={'marginBottom': '15px'}),
        
        # 详情表
        html.Div([
            html.H6("📋 新增竞对详情表", style={'marginBottom': '10px', 'fontWeight': 'bold', 'textAlign': 'center'}),
            html.Div(id='city-competitor-detail-table')
        ], style=CHART_CARD_STYLE)
        
    ], style={'padding': '15px'})


def create_overview_cards(stats: dict):
    """创建概览卡片 - 包含占比信息"""
    # 第一行：基础统计
    row1_data = [
        ('总门店数', stats.get('总门店数', 0), '🏪', '#3498db'),
        ('5km内竞对总数', stats.get('5km内竞对总数', 0), '🎯', '#e74c3c'),
        ('新增竞对总数', stats.get('新增竞对总数', 0), '📈', '#2ecc71'),
        ('有新增竞对门店', stats.get('有新增竞对的门店数', 0), '⚠️', '#f39c12'),
        ('新增品牌数', stats.get('新增竞对品牌数', 0), '🏷️', '#9b59b6'),
        ('覆盖城市数', stats.get('覆盖城市数', 0), '🏙️', '#1abc9c'),
    ]
    
    # 第二行：占比统计
    region_dist = stats.get('区域分布', {})
    circle_dist = stats.get('商圈分布', {})
    
    row2_data = [
        ('市区新增', f"{region_dist.get('市区', 0)}家 ({region_dist.get('市区占比', 0)}%)", '🏙️', '#3498db'),
        ('县城新增', f"{region_dist.get('县城', 0)}家 ({region_dist.get('县城占比', 0)}%)", '🏘️', '#9b59b6'),
        ('强商圈新增', f"{circle_dist.get('强', 0)}家 ({circle_dist.get('强占比', 0)}%)", '💪', '#e74c3c'),
        ('中商圈新增', f"{circle_dist.get('中', 0)}家 ({circle_dist.get('中占比', 0)}%)", '📊', '#f39c12'),
        ('弱商圈新增', f"{circle_dist.get('弱', 0)}家 ({circle_dist.get('弱占比', 0)}%)", '📉', '#95a5a6'),
    ]
    
    def make_card(title, value, icon, color, is_text=False):
        return html.Div([
            html.Div([html.Span(icon, style={'fontSize': '18px', 'marginRight': '6px'}),
                     html.Span(title, style={'fontSize': '11px', 'color': '#666'})]),
            html.Div(f"{value:,}" if not is_text else value, 
                    style={'fontSize': '20px' if not is_text else '16px', 'fontWeight': 'bold', 'color': color, 'marginTop': '3px'})
        ], style={'backgroundColor': 'white', 'padding': '10px', 'borderRadius': '8px',
                 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'textAlign': 'center'})
    
    return html.Div([
        dbc.Row([dbc.Col([make_card(t, v, i, c)], width=2) for t, v, i, c in row1_data]),
        dbc.Row([dbc.Col([make_card(t, v, i, c, is_text=True)], width=2) for t, v, i, c in row2_data], 
               style={'marginTop': '10px'}, className='justify-content-center')
    ])


def create_city_echarts(city_summary: pd.DataFrame):
    """创建城市分布ECharts配置"""
    if city_summary.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    top_cities = city_summary.head(15)
    
    return {
        'toolbox': get_toolbox('新增竞对城市分布'),
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'grid': {'left': '3%', 'right': '4%', 'bottom': '15%', 'top': '8%', 'containLabel': True},
        'xAxis': {
            'type': 'category',
            'data': top_cities['城市'].tolist(),
            'axisLabel': {'rotate': 45, 'fontSize': 11}
        },
        'yAxis': {'type': 'value', 'name': '新增竞对数'},
        'series': [{
            'type': 'bar',
            'data': top_cities['新增竞对数'].tolist(),
            'itemStyle': {'color': '#3498db'},
            'label': {'show': True, 'position': 'top', 'fontSize': 10}
        }]
    }


def create_brand_echarts(brand_ranking: pd.DataFrame):
    """创建品牌排行ECharts配置"""
    if brand_ranking.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    brands = brand_ranking['品牌名称'].tolist()[::-1]
    counts = brand_ranking['出现次数'].tolist()[::-1]
    
    return {
        'toolbox': get_toolbox('新增竞对品牌TOP10'),
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'grid': {'left': '25%', 'right': '10%', 'bottom': '5%', 'top': '8%', 'containLabel': True},
        'xAxis': {'type': 'value'},
        'yAxis': {'type': 'category', 'data': brands, 'axisLabel': {'fontSize': 11}},
        'series': [{
            'type': 'bar',
            'data': counts,
            'itemStyle': {'color': '#e74c3c'},
            'label': {'show': True, 'position': 'right', 'fontSize': 10}
        }]
    }


def create_circle_region_echarts(cross_stats: pd.DataFrame):
    """创建商圈×区域交叉分析ECharts配置"""
    if cross_stats.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    circles = ['强', '中', '弱']
    regions = ['市区', '县城']
    
    series_data = []
    for region in regions:
        region_data = []
        for circle in circles:
            row = cross_stats[(cross_stats['商圈类型'] == circle) & (cross_stats['区域类型'] == region)]
            val = row['平均竞对数'].values[0] if len(row) > 0 else 0
            region_data.append(round(val, 1))
        series_data.append({
            'name': region,
            'type': 'bar',
            'data': region_data,
            'label': {'show': True, 'position': 'top', 'fontSize': 10}
        })
    
    return {
        'toolbox': get_toolbox('不同商圈的平均竞对数对比'),
        'tooltip': {'trigger': 'axis'},
        'legend': {'data': regions, 'top': 5},
        'grid': {'left': '3%', 'right': '4%', 'bottom': '10%', 'top': '15%', 'containLabel': True},
        'xAxis': {'type': 'category', 'data': circles},
        'yAxis': {'type': 'value', 'name': '平均竞对数'},
        'series': series_data
    }


def create_region_echarts(region_stats: pd.DataFrame):
    """创建区域对比ECharts配置（饼图）- 显示新增竞对数量分布"""
    if region_stats.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 构建饼图数据，以新增竞对数为主要展示值
    pie_data = []
    for _, row in region_stats.iterrows():
        region = row['区域类型']
        new_count = int(row.get('新增竞对数', 0)) if '新增竞对数' in region_stats.columns else 0
        store_count = int(row.get('门店数', 0)) if '门店数' in region_stats.columns else 0
        pie_data.append({
            'name': region, 
            'value': new_count,
            'storeCount': store_count
        })
    
    return {
        'toolbox': get_toolbox('市区vs县城竞对分布'),
        'tooltip': {
            'trigger': 'item', 
            'formatter': '{b}<br/>新增竞对: {c}家<br/>占比: {d}%'
        },
        'legend': {'orient': 'horizontal', 'bottom': 10},
        'series': [{
            'type': 'pie',
            'radius': ['35%', '60%'],
            'center': ['50%', '50%'],
            'data': pie_data,
            'itemStyle': {'borderRadius': 5},
            'label': {
                'show': True, 
                'formatter': '{b}\n新增:{c}家\n({d}%)'
            },
            'emphasis': {'itemStyle': {'shadowBlur': 10, 'shadowOffsetX': 0, 'shadowColor': 'rgba(0, 0, 0, 0.5)'}}
        }]
    }


def create_region_circle_echarts(region_data: dict, region_type: str):
    """创建市区/县城商圈分布饼图
    
    Args:
        region_data: {'强': count, '中': count, '弱': count, '强占比': pct, ...}
        region_type: '市区' 或 '县城'
    """
    if not region_data:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    total = region_data.get('总门店数', 0)
    if total == 0:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 商圈颜色
    colors = {'强': '#e74c3c', '中': '#f39c12', '弱': '#95a5a6'}
    
    pie_data = []
    for circle in ['强', '中', '弱']:
        count = region_data.get(circle, 0)
        if count > 0:
            pie_data.append({
                'name': f'{circle}商圈',
                'value': count,
                'itemStyle': {'color': colors[circle]}
            })
    
    return {
        'toolbox': get_toolbox(f'{region_type}门店商圈分布'),
        'tooltip': {
            'trigger': 'item',
            'formatter': '{b}<br/>{c}家 ({d}%)'
        },
        'legend': {'orient': 'horizontal', 'bottom': 5},
        'series': [{
            'type': 'pie',
            'radius': ['30%', '60%'],
            'center': ['50%', '45%'],
            'data': pie_data,
            'itemStyle': {'borderRadius': 5},
            'label': {
                'show': True,
                'formatter': '{b}\n{c}家\n({d}%)'
            },
            'emphasis': {'itemStyle': {'shadowBlur': 10}}
        }]
    }


def create_new_competitor_circle_echarts(region_data: dict, region_type: str):
    """创建市区/县城新增竞对商圈分布饼图
    
    Args:
        region_data: {'强': count, '中': count, '弱': count, '强占比': pct, ..., '总新增竞对数': total}
        region_type: '市区' 或 '县城'
    """
    if not region_data:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    total = region_data.get('总新增竞对数', 0)
    if total == 0:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 商圈颜色
    colors = {'强': '#e74c3c', '中': '#f39c12', '弱': '#95a5a6'}
    
    pie_data = []
    for circle in ['强', '中', '弱']:
        count = region_data.get(circle, 0)
        if count > 0:
            pie_data.append({
                'name': f'{circle}商圈',
                'value': count,
                'itemStyle': {'color': colors[circle]}
            })
    
    return {
        'toolbox': get_toolbox(f'{region_type}新增竞对商圈分布'),
        'tooltip': {
            'trigger': 'item',
            'formatter': '{b}<br/>{c}家 ({d}%)'
        },
        'legend': {'orient': 'horizontal', 'bottom': 5},
        'series': [{
            'type': 'pie',
            'radius': ['30%', '60%'],
            'center': ['50%', '45%'],
            'data': pie_data,
            'itemStyle': {'borderRadius': 5},
            'label': {
                'show': True,
                'formatter': '{b}\n{c}家\n({d}%)'
            },
            'emphasis': {'itemStyle': {'shadowBlur': 10}}
        }]
    }


def create_5km_distribution_echarts(region_dist: pd.DataFrame):
    """创建5km竞对分布ECharts配置（箱线图风格的柱状图）"""
    if region_dist.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 按区域类型分组统计
    stats = region_dist.groupby('区域类型').agg({
        '5km内竞对数量': ['mean', 'min', 'max', 'std']
    }).reset_index()
    stats.columns = ['区域类型', '平均值', '最小值', '最大值', '标准差']
    
    regions = stats['区域类型'].tolist()
    avg_values = [round(v, 1) for v in stats['平均值'].tolist()]
    
    return {
        'toolbox': get_toolbox('市区vs县城平均竞对数'),
        'tooltip': {'trigger': 'axis'},
        'grid': {'left': '10%', 'right': '10%', 'bottom': '15%', 'top': '8%'},
        'xAxis': {'type': 'category', 'data': regions},
        'yAxis': {'type': 'value', 'name': '平均5km内竞对数'},
        'series': [{
            'type': 'bar',
            'data': avg_values,
            'itemStyle': {'color': {'type': 'linear', 'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                   'colorStops': [{'offset': 0, 'color': '#3498db'},
                                                 {'offset': 1, 'color': '#2ecc71'}]}},
            'label': {'show': True, 'position': 'top', 'fontSize': 12, 'fontWeight': 'bold'}
        }]
    }


def create_keywords_display(keywords: dict):
    """创建标签云展示"""
    if not keywords:
        return html.Div("暂无品牌特性数据", style={'color': '#999', 'textAlign': 'center', 'padding': '50px'})
    
    sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:20]
    max_count = max(keywords.values()) if keywords else 1
    
    # 颜色列表
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22', '#16a085']
    
    tags = []
    for i, (keyword, count) in enumerate(sorted_keywords):
        weight = count / max_count
        size = 14 + int(weight * 16)  # 14-30px
        color = colors[i % len(colors)]
        
        tags.append(html.Span(f"{keyword}({count})", style={
            'display': 'inline-block',
            'margin': '6px 8px',
            'padding': '8px 16px',
            'backgroundColor': color,
            'color': 'white',
            'borderRadius': '20px',
            'fontSize': f'{size}px',
            'fontWeight': 'bold' if weight > 0.5 else 'normal',
            'cursor': 'pointer',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.2)',
            'transition': 'transform 0.2s'
        }))
    
    return html.Div(tags, style={
        'textAlign': 'center',
        'padding': '15px',
        'display': 'flex',
        'flexWrap': 'wrap',
        'justifyContent': 'center',
        'alignItems': 'center',
        'height': '100%'
    })


def create_detail_table(details: pd.DataFrame):
    """创建详情表格"""
    if details.empty:
        return html.Div("暂无数据", style={'color': '#999', 'textAlign': 'center', 'padding': '50px'})
    
    if 'SKU数' in details.columns:
        details = details.copy()
        details['SKU数'] = details['SKU数'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")
    
    return dash_table.DataTable(
        data=details.head(100).to_dict('records'),
        columns=[{'name': col, 'id': col} for col in details.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px', 'whiteSpace': 'normal', 'height': 'auto'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
        page_size=15, sort_action='native', filter_action='native'
    )


def create_new15_echarts(new15_stats: pd.DataFrame):
    """创建近15天新增竞对城市分布ECharts配置"""
    if new15_stats.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    top_cities = new15_stats.head(12)
    
    return {
        'toolbox': get_toolbox('近15天新增竞对城市分布'),
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'grid': {'left': '3%', 'right': '4%', 'bottom': '15%', 'top': '8%', 'containLabel': True},
        'xAxis': {
            'type': 'category',
            'data': top_cities['城市'].tolist(),
            'axisLabel': {'rotate': 45, 'fontSize': 11}
        },
        'yAxis': {'type': 'value', 'name': '新增竞对数'},
        'series': [{
            'type': 'bar',
            'data': top_cities['新增竞对总数'].tolist(),
            'itemStyle': {'color': '#e74c3c'},
            'label': {'show': True, 'position': 'top', 'fontSize': 10}
        }]
    }


def create_sku_scale_echarts(sku_dist: dict):
    """创建SKU规模分布ECharts配置（饼图）"""
    if not sku_dist:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    pie_data = [{'name': k, 'value': v} for k, v in sku_dist.items() if v > 0]
    colors = ['#2ecc71', '#f39c12', '#e74c3c']
    
    return {
        'toolbox': get_toolbox('SKU规模分布'),
        'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} ({d}%)'},
        'legend': {'orient': 'horizontal', 'bottom': 5},
        'color': colors,
        'series': [{
            'type': 'pie',
            'radius': ['30%', '55%'],
            'center': ['50%', '52%'],
            'data': pie_data,
            'itemStyle': {'borderRadius': 5},
            'label': {'show': True, 'formatter': '{b}\n{c}家'},
            'emphasis': {'itemStyle': {'shadowBlur': 10}}
        }]
    }


def create_subsidy_echarts(subsidy_dist: dict, subsidy_detail: pd.DataFrame = None):
    """创建商补率分布ECharts配置（柱状图+品牌标注）"""
    if not subsidy_dist:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 按顺序排列
    order = ['无商补', '10%-20%', '20%-30%', '>30%']
    categories = [k for k in order if k in subsidy_dist]
    values = [subsidy_dist.get(k, 0) for k in categories]
    colors = ['#95a5a6', '#3498db', '#f39c12', '#e74c3c']
    
    # 构建带颜色的数据
    bar_data = [{'value': v, 'itemStyle': {'color': colors[i]}} for i, v in enumerate(values)]
    
    return {
        'toolbox': get_toolbox('商补率分布'),
        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
        'grid': {'left': '3%', 'right': '4%', 'bottom': '10%', 'top': '8%', 'containLabel': True},
        'xAxis': {'type': 'category', 'data': categories},
        'yAxis': {'type': 'value', 'name': '竞对数量'},
        'series': [{
            'type': 'bar',
            'data': bar_data,
            'label': {'show': True, 'position': 'top', 'fontSize': 12, 'fontWeight': 'bold'}
        }]
    }


def create_brand_city_heatmap_echarts(heatmap_df: pd.DataFrame):
    """创建品牌×城市热力图ECharts配置
    
    注意：热力图只显示竞对数量最多的前15个城市，
    如果某品牌在其他城市也有分布，这里不会显示。
    品牌总数请参考"新增竞对品牌TOP10"图表。
    """
    if heatmap_df.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    brands = heatmap_df.index.tolist()
    
    # 按城市竞对总数排序，取前15个城市
    city_totals = heatmap_df.sum(axis=0).sort_values(ascending=False)
    cities = city_totals.head(15).index.tolist()
    
    # 构建热力图数据 [x, y, value]
    data = []
    max_val = 0
    for i, brand in enumerate(brands):
        for j, city in enumerate(cities):
            if city in heatmap_df.columns:
                val = int(heatmap_df.loc[brand, city])
                if val > 0:
                    data.append([j, i, val])
                    max_val = max(max_val, val)
    
    return {
        'toolbox': get_toolbox('品牌城市扩张热力图'),
        'tooltip': {'position': 'top', 'formatter': '{b0}: {c0}家'},
        'grid': {'left': '20%', 'right': '5%', 'bottom': '25%', 'top': '5%'},
        'xAxis': {
            'type': 'category',
            'data': cities,
            'axisLabel': {'rotate': 45, 'fontSize': 9}
        },
        'yAxis': {
            'type': 'category',
            'data': brands,
            'axisLabel': {'fontSize': 10}
        },
        'visualMap': {
            'min': 0,
            'max': max(max_val, 1),
            'calculable': True,
            'orient': 'horizontal',
            'left': 'center',
            'bottom': 0,
            'inRange': {'color': ['#f7fbff', '#08519c']}
        },
        'series': [{
            'type': 'heatmap',
            'data': data,
            'label': {'show': True, 'fontSize': 9},
            'emphasis': {'itemStyle': {'shadowBlur': 10, 'shadowColor': 'rgba(0, 0, 0, 0.5)'}}
        }]
    }


def create_brand_expansion_echarts(brand_expansion: pd.DataFrame):
    """创建品牌扩张趋势图表（堆叠柱状图）
    
    展示TOP15品牌在市区和县城的分布对比
    """
    if brand_expansion.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 取TOP15品牌，并剔除市区和县城都为0的数据
    top_brands = brand_expansion.head(20)  # 多取一些，剔除0后可能不够15个
    top_brands = top_brands[(top_brands['市区数量'] > 0) | (top_brands['县城数量'] > 0)]
    top_brands = top_brands.head(15)
    
    if top_brands.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    brands = top_brands['品牌名称'].tolist()
    urban_data = top_brands['市区数量'].tolist()
    county_data = top_brands['县城数量'].tolist()
    
    # 构建数据，0值不显示标签
    urban_series_data = [
        {'value': v, 'label': {'show': v > 0}} for v in urban_data
    ]
    county_series_data = [
        {'value': v, 'label': {'show': v > 0}} for v in county_data
    ]
    
    return {
        'toolbox': get_toolbox('品牌扩张趋势'),
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'shadow'}
        },
        'legend': {
            'data': ['市区', '县城'],
            'top': 5
        },
        'grid': {'left': '3%', 'right': '4%', 'bottom': '15%', 'top': '12%', 'containLabel': True},
        'xAxis': {
            'type': 'category',
            'data': brands,
            'axisLabel': {'rotate': 45, 'fontSize': 10}
        },
        'yAxis': {'type': 'value', 'name': '新增竞对数'},
        'series': [
            {
                'name': '市区',
                'type': 'bar',
                'stack': 'total',
                'data': urban_series_data,
                'itemStyle': {'color': '#3498db'},
                'label': {'position': 'inside', 'fontSize': 9}
            },
            {
                'name': '县城',
                'type': 'bar',
                'stack': 'total',
                'data': county_series_data,
                'itemStyle': {'color': '#9b59b6'},
                'label': {'position': 'inside', 'fontSize': 9}
            }
        ]
    }


def create_insights_display(insights: dict):
    """创建智能洞察展示组件"""
    if not insights:
        return html.Div("暂无洞察数据", style={'color': '#999', 'textAlign': 'center', 'padding': '30px'})
    
    sections = []
    
    # 总体概述
    if insights.get('summary'):
        sections.append(
            html.Div([
                html.Div("📊 总体概述", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#2c3e50', 'marginBottom': '8px'}),
                html.P(insights['summary'], style={'fontSize': '13px', 'color': '#34495e', 'lineHeight': '1.6', 'margin': 0})
            ], style={'backgroundColor': '#ecf0f1', 'padding': '12px', 'borderRadius': '6px', 'marginBottom': '12px'})
        )
    
    # 关键发现
    if insights.get('key_findings'):
        findings_items = [html.Li(f, style={'marginBottom': '6px', 'fontSize': '13px'}) for f in insights['key_findings']]
        sections.append(
            html.Div([
                html.Div("🔍 关键发现", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#2980b9', 'marginBottom': '8px'}),
                html.Ul(findings_items, style={'margin': 0, 'paddingLeft': '20px', 'color': '#2c3e50'})
            ], style={'backgroundColor': '#e8f4f8', 'padding': '12px', 'borderRadius': '6px', 'marginBottom': '12px'})
        )
    
    # 风险预警
    if insights.get('risk_alerts'):
        alerts_items = [html.Li(a, style={'marginBottom': '6px', 'fontSize': '13px'}) for a in insights['risk_alerts']]
        sections.append(
            html.Div([
                html.Div("⚠️ 风险预警", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#e74c3c', 'marginBottom': '8px'}),
                html.Ul(alerts_items, style={'margin': 0, 'paddingLeft': '20px', 'color': '#c0392b'})
            ], style={'backgroundColor': '#fdedec', 'padding': '12px', 'borderRadius': '6px', 'marginBottom': '12px'})
        )
    
    # 建议
    if insights.get('recommendations'):
        rec_items = [html.Li(r, style={'marginBottom': '6px', 'fontSize': '13px'}) for r in insights['recommendations']]
        sections.append(
            html.Div([
                html.Div("💡 行动建议", style={'fontWeight': 'bold', 'fontSize': '14px', 'color': '#27ae60', 'marginBottom': '8px'}),
                html.Ul(rec_items, style={'margin': 0, 'paddingLeft': '20px', 'color': '#1e8449'})
            ], style={'backgroundColor': '#e8f8f5', 'padding': '12px', 'borderRadius': '6px', 'marginBottom': '0'})
        )
    
    if not sections:
        return html.Div("暂无洞察数据", style={'color': '#999', 'textAlign': 'center', 'padding': '30px'})
    
    return html.Div(sections)
