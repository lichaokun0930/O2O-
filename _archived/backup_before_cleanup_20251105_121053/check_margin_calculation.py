import pandas as pd

# 读取低毛利预警商品数据
df = pd.read_excel(r'd:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\淮安生态新城商品10.29 的副本_分析报告.xlsx',
                   sheet_name='低毛利预警商品')

print("=" * 100)
print("低毛利预警商品数据检查")
print("=" * 100)

print(f"\n数据维度: {df.shape}")
print(f"\n列名:")
for i, col in enumerate(df.columns):
    print(f"  {i}: {col}")

print("\n" + "=" * 100)
print("前10行数据详细检查")
print("=" * 100)

for idx in range(min(10, len(df))):
    row = df.iloc[idx]
    print(f"\n商品 {idx+1}: {row['商品名称'][:30]}...")
    print(f"  售价: {row['售价']}")
    print(f"  cost: {row['cost']}")
    print(f"  毛利: {row['毛利']}")
    print(f"  毛利率: {row['毛利率']}")
    print(f"  月售: {row['月售']}")
    print(f"  售价销售额: {row['售价销售额']}")
    print(f"  成本销售额: {row['成本销售额']}")
    
    # 手动计算验证
    manual_margin = row['售价'] - row['cost']
    manual_margin_rate = (manual_margin / row['售价']) if row['售价'] > 0 else 0
    
    print(f"\n  手动验证:")
    print(f"    毛利 = 售价 - 成本 = {row['售价']} - {row['cost']} = {manual_margin}")
    print(f"    毛利率 = 毛利 / 售价 = {manual_margin} / {row['售价']} = {manual_margin_rate:.2%}")
    
    # 检查异常
    if abs(row['毛利率']) > 1:
        print(f"  ❌ 异常！毛利率 {row['毛利率']} 超过100%")
    if row['毛利率'] < 0:
        print(f"  ⚠️ 负毛利率！售价 {row['售价']} < 成本 {row['cost']}")

print("\n" + "=" * 100)
print("毛利率统计")
print("=" * 100)

print(f"毛利率最小值: {df['毛利率'].min()}")
print(f"毛利率最大值: {df['毛利率'].max()}")
print(f"毛利率平均值: {df['毛利率'].mean():.2%}")
print(f"\n毛利率>1的商品数: {(df['毛利率'] > 1).sum()}")
print(f"毛利率<0的商品数: {(df['毛利率'] < 0).sum()}")
print(f"毛利率在[-1, 1]之间的商品数: {((df['毛利率'] >= -1) & (df['毛利率'] <= 1)).sum()}")

print("\n" + "=" * 100)
print("异常数据示例")
print("=" * 100)

# 超过100%的
high_margin = df[df['毛利率'] > 1].copy()
if len(high_margin) > 0:
    print(f"\n毛利率>100%的商品 ({len(high_margin)}个):")
    for idx in range(min(3, len(high_margin))):
        row = high_margin.iloc[idx]
        print(f"  {row['商品名称'][:30]}: 售价={row['售价']}, 成本={row['cost']}, 毛利率={row['毛利率']}")

# 负毛利率的
negative_margin = df[df['毛利率'] < 0].copy()
if len(negative_margin) > 0:
    print(f"\n负毛利率的商品 ({len(negative_margin)}个):")
    for idx in range(min(3, len(negative_margin))):
        row = negative_margin.iloc[idx]
        print(f"  {row['商品名称'][:30]}: 售价={row['售价']}, 成本={row['cost']}, 毛利率={row['毛利率']:.2%}")
