import pandas as pd

df = pd.read_excel('reports/淮安生态新城商品10.29 的副本_分析报告.xlsx', sheet_name=3)

print("=" * 80)
print("折扣数据验证")
print("=" * 80)

print(f"\n索引24 ({df.columns[24]}):")
print(df.iloc[:5, 24].tolist())

print(f"\n索引28 ({df.columns[28]}):")
print(df.iloc[:5, 28].tolist())

print(f"\n前5个分类的折扣数据对比:")
for i in range(5):
    cat = df.iloc[i, 0]
    col24 = df.iloc[i, 24]
    col28 = df.iloc[i, 28]
    print(f"{cat}:")
    print(f"  索引24(毛利贡献度): {col24}")
    print(f"  索引28(折扣): {col28}折")
