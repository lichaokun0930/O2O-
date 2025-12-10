# -*- coding: utf-8 -*-
"""
Gradio 中文版 - 支持文件上传
"""
import gradio as gr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime

# 全局变量存储当前数据
current_data = {}

# 数据加载函数
def load_excel_file(filepath):
    """加载Excel文件并返回所有数据表"""
    data = {}
    try:
        # 核心指标对比
        data['kpi'] = pd.read_excel(filepath, sheet_name='核心指标对比')
        # 价格带分析
        data['price'] = pd.read_excel(filepath, sheet_name='价格带分析')
        # 一级分类
        data['category'] = pd.read_excel(filepath, sheet_name='美团一级分类详细指标')
        # 商品角色
        data['role'] = pd.read_excel(filepath, sheet_name='商品角色分析')
        # 多规格商品
        data['multi_spec'] = pd.read_excel(filepath, sheet_name='多规格商品报告(全)')
        
        return data, True, f"""
        ✅ 数据加载成功！
        
        📊 数据统计：
        - 核心指标: {len(data['kpi'])} 行
        - 价格带: {len(data['price'])} 行
        - 分类: {len(data['category'])} 行
        - 商品角色: {len(data['role'])} 行
        - 多规格商品: {len(data['multi_spec'])} 行
        
        🎯 请点击下方各个标签页查看分析结果
        """
    except Exception as e:
        return {}, False, f"❌ 数据加载失败: {str(e)}\n\n请确保上传的是正确格式的Excel文件"

def upload_file(file):
    """处理文件上传"""
    global current_data
    
    if file is None:
        return "⚠️ 请先选择文件", None, None, None, None, None
    
    # 加载数据
    data, success, message = load_excel_file(file.name)
    
    if success:
        current_data = data
        # 返回消息和各个图表
        return (
            message,
            create_kpi_html(),
            create_price_chart(),
            create_category_chart(5),
            create_role_chart(),
            create_multispec_table()
        )
    else:
        return message, None, None, None, None, None

# KPI卡片
def create_kpi_html():
    """创建KPI指标卡片"""
    if not current_data or current_data.get('kpi', pd.DataFrame()).empty:
        return "<div style='color:orange; padding:2rem; text-align:center;'>⚠️ 请先上传数据文件</div>"
    
    kpi = current_data['kpi'].iloc[0]
    
    html = f"""
    <style>
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }}
        .kpi-card {{
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }}
        .kpi-card:hover {{ transform: translateY(-5px); }}
        .kpi-value {{ font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem; }}
        .kpi-label {{ font-size: 1rem; opacity: 0.9; }}
        .card-1 {{ background: linear-gradient(135deg, #667eea, #764ba2); }}
        .card-2 {{ background: linear-gradient(135deg, #f093fb, #f5576c); }}
        .card-3 {{ background: linear-gradient(135deg, #4facfe, #00f2fe); }}
        .card-4 {{ background: linear-gradient(135deg, #43e97b, #38f9d7); }}
        .card-5 {{ background: linear-gradient(135deg, #fa709a, #fee140); }}
        .card-6 {{ background: linear-gradient(135deg, #30cfd0, #330867); }}
    </style>
    
    <div class="kpi-grid">
        <div class="kpi-card card-1">
            <div class="kpi-value">{int(kpi.get('总SKU数', 0)):,}</div>
            <div class="kpi-label">总SKU数</div>
        </div>
        <div class="kpi-card card-2">
            <div class="kpi-value">{int(kpi.get('多规格商品数', 0)):,}</div>
            <div class="kpi-label">多规格商品</div>
        </div>
        <div class="kpi-card card-3">
            <div class="kpi-value">{int(kpi.get('动销SKU数', 0)):,}</div>
            <div class="kpi-label">动销SKU</div>
        </div>
        <div class="kpi-card card-4">
            <div class="kpi-value">{int(kpi.get('滞销SKU数', 0)):,}</div>
            <div class="kpi-label">滞销SKU</div>
        </div>
        <div class="kpi-card card-5">
            <div class="kpi-value">¥{kpi.get('总销售额', 0):,.0f}</div>
            <div class="kpi-label">总销售额</div>
        </div>
        <div class="kpi-card card-6">
            <div class="kpi-value">{kpi.get('动销率', 0):.1%}</div>
            <div class="kpi-label">动销率</div>
        </div>
    </div>
    """
    return html

# 价格带分析
def create_price_chart():
    """创建价格带分析图表"""
    if not current_data or current_data.get('price', pd.DataFrame()).empty:
        return go.Figure().add_annotation(text="请先上传数据", showarrow=False, font=dict(size=20))
    
    df = current_data['price']
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('SKU数量分布', '销售额占比'),
        specs=[[{"type": "bar"}, {"type": "pie"}]]
    )
    
    fig.add_trace(
        go.Bar(
            x=df['price_band'], 
            y=df['SKU数量'], 
            name='SKU数量',
            marker_color='lightblue',
            text=df['SKU数量'],
            textposition='outside'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Pie(
            labels=df['price_band'], 
            values=df['销售额'], 
            hole=0.4,
            textinfo='label+percent'
        ),
        row=1, col=2
    )
    
    fig.update_layout(height=500, showlegend=False, title_text="价格带分析")
    return fig

# 分类分析
def create_category_chart(top_n):
    """创建分类分析图表"""
    if not current_data or current_data.get('category', pd.DataFrame()).empty:
        return go.Figure().add_annotation(text="请先上传数据", showarrow=False, font=dict(size=20))
    
    df = current_data['category'].sort_values('SKU数量', ascending=False).head(int(top_n))
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df['l1_category'], 
        y=df['SKU数量'], 
        name='SKU数量',
        marker_color='lightblue',
        yaxis='y'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['l1_category'],
        y=df['动销率'] * 100,
        name='动销率(%)',
        mode='lines+markers',
        marker=dict(size=10, color='red'),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title=f'TOP{int(top_n)} 分类表现',
        yaxis=dict(title='SKU数量'),
        yaxis2=dict(title='动销率(%)', overlaying='y', side='right', range=[0, 100]),
        height=500,
        hovermode='x unified'
    )
    
    return fig

# 商品角色分析
def create_role_chart():
    """创建商品角色分析图表"""
    if not current_data or current_data.get('role', pd.DataFrame()).empty:
        return go.Figure().add_annotation(text="请先上传数据", showarrow=False, font=dict(size=20))
    
    df = current_data['role']
    colors = ['#43e97b', '#fa709a', '#4facfe', '#f093fb']
    
    # 尝试使用中文或英文列名
    role_col = '角色分类' if '角色分类' in df.columns else 'product_role'
    sku_col = 'SKU数量' if 'SKU数量' in df.columns else 'sku_count'
    
    fig = go.Figure(data=[go.Pie(
        labels=df[role_col],
        values=df[sku_col],
        hole=0.4,
        marker=dict(colors=colors),
        textinfo='label+value+percent',
        textposition='outside'
    )])
    
    fig.update_layout(title='商品角色分布', height=500, showlegend=True)
    return fig

# 多规格商品表格
def create_multispec_table():
    """创建多规格商品表格"""
    if not current_data or current_data.get('multi_spec', pd.DataFrame()).empty:
        return pd.DataFrame({"提示": ["请先上传数据"]})
    
    df = current_data['multi_spec'].head(50)
    
    # 列名映射（中文->英文）
    col_map = {
        '商品名称': 'product_name',
        '规格名称': 'spec_name', 
        '售价': 'price',
        '月售': 'sales_qty',
        '库存': 'stock',
        '一级分类': 'l1_category'
    }
    
    # 找到实际存在的列
    available_cols = []
    for cn, en in col_map.items():
        if cn in df.columns:
            available_cols.append(cn)
        elif en in df.columns:
            available_cols.append(en)
    
    return df[available_cols] if available_cols else df.head(50)

# Gradio应用界面
with gr.Blocks(title="O2O门店数据分析平台", theme=gr.themes.Soft()) as demo:
    
    gr.Markdown("# 🏪 O2O门店数据分析平台")
    gr.HTML("""
    <div style="text-align:center; background:linear-gradient(135deg, #667eea, #764ba2); color:white; padding:1.5rem; border-radius:10px; margin-bottom:1rem; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
        <h2 style="margin:0;">Gradio 企业版 | 支持文件上传</h2>
        <p style="margin:0.5rem 0 0 0; opacity:0.9;">📤 上传竞对分析报告Excel文件，自动生成可视化分析</p>
    </div>
    """)
    
    # 文件上传区域
    with gr.Row():
        with gr.Column(scale=2):
            file_input = gr.File(
                label="📂 上传Excel文件",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )
            upload_btn = gr.Button("🚀 开始分析", variant="primary", size="lg")
        
        with gr.Column(scale=3):
            upload_status = gr.Markdown("""
            ### 📋 使用说明
            
            1. 点击左侧按钮选择Excel文件
            2. 确保文件包含以下表格：
               - 核心指标对比
               - 价格带分析
               - 美团一级分类详细指标
               - 商品角色分析
               - 多规格商品报告(全)
            3. 点击"开始分析"按钮
            4. 查看下方各个标签页的分析结果
            """)
    
    gr.Markdown("---")
    
    # 分析结果展示
    with gr.Tab("📊 核心指标"):
        gr.Markdown("### 关键业绩指标")
        kpi_html = gr.HTML()
    
    with gr.Tab("💰 价格带分析"):
        gr.Markdown("### 价格结构与销售分布")
        price_plot = gr.Plot()
    
    with gr.Tab("📁 分类分析"):
        gr.Markdown("### 商品分类表现分析")
        with gr.Row():
            top_n_slider = gr.Slider(3, 15, 5, step=1, label="显示TOP N分类")
            cat_refresh_btn = gr.Button("🔄 刷新", variant="secondary")
        cat_plot = gr.Plot()
        cat_refresh_btn.click(fn=create_category_chart, inputs=top_n_slider, outputs=cat_plot)
    
    with gr.Tab("🎯 商品角色"):
        gr.Markdown("### 商品角色定位分布")
        role_plot = gr.Plot()
    
    with gr.Tab("📦 多规格商品"):
        gr.Markdown("### 多规格商品明细（前50条）")
        spec_table = gr.Dataframe(wrap=True)
    
    with gr.Tab("ℹ️ 关于"):
        gr.Markdown(f"""
        ### 📋 系统信息
        
        - **框架**: Gradio 5.49.1
        - **功能**: 支持上传Excel文件动态分析
        - **端口**: 7880
        - **更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        ### ✨ 核心优势
        
        - ✅ 无需预先准备数据文件
        - ✅ 支持多门店数据对比分析
        - ✅ 实时上传、实时分析
        - ✅ 6大分析维度全覆盖
        
        ### 🚀 快速访问
        
        - **本地**: http://localhost:7880
        - **局域网**: http://119.188.71.47:7880
        - **外网**: 配置花生壳后可用
        
        ### 📞 技术支持
        
        如有问题请联系开发团队
        """)
    
    # 绑定上传事件
    upload_btn.click(
        fn=upload_file,
        inputs=file_input,
        outputs=[upload_status, kpi_html, price_plot, cat_plot, role_plot, spec_table]
    )

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  🏪 O2O门店数据分析平台 - 文件上传版")
    print("="*60)
    print("\n💡 功能特性:")
    print("  - 支持上传Excel文件")
    print("  - 实时数据分析")
    print("  - 多维度可视化")
    print("\n🌐 访问地址:")
    print("  - 本地: http://localhost:7880")
    print("  - 局域网: http://119.188.71.47:7880")
    print("\n⏳ 正在启动...")
    print("="*60 + "\n")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7880,
        share=False
    )
