import pandas as pd

# 读取数据
file_path = r"d:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\鲸星购_分析报告.xlsx"
df = pd.read_excel(file_path, sheet_name='美团一级分类汇总')

print("=" * 80)
print("原始数据统计:")
print(f"总分类数: {len(df)}")
print(f"\n列名: {df.columns.tolist()}")

# 提取关键列
sales_col = df.columns[6]  # 销售额
sku_col = df.columns[4]    # 去重SKU数
ratio_col = df.columns[5]  # SKU占比

print(f"\n关键列:")
print(f"销售额列: {sales_col}")
print(f"SKU数列: {sku_col}")
print(f"SKU占比列: {ratio_col}")

print(f"\n销售额统计:")
print(f"  最小值: {df[sales_col].min()}")
print(f"  最大值: {df[sales_col].max()}")
print(f"  平均值: {df[sales_col].mean():.2f}")
print(f"  销售额>0的分类: {(df[sales_col] > 0).sum()} 个")

print(f"\nSKU数统计:")
print(f"  最小值: {df[sku_col].min()}")
print(f"  最大值: {df[sku_col].max()}")
print(f"  平均值: {df[sku_col].mean():.2f}")
print(f"  SKU数>=10的分类: {(df[sku_col] >= 10).sum()} 个")

print(f"\nSKU占比统计:")
print(f"  最小值: {df[ratio_col].min():.4f}")
print(f"  最大值: {df[ratio_col].max():.4f}")
print(f"  平均值: {df[ratio_col].mean():.4f}")
print(f"  占比>=0.5%的分类: {(df[ratio_col] >= 0.005).sum()} 个")
print(f"  占比>=0.005的分类: {(df[ratio_col] >= 0.005).sum()} 个")

print("\n" + "=" * 80)
print("测试不同过滤条件:")

# 测试条件1: 销售额>0
filter1 = df[sales_col] > 0
print(f"1. 销售额>0: {filter1.sum()} 个分类")

# 测试条件2: SKU>=10
filter2 = df[sku_col] >= 10
print(f"2. SKU数>=10: {filter2.sum()} 个分类")

# 测试条件3: 占比>=0.5%
filter3 = df[ratio_col] >= 0.005
print(f"3. SKU占比>=0.5%: {filter3.sum()} 个分类")

# 测试组合条件
filter_all = filter1 & filter2 & filter3
print(f"\n组合条件 (销售额>0 & SKU>=10 & 占比>=0.5%): {filter_all.sum()} 个分类")

if filter_all.sum() == 0:
    print("\n⚠️ 警告: 组合条件过滤掉了所有数据!")
    print("\n尝试放松条件:")
    
    # 尝试只用两个条件
    filter_loose1 = filter1 & filter2
    print(f"  销售额>0 & SKU>=10: {filter_loose1.sum()} 个分类")
    
    filter_loose2 = filter1 & filter3
    print(f"  销售额>0 & 占比>=0.5%: {filter_loose2.sum()} 个分类")
    
    filter_loose3 = filter2 & filter3
    print(f"  SKU>=10 & 占比>=0.5%: {filter_loose3.sum()} 个分类")
    
    # 显示占比数据分布
    print(f"\nSKU占比数据详情:")
    for idx, row in df.iterrows():
        cat = row[df.columns[0]]
        ratio = row[ratio_col]
        sales = row[sales_col]
        sku = row[sku_col]
        print(f"  {cat}: 占比={ratio:.6f} ({ratio*100:.4f}%), SKU={sku}, 销售额={sales:.2f}")
else:
    print(f"\n✅ 过滤后还有 {filter_all.sum()} 个分类")
    filtered_df = df[filter_all]
    print("\n过滤后的分类:")
    for idx, row in filtered_df.iterrows():
        cat = row[df.columns[0]]
        ratio = row[ratio_col]
        sales = row[sales_col]
        sku = row[sku_col]
        print(f"  {cat}: 占比={ratio*100:.2f}%, SKU={sku}, 销售额=¥{sales:,.2f}")
