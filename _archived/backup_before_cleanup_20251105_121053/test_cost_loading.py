import pandas as pd
import sys
import os

# 模拟Dashboard的DataLoader
class TestDataLoader:
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.data = {}
        self.load_data_from_excel()
    
    def load_data_from_excel(self):
        """模拟Dashboard的数据加载逻辑"""
        try:
            print(f"📂 开始加载: {self.excel_path}")
            sheet_names = pd.ExcelFile(self.excel_path).sheet_names
            print(f"📋 Sheet总数: {len(sheet_names)}")
            
            # 定义Sheet名称映射表
            sheet_mapping = {
                'kpi': ['核心指标对比', 'KPI', '核心指标'],
                'role_analysis': ['商品角色分析', '角色分析'],
                'price_analysis': ['价格带分析', '价格分析'],
                'category_l1': ['美团一级分类详细指标', '一级分类详细指标', '一级分类'],
                'sku_details': ['详细SKU报告(去重后)', 'SKU报告', '详细SKU报告']
            }
            
            # 遍历所有Sheet，按名称匹配
            for key, possible_names in sheet_mapping.items():
                for sheet_name in sheet_names:
                    if any(name in sheet_name for name in possible_names):
                        self.data[key] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                        print(f"✅ 加载 {key}: '{sheet_name}' - Shape: {self.data[key].shape}")
                        break
            
            # 加载成本分析相关Sheet（如果存在）
            print("\n🔍 查找成本相关Sheet...")
            for sheet_name in sheet_names:
                if '成本分析汇总' in sheet_name:
                    self.data['cost_summary'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    print(f"✅ 加载成本分析汇总数据 - Shape: {self.data['cost_summary'].shape}")
                elif '高毛利商品' in sheet_name:
                    self.data['high_margin_products'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    print(f"✅ 加载高毛利商品数据 - Shape: {self.data['high_margin_products'].shape}")
                elif '低毛利预警' in sheet_name:
                    self.data['low_margin_warning'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    print(f"✅ 加载低毛利预警数据 - Shape: {self.data['low_margin_warning'].shape}")
            
            # 填充缺失的数据
            for key in ['kpi', 'category_l1', 'role_analysis', 'price_analysis', 'sku_details', 
                        'cost_summary', 'high_margin_products', 'low_margin_warning']:
                if key not in self.data:
                    self.data[key] = pd.DataFrame()
                    print(f"⚠️ {key} 未找到，设置为空DataFrame")
            
            print(f"\n✅ 数据加载完成")
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            import traceback
            traceback.print_exc()

# 测试加载
excel_path = r'd:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\淮安生态新城商品10.29 的副本_分析报告.xlsx'
print("=" * 80)
print("模拟Dashboard数据加载测试")
print("=" * 80)

loader = TestDataLoader(excel_path)

print("\n" + "=" * 80)
print("检查成本数据是否正确加载")
print("=" * 80)

cost_summary = loader.data.get('cost_summary', pd.DataFrame())
high_margin = loader.data.get('high_margin_products', pd.DataFrame())
low_margin = loader.data.get('low_margin_warning', pd.DataFrame())

print(f"cost_summary.empty: {cost_summary.empty}")
print(f"high_margin.empty: {high_margin.empty}")
print(f"low_margin.empty: {low_margin.empty}")

if cost_summary.empty and high_margin.empty and low_margin.empty:
    print("\n❌ 触发'未检测到成本数据'警告！")
else:
    print("\n✅ 成本数据加载成功！")
    if not cost_summary.empty:
        print(f"\n成本分析汇总: {cost_summary.shape}")
        print(f"列名: {cost_summary.columns.tolist()}")
    if not high_margin.empty:
        print(f"\n高毛利商品: {high_margin.shape}")
    if not low_margin.empty:
        print(f"\n低毛利预警: {low_margin.shape}")
