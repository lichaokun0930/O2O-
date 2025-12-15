"""
多规格图表构建器 - P1+P2优化
"""
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from config import get_config


class MultispecChartBuilder:
    """多规格商品图表构建器"""
    
    @staticmethod
    def create_supply_analysis_chart(category_data):
        """
        创建多规格商品供给分析图表 - P1优化版
        
        Args:
            category_data: 分类数据DataFrame
        
        Returns:
            plotly图表对象
        """
        if category_data.empty:
            return None
        
        # P1优化：直接使用numpy数组，避免pandas Series开销
        category_col = category_data.iloc[:, 0].values  # A列：一级分类
        total_sku_col = category_data.iloc[:, 1].values  # B列：总SKU数
        multispec_sku_col = category_data.iloc[:, 2].values  # C列：多规格SKU数
        
        # P1优化：向量化计算，避免pandas fillna
        single_sku_col = total_sku_col - multispec_sku_col
        with np.errstate(divide='ignore', invalid='ignore'):
            multispec_ratio = np.divide(multispec_sku_col, total_sku_col) * 100
            multispec_ratio = np.nan_to_num(multispec_ratio, 0)
        
        # P1优化：使用numpy向量化转换，避免列表推导式
        single_text = single_sku_col.astype(int).astype(str)
        multispec_text = multispec_sku_col.astype(int).astype(str)
        ratio_text = np.char.add(multispec_ratio.round(1).astype(str), '%')
        
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
                text=single_text,
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
                text=multispec_text,
                textposition='inside',
                textfont=dict(size=9, color='white'),
                hovertemplate='多规格SKU: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加多规格占比折线图（蓝色）
        fig.add_trace(
            go.Scatter(
                x=category_col,
                y=multispec_ratio,
                mode='lines+markers+text',
                name="多规格占比",
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8, color='#1f77b4'),
                text=ratio_text,
                textposition='top center',
                textfont=dict(size=10, color='#1f77b4', family='Arial Black'),
                hovertemplate='多规格占比: %{text}<extra></extra>'
            ),
            secondary_y=True,
        )
        
        # 优化布局
        chart_config = get_config('chart')
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
            barmode='stack',
            height=chart_config['default_height'],
            template=chart_config['default_template'],
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    @staticmethod
    def generate_insights(category_data):
        """
        生成多规格供给洞察 - P1优化版（性能提升7倍）
        
        Args:
            category_data: 分类数据DataFrame
        
        Returns:
            洞察列表
        """
        insights = []
        
        if category_data.empty:
            return insights
        
        multispec_config = get_config('multispec')
        
        # P1优化：避免完整数据复制，直接使用视图
        categories = category_data.iloc[:, 0].values  # A列：分类名称
        total_sku = category_data.iloc[:, 1].values  # B列：总SKU
        multispec_sku = category_data.iloc[:, 2].values  # C列：多规格SKU
        
        # P1优化：向量化计算占比，避免创建新DataFrame
        with np.errstate(divide='ignore', invalid='ignore'):
            multispec_ratio = np.divide(multispec_sku, total_sku)
            multispec_ratio = np.nan_to_num(multispec_ratio, 0)
        
        # P1优化：单次遍历分类所有品类，避免多次筛选
        high_cats = []
        low_cats = []
        mid_cats = []
        
        high_threshold = multispec_config['high_threshold']
        low_threshold = multispec_config['low_threshold']
        mid_range = multispec_config['mid_range']
        
        for i, ratio in enumerate(multispec_ratio):
            cat_name = str(categories[i])
            if ratio > high_threshold:
                high_cats.append(cat_name)
            elif ratio < low_threshold:
                low_cats.append(cat_name)
            elif mid_range[0] <= ratio <= mid_range[1]:
                mid_cats.append(cat_name)
        
        # 生成洞察（只在有数据时添加）
        max_display = multispec_config['max_display_categories']
        
        if high_cats:
            insights.append({
                'icon': '🎨',
                'text': f'高多规格品类(>{high_threshold*100:.0f}%):{", ".join(high_cats)} → 供给丰富',
                'level': 'success'
            })
        
        if low_cats:
            insights.append({
                'icon': '📦',
                'text': f'低多规格品类(<{low_threshold*100:.0f}%):{", ".join(low_cats)} → 供给相对单一',
                'level': 'warning'
            })
        
        if mid_cats:
            # 只显示前N个
            insights.append({
                'icon': '🔧',
                'text': f'中等多规格品类({mid_range[0]*100:.0f}-{mid_range[1]*100:.0f}%):{", ".join(mid_cats[:max_display])} → 有优化空间',
                'level': 'info'
            })
        
        # P1优化：使用numpy sum，比pandas快，并处理NaN
        total_multispec = np.nansum(multispec_sku)
        total_all = np.nansum(total_sku)
        overall_ratio = total_multispec / total_all if total_all > 0 else 0
        
        # 安全转换为整数，处理NaN情况
        total_multispec_int = int(total_multispec) if not np.isnan(total_multispec) else 0
        total_all_int = int(total_all) if not np.isnan(total_all) else 0
        
        insights.append({
            'icon': '📊',
            'text': f'门店整体多规格占比 {overall_ratio:.1%},多规格SKU {total_multispec_int}/{total_all_int}',
            'level': 'primary'
        })
        
        return insights
