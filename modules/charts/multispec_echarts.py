# -*- coding: utf-8 -*-
"""
多规格商品供给分析 - ECharts版本
支持单店模式和对比模式
"""
import pandas as pd
import numpy as np
from dash import html
import dash_bootstrap_components as dbc
import dash_echarts


def find_column_index(df: pd.DataFrame, keywords: list, default_index: int = None) -> int:
    """智能查找列索引
    
    Args:
        df: DataFrame
        keywords: 关键词列表
        default_index: 默认索引（如果找不到）
        
    Returns:
        列索引
    """
    for i, col in enumerate(df.columns):
        col_str = str(col).lower()
        for kw in keywords:
            if kw.lower() in col_str:
                return i
    return default_index


def extract_multispec_data(df: pd.DataFrame) -> tuple:
    """从分类数据中提取多规格分析所需的数据
    
    Args:
        df: 分类数据DataFrame（一级分类详细指标）
        
    Returns:
        (categories, total_sku, multispec_sku) 元组
    """
    if df.empty:
        return [], np.array([]), np.array([])
    
    # 第0列：一级分类名称
    categories = df.iloc[:, 0].tolist()
    
    # 查找总SKU数列（优先匹配"一级分类sku数"或"总SKU数"）
    # 实际列名：美团一级分类sku数（索引1）
    total_sku_idx = find_column_index(df, ['一级分类sku数', '总sku数', 'sku数'], default_index=1)
    total_sku = pd.to_numeric(df.iloc[:, total_sku_idx], errors='coerce').fillna(0).values
    
    # 查找多规格SKU数列（优先匹配"多规格SKU数"）
    # 实际列名：美团一级分类多规格SKU数（索引2）
    multispec_idx = find_column_index(df, ['多规格sku数', '多规格SKU数'], default_index=2)
    multispec_sku = pd.to_numeric(df.iloc[:, multispec_idx], errors='coerce').fillna(0).values
    
    return categories, total_sku, multispec_sku


def get_toolbox(chart_name: str) -> dict:
    """获取通用的ECharts工具栏配置"""
    return {
        'show': True,
        'right': 15,
        'top': 5,
        'feature': {
            'saveAsImage': {
                'type': 'png',
                'pixelRatio': 4,
                'title': '下载高清图',
                'name': chart_name,
                'backgroundColor': '#fff',
                'excludeComponents': ['toolbox']
            }
        }
    }


def create_multispec_echarts(category_data: pd.DataFrame) -> dict:
    """创建多规格商品供给分析ECharts配置
    
    Args:
        category_data: 分类数据DataFrame（一级分类详细指标）
        
    Returns:
        ECharts配置字典
    """
    if category_data.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 使用智能数据提取
    categories, total_sku, multispec_sku_arr = extract_multispec_data(category_data)
    
    if len(categories) == 0:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 计算单规格SKU和多规格占比
    single_sku = (total_sku - multispec_sku_arr).tolist()
    multispec_sku = multispec_sku_arr.tolist()
    
    # 计算多规格占比
    with np.errstate(divide='ignore', invalid='ignore'):
        multispec_ratio = np.divide(multispec_sku_arr, total_sku) * 100
        multispec_ratio = np.nan_to_num(multispec_ratio, 0).round(1).tolist()
    
    return {
        'toolbox': get_toolbox('多规格商品供给分析'),
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'cross'}
        },
        'legend': {
            'data': ['单规格SKU', '多规格SKU', '多规格占比'],
            'top': 5
        },
        'grid': {
            'left': '3%',
            'right': '4%',
            'bottom': '15%',
            'top': '12%',
            'containLabel': True
        },
        'xAxis': {
            'type': 'category',
            'data': categories,
            'axisLabel': {'rotate': 45, 'fontSize': 11}
        },
        'yAxis': [
            {
                'type': 'value',
                'name': 'SKU数量',
                'position': 'left',
                'axisLabel': {'formatter': '{value}'}
            },
            {
                'type': 'value',
                'name': '多规格占比(%)',
                'position': 'right',
                'min': 0,
                'max': 100,
                'axisLabel': {'formatter': '{value}%'}
            }
        ],
        'series': [
            {
                'name': '单规格SKU',
                'type': 'bar',
                'stack': 'total',
                'data': single_sku,
                'itemStyle': {'color': '#bdc3c7'},
                'label': {
                    'show': True,
                    'position': 'inside',
                    'fontSize': 9
                }
            },
            {
                'name': '多规格SKU',
                'type': 'bar',
                'stack': 'total',
                'data': multispec_sku,
                'itemStyle': {'color': '#ff7f0e'},
                'label': {
                    'show': True,
                    'position': 'inside',
                    'fontSize': 9,
                    'color': 'white'
                }
            },
            {
                'name': '多规格占比',
                'type': 'line',
                'yAxisIndex': 1,
                'data': multispec_ratio,
                'itemStyle': {'color': '#3498db'},
                'lineStyle': {'width': 3},
                'symbol': 'circle',
                'symbolSize': 8,
                'label': {
                    'show': True,
                    'position': 'top',
                    'formatter': '{c}%',
                    'fontSize': 10,
                    'color': '#3498db'
                }
            }
        ]
    }


def create_multispec_comparison_echarts(own_data: pd.DataFrame, competitor_data: pd.DataFrame, competitor_name: str) -> dict:
    """创建多规格占比差异分析ECharts配置（图表1：差异柱状图）
    
    改进版：直接展示本店与竞对的差异值，正值表示本店领先，负值表示本店落后
    按差异排序，一目了然看出优劣势品类
    
    Args:
        own_data: 本店分类数据
        competitor_data: 竞对分类数据
        competitor_name: 竞对名称
        
    Returns:
        ECharts配置字典
    """
    if own_data.empty and competitor_data.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 使用智能数据提取
    own_cats, own_total, own_multi = extract_multispec_data(own_data)
    comp_cats, comp_total, comp_multi = extract_multispec_data(competitor_data)
    
    # 构建数据字典便于查找
    own_dict = {cat: {'total': own_total[i], 'multi': own_multi[i]} for i, cat in enumerate(own_cats)}
    comp_dict = {cat: {'total': comp_total[i], 'multi': comp_multi[i]} for i, cat in enumerate(comp_cats)}
    
    # 合并分类
    all_categories = sorted(set(own_cats) | set(comp_cats))
    
    # 构建数据
    data_list = []
    for cat in all_categories:
        # 本店数据
        if cat in own_dict:
            total = own_dict[cat]['total']
            multi = own_dict[cat]['multi']
            own_ratio = round(multi / total * 100, 1) if total > 0 else 0
        else:
            own_ratio = 0
        
        # 竞对数据
        if cat in comp_dict:
            total = comp_dict[cat]['total']
            multi = comp_dict[cat]['multi']
            comp_ratio = round(multi / total * 100, 1) if total > 0 else 0
        else:
            comp_ratio = 0
        
        diff = own_ratio - comp_ratio
        data_list.append({
            'category': cat,
            'own_ratio': own_ratio,
            'comp_ratio': comp_ratio,
            'diff': round(diff, 1),
            'abs_diff': abs(diff)
        })
    
    # 按差异值排序（从高到低，正值在上，负值在下）
    data_list.sort(key=lambda x: x['diff'], reverse=True)
    
    categories = [d['category'] for d in data_list]
    
    # 计算X轴范围
    max_diff = max([abs(d['diff']) for d in data_list]) if data_list else 30
    max_val = float(max(max_diff + 5, 30))  # 至少30%
    
    # 构建带标签的差异数据（正值绿色=本店领先，负值红色=本店落后）
    labeled_diff_data = []
    for d in data_list:
        diff = float(d['diff'])
        
        # 根据差异值设置颜色
        if diff > 10:
            color = '#27ae60'  # 深绿色：大幅领先
        elif diff > 0:
            color = '#2ecc71'  # 浅绿色：小幅领先
        elif diff > -10:
            color = '#e74c3c'  # 浅红色：小幅落后
        else:
            color = '#c0392b'  # 深红色：大幅落后
        
        # 格式化标签文本
        if diff > 0:
            label_text = f"+{diff}%"
        elif diff < 0:
            label_text = f"{diff}%"
        else:
            label_text = ""
        
        labeled_diff_data.append({
            'value': diff,
            'itemStyle': {'color': color},
            'label': {
                'show': diff != 0,
                'position': 'right' if diff >= 0 else 'left',
                'formatter': label_text
            }
        })
    
    return {
        'toolbox': get_toolbox('多规格占比差异分析'),
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'shadow'}
        },
        'legend': {'show': False},
        'grid': {
            'left': '3%',
            'right': '8%',
            'bottom': '5%',
            'top': '8%',
            'containLabel': True
        },
        'xAxis': {
            'type': 'value',
            'min': -max_val,
            'max': max_val,
            'axisLabel': {'formatter': '{value}%'},
            'splitLine': {'show': True, 'lineStyle': {'type': 'dashed'}},
            'axisLine': {'lineStyle': {'color': '#999'}}
        },
        'yAxis': {
            'type': 'category',
            'data': categories,
            'axisLabel': {'fontSize': 11},
            'axisTick': {'show': False},
            'axisLine': {'show': False}
        },
        'series': [{
            'name': '多规格占比差异',
            'type': 'bar',
            'data': labeled_diff_data,
            'label': {
                'show': True,
                'fontSize': 10
            },
            'markLine': {
                'silent': True,
                'symbol': 'none',
                'lineStyle': {'color': '#666', 'type': 'solid', 'width': 2},
                'data': [{'xAxis': 0}],
                'label': {'show': False}
            }
        }]
    }


def create_multispec_sku_comparison_echarts(own_data: pd.DataFrame, competitor_data: pd.DataFrame, competitor_name: str) -> dict:
    """创建多规格SKU数量对比ECharts配置（图表2：分组柱状图）
    
    Args:
        own_data: 本店分类数据
        competitor_data: 竞对分类数据
        competitor_name: 竞对名称
        
    Returns:
        ECharts配置字典
    """
    if own_data.empty and competitor_data.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 使用智能数据提取
    own_cats, own_total_arr, own_multi_arr = extract_multispec_data(own_data)
    comp_cats, comp_total_arr, comp_multi_arr = extract_multispec_data(competitor_data)
    
    # 构建数据字典
    own_dict = {cat: {'total': own_total_arr[i], 'multi': own_multi_arr[i]} for i, cat in enumerate(own_cats)}
    comp_dict = {cat: {'total': comp_total_arr[i], 'multi': comp_multi_arr[i]} for i, cat in enumerate(comp_cats)}
    
    # 合并分类
    all_categories = sorted(set(own_cats) | set(comp_cats))
    
    # 构建数据并计算加权分
    data_list = []
    for cat in all_categories:
        # 本店数据
        if cat in own_dict:
            own_total = own_dict[cat]['total']
            own_multi = own_dict[cat]['multi']
            own_ratio = own_multi / own_total * 100 if own_total > 0 else 0
        else:
            own_total, own_multi, own_ratio = 0, 0, 0
        
        # 竞对数据
        if cat in comp_dict:
            comp_total = comp_dict[cat]['total']
            comp_multi = comp_dict[cat]['multi']
            comp_ratio = comp_multi / comp_total * 100 if comp_total > 0 else 0
        else:
            comp_total, comp_multi, comp_ratio = 0, 0, 0
        
        # 加权分 = 多规格占比 × log(总SKU数+1)
        total_sku = max(own_total, comp_total)
        avg_ratio = (own_ratio + comp_ratio) / 2
        weight_score = avg_ratio * np.log10(total_sku + 1) if total_sku > 0 else 0
        
        data_list.append({
            'category': cat,
            'own_multi': int(own_multi),
            'comp_multi': int(comp_multi),
            'weight_score': weight_score
        })
    
    # 按加权分降序排序
    data_list.sort(key=lambda x: x['weight_score'], reverse=True)
    
    # 只取前15个分类
    data_list = data_list[:15]
    
    categories = [d['category'] for d in data_list]
    own_multi_list = [d['own_multi'] for d in data_list]
    comp_multi_list = [d['comp_multi'] for d in data_list]
    
    return {
        'toolbox': {
            'show': True,
            'right': 15,
            'top': 5,
            'feature': {
                'saveAsImage': {
                    'type': 'png',
                    'pixelRatio': 4,
                    'title': '下载高清图',
                    'name': '多规格SKU数量对比',
                    'backgroundColor': '#fff',
                    'excludeComponents': ['toolbox']
                }
            }
        },
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'shadow'}
        },
        'legend': {
            'data': ['本店多规格SKU', f'{competitor_name}多规格SKU'],
            'top': 5
        },
        'grid': {
            'left': '3%',
            'right': '4%',
            'bottom': '15%',
            'top': '12%',
            'containLabel': True
        },
        'xAxis': {
            'type': 'category',
            'data': categories,
            'axisLabel': {'rotate': 45, 'fontSize': 11}
        },
        'yAxis': {
            'type': 'value',
            'name': '多规格SKU数',
            'axisLabel': {'formatter': '{value}'}
        },
        'series': [
            {
                'name': '本店多规格SKU',
                'type': 'bar',
                'data': [{'value': v, 'label': {'show': v > 0}} for v in own_multi_list],
                'itemStyle': {'color': '#3498db'},
                'label': {
                    'show': True,
                    'position': 'top',
                    'fontSize': 9
                }
            },
            {
                'name': f'{competitor_name}多规格SKU',
                'type': 'bar',
                'data': [{'value': v, 'label': {'show': v > 0}} for v in comp_multi_list],
                'itemStyle': {'color': '#e74c3c'},
                'label': {
                    'show': True,
                    'position': 'top',
                    'fontSize': 9
                }
            }
        ]
    }


def create_multispec_structure_comparison_echarts(own_data: pd.DataFrame, competitor_data: pd.DataFrame, competitor_name: str) -> dict:
    """创建多规格占比分组对比ECharts配置（图表3：分组柱状图）
    
    改进版：直接对比本店和竞对的多规格占比，更直观
    
    Args:
        own_data: 本店分类数据
        competitor_data: 竞对分类数据
        competitor_name: 竞对名称
        
    Returns:
        ECharts配置字典
    """
    if own_data.empty and competitor_data.empty:
        return {'title': {'text': '暂无数据', 'left': 'center', 'top': 'center'}}
    
    # 使用智能数据提取
    own_cats, own_total_arr, own_multi_arr = extract_multispec_data(own_data)
    comp_cats, comp_total_arr, comp_multi_arr = extract_multispec_data(competitor_data)
    
    # 构建数据字典
    own_dict = {cat: {'total': own_total_arr[i], 'multi': own_multi_arr[i]} for i, cat in enumerate(own_cats)}
    comp_dict = {cat: {'total': comp_total_arr[i], 'multi': comp_multi_arr[i]} for i, cat in enumerate(comp_cats)}
    
    # 合并分类
    all_categories = sorted(set(own_cats) | set(comp_cats))
    
    # 构建数据
    data_list = []
    for cat in all_categories:
        # 本店数据
        if cat in own_dict:
            own_total = own_dict[cat]['total']
            own_multi = own_dict[cat]['multi']
            own_multi_pct = round(own_multi / own_total * 100, 1) if own_total > 0 else 0
        else:
            own_multi_pct = 0
        
        # 竞对数据
        if cat in comp_dict:
            comp_total = comp_dict[cat]['total']
            comp_multi = comp_dict[cat]['multi']
            comp_multi_pct = round(comp_multi / comp_total * 100, 1) if comp_total > 0 else 0
        else:
            comp_multi_pct = 0
        
        # 计算平均多规格占比用于排序
        avg_pct = (own_multi_pct + comp_multi_pct) / 2
        
        data_list.append({
            'category': cat,
            'own_multi_pct': own_multi_pct,
            'comp_multi_pct': comp_multi_pct,
            'avg_pct': avg_pct
        })
    
    # 按平均多规格占比降序排序，取前15个
    data_list.sort(key=lambda x: x['avg_pct'], reverse=True)
    data_list = data_list[:15]
    
    categories = [d['category'] for d in data_list]
    own_data_list = [float(d['own_multi_pct']) for d in data_list]
    comp_data_list = [float(d['comp_multi_pct']) for d in data_list]
    
    # 构建带标签的数据（只显示非零值）
    own_labeled_data = []
    comp_labeled_data = []
    for i, d in enumerate(data_list):
        own_pct = float(d['own_multi_pct'])
        comp_pct = float(d['comp_multi_pct'])
        
        own_labeled_data.append({
            'value': own_pct,
            'label': {
                'show': own_pct > 0,
                'formatter': f"{own_pct}%"
            }
        })
        comp_labeled_data.append({
            'value': comp_pct,
            'label': {
                'show': comp_pct > 0,
                'formatter': f"{comp_pct}%"
            }
        })
    
    return {
        'toolbox': get_toolbox('多规格占比对比'),
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {'type': 'shadow'}
        },
        'legend': {
            'data': ['本店', competitor_name],
            'top': 5
        },
        'grid': {
            'left': '3%',
            'right': '4%',
            'bottom': '15%',
            'top': '12%',
            'containLabel': True
        },
        'xAxis': {
            'type': 'category',
            'data': categories,
            'axisLabel': {'rotate': 45, 'fontSize': 11, 'interval': 0}
        },
        'yAxis': {
            'type': 'value',
            'name': '多规格占比(%)',
            'max': 100,
            'axisLabel': {'formatter': '{value}%'}
        },
        'series': [
            {
                'name': '本店',
                'type': 'bar',
                'data': own_labeled_data,
                'itemStyle': {'color': '#3498db'},
                'label': {
                    'show': True,
                    'position': 'top',
                    'fontSize': 9
                },
                'barGap': '10%'
            },
            {
                'name': competitor_name,
                'type': 'bar',
                'data': comp_labeled_data,
                'itemStyle': {'color': '#e74c3c'},
                'label': {
                    'show': True,
                    'position': 'top',
                    'fontSize': 9
                }
            }
        ]
    }


def generate_multispec_comparison_insights(own_data: pd.DataFrame, competitor_data: pd.DataFrame, competitor_name: str) -> list:
    """生成多规格对比洞察
    
    Args:
        own_data: 本店分类数据
        competitor_data: 竞对分类数据
        competitor_name: 竞对名称
        
    Returns:
        洞察列表
    """
    insights = []
    
    if own_data.empty and competitor_data.empty:
        return insights
    
    # 使用智能数据提取
    own_cats, own_total_arr, own_multi_arr = extract_multispec_data(own_data)
    comp_cats, comp_total_arr, comp_multi_arr = extract_multispec_data(competitor_data)
    
    # 计算整体统计
    own_total_sku = own_total_arr.sum() if len(own_total_arr) > 0 else 0
    own_multi_sku = own_multi_arr.sum() if len(own_multi_arr) > 0 else 0
    own_overall_ratio = own_multi_sku / own_total_sku * 100 if own_total_sku > 0 else 0
    
    comp_total_sku = comp_total_arr.sum() if len(comp_total_arr) > 0 else 0
    comp_multi_sku = comp_multi_arr.sum() if len(comp_multi_arr) > 0 else 0
    comp_overall_ratio = comp_multi_sku / comp_total_sku * 100 if comp_total_sku > 0 else 0
    
    ratio_diff = own_overall_ratio - comp_overall_ratio
    sku_diff = int(own_multi_sku - comp_multi_sku)
    
    # 整体对比
    if ratio_diff > 5:
        insights.append({
            'icon': '🟢',
            'text': f'整体多规格占比领先竞对 {ratio_diff:.1f}% (本店{own_overall_ratio:.1f}% vs 竞对{comp_overall_ratio:.1f}%)',
            'level': 'success'
        })
    elif ratio_diff < -5:
        insights.append({
            'icon': '🔴',
            'text': f'整体多规格占比落后竞对 {abs(ratio_diff):.1f}% (本店{own_overall_ratio:.1f}% vs 竞对{comp_overall_ratio:.1f}%)',
            'level': 'danger'
        })
    else:
        insights.append({
            'icon': '🟡',
            'text': f'整体多规格占比与竞对接近 (本店{own_overall_ratio:.1f}% vs 竞对{comp_overall_ratio:.1f}%)',
            'level': 'warning'
        })
    
    # SKU数量对比
    insights.append({
        'icon': '📦',
        'text': f'多规格SKU数量: 本店{int(own_multi_sku)} vs 竞对{int(comp_multi_sku)} (差异{sku_diff:+d})',
        'level': 'primary'
    })
    
    # 构建数据字典用于分类级别分析
    own_dict = {cat: {'total': own_total_arr[i], 'multi': own_multi_arr[i]} for i, cat in enumerate(own_cats)}
    comp_dict = {cat: {'total': comp_total_arr[i], 'multi': comp_multi_arr[i]} for i, cat in enumerate(comp_cats)}
    all_categories = set(own_cats) | set(comp_cats)
    
    advantage_cats = []  # 本店领先的品类
    disadvantage_cats = []  # 本店落后的品类
    
    for cat in all_categories:
        # 使用已构建的数据字典
        own_ratio = 0
        if cat in own_dict:
            total = own_dict[cat]['total']
            multi = own_dict[cat]['multi']
            own_ratio = multi / total * 100 if total > 0 else 0
        
        comp_ratio = 0
        if cat in comp_dict:
            total = comp_dict[cat]['total']
            multi = comp_dict[cat]['multi']
            comp_ratio = multi / total * 100 if total > 0 else 0
        
        diff = own_ratio - comp_ratio
        if diff > 10:
            advantage_cats.append(cat)
        elif diff < -10:
            disadvantage_cats.append(cat)
    
    if disadvantage_cats:
        insights.append({
            'icon': '⚠️',
            'text': f'劣势品类(落后>10%): {", ".join(disadvantage_cats[:5])} → 建议增加规格丰富度',
            'level': 'danger'
        })
    
    if advantage_cats:
        insights.append({
            'icon': '✅',
            'text': f'优势品类(领先>10%): {", ".join(advantage_cats[:5])} → 保持供给优势',
            'level': 'success'
        })
    
    return insights


def generate_multispec_insights(category_data: pd.DataFrame) -> list:
    """生成多规格供给洞察
    
    Args:
        category_data: 分类数据DataFrame
        
    Returns:
        洞察列表
    """
    insights = []
    
    if category_data.empty:
        return insights
    
    # 使用智能数据提取
    categories, total_sku, multispec_sku = extract_multispec_data(category_data)
    categories = np.array(categories)
    
    # 计算占比
    with np.errstate(divide='ignore', invalid='ignore'):
        multispec_ratio = np.divide(multispec_sku, total_sku)
        multispec_ratio = np.nan_to_num(multispec_ratio, 0)
    
    # 分类
    high_cats = []  # >50%
    low_cats = []   # <20%
    
    for i, ratio in enumerate(multispec_ratio):
        cat_name = str(categories[i])
        if ratio > 0.5:
            high_cats.append(cat_name)
        elif ratio < 0.2:
            low_cats.append(cat_name)
    
    if high_cats:
        insights.append({
            'icon': '🎨',
            'text': f'高多规格品类(>50%): {", ".join(high_cats[:5])} → 供给丰富',
            'level': 'success'
        })
    
    if low_cats:
        insights.append({
            'icon': '📦',
            'text': f'低多规格品类(<20%): {", ".join(low_cats[:5])} → 供给相对单一',
            'level': 'warning'
        })
    
    # 整体统计
    total_multispec = np.nansum(multispec_sku)
    total_all = np.nansum(total_sku)
    overall_ratio = total_multispec / total_all if total_all > 0 else 0
    
    insights.append({
        'icon': '📊',
        'text': f'门店整体多规格占比 {overall_ratio:.1%}, 多规格SKU {int(total_multispec)}/{int(total_all)}',
        'level': 'primary'
    })
    
    return insights


def create_multispec_insights_display(insights: list):
    """创建洞察展示组件"""
    if not insights:
        return html.Div("暂无洞察", style={'color': '#999', 'textAlign': 'center'})
    
    level_colors = {
        'success': '#27ae60',
        'warning': '#f39c12',
        'danger': '#e74c3c',
        'info': '#3498db',
        'primary': '#2c3e50'
    }
    
    items = []
    for insight in insights:
        color = level_colors.get(insight.get('level', 'info'), '#666')
        items.append(
            html.Div([
                html.Span(insight.get('icon', '💡'), style={'marginRight': '8px'}),
                html.Span(insight.get('text', ''), style={'color': color})
            ], style={'padding': '6px 0', 'fontSize': '13px'})
        )
    
    return html.Div(items, style={'padding': '10px'})


def create_multispec_comparison_kpi_cards(own_data: pd.DataFrame, competitor_data: pd.DataFrame, competitor_name: str):
    """创建多规格对比KPI卡片
    
    Args:
        own_data: 本店分类数据
        competitor_data: 竞对分类数据
        competitor_name: 竞对名称
        
    Returns:
        Dash组件
    """
    # 使用智能数据提取
    own_cats, own_total_arr, own_multi_arr = extract_multispec_data(own_data)
    comp_cats, comp_total_arr, comp_multi_arr = extract_multispec_data(competitor_data)
    
    # 计算统计数据
    own_total_sku = own_total_arr.sum() if len(own_total_arr) > 0 else 0
    own_multi_sku = own_multi_arr.sum() if len(own_multi_arr) > 0 else 0
    own_overall_ratio = own_multi_sku / own_total_sku * 100 if own_total_sku > 0 else 0
    
    comp_total_sku = comp_total_arr.sum() if len(comp_total_arr) > 0 else 0
    comp_multi_sku = comp_multi_arr.sum() if len(comp_multi_arr) > 0 else 0
    comp_overall_ratio = comp_multi_sku / comp_total_sku * 100 if comp_total_sku > 0 else 0
    
    # 计算高/低多规格品类数
    own_high_count = 0
    own_low_count = 0
    comp_high_count = 0
    comp_low_count = 0
    
    for i in range(len(own_cats)):
        total = own_total_arr[i]
        multi = own_multi_arr[i]
        ratio = multi / total if total > 0 else 0
        if ratio > 0.5:
            own_high_count += 1
        elif ratio < 0.2:
            own_low_count += 1
    
    for i in range(len(comp_cats)):
        total = comp_total_arr[i]
        multi = comp_multi_arr[i]
        ratio = multi / total if total > 0 else 0
        if ratio > 0.5:
            comp_high_count += 1
        elif ratio < 0.2:
            comp_low_count += 1
    
    # 计算差异
    ratio_diff = own_overall_ratio - comp_overall_ratio
    sku_diff = int(own_multi_sku - comp_multi_sku)
    high_diff = own_high_count - comp_high_count
    low_diff = own_low_count - comp_low_count
    
    def get_diff_style(diff, reverse=False):
        """获取差异样式（reverse=True表示负值是好的）"""
        if reverse:
            diff = -diff
        if diff > 0:
            return {'color': '#27ae60', 'text': f'+{diff}' if isinstance(diff, int) else f'+{diff:.1f}%'}
        elif diff < 0:
            return {'color': '#e74c3c', 'text': f'{diff}' if isinstance(diff, int) else f'{diff:.1f}%'}
        else:
            return {'color': '#7f8c8d', 'text': '持平'}
    
    def create_kpi_card(title, own_value, comp_value, diff, unit='', reverse=False):
        diff_style = get_diff_style(diff, reverse)
        return html.Div([
            html.Div(title, style={'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '5px'}),
            html.Div([
                html.Span(f'本店: ', style={'fontSize': '11px', 'color': '#666'}),
                html.Span(f'{own_value}{unit}', style={'fontSize': '16px', 'fontWeight': 'bold', 'color': '#3498db'}),
            ]),
            html.Div([
                html.Span(f'竞对: ', style={'fontSize': '11px', 'color': '#666'}),
                html.Span(f'{comp_value}{unit}', style={'fontSize': '16px', 'fontWeight': 'bold', 'color': '#e74c3c'}),
            ]),
            html.Div([
                html.Span('差异: ', style={'fontSize': '11px', 'color': '#666'}),
                html.Span(diff_style['text'], style={'fontSize': '14px', 'fontWeight': 'bold', 'color': diff_style['color']}),
            ], style={'marginTop': '3px'})
        ], style={
            'backgroundColor': 'white',
            'padding': '12px',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'textAlign': 'center',
            'minWidth': '140px'
        })
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                create_kpi_card('整体多规格占比', f'{own_overall_ratio:.1f}', f'{comp_overall_ratio:.1f}', ratio_diff, '%')
            ], width=3),
            dbc.Col([
                create_kpi_card('多规格SKU总数', int(own_multi_sku), int(comp_multi_sku), sku_diff)
            ], width=3),
            dbc.Col([
                create_kpi_card('高多规格品类数(>50%)', own_high_count, comp_high_count, high_diff)
            ], width=3),
            dbc.Col([
                create_kpi_card('低多规格品类数(<20%)', own_low_count, comp_low_count, low_diff, '', reverse=True)
            ], width=3),
        ], className='g-2')
    ], style={'marginBottom': '15px'})
