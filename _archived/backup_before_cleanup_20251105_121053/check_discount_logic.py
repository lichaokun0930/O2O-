import pandas as pd

df = pd.read_excel('reports/淮安生态新城商品10.29 的副本_分析报告.xlsx', sheet_name=3)

print("=" * 80)
print("折扣力度计算逻辑说明")
print("=" * 80)

print(f"\nY列(索引24)名称: {df.columns[24]}")
print(f"\n前10个分类的折扣数据:")

for i in range(min(10, len(df))):
    cat = df.iloc[i, 0]
    y_value = df.iloc[i, 24]
    
    # Dashboard计算逻辑
    if y_value == 0:
        display_value = "0折(免费) → 将替换为中位数"
    else:
        display_value = f"{y_value:.2f}折"
    
    # 折扣率计算：(10 - 折扣力度) / 10 * 100
    if y_value > 0:
        discount_rate = (10 - y_value) / 10 * 100
        discount_info = f"{discount_rate:.1f}% off"
    else:
        discount_info = "异常值"
    
    print(f"{i+1}. {cat}: {display_value} ({discount_info})")

print(f"\n" + "=" * 80)
print("折扣力度说明:")
print("=" * 80)
print("""
数据来源: Excel的Y列 "美团一级分类折扣"

数据含义:
- Y列的值表示"折扣"，单位是"折"（1折到10折）
- 例如：6.5 表示 6.5折（原价10元，售价6.5元）
- 10折 = 不打折（原价销售）
- 数值越小 = 折扣力度越大

Dashboard计算逻辑:
1. 读取Y列的折扣值（如 6.5折）
2. 处理异常值：如果为0（免费），替换为中位数
3. 在气泡图的hover中显示为"平均折扣力度: X.X折"

注意事项:
- 这个"平均折扣"是该分类内所有商品的平均折扣
- 计算公式在untitled1.py中：售价销售额 / 原价销售额 * 10
- 折扣率计算：(10 - 折扣力度) / 10 * 100
  例如：6.5折 → (10-6.5)/10*100 = 35% off
""")
