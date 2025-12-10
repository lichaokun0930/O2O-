"""诊断定价毛利率和售价毛利率不显示的问题"""
import pandas as pd
import os
from datetime import datetime

print("=" * 80)
print("🔍 定价毛利率和售价毛利率不显示问题诊断")
print("=" * 80)

report_file = 'reports/淮安生态新城商品10.29 的副本_分析报告.xlsx'

# 1. 检查文件修改时间
print("\n📅 1. 检查Excel报告生成时间:")
if os.path.exists(report_file):
    mod_time = os.path.getmtime(report_file)
    mod_datetime = datetime.fromtimestamp(mod_time)
    print(f"   文件路径: {report_file}")
    print(f"   最后修改时间: {mod_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查untitled1.py修改时间
    untitled_file = 'untitled1.py'
    if os.path.exists(untitled_file):
        untitled_time = os.path.getmtime(untitled_file)
        untitled_datetime = datetime.fromtimestamp(untitled_time)
        print(f"\n   untitled1.py最后修改时间: {untitled_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if untitled_datetime > mod_datetime:
            print(f"   ⚠️ 警告: untitled1.py在Excel报告生成后被修改过！")
            print(f"   ⏰ 时间差: {(untitled_datetime - mod_datetime).total_seconds() / 60:.1f}分钟")
        else:
            print(f"   ✅ Excel报告是在untitled1.py修改后生成的")
else:
    print(f"   ❌ 文件不存在: {report_file}")

# 2. 检查三个Sheet的列结构
print("\n📊 2. 检查各Sheet的列结构:")

sheets_to_check = {
    '成本分析汇总': ['美团一级分类售价毛利率', '美团一级分类定价毛利率', '原价销售额', '定价毛利'],
    '高毛利商品TOP50': ['原价', '售价', '售价毛利率', '定价毛利率'],
    '低毛利预警商品': ['原价', '售价', '售价毛利率', '定价毛利率']
}

all_issues = []

for sheet_name, expected_cols in sheets_to_check.items():
    print(f"\n   📄 {sheet_name}:")
    try:
        df = pd.read_excel(report_file, sheet_name=sheet_name)
        actual_cols = df.columns.tolist()
        print(f"      实际列数: {len(actual_cols)}")
        print(f"      实际列名: {actual_cols}")
        
        missing = [col for col in expected_cols if col not in actual_cols]
        if missing:
            print(f"      ❌ 缺少列: {missing}")
            all_issues.extend(missing)
        else:
            print(f"      ✅ 所有期望列都存在")
            
    except Exception as e:
        print(f"      ❌ 读取失败: {e}")
        all_issues.append(f"{sheet_name}读取失败")

# 3. 检查代码修改是否生效
print("\n💻 3. 检查untitled1.py代码修改:")
try:
    with open('untitled1.py', 'r', encoding='utf-8') as f:
        code = f.read()
    
    keywords = ['售价毛利率', '定价毛利率', '定价毛利']
    found_keywords = {kw: kw in code for kw in keywords}
    
    print(f"   关键代码检查:")
    for kw, found in found_keywords.items():
        status = "✅" if found else "❌"
        print(f"      {status} '{kw}' 在代码中: {found}")
    
    if all(found_keywords.values()):
        print(f"\n   ✅ 代码修改已完成")
    else:
        print(f"\n   ❌ 代码修改不完整")
        all_issues.append("代码修改不完整")
        
except Exception as e:
    print(f"   ❌ 无法读取代码: {e}")

# 4. 总结和建议
print("\n" + "=" * 80)
print("📋 诊断总结:")
print("=" * 80)

if all_issues:
    unique_issues = set(all_issues)
    print(f"\n❌ 发现 {len(unique_issues)} 个问题:")
    for i, issue in enumerate(unique_issues, 1):
        print(f"   {i}. {issue}")
    
    print("\n💡 解决方案:")
    print("   1️⃣ 确认代码已修改（检查上方'代码修改'部分）")
    print("   2️⃣ 重新运行 untitled1.py 生成新的Excel报告：")
    print("      命令: python untitled1.py")
    print("      或拖拽原始数据文件到终端运行")
    print("   3️⃣ 生成完成后，重启Dashboard验证")
    print("   4️⃣ 新报告应该包含以下新列：")
    print("      • 成本分析汇总: 原价销售额、定价毛利、售价毛利率、定价毛利率")
    print("      • 高/低毛利表: 原价、售价毛利率、定价毛利率")
else:
    print("\n✅ 所有检查通过！")
    print("   Excel报告已是最新版本，包含所有定价毛利率和售价毛利率数据")
    print("   如果Dashboard仍不显示，请重启Dashboard")

print("=" * 80)
