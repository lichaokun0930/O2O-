# -*- coding: utf-8 -*-
"""
测试MultiStoreDataLoader功能
"""
import sys
import os

# 只导入必要的类
import pandas as pd
import re

class DataLoader:
    """简化版DataLoader用于测试"""
    def __init__(self, excel_path):
        self.excel_path = excel_path
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            
            if len(sheet_names) > 0:
                self.data['kpi'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[0])
            if len(sheet_names) > 2:
                self.data['price_analysis'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[2])
            if len(sheet_names) > 4:
                self.data['category_l1'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[4])
            if len(sheet_names) > 1:
                self.data['role_analysis'] = pd.read_excel(self.excel_path, sheet_name=sheet_names[1])
            
            for key in ['kpi', 'category_l1', 'role_analysis', 'price_analysis']:
                if key not in self.data:
                    self.data[key] = pd.DataFrame()
                    
        except Exception as e:
            print(f"❌ 加载失败: {e}")
            self.data = {k: pd.DataFrame() for k in ['kpi', 'category_l1', 'role_analysis', 'price_analysis']}
    
    def get_kpi_summary(self):
        if self.data['kpi'].empty:
            return {}
        
        kpi_df = self.data['kpi']
        if len(kpi_df) > 0:
            row = kpi_df.iloc[0]
            summary = {}
            for i, col in enumerate(kpi_df.columns):
                value = row.iloc[i] if i < len(row) else 0
                if i == 0:
                    summary['门店'] = value
                elif i == 1:
                    summary['总SKU数(含规格)'] = value
                elif i == 6:
                    summary['动销SKU数'] = value
                elif i == 8:
                    summary['总销售额(去重后)'] = value
                elif i == 9:
                    summary['动销率'] = value
            return summary
        return {}
    
    def get_category_analysis(self):
        return self.data['category_l1']
    
    def get_role_analysis(self):
        return self.data['role_analysis']
    
    def get_price_analysis(self):
        return self.data['price_analysis']


class MultiStoreDataLoader:
    """多门店数据加载器"""
    
    def __init__(self, reports_dir='./reports'):
        self.reports_dir = reports_dir
        self.store_data = {}
        self.scan_and_load_stores()
    
    def scan_and_load_stores(self):
        """扫描reports目录并加载所有门店数据"""
        try:
            pattern = re.compile(r'竞对分析报告[_-](.+?)\.xlsx$')
            
            for filename in os.listdir(self.reports_dir):
                match = pattern.match(filename)
                if match:
                    store_name = match.group(1)
                    
                    # 跳过带时间戳的文件和临时文件
                    if re.match(r'\d{8}', store_name) or store_name.startswith('~$'):
                        continue
                    
                    # 清理门店名称
                    store_name = store_name.replace('_FINAL', '').replace(' (2)', '').replace('v3.4_', '').strip()
                    
                    # 加载数据
                    filepath = os.path.join(self.reports_dir, filename)
                    try:
                        self.store_data[store_name] = DataLoader(filepath)
                        print(f"✅ 加载竞对门店: {store_name}")
                    except Exception as e:
                        print(f"⚠️ 跳过文件 {filename}: {e}")
            
            print(f"\n🏪 成功加载 {len(self.store_data)} 个竞对门店")
            print(f"📋 门店列表: {list(self.store_data.keys())}")
            
        except Exception as e:
            print(f"❌ 扫描门店失败: {e}")
    
    def get_store_list(self):
        """获取所有门店名称列表"""
        return list(self.store_data.keys())
    
    def get_multi_store_kpi(self, store_names=None):
        """获取多门店KPI对比数据"""
        if store_names is None:
            store_names = self.get_store_list()
        
        kpi_list = []
        for store in store_names:
            if store in self.store_data:
                kpi = self.store_data[store].get_kpi_summary()
                kpi['门店名称'] = store
                kpi_list.append(kpi)
        
        if kpi_list:
            df = pd.DataFrame(kpi_list)
            cols = ['门店名称'] + [col for col in df.columns if col != '门店名称']
            return df[cols]
        else:
            return pd.DataFrame()


# 测试代码
if __name__ == "__main__":
    print("=" * 70)
    print("测试MultiStoreDataLoader")
    print("=" * 70)
    
    # 创建加载器
    multi_loader = MultiStoreDataLoader('./reports')
    
    # 显示门店列表
    stores = multi_loader.get_store_list()
    print(f"\n📊 门店总数: {len(stores)}")
    print(f"📋 门店列表:")
    for i, store in enumerate(stores, 1):
        print(f"   {i}. {store}")
    
    # 测试KPI对比
    if len(stores) >= 2:
        print(f"\n🔍 KPI对比测试（前2个门店）:")
        test_stores = stores[:2]
        kpi_df = multi_loader.get_multi_store_kpi(test_stores)
        print(kpi_df.to_string())
    
    print("\n✅ 测试完成!")
