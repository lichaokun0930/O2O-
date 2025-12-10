"""检查Excel报告版本和缺失的列"""
import pandas as pd

report_file = 'reports/淮安生态新城商品10.29 的副本_分析报告.xlsx'

print("=" * 80)
print("📊 Excel报告版本检查")
print("=" * 80)

# 检查成本分析汇总
print("\n1️⃣ 成本分析汇总Sheet:")
df_cost = pd.read_excel(report_file, sheet_name='成本分析汇总')
print(f"   列名: {df_cost.columns.tolist()}")

required_cols_cost = ['美团一级分类售价毛利率', '美团一级分类定价毛利率', '原价销售额', '定价毛利']
missing_cost = [col for col in required_cols_cost if col not in df_cost.columns]
if missing_cost:
    print(f"   ❌ 缺少新列: {missing_cost}")
else:
    print(f"   ✅ 所有新列都存在")

# 检查高毛利商品TOP50
print("\n2️⃣ 高毛利商品TOP50 Sheet:")
df_high = pd.read_excel(report_file, sheet_name='高毛利商品TOP50')
print(f"   列名: {df_high.columns.tolist()}")

required_cols_high = ['原价', '售价毛利率', '定价毛利率']
missing_high = [col for col in required_cols_high if col not in df_high.columns]
if missing_high:
    print(f"   ❌ 缺少新列: {missing_high}")
else:
    print(f"   ✅ 所有新列都存在")

# 检查低毛利预警商品
print("\n3️⃣ 低毛利预警商品Sheet:")
df_low = pd.read_excel(report_file, sheet_name='低毛利预警商品')
print(f"   列名: {df_low.columns.tolist()}")

required_cols_low = ['原价', '售价毛利率', '定价毛利率']
missing_low = [col for col in required_cols_low if col not in df_low.columns]
if missing_low:
    print(f"   ❌ 缺少新列: {missing_low}")
else:
    print(f"   ✅ 所有新列都存在")

print("\n" + "=" * 80)
print("📋 总结:")
print("=" * 80)

all_missing = missing_cost + missing_high + missing_low
if all_missing:
    print(f"❌ 当前Excel报告是**旧版本**，缺少 {len(set(all_missing))} 个新列")
    print(f"   缺少的列: {set(all_missing)}")
    print("\n💡 解决方案：")
    print("   1. 运行 untitled1.py 重新生成报告")
    print("   2. 确保原始数据包含'原价'、'成本'列")
    print("   3. 重启Dashboard查看新功能")
else:
    print("✅ Excel报告已是新版本，包含所有定价毛利率和售价毛利率列！")

print("=" * 80)
