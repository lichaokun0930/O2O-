"""测试定价毛利率和售价毛利率功能"""
import pandas as pd

# 读取现有Excel报告的低毛利预警商品
print("📊 测试定价毛利率 vs 售价毛利率功能\n")

xl_file = 'reports/淮安生态新城商品10.29 的副本_分析报告.xlsx'

# 读取低毛利预警商品
try:
    df = pd.read_excel(xl_file, sheet_name='低毛利预警商品')
    print(f"✅ 成功读取低毛利预警商品数据，共 {len(df)} 条记录")
    print(f"\n列名: {df.columns.tolist()}\n")
    
    # 模拟计算定价毛利率和售价毛利率
    if '售价' in df.columns and 'cost' in df.columns and '原价' in df.columns:
        print("=" * 80)
        print("前5个商品的毛利率对比分析:")
        print("=" * 80)
        
        for idx, row in df.head(5).iterrows():
            product_name = row.get('商品名称', '未知')
            price = row.get('售价', 0)
            original_price = row.get('原价', 0)
            cost = row.get('cost', 0)
            
            # 计算售价毛利率
            selling_margin_rate = (price - cost) / price if price > 0 else 0
            
            # 计算定价毛利率
            pricing_margin_rate = (original_price - cost) / original_price if original_price > 0 else 0
            
            # 折扣率
            discount_rate = (original_price - price) / original_price if original_price > 0 else 0
            
            print(f"\n商品: {product_name[:40]}")
            print(f"  原价: ¥{original_price:.2f}")
            print(f"  售价: ¥{price:.2f} (折扣: {discount_rate:.1%})")
            print(f"  成本: ¥{cost:.2f}")
            print(f"  📈 定价毛利率: {pricing_margin_rate:.2%} (按原价计算)")
            print(f"  📊 售价毛利率: {pricing_margin_rate:.2%} (按实际售价计算)")
            print(f"  🔻 毛利率损失: {(pricing_margin_rate - selling_margin_rate):.2%} (促销影响)")
            
            # 判断问题类型
            if selling_margin_rate < 0:
                print(f"  ⚠️ 亏损销售！售价低于成本 ¥{price - cost:.2f}")
            elif pricing_margin_rate > 0.2 and selling_margin_rate < 0.1:
                print(f"  💡 定价合理但折扣过大，建议调整促销力度")
            elif pricing_margin_rate < 0.1:
                print(f"  🔧 定价偏低，建议优化成本或调整定价策略")
    
    else:
        print("⚠️ 未找到必要的列：需要'售价'、'原价'和'cost'列")
        
except FileNotFoundError:
    print(f"❌ 文件不存在: {xl_file}")
    print("请先运行 untitled1.py 生成Excel报告")
except Exception as e:
    print(f"❌ 读取失败: {e}")

print("\n" + "=" * 80)
print("💡 说明:")
print("  - 定价毛利率: (原价 - 成本) / 原价，体现商品本身的盈利能力")
print("  - 售价毛利率: (售价 - 成本) / 售价，体现实际销售的盈利情况")
print("  - 毛利率损失: 由于促销折扣导致的毛利率下降")
print("=" * 80)
