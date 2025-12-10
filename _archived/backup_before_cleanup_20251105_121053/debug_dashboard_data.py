# -*- coding: utf-8 -*-
"""调试Dashboard数据加载"""

import pandas as pd
import sys

# 模拟Dashboard的数据加载
class TestDataLoader:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有sheet数据"""
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            print(f"📊 可用的sheet: {sheet_names}")
            
            # 按照dashboard_v2.py中的逻辑加载
            if len(sheet_names) > 3:
                # 第四个sheet（索引3）是美团一级分类详细指标
                self.data['category_l1'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[3])
                print(f"\n✅ 加载Sheet[3]: {sheet_names[3]}")
                print(f"   数据形状: {self.data['category_l1'].shape}")
                print(f"   前5个分类: {list(self.data['category_l1'].iloc[:5, 0])}")
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")

# 测试默认报告
print("=" * 70)
print("测试1: 默认报告文件")
print("=" * 70)
loader1 = TestDataLoader("./reports/竞对分析报告_v3.4_FINAL.xlsx")

print("\n" + "=" * 70)
print("测试2: 用户报告文件")
print("=" * 70)
loader2 = TestDataLoader("./reports/淮安生态新城商品10.29 的副本_分析报告.xlsx")

print("\n" + "=" * 70)
print("🔍 诊断结论:")
print("=" * 70)

if 'category_l1' in loader1.data and not loader1.data['category_l1'].empty:
    cat1_first = loader1.data['category_l1'].iloc[0, 0]
    print(f"默认报告第一个分类: {cat1_first}")

if 'category_l1' in loader2.data and not loader2.data['category_l1'].empty:
    cat2_first = loader2.data['category_l1'].iloc[0, 0]
    print(f"用户报告第一个分类: {cat2_first}")

print("\n⚠️ 如果Dashboard显示的数据与用户报告不符，")
print("   可能原因:")
print("   1. Dashboard使用的是默认报告文件")
print("   2. 需要重新上传用户报告文件")
print("   3. 浏览器缓存了旧数据（需要硬刷新 Ctrl+Shift+R）")
