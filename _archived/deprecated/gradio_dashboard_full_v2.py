# -*- coding: utf-8 -*-
"""
O2O门店数据分析看板 - Gradio完整版 v2.0
完整移植 dashboard_v2.py 所有底层逻辑
"""
import gradio as gr
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DEFAULT_REPORT_PATH = "./reports/竞对分析报告_v3.4_FINAL.xlsx"
APP_TITLE = "O2O门店数据分析看板 v2.0 - Gradio版"

class DataLoader:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            print(f"✓ 可用的sheet: {len(sheet_names)}个")
            
            if len(sheet_names) > 0:
                self.data["kpi"] = pd.read_excel(self.excel_path, sheet_name=sheet_names[0])
            if len(sheet_names) > 2:
                self.data["price_analysis"] = pd.read_excel(self.excel_path, sheet_name=sheet_names[2])
                if not self.data["price_analysis"].empty and "Unnamed" in str(self.data["price_analysis"].columns[0]):
                    self.data["price_analysis"] = self.data["price_analysis"].drop(self.data["price_analysis"].columns[0], axis=1)
            if len(sheet_names) > 4:
                self.data["category_l1"] = pd.read_excel(self.excel_path, sheet_name=sheet_names[4])
            if len(sheet_names) > 1:
                self.data["role_analysis"] = pd.read_excel(self.excel_path, sheet_name=sheet_names[1])
            if len(sheet_names) > 6:
                self.data["sku_details"] = pd.read_excel(self.excel_path, sheet_name=sheet_names[6])
            
            for key in ["kpi", "category_l1", "role_analysis", "price_analysis", "sku_details"]:
                if key not in self.data:
                    self.data[key] = pd.DataFrame()
            
            print(f"✓ 数据加载成功")
        except Exception as e:
            print(f"✗ 数据加载失败: {e}")
            self.data = {k: pd.DataFrame() for k in ["kpi", "category_l1", "role_analysis", "price_analysis", "sku_details"]}
    
    def get_kpi_summary(self):
        if self.data["kpi"].empty:
            return {}
        kpi_df = self.data["kpi"]
        if len(kpi_df) > 0:
            row = kpi_df.iloc[0]
            summary = {}
            for i in range(len(kpi_df.columns)):
                value = row.iloc[i] if i < len(row) else 0
                if i == 0: summary["门店"] = value
                elif i == 1: summary["总SKU数(含规格)"] = value
                elif i == 4: summary["多规格SKU总数"] = value
                elif i == 5: summary["总SKU数(去重后)"] = value
                elif i == 6: summary["动销SKU数"] = value
                elif i == 7: summary["滞销SKU数"] = value
                elif i == 8: summary["总销售额(去重后)"] = value
                elif i == 9: summary["动销率"] = value
                elif i == 10: summary["唯一多规格商品数"] = value
            
            if not self.data["category_l1"].empty:
                category_df = self.data["category_l1"]
                if len(category_df.columns) > 23:
                    summary["门店爆品数"] = category_df.iloc[:, 23].sum()
                if len(category_df.columns) > 24:
                    discount_col = pd.to_numeric(category_df.iloc[:, 24], errors="coerce")
                    summary["门店平均折扣"] = discount_col.mean()
            
            if not self.data["sku_details"].empty:
                sku_df = self.data["sku_details"]
                if len(sku_df.columns) > 1:
                    price_col = pd.to_numeric(sku_df.iloc[:, 1], errors="coerce")
                    summary["平均SKU单价"] = price_col.mean()
                if len(sku_df.columns) > 1 and "总SKU数(去重后)" in summary:
                    high_value_count = (pd.to_numeric(sku_df.iloc[:, 1], errors="coerce") > 50).sum()
                    total_skus = summary["总SKU数(去重后)"]
                    summary["高价值SKU占比"] = (high_value_count / total_skus) if total_skus > 0 else 0
                if len(sku_df.columns) > 2 and "总销售额(去重后)" in summary:
                    price_col = pd.to_numeric(sku_df.iloc[:, 1], errors="coerce").fillna(0)
                    sales_col = pd.to_numeric(sku_df.iloc[:, 2], errors="coerce").fillna(0)
                    sku_df_temp = sku_df.copy()
                    sku_df_temp["revenue"] = price_col * sales_col
                    top10_revenue = sku_df_temp.nlargest(10, "revenue")["revenue"].sum()
                    total_revenue = summary["总销售额(去重后)"]
                    summary["爆款集中度"] = (top10_revenue / total_revenue) if total_revenue > 0 else 0
            
            if not self.data["category_l1"].empty and "动销SKU数" in summary:
                category_df = self.data["category_l1"]
                if len(category_df.columns) > 22:
                    total_discount_skus = pd.to_numeric(category_df.iloc[:, 22], errors="coerce").sum()
                    active_skus = summary["动销SKU数"]
                    summary["促销强度"] = (total_discount_skus / active_skus) if active_skus > 0 else 0
            
            return summary
        return {}

def create_kpi_display(kpi_data):
    if not kpi_data:
        return "暂无KPI数据"
    kpi_configs = [
        {"key": "总SKU数(含规格)", "title": "总SKU数(含规格)", "icon": "📦", "format": "number"},
        {"key": "多规格SKU总数", "title": "多规格SKU总数", "icon": "🔢", "format": "number"},
        {"key": "动销SKU数", "title": "动销SKU数", "icon": "✅", "format": "number"},
        {"key": "滞销SKU数", "title": "滞销SKU数", "icon": "⚠️", "format": "number"},
        {"key": "总销售额(去重后)", "title": "总销售额", "icon": "💰", "format": "currency"},
        {"key": "动销率", "title": "动销率", "icon": "📈", "format": "percent"},
        {"key": "唯一多规格商品数", "title": "唯一多规格商品数", "icon": "🎯", "format": "number"},
        {"key": "门店爆品数", "title": "门店爆品数", "icon": "🔥", "format": "number"},
        {"key": "门店平均折扣", "title": "门店平均折扣", "icon": "🏷️", "format": "discount"},
        {"key": "平均SKU单价", "title": "平均SKU单价", "icon": "💵", "format": "currency"},
        {"key": "高价值SKU占比", "title": "高价值SKU占比(>50元)", "icon": "💎", "format": "percent"},
        {"key": "促销强度", "title": "促销强度", "icon": "🎁", "format": "percent"},
        {"key": "爆款集中度", "title": "爆款集中度(TOP10)", "icon": "🏆", "format": "percent"}
    ]
    html = ["<div style=\"display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; padding: 20px;\">"]
    for config in kpi_configs:
        if config["key"] in kpi_data:
            value = kpi_data[config["key"]]
            if config.get("format") == "percent":
                formatted_value = f"{value:.1%}" if isinstance(value, (int, float)) else str(value)
            elif config.get("format") == "currency":
                formatted_value = f"¥{value:,.0f}" if isinstance(value, (int, float)) else str(value)
            elif config.get("format") == "discount":
                formatted_value = f"{value:.1f}折" if isinstance(value, (int, float)) else str(value)
            else:
                formatted_value = f"{value:,}" if isinstance(value, (int, float)) else str(value)
            html.append(f"<div style=\"background: white; border: 2px solid #e0e0e0; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);\"><div style=\"font-size: 2.5rem; margin-bottom: 10px;\">{config['icon']}</div><div style=\"font-size: 1.8rem; font-weight: bold; color: #2c3e50; margin-bottom: 5px;\">{formatted_value}</div><div style=\"font-size: 0.9rem; color: #7f8c8d;\">{config['title']}</div></div>")
    html.append("</div>")
    return "".join(html)

def create_category_heatmap(category_data):
    if category_data.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无分类数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=20)
        return fig
    numeric_cols = category_data.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) < 2:
        fig = go.Figure()
        fig.add_annotation(text="数值列不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=20)
        return fig
    priority_map = {"动销率": 100, "sku数": 90, "销售额": 85, "占比": 80, "折扣": 75, "活动": 70, "库存": 65}
    scored_cols = []
    for col in numeric_cols:
        score = 0
        for keyword, weight in priority_map.items():
            if keyword in str(col):
                score += weight
        scored_cols.append((col, score))
    scored_cols.sort(key=lambda x: x[1], reverse=True)
    selected_cols = [col for col, score in scored_cols[:6]]
    if not selected_cols:
        selected_cols = numeric_cols[:6]
    category_col = category_data.columns[0]
    heatmap_data = category_data[[category_col] + selected_cols].copy()
    z_data = []
    for col in selected_cols:
        col_data = pd.to_numeric(heatmap_data[col], errors="coerce").fillna(0)
        z_data.append(col_data.tolist())
    fig = go.Figure(data=go.Heatmap(z=z_data, x=heatmap_data[category_col].tolist(), y=selected_cols, colorscale="RdYlGn", hoverongaps=False, hovertemplate="分类: %{x}<br>指标: %{y}<br>数值: %{z:.2f}<extra></extra>"))
    fig.update_layout(title={"text": "🔥 美团一级分类表现热力图", "font": {"size": 20, "color": "#2c3e50"}, "x": 0.5, "xanchor": "center"}, xaxis_title="分类名称", yaxis_title="关键指标", height=600, margin=dict(l=150, r=50, t=80, b=100), plot_bgcolor="white", paper_bgcolor="white")
    return fig

def create_role_pie_chart(role_data):
    if role_data.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无商品角色数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=20)
        return fig
    role_col = role_data.columns[0]
    value_col = role_data.columns[1] if len(role_data.columns) > 1 else role_data.columns[0]
    color_map = {"引流品": "#3498db", "利润品": "#2ecc71", "形象品": "#9b59b6", "劣势品": "#e74c3c"}
    colors = [color_map.get(role, "#95a5a6") for role in role_data[role_col]]
    fig = go.Figure(data=[go.Pie(labels=role_data[role_col], values=role_data[value_col], marker=dict(colors=colors, line=dict(color="white", width=2)), hovertemplate="<b>%{label}</b><br>SKU数量: %{value}<br>占比: %{percent}<extra></extra>", textinfo="label+percent", textfont_size=14)])
    fig.update_layout(title={"text": "🎯 商品角色分布分析", "font": {"size": 20, "color": "#2c3e50"}, "x": 0.5, "xanchor": "center"}, height=600, showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05), margin=dict(l=50, r=150, t=80, b=50))
    return fig

def create_price_bar_chart(price_data):
    if price_data.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无价格带数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=20)
        return fig
    price_band_col = price_data.columns[0]
    sku_col, revenue_col = None, None
    for col in price_data.columns:
        if "SKU" in str(col) or "sku" in str(col):
            sku_col = col
        if "销售额" in str(col) or "金额" in str(col):
            revenue_col = col
    if not sku_col:
        sku_col = price_data.columns[1] if len(price_data.columns) > 1 else price_band_col
    if not revenue_col:
        revenue_col = price_data.columns[2] if len(price_data.columns) > 2 else sku_col
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(name="SKU数量", x=price_data[price_band_col], y=price_data[sku_col], marker_color="#3498db", hovertemplate="价格带: %{x}<br>SKU数量: %{y}<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(name="销售额", x=price_data[price_band_col], y=price_data[revenue_col], mode="lines+markers", line=dict(color="#e74c3c", width=3), marker=dict(size=10), hovertemplate="价格带: %{x}<br>销售额: %{y:,.0f}<extra></extra>"), secondary_y=True)
    fig.update_layout(title={"text": "💰 价格带分布分析", "font": {"size": 20, "color": "#2c3e50"}, "x": 0.5, "xanchor": "center"}, xaxis_title="价格带", height=600, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(l=80, r=80, t=100, b=80), plot_bgcolor="white", paper_bgcolor="white")
    fig.update_yaxes(title_text="SKU数量", secondary_y=False, gridcolor="#ecf0f1")
    fig.update_yaxes(title_text="销售额 (元)", secondary_y=True)
    return fig

def build_dashboard():
    try:
        loader = DataLoader(DEFAULT_REPORT_PATH)
        kpi_data = loader.get_kpi_summary()
        kpi_html = create_kpi_display(kpi_data)
        heatmap_fig = create_category_heatmap(loader.data.get("category_l1", pd.DataFrame()))
        pie_fig = create_role_pie_chart(loader.data.get("role_analysis", pd.DataFrame()))
        bar_fig = create_price_bar_chart(loader.data.get("price_analysis", pd.DataFrame()))
        category_table = loader.data.get("category_l1", pd.DataFrame()).head(20)
        return kpi_html, heatmap_fig, pie_fig, bar_fig, category_table
    except Exception as e:
        print(f"✗ Dashboard构建失败: {e}")
        return "数据加载失败", go.Figure(), go.Figure(), go.Figure(), pd.DataFrame()

if __name__ == "__main__":
    print("=" * 70)
    print(f"  {APP_TITLE}")
    print("=" * 70)
    with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# 🏪 {APP_TITLE}\n完整移植 dashboard_v2.py 的核心功能\n- ✅ 13个KPI指标（完全对标）\n- ✅ DataLoader数据加载逻辑（100%一致）\n- ✅ KPI计算公式（完全相同）\n- ✅ 图表展示（数据源一致）")
        with gr.Tab("📊 核心KPI"):
            kpi_display = gr.HTML(label="13个核心指标")
        with gr.Tab("🔥 分类分析"):
            heatmap_plot = gr.Plot(label="美团一级分类表现热力图")
        with gr.Tab("🎯 商品角色"):
            pie_plot = gr.Plot(label="商品角色分布")
        with gr.Tab("💰 价格带"):
            bar_plot = gr.Plot(label="价格带分析")
        with gr.Tab("📋 详细数据"):
            category_table = gr.Dataframe(label="美团一级分类详细数据", interactive=False)
        demo.load(fn=build_dashboard, outputs=[kpi_display, heatmap_plot, pie_plot, bar_plot, category_table])
    print("\n✓ 启动 Gradio Dashboard...")
    print("✓ 本地访问: http://localhost:7860")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
