# -*- coding: utf-8 -*-
"""
调试loader.data的内容
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 直接导入dashboard模块检查loader
import dashboard_v2

print("=" * 60)
print("调试: loader.data的内容")
print("=" * 60)

loader = dashboard_v2.loader

print(f"\nloader类型: {type(loader)}")
print(f"loader.data类型: {type(loader.data)}")
print(f"loader.data的键: {list(loader.data.keys())}")

# 检查每个数据的情况
for key in loader.data.keys():
    data = loader.data[key]
    print(f"\n{key}:")
    print(f"  类型: {type(data)}")
    if hasattr(data, 'shape'):
        print(f"  形状: {data.shape}")
    if hasattr(data, 'empty'):
        print(f"  是否为空: {data.empty}")
    if hasattr(data, 'columns'):
        print(f"  列名: {list(data.columns)[:10]}...")  # 只显示前10列

print("\n" + "=" * 60)
