import pandas as pd

# 读取Excel文件
xl = pd.ExcelFile(r'd:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\淮安生态新城商品10.29 的副本_分析报告.xlsx')

print("=" * 80)
print("所有Sheet列表")
print("=" * 80)
for i, name in enumerate(xl.sheet_names):
    print(f"{i}: {name}")

print("\n" + "=" * 80)
print("检查成本相关Sheet")
print("=" * 80)
cost_sheets = [name for name in xl.sheet_names if '成本' in name or '毛利' in name]
if cost_sheets:
    print(f"找到成本相关Sheet: {cost_sheets}")
    
    # 读取成本分析汇总
    if '成本分析汇总' in xl.sheet_names:
        cost_df = pd.read_excel(xl, sheet_name='成本分析汇总')
        print(f"\n成本分析汇总 Shape: {cost_df.shape}")
        print(f"列名: {cost_df.columns.tolist()}")
        print(f"\n前3行数据:")
        print(cost_df.head(3))
    
    # 读取高毛利商品
    if '高毛利商品TOP50' in xl.sheet_names:
        margin_df = pd.read_excel(xl, sheet_name='高毛利商品TOP50')
        print(f"\n高毛利商品TOP50 Shape: {margin_df.shape}")
        print(f"总共有 {len(margin_df)} 个高毛利商品")
else:
    print("❌ 未找到成本相关Sheet")
    print("说明: 当前数据中没有成本列，所以untitled1.py没有生成成本分析Sheet")
    
print("\n" + "=" * 80)
print("检查SKU详细报告中是否有成本列")
print("=" * 80)
sku_df = pd.read_excel(xl, sheet_name='详细SKU报告(去重后)')
print(f"SKU报告列名: {sku_df.columns.tolist()}")
has_cost = any('成本' in str(col) or 'cost' in str(col).lower() for col in sku_df.columns)
print(f"\n是否包含成本列: {'是' if has_cost else '否'}")
