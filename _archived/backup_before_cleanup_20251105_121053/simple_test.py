#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最简测试 - 验证集成逻辑"""

from store_analyzer import StoreAnalyzer
from pathlib import Path

print("="*80)
print("测试: 集成逻辑验证")
print("="*80)

# 1. 创建分析器
analyzer = StoreAnalyzer()
print("\n[1/3] 分析器创建成功")

# 2. 分析文件
result = analyzer.analyze_file('temp/鲸星购(1).xlsx', '鲸星购')
if result:
    print("\n[2/3] 文件分析成功")
else:
    print("\n[2/3] 文件分析失败")
    exit(1)

# 3. 获取核心指标
summary = analyzer.get_summary('鲸星购')
if summary:
    print("\n[3/3] 核心指标提取成功")
    print("\n核心指标:")
    for key, value in summary.items():
        if isinstance(value, float):
            if '率' in key:
                print(f"  {key}: {value*100:.2f}%")
            else:
                print(f"  {key}: {value:,.2f}")
        else:
            print(f"  {key}: {value:,}")
else:
    print("\n[3/3] 核心指标提取失败")
    exit(1)

print("\n" + "="*80)
print("测试通过! 集成逻辑工作正常")
print("="*80)
