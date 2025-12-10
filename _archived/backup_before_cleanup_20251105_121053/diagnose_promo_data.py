#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断促销强度数据问题
"""

import pandas as pd
from pathlib import Path

# 读取Excel数据
report_path = Path("./reports/竞对分析报告_v3.4_FINAL.xlsx")

if report_path.exists():
    print("="*80)
    print("📊 促销强度数据诊断")
    print("="*80)
    
    # 读取美团一级分类详细指标
    df = pd.read_excel(report_path, sheet_name='美团一级分类详细指标')
    
    print(f"\n📋 数据维度: {df.shape[0]}行 × {df.shape[1]}列")
    print(f"\n列名列表:")
    for i, col in enumerate(df.columns):
        print(f"  {i:2d}. {col}")
    
    # 检查Y列(第24列,索引24)
    print(f"\n🔍 第24列数据检查:")
    if len(df.columns) > 24:
        col_name = df.columns[24]
        col_data = df.iloc[:, 24]
        
        print(f"  列名: {col_name}")
        print(f"  数据类型: {col_data.dtype}")
        print(f"  统计信息:")
        print(f"    最小值: {col_data.min()}")
        print(f"    最大值: {col_data.max()}")
        print(f"    平均值: {col_data.mean():.2f}")
        print(f"    中位数: {col_data.median():.2f}")
        print(f"    缺失值: {col_data.isna().sum()}")
        
        print(f"\n  值分布 (前10个唯一值):")
        value_counts = col_data.value_counts().head(10)
        for val, count in value_counts.items():
            print(f"    {val}: {count}个分类")
        
        print(f"\n  示例数据 (前5行):")
        for i in range(min(5, len(df))):
            cat_name = df.iloc[i, 0]
            discount = df.iloc[i, 24]
            print(f"    {cat_name}: {discount}")
        
        # 计算当前促销强度
        discount_level = pd.to_numeric(col_data, errors='coerce').fillna(10)
        promo_intensity = ((10 - discount_level) / 9 * 100).clip(lower=0, upper=100)
        
        print(f"\n📈 当前促销强度计算结果:")
        print(f"  平均促销强度: {promo_intensity.mean():.2f}%")
        print(f"  促销强度分布:")
        print(f"    0-20%: {(promo_intensity < 20).sum()}个分类")
        print(f"    20-40%: {((promo_intensity >= 20) & (promo_intensity < 40)).sum()}个分类")
        print(f"    40-60%: {((promo_intensity >= 40) & (promo_intensity < 60)).sum()}个分类")
        print(f"    60-80%: {((promo_intensity >= 60) & (promo_intensity < 80)).sum()}个分类")
        print(f"    80-100%: {(promo_intensity >= 80).sum()}个分类")
        
        print(f"\n  TOP5 促销强度最高的分类:")
        top5_idx = promo_intensity.nlargest(5).index
        for idx in top5_idx:
            cat = df.iloc[idx, 0]
            disc = df.iloc[idx, 24]
            intensity = promo_intensity.iloc[idx]
            print(f"    {cat}: 折扣={disc}折, 促销强度={intensity:.1f}%")
        
        print(f"\n  TOP5 促销强度最低的分类:")
        bottom5_idx = promo_intensity.nsmallest(5).index
        for idx in bottom5_idx:
            cat = df.iloc[idx, 0]
            disc = df.iloc[idx, 24]
            intensity = promo_intensity.iloc[idx]
            print(f"    {cat}: 折扣={disc}折, 促销强度={intensity:.1f}%")
    else:
        print(f"  ❌ 列数不足,只有{len(df.columns)}列")
    
    # 检查活动占比列
    print(f"\n\n🔍 活动占比数据检查 (替代指标):")
    if len(df.columns) > 10:
        activity_col_idx = 10  # K列(活动占比类内)
        col_name = df.columns[activity_col_idx]
        col_data = df.iloc[:, activity_col_idx]
        
        print(f"  列名: {col_name}")
        print(f"  平均活动占比: {col_data.mean():.2f}%")
        print(f"  TOP5活动占比最高分类:")
        top5 = col_data.nlargest(5)
        for idx in top5.index:
            cat = df.iloc[idx, 0]
            ratio = col_data.iloc[idx]
            print(f"    {cat}: {ratio:.1f}%")
    
    print("\n" + "="*80)
    
else:
    print(f"❌ 文件不存在: {report_path}")
