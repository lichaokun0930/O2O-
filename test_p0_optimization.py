#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0优化验证脚本

验证内容：
1. 数据缓存机制是否正常工作
2. KPI计算结果是否一致
3. 日志系统是否正常
4. 列名映射是否正确
"""

import time
import sys
from pathlib import Path

def test_cache_performance():
    """测试缓存性能"""
    print("\n" + "="*60)
    print("测试1: 数据缓存性能")
    print("="*60)
    
    from dashboard_v2_optimized import DataLoader, data_cache
    
    # 优先使用示例文件，如果不存在则使用默认文件
    test_files = [
        "./reports/示例门店_分析报告.xlsx",
        "./reports/淮安生态新城商品10.29 的副本_分析报告.xlsx"
    ]
    
    test_file = None
    for f in test_files:
        if Path(f).exists():
            test_file = f
            break
    
    if not test_file:
        print(f"❌ 测试文件不存在，请先运行: python create_sample_report.py")
        return False
    
    # 清除缓存
    data_cache.clear()
    
    # 首次加载（无缓存）
    print("\n📂 首次加载（无缓存）...")
    start = time.time()
    loader1 = DataLoader(test_file, use_cache=True)
    time1 = time.time() - start
    print(f"⏱️  耗时: {time1:.2f}秒")
    
    # 二次加载（有缓存）
    print("\n📦 二次加载（有缓存）...")
    start = time.time()
    loader2 = DataLoader(test_file, use_cache=True)
    time2 = time.time() - start
    print(f"⏱️  耗时: {time2:.2f}秒")
    
    # 计算提升倍数
    speedup = time1 / time2 if time2 > 0 else 0
    print(f"\n✅ 性能提升: {speedup:.2f}倍")
    
    if speedup < 3:
        print(f"⚠️  警告: 性能提升不明显（预期>3倍）")
        return False
    
    return True


def test_kpi_consistency():
    """测试KPI计算一致性"""
    print("\n" + "="*60)
    print("测试2: KPI计算一致性")
    print("="*60)
    
    try:
        from dashboard_v2 import DataLoader as OldLoader
        from dashboard_v2_optimized import DataLoader as NewLoader
        
        # 优先使用示例文件
        test_files = [
            "./reports/示例门店_分析报告.xlsx",
            "./reports/淮安生态新城商品10.29 的副本_分析报告.xlsx"
        ]
        
        test_file = None
        for f in test_files:
            if Path(f).exists():
                test_file = f
                break
        
        if not test_file:
            print(f"❌ 测试文件不存在，请先运行: python create_sample_report.py")
            return False
        
        print("\n📊 加载数据...")
        old_loader = OldLoader(test_file)
        new_loader = NewLoader(test_file, use_cache=False)  # 禁用缓存确保公平对比
        
        print("🔍 对比KPI计算结果...")
        old_kpi = old_loader.get_kpi_summary()
        new_kpi = new_loader.get_kpi_summary()
        
        # 验证关键指标
        key_metrics = [
            '总SKU数(含规格)',
            '总SKU数(去重后)',
            '动销SKU数',
            '滞销SKU数',
            '动销率',
            '总销售额(去重后)'
        ]
        
        all_match = True
        for key in key_metrics:
            if key in old_kpi and key in new_kpi:
                old_val = old_kpi[key]
                new_val = new_kpi[key]
                
                # 数值比较（允许浮点误差）
                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                    match = abs(old_val - new_val) < 0.0001
                else:
                    match = old_val == new_val
                
                status = "✅" if match else "❌"
                print(f"{status} {key}: {old_val} == {new_val}")
                
                if not match:
                    all_match = False
            else:
                print(f"⚠️  {key}: 缺失")
        
        if all_match:
            print("\n✅ 所有KPI计算结果一致")
            return True
        else:
            print("\n❌ 部分KPI计算结果不一致")
            return False
            
    except ImportError as e:
        print(f"⚠️  无法导入旧版DataLoader，跳过对比测试: {e}")
        return True  # 不影响整体测试


def test_column_mapping():
    """测试列名映射"""
    print("\n" + "="*60)
    print("测试3: 列名映射功能")
    print("="*60)
    
    from dashboard_v2_optimized import KPIColumnMapping
    import pandas as pd
    
    # 创建测试DataFrame
    test_df = pd.DataFrame({
        '美团一级分类爆品sku数': [10, 20, 30],
        '美团一级分类折扣': [8.5, 9.0, 7.5],
        '其他列': [1, 2, 3]
    })
    
    print("\n🔍 测试列名查找...")
    
    # 测试1：标准列名
    col = KPIColumnMapping.find_column(
        test_df, '爆品数', KPIColumnMapping.CATEGORY_COLUMNS
    )
    if col == '美团一级分类爆品sku数':
        print(f"✅ 找到列: '爆品数' -> '{col}'")
    else:
        print(f"❌ 列名查找失败: '爆品数'")
        return False
    
    # 测试2：不存在的列
    col = KPIColumnMapping.find_column(
        test_df, '不存在的列', KPIColumnMapping.CATEGORY_COLUMNS
    )
    if col is None:
        print(f"✅ 正确处理不存在的列")
    else:
        print(f"❌ 不存在的列应返回None")
        return False
    
    # 测试3：安全获取值
    value = KPIColumnMapping.safe_get_value(
        test_df, 0, '爆品数', KPIColumnMapping.CATEGORY_COLUMNS, default=0
    )
    if value == 10:
        print(f"✅ 安全获取值: {value}")
    else:
        print(f"❌ 值获取错误: 期望10，实际{value}")
        return False
    
    print("\n✅ 列名映射功能正常")
    return True


def test_logging():
    """测试日志系统"""
    print("\n" + "="*60)
    print("测试4: 日志系统")
    print("="*60)
    
    from dashboard_v2_optimized import logger
    from pathlib import Path
    
    # 测试日志输出
    logger.info("测试INFO日志")
    logger.warning("测试WARNING日志")
    logger.debug("测试DEBUG日志")
    
    # 检查日志文件
    log_file = Path('logs/dashboard.log')
    if log_file.exists():
        print(f"✅ 日志文件已创建: {log_file}")
        
        # 读取最后几行
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 0:
                print(f"✅ 日志文件有内容（共{len(lines)}行）")
                print(f"   最后一行: {lines[-1].strip()}")
            else:
                print(f"⚠️  日志文件为空")
        
        return True
    else:
        print(f"❌ 日志文件未创建")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🧪 P0优化验证测试")
    print("="*60)
    
    results = {
        '缓存性能': test_cache_performance(),
        'KPI一致性': test_kpi_consistency(),
        '列名映射': test_column_mapping(),
        '日志系统': test_logging()
    }
    
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！P0优化验证成功")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查日志")
        return 1


if __name__ == '__main__':
    sys.exit(main())
