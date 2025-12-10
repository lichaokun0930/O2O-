import pandas as pd

df = pd.read_excel('reports/淮安生态新城商品10.29 的副本_分析报告.xlsx', sheet_name=3)

print("前5个分类验证:\n")
for i in range(5):
    cat = df.iloc[i, 0]
    e = df.iloc[i, 4]
    i_col = df.iloc[i, 8]
    j = df.iloc[i, 9]
    print(f"{cat}:")
    print(f"  E列(去重SKU): {e}")
    print(f"  I列(活动去重): {i_col}")
    print(f"  J列(活动sku): {j}")
    print(f"  ❌ 错误: 非活动 = {e} - {i_col} = {e-i_col}")
    print(f"  ✅ 正确: 非活动 = {e} - {j} = {e-j}\n")
