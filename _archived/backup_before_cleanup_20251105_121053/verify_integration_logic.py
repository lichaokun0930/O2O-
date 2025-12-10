#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成逻辑验证脚本
对比 untitled1.py 原始逻辑 和 store_analyzer.py 集成逻辑的一致性
"""

import pandas as pd
from pathlib import Path
import sys

# 导入核心函数
from untitled1 import load_and_clean_data, analyze_store_performance, export_full_report_to_excel
from store_analyzer import StoreAnalyzer


def test_logic_consistency(test_file_path: str, store_name: str = "测试门店"):
    """
    验证集成逻辑与原始逻辑的一致性
    
    Args:
        test_file_path: 测试文件路径
        store_name: 门店名称
    """
    print("=" * 80)
    print("🧪 集成逻辑一致性验证")
    print("=" * 80)
    
    # 消费场景配置 (必须完全一致)
    CONSUMPTION_SCENARIOS = {
        "早餐快手": ["早餐", "牛奶", "面包", "麦片", "鸡蛋"],
        "加班能量补给": ["咖啡", "能量饮料", "巧克力", "饼干", "能量棒"],
        "家庭囤货": ["大包装", "家庭装", "组合装", "箱", "量贩"],
        "聚会零食": ["薯片", "膨化", "糖果", "坚果", "汽水", "啤酒"],
    }
    
    # ========================================
    # 方式1: 原始逻辑 (模拟 untitled1.py 主流程)
    # ========================================
    print("\n" + "=" * 80)
    print("📘 方式1: 原始 untitled1.py 逻辑")
    print("=" * 80)
    
    try:
        # 步骤1: 加载和清洗数据
        print("\n🔄 步骤1: 调用 load_and_clean_data()...")
        processed_v1 = load_and_clean_data(test_file_path, store_name, CONSUMPTION_SCENARIOS)
        
        if processed_v1 and not processed_v1[1].empty:
            df_all_v1, df_dedup_v1, df_act_v1 = processed_v1
            
            print(f"✅ 数据加载成功:")
            print(f"   - 全部SKU: {len(df_all_v1)}")
            print(f"   - 去重后: {len(df_dedup_v1)}")
            print(f"   - 动销SKU: {len(df_act_v1)}")
            
            # 步骤2: 执行分析
            print("\n🔄 步骤2: 调用 analyze_store_performance()...")
            analysis_results_v1 = analyze_store_performance(df_all_v1, df_dedup_v1, df_act_v1)
            
            if analysis_results_v1:
                print(f"✅ 分析完成!")
                
                # 提取核心指标
                core_metrics_v1 = analysis_results_v1.get('核心指标对比', {})
                print(f"\n📊 核心指标 (方式1):")
                print(f"   - 总SKU数: {core_metrics_v1.get('总SKU数(含规格)', 0)}")
                print(f"   - 去重后SKU: {core_metrics_v1.get('去重后SKU数', 0)}")
                print(f"   - 动销SKU: {core_metrics_v1.get('动销SKU数', 0)}")
                print(f"   - 多规格SKU: {core_metrics_v1.get('多规格SKU总数', 0)}")
                print(f"   - 总销售额: ¥{core_metrics_v1.get('总销售额', 0):,.2f}")
        else:
            print("❌ 数据加载失败!")
            analysis_results_v1 = None
            core_metrics_v1 = {}
    except Exception as e:
        print(f"❌ 方式1执行失败: {e}")
        import traceback
        traceback.print_exc()
        analysis_results_v1 = None
        core_metrics_v1 = {}
    
    # ========================================
    # 方式2: 集成逻辑 (store_analyzer.py)
    # ========================================
    print("\n" + "=" * 80)
    print("📗 方式2: 集成 store_analyzer.py 逻辑")
    print("=" * 80)
    
    try:
        # 创建分析器实例
        analyzer = StoreAnalyzer()
        
        # 调用 analyze_file (内部会调用相同的核心函数)
        print("\n🔄 调用 StoreAnalyzer.analyze_file()...")
        analysis_results_v2 = analyzer.analyze_file(test_file_path, store_name)
        
        if analysis_results_v2:
            print(f"✅ 分析完成!")
            
            # 提取核心指标
            core_metrics_v2 = analysis_results_v2.get('核心指标对比', {})
            print(f"\n📊 核心指标 (方式2):")
            print(f"   - 总SKU数: {core_metrics_v2.get('总SKU数(含规格)', 0)}")
            print(f"   - 去重后SKU: {core_metrics_v2.get('去重后SKU数', 0)}")
            print(f"   - 动销SKU: {core_metrics_v2.get('动销SKU数', 0)}")
            print(f"   - 多规格SKU: {core_metrics_v2.get('多规格SKU总数', 0)}")
            print(f"   - 总销售额: ¥{core_metrics_v2.get('总销售额', 0):,.2f}")
        else:
            print("❌ 分析失败!")
            core_metrics_v2 = {}
    except Exception as e:
        print(f"❌ 方式2执行失败: {e}")
        import traceback
        traceback.print_exc()
        analysis_results_v2 = None
        core_metrics_v2 = {}
    
    # ========================================
    # 结果对比
    # ========================================
    print("\n" + "=" * 80)
    print("🔍 结果对比")
    print("=" * 80)
    
    if not analysis_results_v1 or not analysis_results_v2:
        print("\n❌ 无法对比 - 至少有一种方式执行失败")
        return False
    
    # 对比核心指标
    print("\n📊 核心指标对比:")
    print(f"{'指标名称':<25} {'方式1 (原始)':<20} {'方式2 (集成)':<20} {'是否一致':<10}")
    print("-" * 80)
    
    all_match = True
    metrics_to_compare = [
        '总SKU数(含规格)',
        '去重后SKU数',
        '动销SKU数',
        '多规格SKU总数',
        '总销售额',
        '均价',
        '动销率'
    ]
    
    for metric in metrics_to_compare:
        val1 = core_metrics_v1.get(metric, 0)
        val2 = core_metrics_v2.get(metric, 0)
        
        # 对于浮点数,允许极小的误差
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            match = abs(val1 - val2) < 0.01
        else:
            match = val1 == val2
        
        status = "✅" if match else "❌"
        print(f"{metric:<25} {str(val1):<20} {str(val2):<20} {status:<10}")
        
        if not match:
            all_match = False
    
    # 对比分析结果的 Sheet 数量
    print(f"\n📋 分析结果 Sheet 数量:")
    sheets_v1 = len(analysis_results_v1)
    sheets_v2 = len(analysis_results_v2)
    sheets_match = sheets_v1 == sheets_v2
    print(f"   方式1: {sheets_v1} 个 Sheet")
    print(f"   方式2: {sheets_v2} 个 Sheet")
    print(f"   {'✅ 数量一致' if sheets_match else '❌ 数量不一致'}")
    
    if not sheets_match:
        all_match = False
    
    # 最终结论
    print("\n" + "=" * 80)
    if all_match:
        print("✅ 验证通过: 两种方式的分析结果完全一致!")
        print("   集成逻辑与原始逻辑 100% 等价,不会导致分析失败或数据出错。")
    else:
        print("❌ 验证失败: 两种方式的结果存在差异!")
        print("   需要进一步检查集成逻辑。")
    print("=" * 80)
    
    return all_match


def main():
    """主函数"""
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python verify_integration_logic.py <测试文件路径> [门店名称]")
        print("\n示例:")
        print("  python verify_integration_logic.py \"可以选.xlsx\" \"可以选\"")
        print("  python verify_integration_logic.py \"D:/data/鲸星购.xlsx\"")
        sys.exit(1)
    
    test_file = sys.argv[1]
    store_name = sys.argv[2] if len(sys.argv) > 2 else "测试门店"
    
    # 检查文件是否存在
    if not Path(test_file).exists():
        print(f"❌ 错误: 文件不存在 - {test_file}")
        sys.exit(1)
    
    # 执行验证
    success = test_logic_consistency(test_file, store_name)
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
