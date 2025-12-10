"""检查气泡图数据计算是否正确"""
import pandas as pd
import numpy as np

# 读取Excel数据
excel_path = './reports/竞对分析报告_v3.4_FINAL.xlsx'
excel_file = pd.ExcelFile(excel_path)
sheet_names = excel_file.sheet_names

print("=" * 80)
print("📊 检查气泡图数据计算")
print("=" * 80)

# 读取美团一级分类详细指标
category_data = pd.read_excel(excel_path, sheet_name=sheet_names[4])

print(f"\n✅ 数据维度: {category_data.shape}")
print(f"\n📋 列名列表:")
for i, col in enumerate(category_data.columns):
    print(f"  {chr(65+i)}列 (索引{i}): {col}")

print("\n" + "=" * 80)
print("🔍 气泡图使用的数据列:")
print("=" * 80)

print(f"\n【X轴】月售数量:")
print(f"  - 使用列: 索引15 = {category_data.columns[15] if len(category_data.columns) > 15 else '索引超出范围'}")
print(f"  - 前5个分类数据:")
if len(category_data.columns) > 15:
    for i in range(min(5, len(category_data))):
        cat_name = category_data.iloc[i, 0]
        value = category_data.iloc[i, 15]
        print(f"    {cat_name}: {value:,.0f}件")

print(f"\n【Y轴】售价销售额:")
print(f"  - 使用列: 索引18 = {category_data.columns[18] if len(category_data.columns) > 18 else '索引超出范围'}")
print(f"  - 前5个分类数据:")
if len(category_data.columns) > 18:
    for i in range(min(5, len(category_data))):
        cat_name = category_data.iloc[i, 0]
        value = category_data.iloc[i, 18]
        print(f"    {cat_name}: ¥{value:,.2f}")

print(f"\n【气泡大小】动销率:")
print(f"  - 使用列: 索引6 = {category_data.columns[6] if len(category_data.columns) > 6 else '索引超出范围'}")
print(f"  - 前5个分类数据:")
if len(category_data.columns) > 6:
    for i in range(min(5, len(category_data))):
        cat_name = category_data.iloc[i, 0]
        value = category_data.iloc[i, 6] * 100
        print(f"    {cat_name}: {value:.2f}%")

print(f"\n【颜色】折扣占比 (折扣SKU数 / 总SKU数):")
print(f"  - 总SKU数列: 索引1 = {category_data.columns[1] if len(category_data.columns) > 1 else '索引超出范围'}")
print(f"  - 折扣SKU数列: 索引22 = {category_data.columns[22] if len(category_data.columns) > 22 else '索引超出范围'}")
print(f"  - 前5个分类数据:")
if len(category_data.columns) > 22:
    for i in range(min(5, len(category_data))):
        cat_name = category_data.iloc[i, 0]
        total_sku = category_data.iloc[i, 1]
        discount_sku = category_data.iloc[i, 22]
        ratio = (discount_sku / total_sku * 100) if total_sku > 0 else 0
        print(f"    {cat_name}: {discount_sku}/{total_sku} = {ratio:.2f}%")

print("\n" + "=" * 80)
print("🔎 数据验证:")
print("=" * 80)

# 验证数据逻辑
print(f"\n1️⃣ 检查是否有负数或异常值:")
for col_idx, col_name in [(15, "月售"), (18, "售价销售额"), (6, "动销率"), (22, "折扣SKU数")]:
    if len(category_data.columns) > col_idx:
        col_data = category_data.iloc[:, col_idx]
        has_negative = (col_data < 0).any()
        has_null = col_data.isna().any()
        print(f"  {col_name}: 负数={has_negative}, 空值={has_null}, 最小值={col_data.min():.2f}, 最大值={col_data.max():.2f}")

print(f"\n2️⃣ 检查月售与销售额的关系:")
if len(category_data.columns) > 18:
    monthly_sales = category_data.iloc[:, 15]
    total_revenue = category_data.iloc[:, 18]
    
    # 计算隐含单价
    avg_price = (total_revenue / monthly_sales).replace([np.inf, -np.inf], 0).fillna(0)
    
    print(f"  隐含平均单价分布:")
    print(f"    最低单价: ¥{avg_price[avg_price > 0].min():.2f}" if (avg_price > 0).any() else "    最低单价: N/A")
    print(f"    最高单价: ¥{avg_price.max():.2f}")
    print(f"    平均单价: ¥{avg_price[avg_price > 0].mean():.2f}" if (avg_price > 0).any() else "    平均单价: N/A")
    
    # 找出可能有问题的分类
    print(f"\n  📌 单价异常分类 (单价 > ¥1000 或 < ¥1):")
    for i in range(len(category_data)):
        cat_name = category_data.iloc[i, 0]
        sales = monthly_sales.iloc[i]
        revenue = total_revenue.iloc[i]
        price = avg_price.iloc[i]
        
        if price > 1000 or (price > 0 and price < 1):
            print(f"    ⚠️ {cat_name}: 月售={sales:,.0f}件, 销售额=¥{revenue:,.2f}, 隐含单价=¥{price:.2f}")

print(f"\n3️⃣ 检查动销率是否在合理范围:")
if len(category_data.columns) > 6:
    active_rate = category_data.iloc[:, 6]
    out_of_range = ((active_rate < 0) | (active_rate > 1)).sum()
    print(f"  动销率超出[0,1]范围的分类数: {out_of_range}")
    if out_of_range > 0:
        print(f"  异常分类:")
        for i in range(len(category_data)):
            rate = active_rate.iloc[i]
            if rate < 0 or rate > 1:
                cat_name = category_data.iloc[i, 0]
                print(f"    ⚠️ {cat_name}: {rate:.4f}")

print("\n" + "=" * 80)
print("✅ 检查完成")
print("=" * 80)
