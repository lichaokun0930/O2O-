"""验证列索引和数据"""
import pandas as pd

excel_path = './reports/竞对分析报告_v3.4_FINAL.xlsx'
excel_file = pd.ExcelFile(excel_path)
sheet_names = excel_file.sheet_names

# 读取美团一级分类详细指标
category_data = pd.read_excel(excel_path, sheet_name=sheet_names[4])

print("=" * 120)
print("📋 列名对照表")
print("=" * 120)

for i, col in enumerate(category_data.columns):
    letter = chr(65 + i) if i < 26 else f"A{chr(65 + i - 26)}"
    print(f"{letter}列 (索引{i:>2}): {col}")

print("\n" + "=" * 120)
print("🔍 关键列数据验证 (休闲食品分类)")
print("=" * 120)

# 找到休闲食品这一行
target_category = "休闲食品"
target_row = category_data[category_data.iloc[:, 0] == target_category]

if not target_row.empty:
    row = target_row.iloc[0]
    print(f"\nA列(索引0) - 一级分类: {row.iloc[0]}")
    print(f"B列(索引1) - 总SKU数: {row.iloc[1]}")
    print(f"E列(索引4) - 去重SKU数: {row.iloc[4]}")
    print(f"W列(索引22) - 折扣SKU数: {row.iloc[22]}")
    print(f"X列(索引23) - 爆品SKU数: {row.iloc[23]}")
    print(f"Y列(索引24) - 折扣: {row.iloc[24]}")
    
    print("\n" + "=" * 120)
    print("🧮 计算验证")
    print("=" * 120)
    
    total_sku = row.iloc[1]
    dedup_sku = row.iloc[4]
    discount_sku = row.iloc[22]
    discount_rate = row.iloc[24]
    
    print(f"\n方案1: W列(折扣SKU数) ÷ B列(总SKU数)")
    print(f"  = {discount_sku} ÷ {total_sku}")
    print(f"  = {discount_sku / total_sku * 100:.2f}%")
    
    print(f"\n方案2: W列(折扣SKU数) ÷ E列(去重SKU数)")
    print(f"  = {discount_sku} ÷ {dedup_sku}")
    print(f"  = {discount_sku / dedup_sku * 100:.2f}%")
    
    print(f"\n方案3: 直接使用Y列(折扣)")
    print(f"  = {discount_rate}")
    if discount_rate <= 1:
        print(f"  = {discount_rate * 100:.2f}% (转换为百分比)")
    else:
        print(f"  = {discount_rate:.2f}% (已是百分比)")
    
    print("\n" + "=" * 120)
    print("💡 结论")
    print("=" * 120)
    print(f"从截图看到折扣占比=100%,说明:")
    print(f"  如果 W÷E={discount_sku / dedup_sku * 100:.2f}%=100%,那么说明所有去重SKU都有折扣")
    print(f"  如果数值正确,这可能反映了真实情况(折扣阈值只有1%)")

print("\n" + "=" * 120)
print("📊 全部分类的折扣占比计算")
print("=" * 120)

print("\n分类             | B列总SKU | E列去重SKU | W列折扣SKU | W÷B占比  | W÷E占比  | Y列折扣")
print("-" * 120)

for idx, row in category_data.head(10).iterrows():
    cat_name = row.iloc[0]
    total_sku = row.iloc[1]
    dedup_sku = row.iloc[4]
    discount_sku = row.iloc[22]
    discount_rate = row.iloc[24]
    
    ratio_b = (discount_sku / total_sku * 100) if total_sku > 0 else 0
    ratio_e = (discount_sku / dedup_sku * 100) if dedup_sku > 0 else 0
    
    print(f"{cat_name:<16} | {total_sku:>8.0f} | {dedup_sku:>10.0f} | {discount_sku:>10.0f} | "
          f"{ratio_b:>7.2f}% | {ratio_e:>7.2f}% | {discount_rate:>7.2f}")
