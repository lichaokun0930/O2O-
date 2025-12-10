"""
重新生成Excel报告 - 快速指南
================================

当前状态：
- Excel报告修改时间: 2025-10-29 18:05:02 (旧版本)
- untitled1.py修改时间: 2025-10-30 10:01:06 (新代码)
- 结论: 需要重新生成报告

操作步骤：
"""

print("=" * 80)
print("📊 重新生成Excel报告 - 快速操作指南")
print("=" * 80)

print("\n🎯 方法1: 直接运行（推荐）")
print("-" * 80)
print("1️⃣ 打开PowerShell终端")
print("2️⃣ 运行命令: python untitled1.py")
print("3️⃣ 根据提示，拖拽原始Excel文件到终端（包含原价和成本的文件）")
print("   💡 提示: 文件名可能类似 '淮安生态新城商品10.29.xlsx' 或 '淮安生态新城商品10.29 的副本.xlsx'")
print("4️⃣ 按回车开始处理")
print("5️⃣ 等待处理完成，新报告会覆盖旧的分析报告")

print("\n🎯 方法2: 查找原始数据文件")
print("-" * 80)

import os
import glob

print("正在搜索可能的原始数据文件...")

# 搜索当前目录和上级目录的xlsx文件
search_paths = [
    ".",
    "..",
    "../../",
]

found_files = []
for path in search_paths:
    pattern = os.path.join(path, "*.xlsx")
    files = glob.glob(pattern)
    for f in files:
        # 排除分析报告和临时文件
        if '_分析报告' not in f and not os.path.basename(f).startswith('~$'):
            size_kb = os.path.getsize(f) / 1024
            # 只显示可能的数据文件（通常小于1MB）
            if size_kb < 1000:
                found_files.append((f, size_kb))

if found_files:
    print(f"\n找到 {len(found_files)} 个可能的原始数据文件：")
    for i, (file, size) in enumerate(found_files, 1):
        print(f"   {i}. {os.path.abspath(file)} ({size:.1f} KB)")
else:
    print("\n❌ 未找到原始数据文件")
    print("   请手动定位包含以下列的Excel文件：")
    print("   - 商品名称、售价、原价、成本、月售、一级分类等")

print("\n" + "=" * 80)
print("⚠️ 重要提示:")
print("=" * 80)
print("1. 原始数据文件必须包含 '原价' 和 'cost'(成本) 列")
print("2. 生成新报告后，关闭并重启Dashboard才能看到新列")
print("3. 新报告将包含以下新列：")
print("   • 成本分析汇总: 原价销售额、定价毛利、美团一级分类售价毛利率、美团一级分类定价毛利率")
print("   • 高毛利TOP50: 原价、售价、售价毛利率、定价毛利率")
print("   • 低毛利预警: 原价、售价、售价毛利率、定价毛利率")
print("=" * 80)

print("\n💡 如果找不到原始文件，请检查:")
print("   - 文件是否在其他文件夹")
print("   - 文件名是否包含特殊字符")
print("   - 是否有备份文件")
print("\n运行命令查看当前目录文件: dir *.xlsx")
print("=" * 80)
