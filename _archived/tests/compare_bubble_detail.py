"""详细对比气泡图展示的数据与原始数据"""
import pandas as pd
import numpy as np

# 读取Excel数据
excel_path = './reports/竞对分析报告_v3.4_FINAL.xlsx'
excel_file = pd.ExcelFile(excel_path)
sheet_names = excel_file.sheet_names

print("=" * 100)
print("🔍 详细对比：气泡图显示数据 vs Excel原始数据")
print("=" * 100)

# 读取美团一级分类详细指标 (用于气泡图)
category_data = pd.read_excel(excel_path, sheet_name=sheet_names[4])

# 读取详细SKU报告 (用于交叉验证)
sku_details = pd.read_excel(excel_path, sheet_name=sheet_names[6])

print(f"\n📊 数据概览:")
print(f"  美团一级分类详细指标: {category_data.shape}")
print(f"  详细SKU报告: {sku_details.shape}")

# 选择几个代表性分类进行对比
sample_categories = ['休闲食品', '饮料/水', '个人洗护', '方便食品', '粮油调味']

print("\n" + "=" * 100)
print("📈 气泡图关键指标对比 (前10个分类按月售排序)")
print("=" * 100)

# 提取气泡图数据
bubble_data = pd.DataFrame({
    '一级分类': category_data.iloc[:, 0],
    '总SKU数': category_data.iloc[:, 1],
    '去重SKU数': category_data.iloc[:, 4],
    '动销SKU数': category_data.iloc[:, 5],
    '动销率': category_data.iloc[:, 6] * 100,
    '月售(件)': category_data.iloc[:, 15],
    '售价销售额(元)': category_data.iloc[:, 18],
    '折扣SKU数': category_data.iloc[:, 22],
    '折扣占比': (category_data.iloc[:, 22] / category_data.iloc[:, 1] * 100).fillna(0)
})

# 计算隐含单价
bubble_data['隐含单价'] = (bubble_data['售价销售额(元)'] / bubble_data['月售(件)']).replace([np.inf, -np.inf], 0).fillna(0)

# 按月售排序,显示前10
top10 = bubble_data.sort_values('月售(件)', ascending=False).head(10)

print("\n排名 | 分类         | 月售(件) | 销售额(元) | 隐含单价 | 总SKU | 动销率  | 折扣占比")
print("-" * 100)
for idx, (i, row) in enumerate(top10.iterrows(), 1):
    print(f"{idx:>2}   | {row['一级分类']:<12} | {row['月售(件)']:>7.0f} | {row['售价销售额(元)']:>9.2f} | "
          f"¥{row['隐含单价']:>6.2f} | {row['总SKU数']:>5.0f} | {row['动销率']:>6.2f}% | {row['折扣占比']:>6.2f}%")

print("\n" + "=" * 100)
print("🔎 交叉验证：从SKU明细反推分类数据")
print("=" * 100)

# 从SKU明细反推各分类的数据
if '一级分类' in sku_details.columns:
    print("\n验证分类 | Excel月售 | 明细反推月售 | 差异   | Excel销售额 | 明细反推销售额 | 差异")
    print("-" * 100)
    
    for cat in sample_categories:
        # 从Excel取值
        excel_row = category_data[category_data.iloc[:, 0] == cat]
        if excel_row.empty:
            continue
            
        excel_monthly_sales = excel_row.iloc[0, 15]
        excel_revenue = excel_row.iloc[0, 18]
        
        # 从SKU明细反推
        cat_skus = sku_details[sku_details['一级分类'] == cat]
        
        if not cat_skus.empty and '月售' in cat_skus.columns and '售价销售额' in cat_skus.columns:
            detail_monthly_sales = cat_skus['月售'].sum()
            detail_revenue = cat_skus['售价销售额'].sum()
            
            sales_diff = detail_monthly_sales - excel_monthly_sales
            revenue_diff = detail_revenue - excel_revenue
            
            print(f"{cat:<12} | {excel_monthly_sales:>8.0f} | {detail_monthly_sales:>12.0f} | "
                  f"{sales_diff:>+6.0f} | {excel_revenue:>11.2f} | {detail_revenue:>14.2f} | {revenue_diff:>+7.2f}")

print("\n" + "=" * 100)
print("⚠️ 潜在问题分析")
print("=" * 100)

# 1. 检查销售额为0但有月售的分类
zero_revenue_with_sales = bubble_data[(bubble_data['售价销售额(元)'] == 0) & (bubble_data['月售(件)'] > 0)]
if not zero_revenue_with_sales.empty:
    print(f"\n1️⃣ ⚠️ 有月售但销售额为0的分类 ({len(zero_revenue_with_sales)}个):")
    for _, row in zero_revenue_with_sales.iterrows():
        print(f"   - {row['一级分类']}: 月售={row['月售(件)']:.0f}件, 销售额=¥{row['售价销售额(元)']:.2f}")
else:
    print(f"\n1️⃣ ✅ 没有月售但销售额为0的异常分类")

# 2. 检查销售额很高但月售很低的分类 (隐含单价 > ¥50)
high_price_cats = bubble_data[bubble_data['隐含单价'] > 50]
if not high_price_cats.empty:
    print(f"\n2️⃣ ⚠️ 隐含单价异常高的分类 (单价 > ¥50, 共{len(high_price_cats)}个):")
    for _, row in high_price_cats.iterrows():
        print(f"   - {row['一级分类']}: 月售={row['月售(件)']:.0f}件, 销售额=¥{row['售价销售额(元)']:.2f}, 隐含单价=¥{row['隐含单价']:.2f}")
else:
    print(f"\n2️⃣ ✅ 没有隐含单价异常高的分类")

# 3. 检查动销率异常低的分类 (< 10%)
low_active_rate = bubble_data[bubble_data['动销率'] < 10]
if not low_active_rate.empty:
    print(f"\n3️⃣ ⚠️ 动销率异常低的分类 (< 10%, 共{len(low_active_rate)}个):")
    for _, row in low_active_rate.sort_values('动销率').iterrows():
        print(f"   - {row['一级分类']}: 动销率={row['动销率']:.2f}%, 动销SKU={row['动销SKU数']:.0f}/{row['去重SKU数']:.0f}")
else:
    print(f"\n3️⃣ ✅ 没有动销率异常低的分类")

# 4. 检查折扣占比异常的分类
high_discount = bubble_data[bubble_data['折扣占比'] > 95]
if not high_discount.empty:
    print(f"\n4️⃣ 💡 高折扣占比分类 (> 95%, 共{len(high_discount)}个):")
    for _, row in high_discount.sort_values('折扣占比', ascending=False).iterrows():
        print(f"   - {row['一级分类']}: 折扣占比={row['折扣占比']:.2f}%, 折扣SKU={row['折扣SKU数']:.0f}/{row['总SKU数']:.0f}")
else:
    print(f"\n4️⃣ 没有高折扣占比的分类")

print("\n" + "=" * 100)
print("📊 数据分布统计")
print("=" * 100)

print(f"\n月售分布:")
print(f"  最小值: {bubble_data['月售(件)'].min():.0f}件")
print(f"  25分位: {bubble_data['月售(件)'].quantile(0.25):.0f}件")
print(f"  中位数: {bubble_data['月售(件)'].median():.0f}件")
print(f"  75分位: {bubble_data['月售(件)'].quantile(0.75):.0f}件")
print(f"  最大值: {bubble_data['月售(件)'].max():.0f}件")
print(f"  平均值: {bubble_data['月售(件)'].mean():.0f}件")

print(f"\n销售额分布:")
print(f"  最小值: ¥{bubble_data['售价销售额(元)'].min():.2f}")
print(f"  25分位: ¥{bubble_data['售价销售额(元)'].quantile(0.25):.2f}")
print(f"  中位数: ¥{bubble_data['售价销售额(元)'].median():.2f}")
print(f"  75分位: ¥{bubble_data['售价销售额(元)'].quantile(0.75):.2f}")
print(f"  最大值: ¥{bubble_data['售价销售额(元)'].max():.2f}")
print(f"  平均值: ¥{bubble_data['售价销售额(元)'].mean():.2f}")

print(f"\n隐含单价分布:")
valid_prices = bubble_data[bubble_data['隐含单价'] > 0]['隐含单价']
print(f"  最小值: ¥{valid_prices.min():.2f}")
print(f"  25分位: ¥{valid_prices.quantile(0.25):.2f}")
print(f"  中位数: ¥{valid_prices.median():.2f}")
print(f"  75分位: ¥{valid_prices.quantile(0.75):.2f}")
print(f"  最大值: ¥{valid_prices.max():.2f}")
print(f"  平均值: ¥{valid_prices.mean():.2f}")

print("\n" + "=" * 100)
print("✅ 检查完成")
print("=" * 100)
