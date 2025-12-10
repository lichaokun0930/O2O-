# -*- coding: utf-8 -*-
"""
Panel AI集成测试脚本
验证dashboard_v2.py中的Panel AI集成是否正常工作
"""

import sys
from pathlib import Path

def test_imports():
    """测试所有导入是否正常"""
    print("=" * 60)
    print("测试1: 验证Panel AI模块导入")
    print("=" * 60)
    
    try:
        from ai_panel_analyzers import (
            KPIPanelAnalyzer,
            CategoryPanelAnalyzer,
            PricePanelAnalyzer,
            PromoPanelAnalyzer,
            MasterAnalyzer
        )
        print("✅ ai_panel_analyzers 模块导入成功")
        print(f"   - KPIPanelAnalyzer: {KPIPanelAnalyzer}")
        print(f"   - CategoryPanelAnalyzer: {CategoryPanelAnalyzer}")
        print(f"   - PricePanelAnalyzer: {PricePanelAnalyzer}")
        print(f"   - PromoPanelAnalyzer: {PromoPanelAnalyzer}")
        print(f"   - MasterAnalyzer: {MasterAnalyzer}")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False


def test_analyzer_instantiation():
    """测试分析器实例化"""
    print("\n" + "=" * 60)
    print("测试2: 验证分析器实例化")
    print("=" * 60)
    
    try:
        from ai_panel_analyzers import (
            KPIPanelAnalyzer,
            CategoryPanelAnalyzer,
            PricePanelAnalyzer,
            PromoPanelAnalyzer,
            MasterAnalyzer
        )
        
        # 实例化各分析器
        kpi_analyzer = KPIPanelAnalyzer()
        print(f"✅ KPI分析器实例化成功: {type(kpi_analyzer).__name__}")
        
        category_analyzer = CategoryPanelAnalyzer()
        print(f"✅ 分类分析器实例化成功: {type(category_analyzer).__name__}")
        
        price_analyzer = PricePanelAnalyzer()
        print(f"✅ 价格带分析器实例化成功: {type(price_analyzer).__name__}")
        
        promo_analyzer = PromoPanelAnalyzer()
        print(f"✅ 促销分析器实例化成功: {type(promo_analyzer).__name__}")
        
        master_analyzer = MasterAnalyzer()
        print(f"✅ 主AI分析器实例化成功: {type(master_analyzer).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ 实例化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dashboard_imports():
    """测试dashboard_v2.py是否能正确导入Panel AI"""
    print("\n" + "=" * 60)
    print("测试3: 验证dashboard_v2.py导入Panel AI")
    print("=" * 60)
    
    try:
        # 只导入模块,不运行app
        import importlib.util
        
        dashboard_path = Path(__file__).parent / "dashboard_v2.py"
        spec = importlib.util.spec_from_file_location("dashboard_v2", dashboard_path)
        dashboard_module = importlib.util.module_from_spec(spec)
        
        # 尝试加载模块(这会执行顶层代码)
        print("   正在加载dashboard_v2.py...")
        spec.loader.exec_module(dashboard_module)
        
        # 验证是否包含我们的分析器
        if hasattr(dashboard_module, 'KPIPanelAnalyzer'):
            print("✅ dashboard_v2.py 成功导入KPIPanelAnalyzer")
        else:
            print("⚠️  dashboard_v2.py 未找到KPIPanelAnalyzer (可能正常,取决于导入方式)")
        
        print("✅ dashboard_v2.py 加载成功,未报错")
        return True
        
    except Exception as e:
        print(f"❌ dashboard_v2.py加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_callback_structure():
    """测试回调函数结构"""
    print("\n" + "=" * 60)
    print("测试4: 验证回调函数结构")
    print("=" * 60)
    
    try:
        # 读取dashboard_v2.py源代码
        dashboard_path = Path(__file__).parent / "dashboard_v2.py"
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否存在所需的回调函数
        callbacks_to_check = [
            "def analyze_kpi_panel",
            "def analyze_category_panel",
            "def analyze_price_panel",
            "def analyze_promo_panel",
            "def analyze_master_ai"
        ]
        
        found_callbacks = []
        missing_callbacks = []
        
        for callback_name in callbacks_to_check:
            if callback_name in content:
                found_callbacks.append(callback_name)
                print(f"✅ 找到回调函数: {callback_name}")
            else:
                missing_callbacks.append(callback_name)
                print(f"❌ 缺失回调函数: {callback_name}")
        
        # 检查UI组件ID
        ui_ids = [
            "kpi-ai-analyze-btn",
            "category-ai-analyze-btn",
            "price-ai-analyze-btn",
            "promo-ai-analyze-btn",
            "master-ai-analyze-btn",
            "kpi-ai-insight",
            "category-ai-insight",
            "price-ai-insight",
            "promo-ai-insight",
            "master-ai-insight"
        ]
        
        print("\n   UI组件ID检查:")
        for ui_id in ui_ids:
            if ui_id in content:
                print(f"   ✅ {ui_id}")
            else:
                print(f"   ❌ {ui_id}")
        
        return len(missing_callbacks) == 0
        
    except Exception as e:
        print(f"❌ 结构检查失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "🚀" * 30)
    print("Panel AI集成测试开始")
    print("🚀" * 30 + "\n")
    
    results = []
    
    # 测试1: 导入
    results.append(("模块导入", test_imports()))
    
    # 测试2: 实例化
    results.append(("分析器实例化", test_analyzer_instantiation()))
    
    # 测试3: Dashboard导入
    results.append(("Dashboard导入", test_dashboard_imports()))
    
    # 测试4: 回调结构
    results.append(("回调函数结构", test_callback_structure()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:20s}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过! Panel AI集成完成!")
        print("\n下一步:")
        print("1. 启动dashboard_v2.py")
        print("2. 点击各看板的'🤖 AI智能分析'按钮")
        print("3. 查看Panel级AI洞察")
        print("4. 点击'🧠 主AI综合洞察'按钮生成综合诊断")
    else:
        print("\n⚠️  部分测试失败,请检查错误信息")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
