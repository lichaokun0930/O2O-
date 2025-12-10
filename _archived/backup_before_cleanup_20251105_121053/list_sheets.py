import pandas as pd

file_path = r"d:\Python1\O2O_Analysis\O2O数据分析\门店基础数据分析\reports\鲸星购_分析报告.xlsx"
xl = pd.ExcelFile(file_path)
print("可用的Sheet:")
for i, sheet in enumerate(xl.sheet_names, 1):
    print(f"{i}. {sheet}")
