# -*- coding: utf-8 -*-
"""
调试collect_dashboard_data返回的数据结构
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 模拟dashboard_v2.py的数据加载
from dashboard_v2 import collect_dashboard_data

print("=" * 60)
print("调试: collect_dashboard_data()返回的数据结构")
print("=" * 60)

try:
    # 调用数据收集函数（不筛选分类）
    dashboard_data = collect_dashboard_data(selected_categories=None)
    
    print("\n✅ 数据收集成功!")
    print(f"\n返回的字典键: {list(dashboard_data.keys())}")
    
    # 检查KPI数据
    print("\n" + "-" * 60)
    print("📊 KPI数据:")
    print(f"   类型: {type(dashboard_data.get('kpi'))}")
    print(f"   长度: {len(dashboard_data.get('kpi', {}))}")
    if dashboard_data.get('kpi'):
        print(f"   字段列表:")
        for key, value in list(dashboard_data['kpi'].items())[:5]:  # 只显示前5个
            print(f"      - {key}: {value} ({type(value).__name__})")
        if len(dashboard_data['kpi']) > 5:
            print(f"      ... (共{len(dashboard_data['kpi'])}个字段)")
    
    # 检查Category数据
    print("\n" + "-" * 60)
    print("📦 Category数据:")
    print(f"   类型: {type(dashboard_data.get('category'))}")
    print(f"   长度: {len(dashboard_data.get('category', []))}")
    if dashboard_data.get('category'):
        print(f"   第一个元素:")
        first_cat = dashboard_data['category'][0]
        for key, value in first_cat.items():
            print(f"      - {key}: {value}")
    
    # 检查Price数据
    print("\n" + "-" * 60)
    print("💰 Price数据:")
    print(f"   类型: {type(dashboard_data.get('price'))}")
    print(f"   长度: {len(dashboard_data.get('price', []))}")
    if dashboard_data.get('price'):
        print(f"   第一个元素:")
        first_price = dashboard_data['price'][0]
        for key, value in first_price.items():
            print(f"      - {key}: {value}")
    
    # 检查Promo数据
    print("\n" + "-" * 60)
    print("🎯 Promo数据:")
    print(f"   类型: {type(dashboard_data.get('promo'))}")
    print(f"   长度: {len(dashboard_data.get('promo', []))}")
    if dashboard_data.get('promo'):
        print(f"   第一个元素:")
        first_promo = dashboard_data['promo'][0]
        for key, value in first_promo.items():
            print(f"      - {key}: {value}")
    
    # 检查Meta数据
    print("\n" + "-" * 60)
    print("ℹ️  Meta数据:")
    print(f"   类型: {type(dashboard_data.get('meta'))}")
    if dashboard_data.get('meta'):
        for key, value in dashboard_data['meta'].items():
            print(f"      - {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ 数据结构检查完成!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
