# -*- coding: utf-8 -*-
"""测试一级分类数据修复"""

import pandas as pd
from pathlib import Path

# 测试文件路径
report_path = "./reports/淮安生态新城商品10.29 的副本_分析报告.xlsx"

print("=" * 60)
print("一级分类数据修复验证")
print("=" * 60)

# 加载Excel文件
xl = pd.ExcelFile(report_path)
sheet_names = xl.sheet_names

print(f"\n📊 所有Sheet（共{len(sheet_names)}个）:")
for i, name in enumerate(sheet_names):
    print(f"   索引{i}: {name}")

# 正确的索引
correct_index = 3  # 美团一级分类详细指标

print(f"\n✅ 正确的一级分类Sheet索引: {correct_index}")
print(f"✅ 正确的Sheet名称: {sheet_names[correct_index]}")

# 加载正确的一级分类数据
df_category_l1 = pd.read_excel(report_path, sheet_name=correct_index)

print(f"\n📊 一级分类数据形状: {df_category_l1.shape}")
print(f"📊 列数: {len(df_category_l1.columns)}")
print(f"📊 行数(分类数): {len(df_category_l1)}")

# 显示第一列（分类名称）
print(f"\n📋 分类列表（前10个）:")
for i, cat in enumerate(df_category_l1.iloc[:10, 0]):
    print(f"   {i+1}. {cat}")

# 显示列名（前10个）
print(f"\n📋 列名（前10个）:")
for i, col in enumerate(df_category_l1.columns[:10]):
    print(f"   {i+1}. {col}")

# 检查关键列是否存在
key_columns = ['美团一级分类sku数', '美团一级分类动销sku数', '美团一级分类折扣sku数', '售价销售额']
print(f"\n🔍 关键列检查:")
for col in key_columns:
    exists = col in df_category_l1.columns
    status = "✅" if exists else "❌"
    print(f"   {status} {col}: {'存在' if exists else '不存在'}")

print("\n" + "=" * 60)
print("✅ 验证完成！")
print("=" * 60)
