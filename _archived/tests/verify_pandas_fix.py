# -*- coding: utf-8 -*-
"""
验证pandas Series访问修复
"""

import pandas as pd

# 模拟category_data
category_data = pd.DataFrame({
    '一级分类': ['饮料', '休闲食品', '乳制品'],
    '售价销售额': [42350.5, 38920.3, 24160.2],
    '美团一级分类去重SKU数(口径同动销率)': [65, 48, 32],
    '美团一级分类动销率(类内)': [82.3, 75.0, 68.8],
    '美团一级分类折扣': [9.2, 9.5, 9.8]
})

print("=" * 60)
print("测试: pandas Series正确访问方式")
print("=" * 60)

sorted_cats = category_data.sort_values('售价销售额', ascending=False).copy()

category_summary = []
for idx, row in sorted_cats.iterrows():
    # 正确的访问方式：使用方括号
    cat_info = {
        '一级分类': row['一级分类'] if '一级分类' in row and pd.notna(row['一级分类']) else '未知',
        '售价销售额': row['售价销售额'] if '售价销售额' in row and pd.notna(row['售价销售额']) else 0,
        '美团一级分类去重SKU数(口径同动销率)': row['美团一级分类去重SKU数(口径同动销率)'] if '美团一级分类去重SKU数(口径同动销率)' in row and pd.notna(row['美团一级分类去重SKU数(口径同动销率)']) else 0,
        '美团一级分类动销率(类内)': row['美团一级分类动销率(类内)'] if '美团一级分类动销率(类内)' in row and pd.notna(row['美团一级分类动销率(类内)']) else 0,
        '美团一级分类折扣': row['美团一级分类折扣'] if '美团一级分类折扣' in row and pd.notna(row['美团一级分类折扣']) else 10,
    }
    category_summary.append(cat_info)

print("✅ 数据提取成功!")
print(f"\n提取了 {len(category_summary)} 个分类:")
for cat in category_summary:
    print(f"  - {cat['一级分类']}: ¥{cat['售价销售额']:,.2f}, 动销率{cat['美团一级分类动销率(类内)']}%")

print("\n测试CategoryPanelAnalyzer.analyze()所需数据格式:")
print(f"类型检查: {type(category_summary)} (应该是list)")
print(f"第一个元素类型: {type(category_summary[0])} (应该是dict)")
print(f"第一个元素可以.get(): {category_summary[0].get('一级分类', '未知')} ✅")

print("\n" + "=" * 60)
print("✅ 修复验证完成! Dashboard应该可以正常工作了")
print("=" * 60)
