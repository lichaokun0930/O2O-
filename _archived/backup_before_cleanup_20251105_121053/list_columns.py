import pandas as pd

df = pd.read_excel('reports/淮安生态新城商品10.29 的副本_分析报告.xlsx', sheet_name=3)

print("所有列名:")
for i, col in enumerate(df.columns):
    if '折扣' in col or i in [24, 25, 26, 27, 28]:
        print(f"*** {i}: {col}")
    else:
        print(f"{i}: {col}")
