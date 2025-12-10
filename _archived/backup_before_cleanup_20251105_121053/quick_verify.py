#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速验证促销数据读取"""

import pandas as pd
import sys
from pathlib import Path

def verify_promo_data():
    """验证促销效能分析的数据"""
    print("=" * 80)
    print("🧪 促销效能数据验证")
    print("=" * 80)
    
    # 读取分析报告
    file_path = r"d:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\鲸星购_分析报告.xlsx"
    
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        print("\n请先运行 untitled1.py 生成分析报告")
        return False
    
    try:
        # 读取Excel文件
        xl = pd.ExcelFile(file_path)
        print(f"\n📁 文件: {file_path}")
        print(f"📋 包含的Sheet: {xl.sheet_names}")
        
        # 检查是否有分类汇总sheet
        if '美团一级分类汇总' not in xl.sheet_names:
            print(f"\n❌ 缺少'美团一级分类汇总' sheet")
            print("这不是完整的分析报告")
            return False
        
        # 读取分类汇总数据
        df = pd.read_excel(file_path, sheet_name='美团一级分类汇总')
        print(f"\n✅ 成功读取'美团一级分类汇总'")
        print(f"数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
        
        # 显示列名
        print(f"\n列名 (前25列):")
        for i, col in enumerate(df.columns[:25]):
            print(f"  列{i:2d}: {col}")
        
        # 检查第10列(K列) - 活动SKU占比
        if len(df.columns) > 10:
            col_10 = df.iloc[:, 10]  # K列
            print(f"\n第10列数据检查:")
            print(f"  列名: {df.columns[10]}")
            print(f"  数据类型: {col_10.dtype}")
            print(f"  最小值: {col_10.min():.6f}")
            print(f"  最大值: {col_10.max():.6f}")
            print(f"  平均值: {col_10.mean():.6f}")
            print(f"  中位数: {col_10.median():.6f}")
            
            # 显示具体数据
            print(f"\n前10个分类的活动占比:")
            for idx in range(min(10, len(df))):
                cat = df.iloc[idx, 0]
                val = df.iloc[idx, 10]
                print(f"  {cat}: {val:.6f} ({val*100:.2f}%)")
            
            # 判断数据格式
            if col_10.max() <= 1.0:
                print(f"\n⚠️ 数据格式: 小数(0-1),需要×100转为百分比")
                print(f"   Dashboard代码应该×100来显示")
            else:
                print(f"\n✅ 数据格式: 已是百分比(0-100)")
                
        # 检查过滤条件
        print(f"\n" + "=" * 80)
        print("过滤条件测试:")
        
        sales = pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0)  # S列:销售额
        sku = pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0)  # E列:去重SKU数
        ratio = pd.to_numeric(df.iloc[:, 14], errors='coerce').fillna(0)  # O列:SKU占比
        
        filter1 = sku > 0
        filter2 = sales > 0
        filter3 = sku >= 10
        filter4 = ratio >= 0.005
        
        print(f"1. 去重SKU数>0: {filter1.sum()} 个分类")
        print(f"2. 销售额>0: {filter2.sum()} 个分类")
        print(f"3. 去重SKU数>=10: {filter3.sum()} 个分类")
        print(f"4. SKU占比>=0.005(0.5%): {filter4.sum()} 个分类")
        
        filter_all = filter1 & filter2 & filter3 & filter4
        print(f"\n✅ 通过所有过滤条件: {filter_all.sum()} 个分类")
        
        if filter_all.sum() > 0:
            filtered_df = df[filter_all]
            print(f"\n过滤后的分类:")
            for idx in filtered_df.index[:10]:
                cat = df.iloc[idx, 0]
                s = sales.iloc[idx]
                k = sku.iloc[idx]
                r = ratio.iloc[idx]
                a = df.iloc[idx, 10]
                print(f"  {cat}: 销售¥{s:,.0f}, SKU={k:.0f}, 占比={r*100:.2f}%, 活动占比={a*100:.2f}%")
        else:
            print(f"\n❌ 没有分类通过过滤条件!")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_promo_data()
    sys.exit(0 if success else 1)
