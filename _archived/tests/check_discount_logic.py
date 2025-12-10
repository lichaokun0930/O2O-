"""检查折扣占比计算逻辑"""
import pandas as pd

# 读取Excel数据
excel_path = './reports/竞对分析报告_v3.4_FINAL.xlsx'
excel_file = pd.ExcelFile(excel_path)
sheet_names = excel_file.sheet_names

print("=" * 120)
print("🔍 折扣占比计算逻辑分析")
print("=" * 120)

# 读取美团一级分类详细指标
category_data = pd.read_excel(excel_path, sheet_name=sheet_names[4])

# 读取详细SKU报告
sku_details = pd.read_excel(excel_path, sheet_name=sheet_names[6])

print(f"\n📊 折扣定义:")
print(f"  折扣 = (原价 - 售价) / 原价")
print(f"  折扣SKU = 折扣 > 1% (ACTIVITY_THRESHOLD = 0.01)")
print(f"  折扣占比 = 折扣SKU数 / 总SKU数 × 100%")

print("\n" + "=" * 120)
print("📈 各分类折扣占比详情")
print("=" * 120)

# 提取数据
result_df = pd.DataFrame({
    '一级分类': category_data.iloc[:, 0],
    '总SKU数': category_data.iloc[:, 1],
    '折扣SKU数': category_data.iloc[:, 22],
    '折扣占比(%)': (category_data.iloc[:, 22] / category_data.iloc[:, 1] * 100).fillna(0)
})

# 按折扣占比降序排列
result_df = result_df.sort_values('折扣占比(%)', ascending=False)

print("\n排名 | 分类             | 总SKU数 | 折扣SKU数 | 折扣占比  | 无折扣SKU数")
print("-" * 120)
for idx, (i, row) in enumerate(result_df.iterrows(), 1):
    no_discount = row['总SKU数'] - row['折扣SKU数']
    print(f"{idx:>2}   | {row['一级分类']:<16} | {row['总SKU数']:>7.0f} | {row['折扣SKU数']:>9.0f} | "
          f"{row['折扣占比(%)']:>8.2f}% | {no_discount:>11.0f}")

print("\n" + "=" * 120)
print("🔍 交叉验证：从SKU明细反推折扣数据")
print("=" * 120)

# 选择几个代表性分类进行验证
sample_categories = ['休闲食品', '饮料/营养冲调', '个人洗护', '粮油调味干货', '家居日用']

print("\n分类             | Excel总SKU | Excel折扣SKU | Excel折扣占比 | 明细总SKU | 明细折扣SKU | 明细折扣占比 | 差异")
print("-" * 120)

for cat in sample_categories:
    # 从Excel取值
    excel_row = category_data[category_data.iloc[:, 0] == cat]
    if excel_row.empty:
        continue
    
    excel_total = excel_row.iloc[0, 1]
    excel_discount = excel_row.iloc[0, 22]
    excel_ratio = (excel_discount / excel_total * 100) if excel_total > 0 else 0
    
    # 从SKU明细计算
    cat_skus = sku_details[sku_details['一级分类'] == cat]
    
    if not cat_skus.empty and '原价' in cat_skus.columns and '售价' in cat_skus.columns:
        # 计算每个SKU的折扣
        detail_total = len(cat_skus)
        
        # 计算折扣 = (原价 - 售价) / 原价
        cat_skus_copy = cat_skus.copy()
        cat_skus_copy['折扣'] = 0
        valid_mask = (cat_skus_copy['原价'] > 0) & (cat_skus_copy['售价'] >= 0)
        cat_skus_copy.loc[valid_mask, '折扣'] = (cat_skus_copy['原价'] - cat_skus_copy['售价']) / cat_skus_copy['原价']
        cat_skus_copy.loc[cat_skus_copy['折扣'] < 0, '折扣'] = 0
        
        # 折扣SKU数 (折扣 > 1%)
        detail_discount = (cat_skus_copy['折扣'] > 0.01).sum()
        detail_ratio = (detail_discount / detail_total * 100) if detail_total > 0 else 0
        
        diff = detail_ratio - excel_ratio
        
        print(f"{cat:<16} | {excel_total:>10.0f} | {excel_discount:>12.0f} | {excel_ratio:>13.2f}% | "
              f"{detail_total:>9} | {detail_discount:>11} | {detail_ratio:>12.2f}% | {diff:>+5.2f}%")

print("\n" + "=" * 120)
print("📊 折扣分布统计")
print("=" * 120)

# 从SKU明细计算所有商品的折扣分布
if '原价' in sku_details.columns and '售价' in sku_details.columns:
    sku_copy = sku_details.copy()
    sku_copy['折扣'] = 0
    valid_mask = (sku_copy['原价'] > 0) & (sku_copy['售价'] >= 0)
    sku_copy.loc[valid_mask, '折扣'] = (sku_copy['原价'] - sku_copy['售价']) / sku_copy['原价']
    sku_copy.loc[sku_copy['折扣'] < 0, '折扣'] = 0
    
    total_skus = len(sku_copy)
    discount_ranges = [
        ('0% (无折扣)', sku_copy['折扣'] == 0),
        ('0-1% (极小折扣)', (sku_copy['折扣'] > 0) & (sku_copy['折扣'] <= 0.01)),
        ('1-5% (小折扣)', (sku_copy['折扣'] > 0.01) & (sku_copy['折扣'] <= 0.05)),
        ('5-10% (中折扣)', (sku_copy['折扣'] > 0.05) & (sku_copy['折扣'] <= 0.10)),
        ('10-20% (大折扣)', (sku_copy['折扣'] > 0.10) & (sku_copy['折扣'] <= 0.20)),
        ('20-30%', (sku_copy['折扣'] > 0.20) & (sku_copy['折扣'] <= 0.30)),
        ('30-50%', (sku_copy['折扣'] > 0.30) & (sku_copy['折扣'] <= 0.50)),
        ('>50% (超大折扣)', sku_copy['折扣'] > 0.50),
    ]
    
    print(f"\n全部SKU折扣分布 (总计: {total_skus} 个):")
    print("-" * 120)
    print("折扣范围          | SKU数量 | 占比    | 累计占比")
    print("-" * 120)
    
    cumulative = 0
    for label, mask in discount_ranges:
        count = mask.sum()
        ratio = (count / total_skus * 100) if total_skus > 0 else 0
        cumulative += ratio
        print(f"{label:<16} | {count:>7} | {ratio:>6.2f}% | {cumulative:>7.2f}%")
    
    print("\n" + "=" * 120)
    print("⚠️ 关键发现:")
    print("=" * 120)
    
    no_discount = (sku_copy['折扣'] == 0).sum()
    tiny_discount = ((sku_copy['折扣'] > 0) & (sku_copy['折扣'] <= 0.01)).sum()
    has_discount = (sku_copy['折扣'] > 0.01).sum()
    
    print(f"\n1️⃣ 折扣阈值设置: > 1% (ACTIVITY_THRESHOLD = 0.01)")
    print(f"   - 无折扣SKU (0%):        {no_discount:>5} 个 ({no_discount/total_skus*100:.2f}%)")
    print(f"   - 微小折扣 (0-1%):       {tiny_discount:>5} 个 ({tiny_discount/total_skus*100:.2f}%)")
    print(f"   - 有效折扣SKU (>1%):     {has_discount:>5} 个 ({has_discount/total_skus*100:.2f}%)")
    
    print(f"\n2️⃣ 为什么折扣占比这么高?")
    print(f"   因为折扣阈值设置为 >1%,只要原价和售价相差超过1%就算折扣SKU。")
    print(f"   这意味着即使是2.50元商品卖2.48元(折扣0.8%),也不算折扣SKU。")
    print(f"   而2.50元商品卖2.45元(折扣2%),就算折扣SKU。")
    
    # 找出高折扣商品示例
    high_discount = sku_copy[sku_copy['折扣'] > 0.3].sort_values('折扣', ascending=False).head(5)
    if not high_discount.empty:
        print(f"\n3️⃣ 高折扣商品示例 (折扣 > 30%):")
        for idx, row in high_discount.iterrows():
            print(f"   - {row['商品名称'][:40]:<40}: 原价=¥{row['原价']:.2f}, 售价=¥{row['售价']:.2f}, "
                  f"折扣={row['折扣']*100:.1f}%, 分类={row['一级分类']}")

print("\n" + "=" * 120)
print("✅ 检查完成")
print("=" * 120)
