import pandas as pd

# 读取Excel文件
df = pd.read_excel('./reports/竞对分析报告_v3.4_FINAL.xlsx', 
                   sheet_name='美团一级分类详细指标')

print("=" * 100)
print("折扣数据详细分析")
print("=" * 100)

# 显示关键列
print(f"\n总共 {len(df)} 个分类\n")

# 提取关键列
categories = df.iloc[:, 0]  # A列：一级分类
dedup_sku = df.iloc[:, 4]  # E列：去重SKU数
discount_sku = df.iloc[:, 22]  # W列：折扣SKU数

# 计算折扣占比
discount_ratio = (discount_sku / dedup_sku * 100).fillna(0)

# 显示每个分类的详细数据
print(f"{'分类':<20} {'去重SKU数':>12} {'折扣SKU数':>12} {'折扣占比':>12}")
print("-" * 100)

for i in range(len(df)):
    cat = categories.iloc[i]
    dedup = dedup_sku.iloc[i]
    disc = discount_sku.iloc[i]
    ratio = discount_ratio.iloc[i]
    
    print(f"{cat:<20} {dedup:>12.0f} {disc:>12.0f} {ratio:>11.1f}%")

print("-" * 100)

# 统计分析
print(f"\n统计摘要:")
print(f"折扣占比最小值: {discount_ratio.min():.2f}%")
print(f"折扣占比最大值: {discount_ratio.max():.2f}%")
print(f"折扣占比平均值: {discount_ratio.mean():.2f}%")
print(f"折扣占比中位数: {discount_ratio.median():.2f}%")

# 检查100%的分类
ratio_100 = (discount_ratio >= 99.9).sum()
print(f"\n折扣占比≥99.9%的分类数: {ratio_100} / {len(df)}")

# 检查低于100%的分类
ratio_below_100 = (discount_ratio < 99.9).sum()
print(f"折扣占比<99.9%的分类数: {ratio_below_100} / {len(df)}")

if ratio_below_100 > 0:
    print("\n折扣占比<99.9%的分类:")
    for i in range(len(df)):
        if discount_ratio.iloc[i] < 99.9:
            cat = categories.iloc[i]
            ratio = discount_ratio.iloc[i]
            print(f"  - {cat}: {ratio:.2f}%")

print("\n" + "=" * 100)
print("💡 分析结论:")
print("=" * 100)
if discount_ratio.min() == 100.0 and discount_ratio.max() == 100.0:
    print("⚠️ 所有分类的折扣占比都是100%!")
    print("   这说明:每个分类的【折扣SKU数】 = 【去重SKU数】")
    print("   原因可能是:")
    print("   1. 门店所有商品都在打折(折扣阈值只有1%)")
    print("   2. 数据计算逻辑有误")
    print("   3. W列的数据不是真正的'折扣SKU数'")
else:
    print(f"✅ 折扣占比范围: {discount_ratio.min():.1f}% - {discount_ratio.max():.1f}%")
    print(f"   数据呈现正常的差异分布")
