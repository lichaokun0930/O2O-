#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的上传测试程序 - 用于验证Dash上传功能是否正常
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

# 创建应用
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1("📤 Dash上传功能测试"),
    html.Hr(),
    
    # 上传组件
    dcc.Upload(
        id='upload-test',
        children=html.Div([
            '🖱️ 点击或拖拽文件到此处上传'
        ]),
        style={
            'width': '100%',
            'height': '150px',
            'lineHeight': '150px',
            'borderWidth': '3px',
            'borderStyle': 'dashed',
            'borderRadius': '10px',
            'textAlign': 'center',
            'borderColor': '#007bff',
            'backgroundColor': '#f0f8ff',
            'cursor': 'pointer',
            'fontSize': '18px',
            'fontWeight': 'bold'
        },
        multiple=False
    ),
    
    # 显示上传状态
    html.Div(id='upload-output', style={
        'marginTop': '30px',
        'padding': '20px',
        'borderRadius': '8px',
        'backgroundColor': '#e9ecef',
        'minHeight': '100px'
    })
])


@app.callback(
    Output('upload-output', 'children'),
    Input('upload-test', 'contents'),
    State('upload-test', 'filename'),
    prevent_initial_call=True
)
def test_upload(contents, filename):
    """测试上传回调"""
    print(f"\n{'='*60}")
    print(f"✅ 上传回调被触发!")
    print(f"   filename: {filename}")
    print(f"   contents length: {len(contents) if contents else 0}")
    print(f"{'='*60}\n")
    
    if contents and filename:
        return html.Div([
            html.H3("✅ 上传成功!", style={'color': '#28a745'}),
            html.Hr(),
            html.P(f"📁 文件名: {filename}", style={'fontSize': '16px'}),
            html.P(f"📊 文件大小: {len(contents)} 字符", style={'fontSize': '14px', 'color': '#666'})
        ])
    else:
        return html.Div([
            html.H3("❌ 上传失败", style={'color': '#dc3545'}),
            html.P("未检测到文件内容")
        ])


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 启动上传测试服务器...")
    print("📊 访问地址: http://localhost:8056")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=8056)
