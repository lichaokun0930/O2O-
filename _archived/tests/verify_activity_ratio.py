import pandas as pd

# 读取Excel文件
df = pd.read_excel('./reports/竞对分析报告_v3.4_FINAL.xlsx', 
                   sheet_name='美团一级分类详细指标')

print("=" * 100)
print("活动占比数据验证")
print("=" * 100)

# 提取关键列
categories = df.iloc[:, 0]  # A列：一级分类
dedup_sku = pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0)  # E列：去重SKU数
activity_dedup_sku = pd.to_numeric(df.iloc[:, 8], errors='coerce').fillna(0)  # I列：活动去重SKU数
k_col = pd.to_numeric(df.iloc[:, 10], errors='coerce').fillna(0)  # K列：活动SKU占比(类内)

# 计算活动占比
activity_ratio = (activity_dedup_sku / dedup_sku * 100).fillna(0)

print(f"\n{'分类':<20} {'去重SKU':>10} {'活动SKU':>10} {'K列原值':>10} {'计算占比':>10}")
print("-" * 100)

for i in range(len(df)):
    cat = categories.iloc[i]
    dedup = int(dedup_sku.iloc[i])
    activity = int(activity_dedup_sku.iloc[i])
    k_val = k_col.iloc[i]
    ratio = activity_ratio.iloc[i]
    
    print(f"{cat:<20} {dedup:>10} {activity:>10} {k_val:>9.2%} {ratio:>9.1f}%")

print("-" * 100)

# 统计分析
print(f"\n统计摘要:")
print(f"活动占比最小值: {activity_ratio.min():.2f}%")
print(f"活动占比最大值: {activity_ratio.max():.2f}%")
print(f"活动占比平均值: {activity_ratio.mean():.2f}%")
print(f"活动占比中位数: {activity_ratio.median():.2f}%")

# 检查100%的分类
ratio_100 = (activity_ratio >= 99.9).sum()
print(f"\n活动占比≥99.9%的分类数: {ratio_100} / {len(df)}")

# 检查低于100%的分类
ratio_below_100 = (activity_ratio < 99.9).sum()
print(f"活动占比<99.9%的分类数: {ratio_below_100} / {len(df)}")

if ratio_below_100 > 0:
    print("\n活动占比<99.9%的分类:")
    for i in range(len(df)):
        if activity_ratio.iloc[i] < 99.9:
            cat = categories.iloc[i]
            ratio = activity_ratio.iloc[i]
            print(f"  - {cat}: {ratio:.2f}%")

print("\n" + "=" * 100)
print("💡 数据说明:")
print("=" * 100)
print("K列(索引10) = '美团一级分类活动SKU占比(类内)' - 已经是小数形式(1.0=100%)")
print("正确计算方式 = I列(活动去重SKU数) ÷ E列(去重SKU数) × 100%")
print("=" * 100)
