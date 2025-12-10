"""检查有月售但销售额为0的分类的原始SKU数据"""
import pandas as pd

# 读取Excel数据
excel_path = './reports/竞对分析报告_v3.4_FINAL.xlsx'
excel_file = pd.ExcelFile(excel_path)
sheet_names = excel_file.sheet_names

print("=" * 100)
print("🔍 检查异常分类的SKU明细")
print("=" * 100)

# 读取详细SKU报告
sku_details = pd.read_excel(excel_path, sheet_name=sheet_names[6])

# 异常分类: 有月售但销售额为0
problem_categories = ['熟食/鲜食', '蔬菜/豆制品']

for cat in problem_categories:
    print(f"\n{'=' * 100}")
    print(f"📊 分类: {cat}")
    print("=" * 100)
    
    cat_skus = sku_details[sku_details['一级分类'] == cat]
    
    if cat_skus.empty:
        print(f"⚠️ 该分类没有SKU数据")
        continue
    
    print(f"\n📈 基本统计:")
    print(f"  SKU总数: {len(cat_skus)}")
    print(f"  总月售: {cat_skus['月售'].sum():.0f}件")
    print(f"  总销售额: ¥{cat_skus['售价销售额'].sum():.2f}")
    
    print(f"\n🔍 详细SKU列表:")
    print("-" * 100)
    
    # 显示关键列
    display_cols = ['商品名称', '售价', '原价', '月售', '原价销售额', '售价销售额', '库存', '规格']
    existing_cols = [col for col in display_cols if col in cat_skus.columns]
    
    for idx, row in cat_skus.iterrows():
        print(f"\n  商品: {row['商品名称']}")
        for col in existing_cols[1:]:  # 跳过商品名称
            if col in row:
                value = row[col]
                if pd.notna(value):
                    if col in ['售价', '原价', '原价销售额', '售价销售额']:
                        print(f"    {col}: ¥{value:.2f}")
                    else:
                        print(f"    {col}: {value}")
                else:
                    print(f"    {col}: [空值]")
    
    # 检查是否有价格为0的商品
    zero_price = cat_skus[cat_skus['售价'] == 0]
    if not zero_price.empty:
        print(f"\n  ⚠️ 发现 {len(zero_price)} 个售价为0的SKU")
    
    # 检查是否有价格缺失的商品
    null_price = cat_skus[cat_skus['售价'].isna()]
    if not null_price.empty:
        print(f"\n  ⚠️ 发现 {len(null_price)} 个售价缺失的SKU")
    
    # 检查月售不为0但销售额为0的商品
    sales_but_no_revenue = cat_skus[(cat_skus['月售'] > 0) & (cat_skus['售价销售额'] == 0)]
    if not sales_but_no_revenue.empty:
        print(f"\n  🚨 有月售但销售额为0的SKU ({len(sales_but_no_revenue)}个):")
        for idx, row in sales_but_no_revenue.iterrows():
            print(f"    - {row['商品名称']}: 月售={row['月售']}件, 售价={row['售价']}, 销售额=¥{row['售价销售额']:.2f}")

print("\n" + "=" * 100)
print("✅ 检查完成")
print("=" * 100)

print("\n💡 结论:")
print("  如果发现售价为0或缺失的商品,说明这是数据源问题,不是计算错误。")
print("  建议在数据清洗阶段过滤掉这些异常商品,或者在气泡图中添加数据过滤。")
