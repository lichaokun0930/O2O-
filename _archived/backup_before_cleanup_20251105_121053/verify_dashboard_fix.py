# -*- coding: utf-8 -*-
"""验证Dashboard数据加载修复"""

import pandas as pd

print("=" * 80)
print("📊 Dashboard数据加载修复验证")
print("=" * 80)

# 测试两个报告文件
test_files = [
    ("默认报告", "./reports/竞对分析报告_v3.4_FINAL.xlsx"),
    ("用户报告", "./reports/淮安生态新城商品10.29 的副本_分析报告.xlsx")
]

for file_label, file_path in test_files:
    print(f"\n{'='*80}")
    print(f"📁 测试文件: {file_label}")
    print(f"   路径: {file_path}")
    print(f"{'='*80}")
    
    try:
        # 读取Sheet列表
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        
        print(f"\n📋 Sheet列表（共{len(sheet_names)}个）:")
        for i, name in enumerate(sheet_names):
            marker = ""
            if "一级分类" in name:
                marker = " ✅ 一级分类"
            elif "三级分类" in name:
                marker = " ⚠️ 三级分类"
            elif "校验" in name:
                marker = " 🔍 校验Sheet"
            print(f"   [{i:2d}] {name}{marker}")
        
        # 🔧 新逻辑：按名称查找一级分类Sheet
        target_names = ['美团一级分类详细指标', '一级分类详细指标', '一级分类']
        found_sheet = None
        for sheet_name in sheet_names:
            if any(name in sheet_name for name in target_names):
                found_sheet = sheet_name
                break
        
        if found_sheet:
            print(f"\n✅ 找到一级分类Sheet: '{found_sheet}'")
            df = pd.read_excel(file_path, sheet_name=found_sheet)
            print(f"   数据形状: {df.shape}")
            print(f"   第一列名: {df.columns[0]}")
            print(f"   前5个分类:")
            for i, cat in enumerate(df.iloc[:5, 0], 1):
                print(f"      {i}. {cat}")
            
            # 验证关键列
            key_cols = ['美团一级分类sku数', '美团一级分类动销sku数', '美团一级分类折扣sku数']
            missing = [col for col in key_cols if col not in df.columns]
            if missing:
                print(f"   ⚠️ 缺少列: {missing}")
            else:
                print(f"   ✅ 关键列齐全")
        else:
            print(f"\n❌ 未找到一级分类Sheet！")
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")

print(f"\n{'='*80}")
print("🎯 修复说明:")
print("=" * 80)
print("""
修复前问题:
- Dashboard使用固定索引读取Sheet（如sheet_names[3]）
- 不同报告文件的Sheet顺序不同（有些有校验Sheet，有些没有）
- 导致读取到错误的Sheet

修复后方案:
- 改用Sheet名称匹配，不依赖索引顺序
- 支持多种Sheet名称变体（如"一级分类"、"美团一级分类详细指标"等）
- 兼容所有报告文件格式

建议操作:
1. 重启Dashboard（使用修复后的代码）
2. 浏览器硬刷新（Ctrl+Shift+R）清除缓存
3. 如果仍有问题，上传新报告文件
""")
