"""最终验证：W列和Y列到底是什么"""
import pandas as pd

excel_path = './reports/竞对分析报告_v3.4_FINAL.xlsx'
df = pd.read_excel(excel_path, sheet_name='美团一级分类详细指标')

print("=" * 100)
print("📋 关键列验证")
print("=" * 100)

print(f"\nW列(索引22)的列名: {df.columns[22]}")
print(f"Y列(索引24)的列名: {df.columns[24]}")

print("\n" + "=" * 100)
print("📊 休闲食品分类的实际数据")
print("=" * 100)

target_row = df[df.iloc[:, 0] == "休闲食品"].iloc[0]

print(f"\nE列(索引4) - 去重SKU数: {target_row.iloc[4]}")
print(f"W列(索引22) - {df.columns[22]}: {target_row.iloc[22]}")
print(f"Y列(索引24) - {df.columns[24]}: {target_row.iloc[24]}")

print("\n" + "=" * 100)
print("💡 结论")
print("=" * 100)

print(f"""
根据列名和数值:
- W列(索引22) = {df.columns[22]}
  休闲食品的值: {target_row.iloc[22]} (这是SKU数量)
  
- Y列(索引24) = {df.columns[24]}
  休闲食品的值: {target_row.iloc[24]} (这是折扣力度,如3.58折)

如果W列数值({target_row.iloc[22]}) ≈ E列数值({target_row.iloc[4]}),
说明W列确实是"折扣SKU数",且几乎所有SKU都有折扣。
""")
