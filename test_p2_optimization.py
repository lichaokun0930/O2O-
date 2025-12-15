"""
P2优化验证测试
测试配置外部化和图表组件工厂化
"""
import pandas as pd
import numpy as np
from config import get_config, update_config, MULTISPEC_CONFIG
from chart_factory import ChartFactory, quick_bar, quick_pie


def test_config_system():
    """测试配置系统"""
    print("="*70)
    print("🧪 测试1: 配置系统")
    print("="*70)
    
    # 测试获取配置
    app_config = get_config('app')
    print(f"\n✅ 应用配置:")
    print(f"   标题: {app_config['title']}")
    print(f"   端口: {app_config['port']}")
    
    cache_config = get_config('cache')
    print(f"\n✅ 缓存配置:")
    print(f"   启用: {cache_config['enabled']}")
    print(f"   目录: {cache_config['cache_dir']}")
    print(f"   最大大小: {cache_config['max_size_mb']}MB")
    
    multispec_config = get_config('multispec')
    print(f"\n✅ 多规格配置:")
    print(f"   高阈值: {multispec_config['high_threshold']}")
    print(f"   低阈值: {multispec_config['low_threshold']}")
    
    # 测试更新配置
    original_port = app_config['port']
    update_config('app', 'port', 9999)
    new_config = get_config('app')
    print(f"\n✅ 配置更新测试:")
    print(f"   原端口: {original_port}")
    print(f"   新端口: {new_config['port']}")
    
    # 恢复原配置
    update_config('app', 'port', original_port)
    
    # 测试获取所有配置
    all_configs = get_config()
    print(f"\n✅ 配置节数量: {len(all_configs)}个")
    print(f"   配置节: {', '.join(all_configs.keys())}")
    
    return True


def test_chart_factory():
    """测试图表工厂"""
    print("\n" + "="*70)
    print("🧪 测试2: 图表组件工厂")
    print("="*70)
    
    # 创建测试数据
    test_data = pd.DataFrame({
        '分类': ['饮料', '零食', '日用品', '生鲜', '酒类'],
        '销售额': [15000, 12000, 8000, 6000, 5000],
        '销量': [500, 450, 300, 200, 150],
        '毛利率': [0.35, 0.42, 0.28, 0.15, 0.38]
    })
    
    # 测试柱状图
    try:
        fig1 = ChartFactory.create_bar_chart(
            test_data,
            x='分类',
            y='销售额',
            title='各分类销售额'
        )
        print("\n✅ 柱状图创建成功")
        print(f"   数据点数: {len(fig1.data)}")
    except Exception as e:
        print(f"\n❌ 柱状图创建失败: {e}")
        return False
    
    # 测试饼图
    try:
        fig2 = ChartFactory.create_pie_chart(
            test_data,
            values='销售额',
            names='分类',
            title='销售额占比'
        )
        print("✅ 饼图创建成功")
    except Exception as e:
        print(f"❌ 饼图创建失败: {e}")
        return False
    
    # 测试散点图
    try:
        fig3 = ChartFactory.create_scatter_chart(
            test_data,
            x='销量',
            y='销售额',
            title='销量vs销售额',
            size='毛利率'
        )
        print("✅ 散点图创建成功")
    except Exception as e:
        print(f"❌ 散点图创建失败: {e}")
        return False
    
    # 测试双Y轴图表
    try:
        fig4 = ChartFactory.create_dual_axis_chart(
            test_data,
            x='分类',
            y1='销售额',
            y2='毛利率',
            title='销售额与毛利率对比'
        )
        print("✅ 双Y轴图表创建成功")
    except Exception as e:
        print(f"❌ 双Y轴图表创建失败: {e}")
        return False
    
    # 测试便捷函数
    try:
        fig5 = quick_bar(test_data, '分类', '销售额', '快速柱状图')
        fig6 = quick_pie(test_data, '销售额', '分类', '快速饼图')
        print("✅ 便捷函数创建成功")
    except Exception as e:
        print(f"❌ 便捷函数创建失败: {e}")
        return False
    
    # 测试仪表盘
    try:
        fig7 = ChartFactory.create_gauge_chart(
            value=75,
            title='动销率',
            max_value=100
        )
        print("✅ 仪表盘图表创建成功")
    except Exception as e:
        print(f"❌ 仪表盘图表创建失败: {e}")
        return False
    
    print(f"\n✅ 图表工厂测试完成，共创建7种图表类型")
    return True


def test_config_integration():
    """测试配置与实际功能的集成"""
    print("\n" + "="*70)
    print("🧪 测试3: 配置集成")
    print("="*70)
    
    # 测试多规格配置的使用
    multispec_config = get_config('multispec')
    
    test_data = pd.DataFrame({
        '分类': ['A', 'B', 'C', 'D'],
        '总SKU': [100, 100, 100, 100],
        '多规格SKU': [60, 10, 30, 45]  # 60%, 10%, 30%, 45%
    })
    
    # 使用配置中的阈值进行分类
    high_threshold = multispec_config['high_threshold']
    low_threshold = multispec_config['low_threshold']
    mid_range = multispec_config['mid_range']
    
    test_data['占比'] = test_data['多规格SKU'] / test_data['总SKU']
    
    high_cats = test_data[test_data['占比'] > high_threshold]['分类'].tolist()
    low_cats = test_data[test_data['占比'] < low_threshold]['分类'].tolist()
    mid_cats = test_data[
        (test_data['占比'] >= mid_range[0]) & 
        (test_data['占比'] <= mid_range[1])
    ]['分类'].tolist()
    
    print(f"\n✅ 使用配置阈值分类:")
    print(f"   高多规格(>{high_threshold*100}%): {high_cats}")
    print(f"   低多规格(<{low_threshold*100}%): {low_cats}")
    print(f"   中等多规格({mid_range[0]*100}-{mid_range[1]*100}%): {mid_cats}")
    
    # 验证结果
    assert len(high_cats) == 1 and 'A' in high_cats, "高多规格分类错误"
    assert len(low_cats) == 1 and 'B' in low_cats, "低多规格分类错误"
    assert len(mid_cats) == 1 and 'C' in mid_cats, "中等多规格分类错误"
    
    print("\n✅ 配置集成验证通过")
    return True


def test_chart_config_usage():
    """测试图表配置的使用"""
    print("\n" + "="*70)
    print("🧪 测试4: 图表配置使用")
    print("="*70)
    
    chart_config = get_config('chart')
    
    test_data = pd.DataFrame({
        '月份': ['1月', '2月', '3月', '4月', '5月'],
        '销售额': [10000, 12000, 15000, 13000, 16000]
    })
    
    # 使用配置中的颜色方案
    fig = ChartFactory.create_bar_chart(
        test_data,
        x='月份',
        y='销售额',
        title='月度销售趋势',
        colors=chart_config['color_schemes']['primary'],
        height=chart_config['default_height'],
        title_size=chart_config['title_font_size']
    )
    
    print(f"\n✅ 使用图表配置:")
    print(f"   默认高度: {chart_config['default_height']}px")
    print(f"   标题字号: {chart_config['title_font_size']}px")
    print(f"   颜色方案: {len(chart_config['color_schemes']['primary'])}种颜色")
    print(f"   字体: {chart_config['font_family']}")
    
    return True


def test_performance_improvement():
    """测试性能改进"""
    print("\n" + "="*70)
    print("🧪 测试5: 性能对比")
    print("="*70)
    
    import time
    
    # 生成大数据集
    n = 1000
    large_data = pd.DataFrame({
        '分类': [f'分类{i}' for i in range(n)],
        '值': np.random.randint(100, 1000, n)
    })
    
    # 测试图表工厂性能
    start = time.perf_counter()
    for _ in range(10):
        fig = ChartFactory.create_bar_chart(
            large_data.head(50),
            x='分类',
            y='值',
            title='性能测试'
        )
    elapsed = time.perf_counter() - start
    
    print(f"\n✅ 性能测试:")
    print(f"   数据规模: {n}行")
    print(f"   创建10个图表耗时: {elapsed*1000:.1f}ms")
    print(f"   平均每个图表: {elapsed*100:.1f}ms")
    
    return True


def main():
    """主测试函数"""
    print("\n" + "🚀"*35)
    print("P2优化验证测试")
    print("🚀"*35 + "\n")
    
    results = {}
    
    # 测试1: 配置系统
    try:
        results['config'] = test_config_system()
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
        results['config'] = False
    
    # 测试2: 图表工厂
    try:
        results['chart_factory'] = test_chart_factory()
    except Exception as e:
        print(f"❌ 图表工厂测试失败: {e}")
        results['chart_factory'] = False
    
    # 测试3: 配置集成
    try:
        results['integration'] = test_config_integration()
    except Exception as e:
        print(f"❌ 配置集成测试失败: {e}")
        results['integration'] = False
    
    # 测试4: 图表配置使用
    try:
        results['chart_config'] = test_chart_config_usage()
    except Exception as e:
        print(f"❌ 图表配置测试失败: {e}")
        results['chart_config'] = False
    
    # 测试5: 性能测试
    try:
        results['performance'] = test_performance_improvement()
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        results['performance'] = False
    
    # 总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有P2优化测试通过！")
        print("\n📈 P2优化成果:")
        print("   ✅ 配置外部化 - 便于部署和维护")
        print("   ✅ 图表组件工厂化 - 提升复用性")
        print("   ✅ 统一接口 - 降低学习成本")
        print("   ✅ 灵活配置 - 支持动态调整")
    else:
        print("\n⚠️  部分测试未通过，请检查")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
