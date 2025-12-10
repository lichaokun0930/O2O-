# -*- coding: utf-8 -*-
"""
Panel AI快速测试脚本
不启动完整Dashboard,直接测试Panel AI分析功能
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from ai_panel_analyzers import (
    KPIPanelAnalyzer,
    CategoryPanelAnalyzer,
    PricePanelAnalyzer,
    PromoPanelAnalyzer,
    MasterAnalyzer
)


def load_sample_data():
    """加载样本数据"""
    print("📂 加载测试数据...")
    
    # 模拟collect_dashboard_data返回的数据结构
    sample_data = {
        'kpi': {
            '总SKU数(含规格)': 258,
            '多规格SKU总数': 75,
            '动销SKU数': 198,
            '滞销SKU数': 60,
            '总销售额(去重后)': 125430.5,
            '平均单价': 18.6,
            '客单价': 45.2,
            '总库存': 1560,
            '库存周转率': 8.5,
            '动销率': 76.7,
            '滞销率': 23.3
        },
        'category': [
            {'一级分类': '饮料', '售价销售额': 42350.5, '美团一级分类去重SKU数(口径同动销率)': 65, '美团一级分类动销率(类内)': 82.3, '美团一级分类折扣': 9.2},
            {'一级分类': '休闲食品', '售价销售额': 38920.3, '美团一级分类去重SKU数(口径同动销率)': 48, '美团一级分类动销率(类内)': 75.0, '美团一级分类折扣': 9.5},
            {'一级分类': '乳制品', '售价销售额': 24160.2, '美团一级分类去重SKU数(口径同动销率)': 32, '美团一级分类动销率(类内)': 68.8, '美团一级分类折扣': 9.8},
        ],
        'price': [
            {'price_band': '0-5元', 'SKU数量': 45, '销售额': 8920.5, '销售额占比': 7.1},
            {'price_band': '5-10元', 'SKU数量': 78, '销售额': 35420.3, '销售额占比': 28.2},
            {'price_band': '10-15元', 'SKU数量': 62, '销售额': 42350.2, '销售额占比': 33.8},
            {'price_band': '15-20元', 'SKU数量': 38, '销售额': 24160.5, '销售额占比': 19.3},
            {'price_band': '20+元', 'SKU数量': 35, '销售额': 14579.0, '销售额占比': 11.6},
        ],
        'promo': [
            {'分类': '饮料', '促销强度': 88.9, '折扣力度': 9.2},
            {'分类': '休闲食品', '促销强度': 55.6, '折扣力度': 9.5},
            {'分类': '乳制品', '促销强度': 22.2, '折扣力度': 9.8},
        ],
        'meta': {
            '总分类数': 28,
            '筛选分类': '全部',
            '分析时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'TOP3销售额占比': 84.2,
            '健康分类数': 3,
            '问题分类数': 25
        }
    }
    
    print("✅ 数据加载完成")
    return sample_data


def test_kpi_analyzer(data):
    """测试KPI Panel分析"""
    print("\n" + "=" * 60)
    print("🧪 测试KPI Panel Analyzer")
    print("=" * 60)
    
    analyzer = KPIPanelAnalyzer()
    print("📊 正在分析KPI看板数据...")
    
    try:
        result = analyzer.analyze(data)
        print("\n✅ 分析完成!\n")
        print(result)
        return result
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_category_analyzer(data):
    """测试分类Panel分析"""
    print("\n" + "=" * 60)
    print("🧪 测试Category Panel Analyzer")
    print("=" * 60)
    
    analyzer = CategoryPanelAnalyzer()
    print("📦 正在分析分类看板数据...")
    
    try:
        result = analyzer.analyze(data)
        print("\n✅ 分析完成!\n")
        print(result)
        return result
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_price_analyzer(data):
    """测试价格带Panel分析"""
    print("\n" + "=" * 60)
    print("🧪 测试Price Panel Analyzer")
    print("=" * 60)
    
    analyzer = PricePanelAnalyzer()
    print("💰 正在分析价格带看板数据...")
    
    try:
        result = analyzer.analyze(data)
        print("\n✅ 分析完成!\n")
        print(result)
        return result
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_promo_analyzer(data):
    """测试促销Panel分析"""
    print("\n" + "=" * 60)
    print("🧪 测试Promo Panel Analyzer")
    print("=" * 60)
    
    analyzer = PromoPanelAnalyzer()
    print("🎯 正在分析促销看板数据...")
    
    try:
        result = analyzer.analyze(data)
        print("\n✅ 分析完成!\n")
        print(result)
        return result
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_master_analyzer(data, panel_insights):
    """测试主AI综合诊断"""
    print("\n" + "=" * 60)
    print("🧪 测试Master AI Analyzer")
    print("=" * 60)
    
    analyzer = MasterAnalyzer()
    print("🧠 正在生成综合诊断报告...")
    
    try:
        result = analyzer.analyze(data, panel_insights)
        print("\n✅ 分析完成!\n")
        print(result)
        return result
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试流程"""
    print("\n" + "🚀" * 30)
    print("Panel AI功能快速测试")
    print("🚀" * 30 + "\n")
    
    # 加载数据
    data = load_sample_data()
    
    # 存储各Panel的分析结果
    panel_insights = {}
    
    print("\n请选择测试模式:")
    print("1. 测试单个Panel AI (KPI)")
    print("2. 测试单个Panel AI (分类)")
    print("3. 测试单个Panel AI (价格带)")
    print("4. 测试单个Panel AI (促销)")
    print("5. 测试所有Panel AI + 主AI综合诊断 (完整流程)")
    print("6. 仅测试主AI (需先有Panel分析结果)")
    
    choice = input("\n请输入选项 (1-6, 默认5): ").strip() or "5"
    
    if choice == "1":
        test_kpi_analyzer(data)
    elif choice == "2":
        test_category_analyzer(data)
    elif choice == "3":
        test_price_analyzer(data)
    elif choice == "4":
        test_promo_analyzer(data)
    elif choice == "5":
        # 完整流程
        print("\n🎯 开始完整测试流程...")
        
        kpi_result = test_kpi_analyzer(data)
        if kpi_result:
            panel_insights['KPI看板'] = kpi_result
        
        cat_result = test_category_analyzer(data)
        if cat_result:
            panel_insights['分类看板'] = cat_result
        
        price_result = test_price_analyzer(data)
        if price_result:
            panel_insights['价格带看板'] = price_result
        
        promo_result = test_promo_analyzer(data)
        if promo_result:
            panel_insights['促销看板'] = promo_result
        
        if panel_insights:
            test_master_analyzer(data, panel_insights)
    elif choice == "6":
        # 仅主AI (需要手动构建panel_insights)
        print("\n⚠️  警告: 主AI需要Panel分析结果,使用模拟数据...")
        panel_insights = {
            'KPI看板': "KPI看板分析结果 (模拟)",
            '分类看板': "分类看板分析结果 (模拟)",
        }
        test_master_analyzer(data, panel_insights)
    else:
        print("❌ 无效选项,退出")
        return
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    
    print("\n💡 提示:")
    print("- 如需在Dashboard中使用,请运行: python dashboard_v2.py")
    print("- 各Panel AI按钮位于对应看板区域")
    print("- 主AI按钮位于页面底部")


if __name__ == "__main__":
    main()
