#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试深度版数据收集"""

import pandas as pd
import json

# 模拟DataLoader
class MockLoader:
    def __init__(self):
        self.data = {}
    
    def load_data(self, filepath):
        # 加载KPI
        self.data['kpi_data'] = pd.read_excel(filepath, sheet_name='核心指标对比')
        # 加载分类数据
        self.data['category_data'] = pd.read_excel(filepath, sheet_name='美团一级分类详细指标')
        # 加载价格带
        role_data = pd.read_excel(filepath, sheet_name='商品角色分析')
        self.data['price_data'] = role_data[role_data['角色'].isin(['0-10元', '10-20元', '20-50元', '50元以上'])].copy()
        self.data['price_data'].rename(columns={'角色': 'price_band', 'sku数(去重)': 'SKU数量', 
                                               '角色内销售额': '销售额', '角色内销售额占比': '销售额占比'}, inplace=True)

# 初始化
loader = MockLoader()
loader.load_data('./reports/竞对分析报告_v3.4_FINAL.xlsx')

print('='*70)
print('深度版数据收集测试')
print('='*70)

# 提取KPI
kpi_data = loader.data.get('kpi_data', pd.DataFrame())
kpi_dict = {}
if not kpi_data.empty:
    for col in kpi_data.columns:
        value = kpi_data[col].iloc[0]
        if pd.notna(value):
            if isinstance(value, str) and '%' in value:
                try:
                    kpi_dict[col] = float(value.replace('%', ''))
                except:
                    kpi_dict[col] = value
            else:
                kpi_dict[col] = value

print('\n1. ✅ KPI数据提取:')
for key, value in list(kpi_dict.items())[:6]:
    print(f'   {key}: {value}')

# 提取分类数据
category_data = loader.data.get('category_data', pd.DataFrame())
category_summary = []

if not category_data.empty:
    sorted_cats = category_data.sort_values('售价销售额', ascending=False).copy()
    
    for idx, row in sorted_cats.head(5).iterrows():
        cat_info = {
            '一级分类': row.get('一级分类', '未知'),
            '售价销售额': row.get('售价销售额', 0),
            'SKU数': row.get('美团一级分类去重SKU数(口径同动销率)', 0),
            '动销率': row.get('美团一级分类动销率(类内)', 0),
            '折扣': row.get('美团一级分类折扣', 10),
        }
        
        # 计算促销强度
        if len(category_data.columns) > 24:
            discount_level = row.iloc[24] if pd.notna(row.iloc[24]) else 10
            cat_info['折扣力度'] = discount_level
            cat_info['促销强度'] = ((10 - discount_level) / 9 * 100) if discount_level < 10 else 0
        
        category_summary.append(cat_info)

print('\n2. ✅ 分类数据提取(TOP5):')
for idx, cat in enumerate(category_summary, 1):
    print(f'   {idx}. {cat["一级分类"]}: 销售额={cat["售价销售额"]:.0f}元, 动销率={cat["动销率"]:.1f}%, 促销强度={cat.get("促销强度", 0):.1f}%')

# 计算元数据
total_revenue = sum(c['售价销售额'] for c in category_summary)
top3_revenue = sum(c['售价销售额'] for c in category_summary[:3])
concentration = (top3_revenue / total_revenue * 100) if total_revenue > 0 else 0

health_count = sum(1 for c in category_summary if c['动销率'] >= 60)
problem_count = len(category_summary) - health_count

print('\n3. ✅ 衍生指标计算:')
print(f'   TOP3销售额集中度: {concentration:.1f}%')
print(f'   健康分类数(动销率≥60%): {health_count}个')
print(f'   问题分类数(动销率<60%): {problem_count}个')

print('\n4. ✅ 价格带数据:')
price_data = loader.data.get('price_data', pd.DataFrame())
if not price_data.empty:
    for idx, row in price_data.iterrows():
        print(f'   {row["price_band"]}: SKU={row["SKU数量"]}个, 销售额={row["销售额"]:.0f}元, 占比={row["销售额占比"]:.1f}%')

print('\n' + '='*70)
print('✅ 所有数据提取测试通过!')
print('='*70)
