#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成示例分析报告

用于测试Dashboard功能
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def create_sample_report():
    """创建示例分析报告"""
    
    output_path = Path('./reports/示例门店_分析报告.xlsx')
    
    print("="*60)
    print("生成示例分析报告")
    print("="*60)
    
    # 1. 核心指标对比
    kpi_data = pd.DataFrame({
        '门店': ['示例门店'],
        '总SKU数(含规格)': [1234],
        '单规格SPU数': [800],
        '单规格SKU数': [800],
        '多规格SKU总数': [434],
        '总SKU数(去重后)': [1000],
        '动销SKU数': [750],
        '滞销SKU数': [250],
        '总销售额(去重后)': [125000.50],
        '动销率': [0.75],
        '唯一多规格商品数': [150]
    })
    
    # 2. 美团一级分类详细指标
    categories = ['饮料', '零食', '日用品', '粮油', '乳制品', '方便速食', '酒水', '调味品']
    category_data = pd.DataFrame({
        '一级分类': categories,
        '美团一级分类sku数': [150, 200, 180, 120, 100, 90, 80, 80],
        '美团一级分类去重SKU数(口径同动销率)': [120, 180, 150, 100, 90, 80, 70, 70],
        '美团一级分类动销sku数': [90, 150, 120, 80, 70, 60, 50, 50],
        '美团一级分类动销率(类内)': [0.75, 0.83, 0.80, 0.80, 0.78, 0.75, 0.71, 0.71],
        '售价销售额': [25000, 30000, 20000, 15000, 12000, 10000, 8000, 5000],
        '美团一级分类爆品sku数': [15, 20, 12, 10, 8, 6, 5, 4],
        '美团一级分类折扣': [8.5, 9.0, 8.8, 9.2, 8.7, 8.3, 9.5, 9.0],
        '美团一级分类折扣sku数': [30, 40, 35, 25, 20, 18, 15, 12]
    })
    
    # 3. 价格带分析
    price_data = pd.DataFrame({
        '价格带': ['0-5元', '5-10元', '10-20元', '20-30元', '30-40元', '40-50元', '50-60元', '100元以上'],
        'SKU数量': [150, 250, 300, 180, 80, 30, 10, 0],
        '销售额': [5000, 15000, 40000, 35000, 20000, 8000, 2000, 50],
        '销售额占比': [0.04, 0.12, 0.32, 0.28, 0.16, 0.064, 0.016, 0.0004],
        'SKU占比': [0.15, 0.25, 0.30, 0.18, 0.08, 0.03, 0.01, 0.0]
    })
    
    # 4. 详细SKU报告
    np.random.seed(42)
    sku_count = 1000
    
    product_names = [
        '可口可乐', '百事可乐', '雪碧', '芬达', '康师傅冰红茶', '统一冰红茶',
        '农夫山泉', '怡宝', '娃哈哈', '乐事薯片', '上好佳', '旺旺雪饼',
        '奥利奥', '趣多多', '德芙巧克力', '士力架', '康师傅方便面', '统一方便面',
        '蒙牛纯牛奶', '伊利纯牛奶', '光明酸奶', '安慕希', '金龙鱼食用油', '福临门大米'
    ]
    
    specs = ['', '300ml', '500ml', '1L', '1.5L', '小包装', '大包装', '家庭装', '分享装']
    
    sku_names = []
    for _ in range(sku_count):
        base_name = np.random.choice(product_names)
        spec = np.random.choice(specs)
        if spec:
            sku_names.append(f"{base_name}({spec})")
        else:
            sku_names.append(base_name)
    
    sku_data = pd.DataFrame({
        '商品名称': sku_names,
        '售价': np.random.uniform(3, 100, sku_count).round(2),
        '月售': np.random.poisson(10, sku_count),
        '原价': np.random.uniform(5, 120, sku_count).round(2),
        '库存': np.random.randint(0, 500, sku_count),
        '一级分类': np.random.choice(categories, sku_count)
    })
    
    # 确保售价 <= 原价
    sku_data['原价'] = sku_data[['售价', '原价']].max(axis=1)
    
    # 5. 成本分析汇总（可选）
    cost_data = pd.DataFrame({
        '门店': ['示例门店'],
        '美团一级分类': ['全部分类汇总'],
        '成本销售额': [87500.0],
        '售价销售额': [125000.5],
        '原价销售额': [145000.0],
        '毛利': [37500.5],
        '美团一级分类定价毛利率': [0.40],
        '美团一级分类售价毛利率': [0.30]
    })
    
    # 添加各分类的成本数据
    for cat in categories:
        cat_revenue = category_data[category_data['一级分类'] == cat]['售价销售额'].values[0]
        cost_data = pd.concat([cost_data, pd.DataFrame({
            '门店': ['示例门店'],
            '美团一级分类': [cat],
            '成本销售额': [cat_revenue * 0.7],
            '售价销售额': [cat_revenue],
            '原价销售额': [cat_revenue * 1.15],
            '毛利': [cat_revenue * 0.3],
            '美团一级分类定价毛利率': [0.35 + np.random.uniform(-0.05, 0.05)],
            '美团一级分类售价毛利率': [0.28 + np.random.uniform(-0.05, 0.05)]
        })], ignore_index=True)
    
    # 6. 高毛利商品TOP50
    high_margin_products = sku_data.copy()
    high_margin_products['成本'] = high_margin_products['售价'] * 0.6
    high_margin_products['毛利率'] = (high_margin_products['售价'] - high_margin_products['成本']) / high_margin_products['售价']
    high_margin_products = high_margin_products.nlargest(50, '毛利率')[
        ['商品名称', '售价', '成本', '毛利率', '月售', '一级分类']
    ]
    
    # 写入Excel
    print(f"\n正在写入Excel文件: {output_path}")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        kpi_data.to_excel(writer, sheet_name='核心指标对比', index=False)
        category_data.to_excel(writer, sheet_name='美团一级分类详细指标', index=False)
        price_data.to_excel(writer, sheet_name='价格带分析', index=False)
        sku_data.to_excel(writer, sheet_name='详细SKU报告(去重后)', index=False)
        cost_data.to_excel(writer, sheet_name='成本分析汇总', index=False)
        high_margin_products.to_excel(writer, sheet_name='高毛利商品TOP50', index=False)
    
    print(f"✅ 示例报告已生成: {output_path}")
    print(f"\n报告包含以下Sheet:")
    print(f"  1. 核心指标对比 ({len(kpi_data)}行)")
    print(f"  2. 美团一级分类详细指标 ({len(category_data)}行)")
    print(f"  3. 价格带分析 ({len(price_data)}行)")
    print(f"  4. 详细SKU报告(去重后) ({len(sku_data)}行)")
    print(f"  5. 成本分析汇总 ({len(cost_data)}行)")
    print(f"  6. 高毛利商品TOP50 ({len(high_margin_products)}行)")
    
    print(f"\n现在可以运行:")
    print(f"  python dashboard_v2_optimized.py")
    print(f"\n或修改代码中的 DEFAULT_REPORT_PATH 指向此文件")
    
    return output_path


if __name__ == '__main__':
    try:
        create_sample_report()
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
