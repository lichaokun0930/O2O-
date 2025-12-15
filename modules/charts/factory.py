"""
图表组件工厂 - P2优化：图表组件工厂化
提供统一的图表创建接口，提升复用性和可维护性
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from config import CHART_CONFIG


class ChartFactory:
    """图表工厂类 - 统一创建各类图表"""
    
    @staticmethod
    def _get_default_layout(title, **kwargs):
        """获取默认布局配置"""
        return {
            'title': {
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {
                    'size': kwargs.get('title_size', CHART_CONFIG['title_font_size']),
                    'family': CHART_CONFIG['font_family']
                }
            },
            'template': kwargs.get('template', CHART_CONFIG['default_template']),
            'height': kwargs.get('height', CHART_CONFIG['default_height']),
            'showlegend': kwargs.get('showlegend', True),
            'hovermode': kwargs.get('hovermode', 'closest'),
            'font': {'family': CHART_CONFIG['font_family']},
        }
    
    @classmethod
    def create_bar_chart(cls, data, x, y, title, **kwargs):
        """
        创建柱状图
        
        Args:
            data: DataFrame数据
            x: X轴列名
            y: Y轴列名或列名列表
            title: 图表标题
            **kwargs: 其他配置参数
        
        Returns:
            plotly图表对象
        """
        if isinstance(y, list):
            # 多系列柱状图
            fig = go.Figure()
            colors = kwargs.get('colors', CHART_CONFIG['color_schemes']['primary'])
            
            for i, y_col in enumerate(y):
                fig.add_trace(go.Bar(
                    x=data[x],
                    y=data[y_col],
                    name=y_col,
                    marker_color=colors[i % len(colors)],
                    text=data[y_col],
                    textposition='auto',
                ))
        else:
            # 单系列柱状图
            fig = px.bar(
                data,
                x=x,
                y=y,
                title=title,
                color=kwargs.get('color_col'),
                **kwargs.get('px_kwargs', {})
            )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_line_chart(cls, data, x, y, title, **kwargs):
        """创建折线图"""
        fig = px.line(
            data,
            x=x,
            y=y,
            title=title,
            markers=kwargs.get('markers', True),
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_pie_chart(cls, data, values, names, title, **kwargs):
        """创建饼图"""
        fig = px.pie(
            data,
            values=values,
            names=names,
            title=title,
            hole=kwargs.get('hole', 0),  # 0为饼图，>0为环形图
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_scatter_chart(cls, data, x, y, title, **kwargs):
        """创建散点图"""
        fig = px.scatter(
            data,
            x=x,
            y=y,
            title=title,
            size=kwargs.get('size'),
            color=kwargs.get('color'),
            hover_data=kwargs.get('hover_data'),
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_heatmap(cls, data, x, y, z, title, **kwargs):
        """创建热力图"""
        fig = px.imshow(
            data.pivot(index=y, columns=x, values=z),
            title=title,
            color_continuous_scale=kwargs.get('colorscale', 'RdYlGn'),
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_dual_axis_chart(cls, data, x, y1, y2, title, **kwargs):
        """
        创建双Y轴图表
        
        Args:
            data: DataFrame数据
            x: X轴列名
            y1: 左Y轴列名（柱状图）
            y2: 右Y轴列名（折线图）
            title: 图表标题
        """
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 左Y轴 - 柱状图
        if isinstance(y1, list):
            for y_col in y1:
                fig.add_trace(
                    go.Bar(x=data[x], y=data[y_col], name=y_col),
                    secondary_y=False
                )
        else:
            fig.add_trace(
                go.Bar(x=data[x], y=data[y1], name=y1),
                secondary_y=False
            )
        
        # 右Y轴 - 折线图
        fig.add_trace(
            go.Scatter(
                x=data[x],
                y=data[y2],
                name=y2,
                mode='lines+markers',
                line=dict(width=3),
                marker=dict(size=8)
            ),
            secondary_y=True
        )
        
        # 更新布局
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        fig.update_xaxes(title_text=kwargs.get('x_title', x))
        fig.update_yaxes(title_text=kwargs.get('y1_title', y1), secondary_y=False)
        fig.update_yaxes(title_text=kwargs.get('y2_title', y2), secondary_y=True)
        
        return fig
    
    @classmethod
    def create_treemap(cls, data, path, values, title, **kwargs):
        """创建树状图"""
        fig = px.treemap(
            data,
            path=path,
            values=values,
            title=title,
            color=kwargs.get('color'),
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_funnel_chart(cls, data, x, y, title, **kwargs):
        """创建漏斗图"""
        fig = go.Figure(go.Funnel(
            y=data[y],
            x=data[x],
            textposition="inside",
            textinfo="value+percent initial",
            marker={"color": kwargs.get('colors', CHART_CONFIG['color_schemes']['primary'])}
        ))
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_waterfall_chart(cls, data, x, y, title, **kwargs):
        """创建瀑布图"""
        fig = go.Figure(go.Waterfall(
            x=data[x],
            y=data[y],
            text=data[y],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_gauge_chart(cls, value, title, **kwargs):
        """
        创建仪表盘图表
        
        Args:
            value: 当前值
            title: 标题
            **kwargs: 可选参数
                - max_value: 最大值（默认100）
                - threshold_colors: 阈值颜色配置
        """
        max_value = kwargs.get('max_value', 100)
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            title={'text': title},
            delta={'reference': kwargs.get('reference', max_value * 0.8)},
            gauge={
                'axis': {'range': [None, max_value]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, max_value * 0.5], 'color': "lightgray"},
                    {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': max_value * 0.9
                }
            }
        ))
        
        fig.update_layout(height=kwargs.get('height', 400))
        return fig
    
    @classmethod
    def create_box_plot(cls, data, x, y, title, **kwargs):
        """创建箱线图"""
        fig = px.box(
            data,
            x=x,
            y=y,
            title=title,
            color=kwargs.get('color'),
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_violin_plot(cls, data, x, y, title, **kwargs):
        """创建小提琴图"""
        fig = px.violin(
            data,
            x=x,
            y=y,
            title=title,
            color=kwargs.get('color'),
            box=True,
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def create_sunburst_chart(cls, data, path, values, title, **kwargs):
        """创建旭日图"""
        fig = px.sunburst(
            data,
            path=path,
            values=values,
            title=title,
            color=kwargs.get('color'),
            **kwargs.get('px_kwargs', {})
        )
        
        fig.update_layout(**cls._get_default_layout(title, **kwargs))
        return fig
    
    @classmethod
    def add_annotations(cls, fig, annotations):
        """
        为图表添加注释
        
        Args:
            fig: plotly图表对象
            annotations: 注释列表，每个注释是一个字典
        """
        fig.update_layout(annotations=annotations)
        return fig
    
    @classmethod
    def add_shapes(cls, fig, shapes):
        """
        为图表添加形状（如参考线）
        
        Args:
            fig: plotly图表对象
            shapes: 形状列表
        """
        fig.update_layout(shapes=shapes)
        return fig
    
    @classmethod
    def export_chart(cls, fig, filename, format='png', **kwargs):
        """
        导出图表
        
        Args:
            fig: plotly图表对象
            filename: 文件名
            format: 格式 ('png', 'jpg', 'svg', 'pdf', 'html')
        """
        if format == 'html':
            fig.write_html(filename, **kwargs)
        else:
            fig.write_image(filename, format=format, **kwargs)


# 便捷函数
def quick_bar(data, x, y, title="", **kwargs):
    """快速创建柱状图"""
    return ChartFactory.create_bar_chart(data, x, y, title, **kwargs)


def quick_line(data, x, y, title="", **kwargs):
    """快速创建折线图"""
    return ChartFactory.create_line_chart(data, x, y, title, **kwargs)


def quick_pie(data, values, names, title="", **kwargs):
    """快速创建饼图"""
    return ChartFactory.create_pie_chart(data, values, names, title, **kwargs)


def quick_scatter(data, x, y, title="", **kwargs):
    """快速创建散点图"""
    return ChartFactory.create_scatter_chart(data, x, y, title, **kwargs)
