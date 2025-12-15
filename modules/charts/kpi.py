"""
KPI图表构建器
"""
import plotly.graph_objects as go
from config import get_config


class KPIChartBuilder:
    """KPI图表构建器"""
    
    @staticmethod
    def create_kpi_cards(kpi_data):
        """
        创建KPI卡片
        
        Args:
            kpi_data: KPI数据字典
        
        Returns:
            KPI卡片组件列表
        """
        # 这是一个占位实现，实际会在dashboard中使用
        return []
    
    @staticmethod
    def create_kpi_trend_chart(data, metric_name):
        """
        创建KPI趋势图
        
        Args:
            data: 趋势数据
            metric_name: 指标名称
        
        Returns:
            plotly图表对象
        """
        chart_config = get_config('chart')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data.values,
            mode='lines+markers',
            name=metric_name,
            line=dict(width=3),
            marker=dict(size=8)
        ))
        
        fig.update_layout(
            title=f'{metric_name}趋势',
            height=chart_config['default_height'],
            template=chart_config['default_template']
        )
        
        return fig
