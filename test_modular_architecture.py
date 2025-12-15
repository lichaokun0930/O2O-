"""
模块化架构测试 - P2优化
验证模块化重构后的功能完整性
"""
import sys
import pandas as pd
import numpy as np

# 测试模块导入
def test_module_imports():
    """测试模块导入"""
    print("="*70)
    print("🧪 测试1: 模块导入")
    print("="*70)
    
    try:
        # 数据模块
        from modules.data import DataLoader, DataCache
        print("✅ 数据模块导入成功: DataLoader, DataCache")
        
        # 工具模块
        from modules.utils import setup_logger, format_number, format_currency
        from modules.utils import calculate_growth_rate, calculate_ratio
        print("✅ 工具模块导入成功: logger, formatters, calculators")
        
        # 图表模块
        from modules.charts import ChartFactory, MultispecChartBuilder
        print("✅ 图表模块导入成功: ChartFactory, MultispecChartBuilder")
        
        # 配置模块
        from config import get_config
        print("✅ 配置模块导入成功: get_config")
        
        return True
    except Exception as e:
        print(f"❌ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_module():
    """测试数据模块"""
    print("\n" + "="*70)
    print("🧪 测试2: 数据模块功能")
    print("="*70)
    
    try:
        from modules.data import DataLoader, DataCache
        
        # 测试缓存
        cache = DataCache('./cache')
        print(f"✅ 缓存初始化成功")
        print(f"   缓存目录: {cache.cache_dir}")
        print(f"   缓存文件数: {cache.get_cache_count()}")
        print(f"   缓存大小: {cache.get_cache_size():.2f}MB")
        
        # 测试数据加载
        loader = DataLoader("reports/示例门店_分析报告.xlsx", use_cache=True)
        print(f"\n✅ 数据加载成功")
        
        # 测试KPI摘要
        kpi_summary = loader.get_kpi_summary()
        print(f"\n✅ KPI摘要获取成功")
        print(f"   门店: {kpi_summary.get('门店', 'N/A')}")
        print(f"   总SKU数: {kpi_summary.get('总SKU数(含规格)', 0)}")
        print(f"   动销率: {kpi_summary.get('动销率', 0):.1%}")
        
        # 测试分类数据
        category_data = loader.get_category_data()
        print(f"\n✅ 分类数据获取成功: {category_data.shape}")
        
        return True
    except Exception as e:
        print(f"❌ 数据模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_utils_module():
    """测试工具模块"""
    print("\n" + "="*70)
    print("🧪 测试3: 工具模块功能")
    print("="*70)
    
    try:
        from modules.utils import (
            format_number, format_currency, format_percent,
            calculate_growth_rate, calculate_ratio
        )
        
        # 测试格式化
        print("✅ 格式化工具:")
        print(f"   数字: {format_number(1234567.89)}")
        print(f"   货币: {format_currency(1234567.89)}")
        print(f"   百分比: {format_percent(0.7523, multiply_100=True)}")
        
        # 测试计算
        print("\n✅ 计算工具:")
        growth = calculate_growth_rate(120, 100)
        print(f"   增长率: {growth:.1%}")
        
        ratio = calculate_ratio(75, 100)
        print(f"   比率: {ratio:.1%}")
        
        return True
    except Exception as e:
        print(f"❌ 工具模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_charts_module():
    """测试图表模块"""
    print("\n" + "="*70)
    print("🧪 测试4: 图表模块功能")
    print("="*70)
    
    try:
        from modules.charts import ChartFactory, MultispecChartBuilder
        from modules.data import DataLoader
        
        # 创建测试数据
        test_data = pd.DataFrame({
            '分类': ['饮料', '零食', '日用品'],
            '销售额': [15000, 12000, 8000]
        })
        
        # 测试图表工厂
        fig1 = ChartFactory.create_bar_chart(
            test_data, x='分类', y='销售额', title='测试柱状图'
        )
        print("✅ 图表工厂创建柱状图成功")
        
        # 测试多规格图表
        loader = DataLoader("reports/示例门店_分析报告.xlsx", use_cache=True)
        category_data = loader.get_category_data()
        
        if not category_data.empty:
            fig2 = MultispecChartBuilder.create_supply_analysis_chart(category_data)
            print("✅ 多规格图表创建成功")
            
            insights = MultispecChartBuilder.generate_insights(category_data)
            print(f"✅ 多规格洞察生成成功: {len(insights)}条")
        
        return True
    except Exception as e:
        print(f"❌ 图表模块测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """测试模块集成"""
    print("\n" + "="*70)
    print("🧪 测试5: 模块集成")
    print("="*70)
    
    try:
        from modules.data import DataLoader
        from modules.charts import MultispecChartBuilder
        from modules.utils import format_number, format_percent
        from config import get_config
        
        # 加载数据
        loader = DataLoader("reports/示例门店_分析报告.xlsx", use_cache=True)
        category_data = loader.get_category_data()
        
        # 生成洞察
        insights = MultispecChartBuilder.generate_insights(category_data)
        
        # 格式化输出
        print("\n✅ 集成测试 - 多规格分析:")
        for i, insight in enumerate(insights, 1):
            print(f"   {i}. {insight['icon']} {insight['text']}")
        
        # 使用配置
        config = get_config('multispec')
        print(f"\n✅ 配置集成:")
        print(f"   高阈值: {format_percent(config['high_threshold']*100)}")
        print(f"   低阈值: {format_percent(config['low_threshold']*100)}")
        
        return True
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """测试性能"""
    print("\n" + "="*70)
    print("🧪 测试6: 性能对比")
    print("="*70)
    
    try:
        import time
        from modules.data import DataLoader
        from modules.charts import MultispecChartBuilder
        
        # 测试数据加载性能
        start = time.perf_counter()
        loader = DataLoader("reports/示例门店_分析报告.xlsx", use_cache=True)
        elapsed = time.perf_counter() - start
        print(f"✅ 数据加载耗时: {elapsed*1000:.1f}ms")
        
        # 测试多规格分析性能
        category_data = loader.get_category_data()
        
        start = time.perf_counter()
        for _ in range(100):
            insights = MultispecChartBuilder.generate_insights(category_data)
        elapsed = time.perf_counter() - start
        print(f"✅ 多规格分析耗时（100次平均）: {elapsed*10:.2f}ms")
        
        return True
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "🚀"*35)
    print("模块化架构验证测试")
    print("🚀"*35 + "\n")
    
    results = {}
    
    # 测试1: 模块导入
    results['imports'] = test_module_imports()
    
    # 测试2: 数据模块
    results['data'] = test_data_module()
    
    # 测试3: 工具模块
    results['utils'] = test_utils_module()
    
    # 测试4: 图表模块
    results['charts'] = test_charts_module()
    
    # 测试5: 模块集成
    results['integration'] = test_integration()
    
    # 测试6: 性能
    results['performance'] = test_performance()
    
    # 总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有模块化测试通过！")
        print("\n📈 模块化架构优势:")
        print("   ✅ 代码组织清晰 - 按功能分模块")
        print("   ✅ 职责分离 - 每个模块专注单一功能")
        print("   ✅ 易于维护 - 修改影响范围小")
        print("   ✅ 便于测试 - 可独立测试每个模块")
        print("   ✅ 提升复用 - 模块可在其他项目中复用")
    else:
        print("\n⚠️  部分测试未通过，请检查")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
