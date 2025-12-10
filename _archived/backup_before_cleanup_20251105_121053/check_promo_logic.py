import pandas as pd

# 读取数据
df = pd.read_excel(r'd:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\淮安生态新城商品10.29 的副本_分析报告.xlsx', 
                   sheet_name='美团一级分类详细指标')

print("=" * 80)
print("关键列名对照")
print("=" * 80)
for i in [1, 4, 5, 8, 9, 10, 26]:
    print(f"索引{i:2d}: {df.columns[i]}")

print("\n" + "=" * 80)
print("个人洗护分类的数据示例")
print("=" * 80)
row = df[df.iloc[:,0]=='个人洗护'].iloc[0]
print(f"总SKU数(索引1): {row.iloc[1]}")
print(f"去重SKU(索引4): {row.iloc[4]}")
print(f"动销SKU(索引5): {row.iloc[5]}")
print(f"活动去重SKU(索引8): {row.iloc[8]}")
print(f"活动SKU(索引9): {row.iloc[9]}")
print(f"活动SKU占比(索引10): {row.iloc[10]:.2%}")
print(f"折扣SKU(索引26): {row.iloc[26]}")

print("\n" + "=" * 80)
print("促销强度的几种计算方式对比")
print("=" * 80)

total_sku = df.iloc[:, 1].sum()
dedup_sku = df.iloc[:, 4].sum()
active_sku = df.iloc[:, 5].sum()
activity_sku = df.iloc[:, 9].sum()
discount_sku = df.iloc[:, 26].sum()

print(f"\n方案1: 折扣SKU / 总SKU")
print(f"  = {discount_sku} / {total_sku}")
print(f"  = {discount_sku/total_sku*100:.1f}%")
print(f"  含义: 所有商品中{discount_sku/total_sku*100:.1f}%参与了折扣")

print(f"\n方案2: 折扣SKU / 去重SKU")
print(f"  = {discount_sku} / {dedup_sku}")
print(f"  = {discount_sku/dedup_sku*100:.1f}%")
print(f"  含义: 去重后{discount_sku/dedup_sku*100:.1f}%的商品参与了折扣")

print(f"\n方案3: 折扣SKU / 动销SKU")
print(f"  = {discount_sku} / {active_sku}")
print(f"  = {discount_sku/active_sku*100:.1f}% ❌ 超过100%！")
print(f"  问题: 折扣商品({discount_sku}) > 动销商品({active_sku})")
print(f"  说明: 有 {discount_sku - active_sku} 个折扣商品是滞销的")

print(f"\n方案4: 折扣SKU / 活动SKU（当前实现）")
print(f"  = {discount_sku} / {activity_sku}")
print(f"  = {discount_sku/activity_sku*100:.1f}%")
print(f"  问题: 活动SKU = 折扣SKU，永远是100%，没有意义！")

print("\n" + "=" * 80)
print("建议的促销强度定义")
print("=" * 80)
print(f"✅ 推荐方案1或2，能真实反映促销力度")
print(f"   方案1(总SKU): {discount_sku/total_sku*100:.1f}%")
print(f"   方案2(去重SKU): {discount_sku/dedup_sku*100:.1f}%")

print("\n" + "=" * 80)
print("数据异常分析")
print("=" * 80)
print(f"活动SKU数 = 折扣SKU数 = {activity_sku}")
print(f"这说明在当前数据中，'活动'就等于'折扣'")
print(f"可能的原因:")
print(f"1. 数据源中没有区分'活动'和'折扣'")
print(f"2. 所有活动都是通过折扣实现的")
print(f"3. 列定义可能有问题（活动SKU和折扣SKU应该是不同维度）")
