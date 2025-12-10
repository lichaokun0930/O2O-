"""诊断活动占比计算问题"""
import pandas as pd

# 模拟dashboard的数据处理流程
print("=" * 80)
print("诊断: 活动占比为什么都是100%?")
print("=" * 80)

# 假设这是从分析结果中获取的category_df
# 我们需要检查实际的数据结构

# 先检查store_analyzer生成的数据
from store_analyzer import StoreAnalyzer

analyzer = StoreAnalyzer()

# 检查是否有缓存的分析结果
if '鲸星购' in analyzer.analysis_results:
    result = analyzer.analysis_results['鲸星购']
    
    if '美团一级分类汇总' in result:
        category_data = result['美团一级分类汇总']
        
        print(f"\n美团一级分类汇总数据:")
        print(f"数据类型: {type(category_data)}")
        
        if isinstance(category_data, pd.DataFrame):
            df = category_data
        else:
            # 转换为DataFrame
            df = pd.DataFrame(category_data)
        
        print(f"数据维度: {df.shape}")
        print(f"\n列名 (前15列):")
        for i, col in enumerate(df.columns[:15]):
            print(f"  列{i:2d}: {col}")
        
        # 检查关键列
        print(f"\n关键数据检查:")
        
        # E列: 去重SKU数 (第4列,索引从0开始)
        # I列: 活动去重SKU数 (第8列)
        # K列: 活动SKU占比(类内) (第10列)
        
        if len(df.columns) > 10:
            print(f"\n前10个分类的数据:")
            for idx in range(min(10, len(df))):
                cat = df.iloc[idx, 0]
                
                # 提取关键数据
                dedup_sku = df.iloc[idx, 4] if len(df.columns) > 4 else 0
                activity_dedup = df.iloc[idx, 8] if len(df.columns) > 8 else 0
                activity_ratio_k = df.iloc[idx, 10] if len(df.columns) > 10 else 0
                
                # 计算占比
                if dedup_sku > 0:
                    calculated_ratio = (activity_dedup / dedup_sku * 100)
                else:
                    calculated_ratio = 0
                
                print(f"\n  {cat}:")
                print(f"    去重SKU数(E列): {dedup_sku}")
                print(f"    活动去重SKU数(I列): {activity_dedup}")
                print(f"    K列原始值: {activity_ratio_k}")
                print(f"    手动计算占比: {calculated_ratio:.2f}%")
                
                if calculated_ratio == 100.0:
                    print(f"    ⚠️ 这个分类100%商品都在活动!")
        else:
            print(f"❌ 数据列数不足")
    else:
        print("❌ 没有'美团一级分类汇总'数据")
else:
    print("❌ 没有'鲸星购'的分析结果缓存")
    print("\n请先在Dashboard中上传并分析鲸星购的数据")
