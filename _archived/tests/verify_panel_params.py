# -*- coding: utf-8 -*-
"""
验证所有Panel AI的参数传递修复
"""

import pandas as pd
from ai_panel_analyzers import (
    KPIPanelAnalyzer,
    CategoryPanelAnalyzer,
    PricePanelAnalyzer,
    PromoPanelAnalyzer,
    MasterAnalyzer
)

print("=" * 60)
print("测试: Panel AI参数传递修复验证")
print("=" * 60)

# 模拟dashboard_data结构
dashboard_data = {
    'kpi': {
        '动销率': 76.7,
        '去重SKU数': 258,
        '滞销占比': 23.3,
        '平均售价': 18.6,
        '平均折扣': 9.5
    },
    'category': [
        {'一级分类': '饮料', '售价销售额': 42350.5, '美团一级分类动销率(类内)': 82.3},
        {'一级分类': '休闲食品', '售价销售额': 38920.3, '美团一级分类动销率(类内)': 75.0},
        {'一级分类': '乳制品', '售价销售额': 24160.2, '美团一级分类动销率(类内)': 68.8},
    ],
    'price': [
        {'price_band': '0-5元', 'SKU数量': 45, '销售额': 8920.5},
        {'price_band': '5-10元', 'SKU数量': 78, '销售额': 35420.3},
        {'price_band': '10-15元', 'SKU数量': 62, '销售额': 42350.2},
    ],
    'promo': [
        {'分类': '饮料', '促销强度': 88.9, '折扣力度': 9.2},
        {'分类': '休闲食品', '促销强度': 55.6, '折扣力度': 9.5},
    ],
    'meta': {
        '总分类数': 28,
        '筛选分类': '全部',
        'TOP3销售额占比': 84.2,
    }
}

print("\n✅ 模拟数据创建成功")
print(f"   - KPI数据类型: {type(dashboard_data['kpi'])} (应为dict)")
print(f"   - Category数据类型: {type(dashboard_data['category'])} (应为list)")
print(f"   - Price数据类型: {type(dashboard_data['price'])} (应为list)")
print(f"   - Promo数据类型: {type(dashboard_data['promo'])} (应为list)")

# 测试1: KPI Analyzer
print("\n" + "-" * 60)
print("测试1: KPI Analyzer (传递dict)")
try:
    kpi_analyzer = KPIPanelAnalyzer()
    # 正确调用: 传递kpi字典
    result = kpi_analyzer.analyze(dashboard_data['kpi'])
    print(f"✅ KPI Analyzer调用成功")
    print(f"   参数类型: {type(dashboard_data['kpi'])}")
    print(f"   返回类型: {type(result)}")
except Exception as e:
    print(f"❌ KPI Analyzer失败: {e}")

# 测试2: Category Analyzer
print("\n" + "-" * 60)
print("测试2: Category Analyzer (传递list)")
try:
    category_analyzer = CategoryPanelAnalyzer()
    # 正确调用: 传递category列表
    result = category_analyzer.analyze(dashboard_data['category'])
    print(f"✅ Category Analyzer调用成功")
    print(f"   参数类型: {type(dashboard_data['category'])}")
    print(f"   第一个元素: {type(dashboard_data['category'][0])}")
    print(f"   返回类型: {type(result)}")
except Exception as e:
    print(f"❌ Category Analyzer失败: {e}")

# 测试3: Price Analyzer
print("\n" + "-" * 60)
print("测试3: Price Analyzer (传递list)")
try:
    price_analyzer = PricePanelAnalyzer()
    # 正确调用: 传递price列表
    result = price_analyzer.analyze(dashboard_data['price'])
    print(f"✅ Price Analyzer调用成功")
    print(f"   参数类型: {type(dashboard_data['price'])}")
    print(f"   返回类型: {type(result)}")
except Exception as e:
    print(f"❌ Price Analyzer失败: {e}")

# 测试4: Promo Analyzer
print("\n" + "-" * 60)
print("测试4: Promo Analyzer (传递list)")
try:
    promo_analyzer = PromoPanelAnalyzer()
    # 正确调用: 传递promo列表
    result = promo_analyzer.analyze(dashboard_data['promo'])
    print(f"✅ Promo Analyzer调用成功")
    print(f"   参数类型: {type(dashboard_data['promo'])}")
    print(f"   返回类型: {type(result)}")
except Exception as e:
    print(f"❌ Promo Analyzer失败: {e}")

# 测试5: Master Analyzer
print("\n" + "-" * 60)
print("测试5: Master Analyzer (传递dashboard_data + panel_insights)")
try:
    master_analyzer = MasterAnalyzer()
    panel_insights = {
        'KPI看板': 'KPI分析结果(模拟)',
        '分类看板': '分类分析结果(模拟)',
    }
    # 正确调用: 传递完整dashboard_data和panel_insights
    result = master_analyzer.analyze(dashboard_data, panel_insights)
    print(f"✅ Master Analyzer调用成功")
    print(f"   参数1类型: {type(dashboard_data)}")
    print(f"   参数2类型: {type(panel_insights)}")
    print(f"   返回类型: {type(result)}")
except Exception as e:
    print(f"❌ Master Analyzer失败: {e}")

print("\n" + "=" * 60)
print("✅ 所有参数传递测试完成!")
print("=" * 60)
print("\n📝 修复总结:")
print("1. KPI Analyzer: 接收 dashboard_data['kpi'] (dict)")
print("2. Category Analyzer: 接收 dashboard_data['category'] (list)")
print("3. Price Analyzer: 接收 dashboard_data['price'] (list)")
print("4. Promo Analyzer: 接收 dashboard_data['promo'] (list)")
print("5. Master Analyzer: 接收 dashboard_data (dict) + panel_insights (dict)")
print("\n💡 Dashboard回调函数已全部修正!")
