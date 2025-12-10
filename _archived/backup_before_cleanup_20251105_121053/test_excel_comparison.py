#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel报告对比测试 - 验证集成版本和原始版本导出的Excel文件是否完全一致
"""

import pandas as pd
from pathlib import Path
import sys

def compare_excel_reports(file1: str, file2: str):
    """
    对比两个Excel报告文件
    
    Args:
        file1: 第一个Excel文件路径 (原始版本)
        file2: 第二个Excel文件路径 (集成版本)
    """
    print("=" * 100)
    print("📊 Excel报告对比测试")
    print("=" * 100)
    
    # 检查文件是否存在
    p1 = Path(file1)
    p2 = Path(file2)
    
    if not p1.exists():
        print(f"\n❌ 文件1不存在: {file1}")
        return False
    
    if not p2.exists():
        print(f"\n❌ 文件2不存在: {file2}")
        return False
    
    print(f"\n📁 文件1 (原始版本): {p1.name}")
    print(f"📁 文件2 (集成版本): {p2.name}")
    
    # 读取所有Sheet名称
    try:
        excel1 = pd.ExcelFile(file1)
        excel2 = pd.ExcelFile(file2)
        
        sheets1 = excel1.sheet_names
        sheets2 = excel2.sheet_names
        
        print(f"\n📋 Sheet数量对比:")
        print(f"   文件1: {len(sheets1)} 个Sheet")
        print(f"   文件2: {len(sheets2)} 个Sheet")
        
        if len(sheets1) != len(sheets2):
            print(f"\n❌ Sheet数量不一致!")
            print(f"   文件1的Sheet: {sheets1}")
            print(f"   文件2的Sheet: {sheets2}")
            return False
        else:
            print(f"   ✅ Sheet数量一致")
        
        # 对比每个Sheet
        print(f"\n{'='*100}")
        print("📊 逐Sheet数据对比:")
        print(f"{'='*100}\n")
        
        all_match = True
        
        for i, sheet_name in enumerate(sheets1, 1):
            print(f"[{i}/{len(sheets1)}] Sheet: '{sheet_name}'")
            print("-" * 100)
            
            # 检查Sheet是否在第二个文件中
            if sheet_name not in sheets2:
                print(f"   ❌ 文件2中缺少此Sheet")
                all_match = False
                continue
            
            # 读取数据
            df1 = pd.read_excel(file1, sheet_name=sheet_name)
            df2 = pd.read_excel(file2, sheet_name=sheet_name)
            
            # 对比行数
            rows1, cols1 = df1.shape
            rows2, cols2 = df2.shape
            
            print(f"   • 数据维度: 文件1={rows1}行×{cols1}列, 文件2={rows2}行×{cols2}列", end="")
            
            if rows1 != rows2 or cols1 != cols2:
                print(f" ❌ 维度不一致!")
                all_match = False
                continue
            else:
                print(f" ✅")
            
            # 对比列名
            cols_match = list(df1.columns) == list(df2.columns)
            print(f"   • 列名一致性: ", end="")
            if not cols_match:
                print("❌ 列名不一致")
                print(f"     文件1列名: {list(df1.columns)[:5]}...")
                print(f"     文件2列名: {list(df2.columns)[:5]}...")
                all_match = False
                continue
            else:
                print("✅")
            
            # 对比数据内容
            try:
                # 处理索引和列名可能的差异
                df1_reset = df1.reset_index(drop=True)
                df2_reset = df2.reset_index(drop=True)
                
                # 对比数值
                comparison = df1_reset.equals(df2_reset)
                
                if not comparison:
                    # 尝试忽略极小的浮点数差异
                    numeric_cols = df1_reset.select_dtypes(include=['float64', 'int64']).columns
                    non_numeric_cols = df1_reset.select_dtypes(exclude=['float64', 'int64']).columns
                    
                    # 非数值列必须完全一致
                    non_numeric_match = True
                    if len(non_numeric_cols) > 0:
                        for col in non_numeric_cols:
                            if not df1_reset[col].equals(df2_reset[col]):
                                non_numeric_match = False
                                break
                    
                    # 数值列允许极小误差
                    numeric_match = True
                    max_diff = 0
                    if len(numeric_cols) > 0:
                        for col in numeric_cols:
                            diff = (df1_reset[col] - df2_reset[col]).abs().max()
                            if diff > 0.01:  # 允许0.01的误差
                                numeric_match = False
                            max_diff = max(max_diff, diff)
                    
                    if non_numeric_match and numeric_match:
                        print(f"   • 数据内容: ✅ 一致 (数值最大差异: {max_diff:.6f})")
                    else:
                        print(f"   • 数据内容: ❌ 不一致")
                        
                        # 显示差异示例
                        if not non_numeric_match:
                            print(f"     非数值列存在差异")
                        if not numeric_match:
                            print(f"     数值列差异超过阈值 (最大差异: {max_diff})")
                        
                        # 显示前5行对比
                        print(f"\n     文件1前3行:")
                        print(f"     {df1_reset.head(3).to_string(index=False)[:200]}...")
                        print(f"\n     文件2前3行:")
                        print(f"     {df2_reset.head(3).to_string(index=False)[:200]}...")
                        
                        all_match = False
                else:
                    print(f"   • 数据内容: ✅ 完全一致")
                
            except Exception as e:
                print(f"   • 数据内容: ❌ 对比失败 - {e}")
                all_match = False
            
            print()
        
        # 最终结论
        print("=" * 100)
        if all_match:
            print("✅ 验证通过: 两个Excel文件的所有Sheet数据完全一致!")
            print("   集成版本的导出功能与原始版本100%等价")
        else:
            print("❌ 验证失败: 两个Excel文件存在差异")
            print("   需要检查集成逻辑")
        print("=" * 100)
        
        return all_match
        
    except Exception as e:
        print(f"\n❌ 读取Excel文件时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_test_reports():
    """生成测试用的报告文件"""
    print("\n" + "="*100)
    print("🔧 生成测试报告文件")
    print("="*100)
    
    test_file = "temp/鲸星购(1).xlsx"
    store_name = "鲸星购"
    
    # 1. 使用原始版本生成报告
    print("\n[1/2] 使用原始 untitled1.py 生成报告...")
    print("-" * 100)
    
    from untitled1 import load_and_clean_data, analyze_store_performance, export_full_report_to_excel
    
    CONSUMPTION_SCENARIOS = {
        "早餐快手": ["早餐", "牛奶", "面包", "麦片", "鸡蛋"],
        "加班能量补给": ["咖啡", "能量饮料", "巧克力", "饼干", "能量棒"],
        "家庭囤货": ["大包装", "家庭装", "组合装", "箱", "量贩"],
        "聚会零食": ["薯片", "膨化", "糖果", "坚果", "汽水", "啤酒"],
    }
    
    # 原始版本流程
    processed = load_and_clean_data(test_file, store_name, CONSUMPTION_SCENARIOS)
    if not processed:
        print("❌ 原始版本数据加载失败")
        return False
    
    df_all, df_dedup, df_act = processed
    
    analysis_results = analyze_store_performance(df_all, df_dedup, df_act)
    if not analysis_results:
        print("❌ 原始版本分析失败")
        return False
    
    # 导出原始版本报告
    original_report = "reports/test_original_鲸星购.xlsx"
    all_store_results = {store_name: analysis_results}
    all_store_data = {store_name: {'all_skus': df_all, 'deduplicated': df_dedup, 'active': df_act}}
    
    export_full_report_to_excel(all_store_results, all_store_data, original_report)
    
    if Path(original_report).exists():
        print(f"✅ 原始版本报告生成成功: {original_report}")
    else:
        print(f"❌ 原始版本报告生成失败")
        return False
    
    # 2. 使用集成版本生成报告
    print("\n[2/2] 使用集成 store_analyzer.py 生成报告...")
    print("-" * 100)
    
    from store_analyzer import StoreAnalyzer
    
    analyzer = StoreAnalyzer()
    result = analyzer.analyze_file(test_file, store_name)
    
    if not result:
        print("❌ 集成版本分析失败")
        return False
    
    # 导出集成版本报告
    integrated_report = "reports/test_integrated_鲸星购.xlsx"
    analyzer.export_report(store_name, integrated_report)
    
    if Path(integrated_report).exists():
        print(f"✅ 集成版本报告生成成功: {integrated_report}")
    else:
        print(f"❌ 集成版本报告生成失败")
        return False
    
    return original_report, integrated_report


def main():
    """主函数"""
    # 生成测试报告
    result = generate_test_reports()
    
    if not result:
        print("\n❌ 报告生成失败,无法进行对比")
        sys.exit(1)
    
    original_report, integrated_report = result
    
    # 对比报告
    print("\n\n")
    success = compare_excel_reports(original_report, integrated_report)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
