import pandas as pd

df = pd.read_excel('./reports/竞对分析报告_v3.4_FINAL.xlsx', sheet_name='美团一级分类详细指标')

# 找出折扣为0的分类
extreme = df[df.iloc[:, 24] == 0]

print('='*80)
print('100%促销强度分类详情 (折扣=0)')
print('='*80)

for idx in extreme.index:
    print(f'\n📦 {df.iloc[idx, 0]}:')
    print(f'   总SKU数: {int(df.iloc[idx, 1])}')
    print(f'   去重SKU数: {int(df.iloc[idx, 4])}')
    print(f'   动销SKU数: {int(df.iloc[idx, 5])}')
    print(f'   销售额: ¥{df.iloc[idx, 18]:,.0f}')
    print(f'   月售: {int(df.iloc[idx, 15])}')
    print(f'   活动占比: {df.iloc[idx, 10]:.1f}%')
    print(f'   SKU占比: {df.iloc[idx, 14]:.2f}%')

print('\n' + '='*80)
print('统计汇总:')
print(f'   极端分类数量: {len(extreme)}个')
print(f'   总SKU数合计: {int(extreme.iloc[:, 1].sum())}')
print(f'   总销售额合计: ¥{extreme.iloc[:, 18].sum():,.0f}')
print(f'   占全店SKU比例: {extreme.iloc[:, 14].sum():.2f}%')
print(f'   占全店销售额比例: {extreme.iloc[:, 20].sum():.2f}%')
print('='*80)
