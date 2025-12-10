import pandas as pd

# 读取Excel数据
path = r'd:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\淮安生态新城商品10.29 的副本_分析报告.xlsx'

# 读取核心指标对比
kpi_df = pd.read_excel(path, sheet_name='核心指标对比')
print("=" * 80)
print("核心指标对比 Sheet")
print("=" * 80)
print(f"Shape: {kpi_df.shape}")
print(f"\n列名:")
for i, col in enumerate(kpi_df.columns):
    print(f"  索引{i}: {col}")

print(f"\n第一行数据:")
for i in range(min(11, len(kpi_df.columns))):
    print(f"  索引{i}: {kpi_df.iloc[0, i]}")

# 读取一级分类数据
cat_df = pd.read_excel(path, sheet_name='美团一级分类详细指标')
print("\n" + "=" * 80)
print("从一级分类计算的指标")
print("=" * 80)
print(f"总SKU数(B列,索引1): {cat_df.iloc[:, 1].sum()}")
print(f"去重SKU数(E列,索引4): {cat_df.iloc[:, 4].sum()}")
print(f"动销SKU数(F列,索引5): {cat_df.iloc[:, 5].sum()}")
print(f"滞销SKU数(G列,索引6): {cat_df.iloc[:, 6].sum()}")
print(f"多规格SKU数(D列,索引3): {cat_df.iloc[:, 3].sum()}")
print(f"门店爆品数(X列,索引23): {cat_df.iloc[:, 23].sum()}")
print(f"平均折扣(AC列,索引28): {cat_df.iloc[:, 28].mean():.2f}折")
print(f"折扣SKU数(AA列,索引26): {cat_df.iloc[:, 26].sum()}")
print(f"动销率(G列,索引6)均值: {cat_df.iloc[:, 6].mean() * 100:.1f}%")

# 计算促销强度
active_skus = cat_df.iloc[:, 5].sum()  # F列动销SKU数
discount_skus = cat_df.iloc[:, 26].sum()  # AA列折扣SKU数
promo_strength = (discount_skus / active_skus * 100) if active_skus > 0 else 0
print(f"促销强度({discount_skus}/{active_skus}): {promo_strength:.1f}%")

print("\n" + "=" * 80)
print("Screenshot中的数值对比")
print("=" * 80)
print("总SKU数(含规格): 8508 <- 应该从哪里来?")
print("多规格SKU总数: 1117 <- 应该从哪里来?")
print("动销SKU数: 3336 <- 匹配✅")
print("滞销SKU数: 4514 <- 应该从哪里来?")
print("总销售额(去重后): ¥150,273 <- 应该从哪里来?")
print("动销率: 42.5% <- 应该从哪里来?")
print("唯一多规格商品数: 455 <- 应该从哪里来?")
print("门店爆品数: 13.545... <- Bug! 应该是整数")
print("门店平均折扣: 7.6折 <- 匹配✅")
print("平均SKU单价: ¥17 <- 需要从SKU详细计算")
print("促销强度: 198.0% <- Bug! 不可能>100%")
print("爆款集中度(TOP10): 9.7% <- 需要从SKU详细计算")

print("\n" + "=" * 80)
print("检查爆品SKU列")
print("=" * 80)
print(f"索引23列名: {cat_df.columns[23]}")
print(f"索引23前3行: {cat_df.iloc[:3, 23].tolist()}")
print(f"索引23求和: {cat_df.iloc[:, 23].sum()}")

print("\n查找包含'爆品'的列:")
for i, col in enumerate(cat_df.columns):
    if '爆品' in col:
        print(f"  索引{i}: {col}")
        print(f"    前3行: {cat_df.iloc[:3, i].tolist()}")
        print(f"    求和: {cat_df.iloc[:, i].sum()}")

print("\n" + "=" * 80)
print("检查折扣SKU列")
print("=" * 80)
print(f"索引26列名: {cat_df.columns[26]}")
print(f"索引26前3行: {cat_df.iloc[:3, 26].tolist()}")
print(f"索引26求和: {cat_df.iloc[:, 26].sum()}")

print("\n所有30列的列名:")
for i in range(min(30, len(cat_df.columns))):
    print(f"  索引{i:2d}: {cat_df.columns[i]}")
