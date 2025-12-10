import pandas as pd

# 读取Excel文件
df = pd.read_excel('./reports/竞对分析报告_v3.4_FINAL.xlsx', 
                   sheet_name='美团一级分类详细指标')

print("=" * 100)
print("Excel列字母 vs Pandas索引 对照表")
print("=" * 100)
print(f"总共有 {len(df.columns)} 列")
print()

# 显示所有列的对应关系
for i, col_name in enumerate(df.columns):
    # 计算Excel列字母 (A=0, B=1, ..., Z=25, AA=26, AB=27, ...)
    excel_letter = ""
    n = i
    while True:
        excel_letter = chr(65 + (n % 26)) + excel_letter
        n = n // 26
        if n == 0:
            break
        n -= 1
    
    print(f"Excel {excel_letter:3} 列 = Pandas索引 {i:2} = 列名: {col_name}")

print()
print("=" * 100)
print("重点列数据 (休闲食品分类):")
print("=" * 100)

# 找到休闲食品的数据
leisure_food = df[df.iloc[:, 0] == '休闲食品'].iloc[0]

# 显示索引20-25的数据
for i in range(20, min(26, len(df.columns))):
    excel_letter = ""
    n = i
    while True:
        excel_letter = chr(65 + (n % 26)) + excel_letter
        n = n // 26
        if n == 0:
            break
        n -= 1
    
    print(f"Excel {excel_letter} 列 (索引{i}) - {df.columns[i]}: {leisure_food.iloc[i]}")

print()
print("=" * 100)
print("如果您在Excel中看到的列名与上面不一致,可能是因为:")
print("1. Excel中有隐藏列")
print("2. 列标题不在第一行")
print("3. 查看的是不同版本的文件")
print("=" * 100)
