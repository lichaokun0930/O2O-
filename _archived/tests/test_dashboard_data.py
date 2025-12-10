# -*- coding: utf-8 -*-
"""
Dashboard数据完整性测试
验证所有看板是否能正常加载数据
"""
import pandas as pd
import sys

DEFAULT_REPORT_PATH = "./reports/竞对分析报告_v3.4_FINAL.xlsx"

def test_data_loading():
    """测试数据加载"""
    print("=" * 70)
    print("📊 Dashboard数据完整性测试")
    print("=" * 70)
    
    try:
        # 加载Excel
        excel_file = pd.ExcelFile(DEFAULT_REPORT_PATH)
        sheet_names = excel_file.sheet_names
        print(f"\n✅ Excel文件加载成功，共{len(sheet_names)}个sheet")
        
        # 加载关键sheet
        kpi_df = pd.read_excel(DEFAULT_REPORT_PATH, sheet_name=sheet_names[0])
        category_l1_df = pd.read_excel(DEFAULT_REPORT_PATH, sheet_name=sheet_names[4])
        role_df = pd.read_excel(DEFAULT_REPORT_PATH, sheet_name=sheet_names[1])
        price_df = pd.read_excel(DEFAULT_REPORT_PATH, sheet_name=sheet_names[2])
        sku_details_df = pd.read_excel(DEFAULT_REPORT_PATH, sheet_name=sheet_names[6])
        
        print(f"\n📋 数据维度检查:")
        print(f"  1. KPI数据: {kpi_df.shape} (期望: 1行 × 11列)")
        print(f"  2. 一级分类: {category_l1_df.shape} (期望: 28行 × 26列)")
        print(f"  3. 商品角色: {role_df.shape}")
        print(f"  4. 价格带: {price_df.shape}")
        print(f"  5. SKU详情: {sku_details_df.shape} (期望: 7828行 × 17列)")
        
        # 测试KPI计算
        print(f"\n🔢 KPI计算测试:")
        kpi_count = 0
        kpi_list = []
        
        row = kpi_df.iloc[0]
        summary = {}
        
        for i in range(len(kpi_df.columns)):
            value = row.iloc[i]
            if i == 0: 
                summary['门店'] = value
                kpi_list.append(f"门店={value}")
            elif i == 1: 
                summary['总SKU数(含规格)'] = value
                kpi_list.append(f"总SKU数(含规格)={value}")
                kpi_count += 1
            elif i == 4: 
                summary['多规格SKU总数'] = value
                kpi_list.append(f"多规格SKU总数={value}")
                kpi_count += 1
            elif i == 5:  # 重点检查!
                summary['总SKU数(去重后)'] = value
                kpi_list.append(f"总SKU数(去重后)={value}")
                kpi_count += 1
            elif i == 6: 
                summary['动销SKU数'] = value
                kpi_list.append(f"动销SKU数={value}")
                kpi_count += 1
            elif i == 7: 
                summary['滞销SKU数'] = value
                kpi_list.append(f"滞销SKU数={value}")
                kpi_count += 1
            elif i == 8: 
                summary['总销售额(去重后)'] = value
                kpi_list.append(f"总销售额(去重后)={value}")
                kpi_count += 1
            elif i == 9: 
                summary['动销率'] = value
                kpi_list.append(f"动销率={value:.1%}")
                kpi_count += 1
            elif i == 10: 
                summary['唯一多规格商品数'] = value
                kpi_list.append(f"唯一多规格商品数={value}")
                kpi_count += 1
        
        # 从分类数据计算
        if len(category_l1_df.columns) > 23:
            val = category_l1_df.iloc[:, 23].sum()
            summary['门店爆品数'] = val
            kpi_list.append(f"门店爆品数={val}")
            kpi_count += 1
            
        if len(category_l1_df.columns) > 24:
            val = pd.to_numeric(category_l1_df.iloc[:, 24], errors='coerce').mean()
            summary['门店平均折扣'] = val
            kpi_list.append(f"门店平均折扣={val:.1f}折")
            kpi_count += 1
        
        # 从SKU详情计算
        if len(sku_details_df.columns) > 1:
            val = pd.to_numeric(sku_details_df.iloc[:, 1], errors='coerce').mean()
            summary['平均SKU单价'] = val
            kpi_list.append(f"平均SKU单价=¥{val:.2f}")
            kpi_count += 1
        
        if len(sku_details_df.columns) > 1 and '总SKU数(去重后)' in summary:
            high_value_count = (pd.to_numeric(sku_details_df.iloc[:, 1], errors='coerce') > 50).sum()
            total_skus = summary['总SKU数(去重后)']
            val = (high_value_count / total_skus) if total_skus > 0 else 0
            summary['高价值SKU占比'] = val
            kpi_list.append(f"高价值SKU占比={val:.1%}")
            kpi_count += 1
        
        if len(sku_details_df.columns) > 2 and '总销售额(去重后)' in summary:
            price_col = pd.to_numeric(sku_details_df.iloc[:, 1], errors='coerce').fillna(0)
            sales_col = pd.to_numeric(sku_details_df.iloc[:, 2], errors='coerce').fillna(0)
            sku_temp = sku_details_df.copy()
            sku_temp['revenue'] = price_col * sales_col
            top10_revenue = sku_temp.nlargest(10, 'revenue')['revenue'].sum()
            total_revenue = summary['总销售额(去重后)']
            val = (top10_revenue / total_revenue) if total_revenue > 0 else 0
            summary['爆款集中度'] = val
            kpi_list.append(f"爆款集中度={val:.1%}")
            kpi_count += 1
        
        if len(category_l1_df.columns) > 22 and '动销SKU数' in summary:
            total_discount_skus = pd.to_numeric(category_l1_df.iloc[:, 22], errors='coerce').sum()
            active_skus = summary['动销SKU数']
            val = (total_discount_skus / active_skus) if active_skus > 0 else 0
            summary['促销强度'] = val
            kpi_list.append(f"促销强度={val:.1%}")
            kpi_count += 1
        
        print(f"  ✅ 成功计算 {kpi_count}/13 个KPI (期望13个)")
        if kpi_count < 13:
            print(f"  ⚠️  缺失KPI:")
            expected_kpis = [
                '总SKU数(含规格)', '多规格SKU总数', '总SKU数(去重后)', '动销SKU数',
                '滞销SKU数', '总销售额(去重后)', '动销率', '唯一多规格商品数',
                '门店爆品数', '门店平均折扣', '平均SKU单价', '高价值SKU占比',
                '爆款集中度', '促销强度'
            ]
            for expected in expected_kpis:
                if expected not in summary:
                    print(f"     - {expected}")
        
        # 测试看板数据
        print(f"\n📊 看板数据测试:")
        
        # 1. 一级分类动销分析
        if not category_l1_df.empty and len(category_l1_df.columns) >= 7:
            print(f"  ✅ 一级分类动销分析: 数据正常 ({len(category_l1_df)}行)")
        else:
            print(f"  ❌ 一级分类动销分析: 数据不足")
        
        # 2. 多规格商品供给分析
        if not category_l1_df.empty and len(category_l1_df.columns) >= 5:
            print(f"  ✅ 多规格商品供给分析: 数据正常")
        else:
            print(f"  ❌ 多规格商品供给分析: 数据不足")
        
        # 3. 折扣渗透率热力图
        if not category_l1_df.empty and len(category_l1_df.columns) >= 22:
            print(f"  ✅ 折扣渗透率热力图: 数据正常")
        else:
            print(f"  ❌ 折扣渗透率热力图: 数据不足")
        
        # 4. 促销效能分析
        if not category_l1_df.empty and len(category_l1_df.columns) >= 18:
            print(f"  ✅ 促销效能分析: 数据正常")
        else:
            print(f"  ❌ 促销效能分析: 数据不足")
        
        # 5. 滞销商品诊断
        if not sku_details_df.empty:
            unsold_count = (pd.to_numeric(sku_details_df.iloc[:, 2], errors='coerce') == 0).sum()
            print(f"  ✅ 滞销商品诊断: 数据正常 ({unsold_count}个滞销商品)")
        else:
            print(f"  ❌ 滞销商品诊断: SKU数据缺失")
        
        print(f"\n" + "=" * 70)
        print(f"测试完成!")
        print(f"=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_data_loading()
    sys.exit(0 if success else 1)
