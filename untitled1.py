# -*- coding: utf-8 -*-
"""
门店基础数据分析工具 v3.4 - 本地运行版
python untitled1.py --inputs "你的Excel文件路径.xlsx"
【运行指令】
PowerShell中执行：
        cd "D:\\Python1\\O2O_Analysis\\O2O数据分析"
        .\\.venv\\Scripts\\python.exe 门店基础数据分析\\untitled1.py

或者在VS Code终端中执行：
    & D:\\Python1\\O2O_Analysis\\O2O数据分析\\.venv\\Scripts\\python.exe d:/Python1/O2O_Analysis/O2O数据分析/门店基础数据分析/untitled1.py

【功能说明】
本脚本来源于 Google Colab，已优化为本地/VS Code 环境可直接运行的版本。
主要功能：
1. 门店商品结构分析（SKU/SPU统计、多规格商品识别）
2. 价格带分析、商品角色分析
3. 美团一级分类详细指标分析
4. 多规格商品报告生成
5. 数据一致性校验

【输出报告】
- 核心指标对比：包含总SKU数、单规格SKU数、多规格SKU总数等关键指标
- 多规格商品报告(全)：所有被识别为多规格的商品详细清单
- 唯一多规格商品列表：去重后的多规格商品，包含分类和月售信息
- 美团一级分类详细指标：各分类的详细统计数据

优化要点（不改变业务逻辑/需求）：
- 去除 files.upload 与 /content 路径依赖，支持命令行传入或交互式输入本地文件路径
- 补齐必要导入与健壮性校验（文件存在、Excel 锁文件、数值列类型）
- Excel 导出优先 xlsxwriter，不可用时回退 openpyxl
- 确保数据一致性：多规格商品报告(全)行数 = 核心指标中多规格SKU总数
"""

import os
import sys
import argparse
import traceback
from pathlib import Path
import pandas as pd
import numpy as np
import datetime as dt
import re

# ----------------------------------------
# 2. 核心函数定义 (与之前版本相同，保持完整性)
# ----------------------------------------

def assign_product_role(row):
    """根据价格带和销量为商品分配角色。"""
    if pd.isna(row['price_band']): return '劣势品'
    if row['price_band'] in ['0-5 元', '5-10 元'] and row['sales_qty'] > 10: return '引流品'
    if row['price_band'] in ['10-20 元', '20-30 元', '30-40 元', '40-50 元', '50-60 元', '60-70 元', '70-80 元', '80-90 元'] and row['revenue'] > 50: return '利润品'
    if row['price_band'] == '100 元以上': return '形象品'
    return '劣势品'

def assign_consumption_scenarios(df, scenarios_dict):
    """根据关键词为商品分配消费场景标签。"""
    if 'product_name' not in df.columns or 'l1_category' not in df.columns:
        df['consumption_scenarios'] = [[]] * len(df)
        return df
    def get_scenarios(row):
        product_info = str(row.get('product_name', '')).lower() + str(row.get('l1_category', '')).lower()
        return [scenario for scenario, keywords in scenarios_dict.items() if any(kw.lower() in product_info for kw in keywords)]
    df['consumption_scenarios'] = df.apply(get_scenarios, axis=1)
    return df

def load_and_clean_data(file_path, store_name, scenarios_dict):
    """加载、清洗并预处理单个门店的数据，一次性计算所有衍生列。"""
    print(f"\n⚙️  开始处理: {store_name} (文件: {os.path.basename(file_path)})")
    # 基础文件校验
    p = Path(file_path)
    if not p.exists():
        print(f"❌ 文件不存在: {file_path}"); return None
    if p.name.startswith('~$'):
        print(f"❌ 检测到 Excel 锁文件: {p.name}，请先关闭 Excel 后重试。"); return None

    try:
        if p.suffix.lower() == '.csv':
            try:
                df = pd.read_csv(p, on_bad_lines='skip', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(p, on_bad_lines='skip', encoding='gbk')
        else:
            df = pd.read_excel(p)
        print(f"✅ 文件 '{p.name}' 读取成功。原始行数: {len(df)}")
    except Exception as e:
        print(f"❌ 读取文件时出错: {e}"); return None

    # Strip whitespace from column names immediately after reading
    df.columns = df.columns.str.strip()
    print(f"ℹ️ 读取文件后，去除首尾空格的列名: {list(df.columns)}")

    # More flexible column mapping based on keywords
    mapped_columns = {}
    # Define potential column names in both English and Chinese, prioritizing English if present
    potential_col_names = {
        # 分类
        'l1_category': ['l1_category', '一级分类', '美团一级分类', '大类', '分类', '一级品类'],
        'l3_category': ['l3_category', '美团三级分类', '三级分类', '子类', '细类', '三级品类'],
        '商家分类': ['商家分类'],
        # 基础商品信息
        'product_name': ['product_name', '商品名称', '品名', '名称'],
        'barcode': ['barcode', '条码', '条形码', 'EAN', 'UPC'],
        # 价格/销量
        'price': ['price', '售价', '现价', '销售价', '价格'],
        'original_price': ['original_price', '原价', '划线价', '参考价'],
        'sales_qty': ['sales_qty', '月售', '销量', '月销量', '销售数量'],
        # 库存/规格
        '库存': ['库存', '剩余库存', '库存数', '库存数量', 'stock', 'Stock'],
        '规格名称': ['规格名称', '规格', '规格名', '规格型号', '规格值', 'spec', 'spec_name', 'variant'],
        # 成本相关
        'cost': ['cost', '成本', '成本价', '进价', '进货价', '采购价', '商品成本'],
        'store_code': ['store_code', '店内码', '商品编码', '内部编码', '商品代码', '门店编码', '店铺编码']
    }

    # Attempt to find the correct column in the dataframe based on potential names
    # Store the mapping from original stripped name to standard name
    reverse_mapped_columns = {}
    for standard_name, potential_names in potential_col_names.items():
        found_col = None
        for name in potential_names:
            if name in df.columns:
                found_col = name
                break # Found a match, move to the next standard name
        if found_col:
            mapped_columns[found_col] = standard_name
            reverse_mapped_columns[standard_name] = found_col # Store mapping from standard back to found original
        else:
             # If a primary essential column is not found, print a warning
            if standard_name in ['product_name', 'price', 'sales_qty', 'l1_category', 'original_price', '库存']:
                 print(f"⚠️ 未找到必要列 '{standard_name}' (尝试名称: {potential_names})")

    # Rename columns based on the mapping found
    df.rename(columns=mapped_columns, inplace=True)
    print(f"ℹ️ 应用列名映射后，当前列名: {list(df.columns)}")

    # Define essential columns using the *standard* names after mapping
    essential_cols = ['product_name', 'price', 'sales_qty', 'l1_category', 'original_price', '库存']

    print(f"ℹ️ 检查必要列是否存在: {essential_cols}")
    df_cols = list(df.columns)
    print(f"ℹ️ DataFrame columns after renaming: {df_cols}")
    print(f"ℹ️ Essential columns list: {essential_cols}")

    # Robust check for essential columns: verify all essential columns are in df.columns
    missing_cols = [col for col in essential_cols if col not in df_cols]
    if missing_cols:
        print(f"❌ 错误: 文件缺少必要列: {missing_cols}"); return None
    print("✅ 必要列检查通过。")

    # Select only the essential columns (and other desired columns) into a new DataFrame
    # Include other potentially useful columns if they were found and mapped
    cols_to_keep = essential_cols + ['规格名称', 'l3_category', '商家分类', 'barcode', 'cost', 'store_code']
    # Filter cols_to_keep to only include those actually present in the DataFrame after renaming
    cols_to_keep_present = [col for col in cols_to_keep if col in df.columns]
    df_processed = df[cols_to_keep_present].copy()

    print(f"ℹ️ 创建新的DataFrame，只包含以下列: {list(df_processed.columns)}")

    initial_rows = len(df_processed)

    # 标准化规格名称，避免空白/字符串"nan"计入规格
    if '规格名称' in df_processed.columns:
        df_processed['规格名称'] = df_processed['规格名称'].where(~df_processed['规格名称'].isna(), None)
        df_processed['规格名称'] = df_processed['规格名称'].apply(lambda x: x.strip() if isinstance(x, str) else x)
        df_processed.loc[df_processed['规格名称'] == '', '规格名称'] = None

    # 先规范化销量文本（如 1.2万、3千、1,234、500+）到纯数字
    def parse_quantity(val):
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        if s == "":
            return np.nan
        # 去掉逗号与加号
        s = s.replace(',', '').replace('+', '')
        # 匹配带单位的中文数量
        m = re.match(r'^(\d+(?:\.\d+)?)\s*([万亿千百wWkK]?)$', s)
        if m:
            num = float(m.group(1))
            unit = m.group(2)
            factor = 1.0
            if unit in ['w', 'W', '万']:
                factor = 10000.0
            elif unit in ['k', 'K', '千']:
                factor = 1000.0
            elif unit in ['百']:
                factor = 100.0
            elif unit in ['亿']:
                factor = 100000000.0
            return num * factor
        # 纯数字或其他可解析样式
        try:
            return float(s)
        except Exception:
            return np.nan

    if 'sales_qty' in df_processed.columns:
        df_processed['sales_qty'] = df_processed['sales_qty'].apply(parse_quantity)
    # 数值化并将缺失值填 0，避免因 NaN 被丢弃导致动销统计失真
    for col in ['price', 'sales_qty', 'original_price', '库存']:
        if col in df_processed.columns:
            df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0)
    print(f"ℹ️ 转换必要数值列为数值类型完成，并将缺失值填充为 0。")

    # 仅对真正必需的标识性/分组性字段做非空校验，避免把 0 销售/价格的SKU直接丢弃
    df_processed.dropna(subset=['product_name', 'l1_category'], inplace=True)
    rows_after_dropna = len(df_processed)
    print(f"ℹ️ 移除关键标识/分类空值行后，剩余行数: {rows_after_dropna} (移除了 {initial_rows - rows_after_dropna} 行)")

    initial_rows_after_dropna = len(df_processed)
    if 'l1_category' in df_processed.columns: # Check if the column exists before filtering
        df_processed = df_processed[df_processed['l1_category'] != '店铺管理'].copy()
    rows_after_filter = len(df_processed)
    print(f"ℹ️ 移除 'l1_category' 为 '店铺管理' 的行。剩余行数: {rows_after_filter} (移除了 {initial_rows_after_dropna - rows_after_filter} 行)")


    if df_processed.empty:
        print("⚠️ 经过清洗后，DataFrame 为空。")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_processed['revenue'] = df_processed['price'] * df_processed['sales_qty']
    df_processed['original_price_revenue'] = df_processed['original_price'] * df_processed['sales_qty']
    # Add a check before calculating discount to avoid division by zero or issues with original_price being NaN/0
    df_processed['discount'] = 0 # Default discount to 0
    valid_price_mask = (df_processed['original_price'] > 0) & (df_processed['price'] >= 0) # Ensure original_price is positive and price is non-negative
    df_processed.loc[valid_price_mask, 'discount'] = (df_processed['original_price'] - df_processed['price']) / df_processed['original_price']
    df_processed.loc[df_processed['discount'] < 0, 'discount'] = 0 # Ensure discount is not negative


    df_processed['Store'] = store_name
    print("ℹ️ 计算衍生列完成 (revenue, original_price_revenue, discount, Store)。")

    price_bins = [0, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, np.inf]
    price_labels = ['0-5 元', '5-10 元', '10-20 元', '20-30 元', '30-40 元', '40-50 元', '50-60 元', '60-70 元', '70-80 元', '80-90 元', '100 元以上']
    df_processed['price_band'] = pd.cut(df_processed['price'], bins=price_bins, labels=price_labels, right=False, include_lowest=True)
    print("ℹ️ 分配价格带完成。")

    df_processed['role'] = df_processed.apply(assign_product_role, axis=1)
    print("ℹ️ 分配商品角色完成。")

    df_processed = assign_consumption_scenarios(df_processed, scenarios_dict)
    print("ℹ️ 分配消费场景完成。")

    df_all_skus = df_processed.copy()
    
    # 调试：检查成本列是否存在
    if 'cost' in df_all_skus.columns:
        cost_count = df_all_skus['cost'].notna().sum()
        print(f"ℹ️ 成本数据检测：共 {cost_count} 条SKU包含成本数据")
    
    # 使用多级排序进行去重：销量降序、价格升序、库存降序、规格名称升序（如果存在）
    # 确保对于相同销量的多规格商品，优先选择价格低、库存高的规格作为代表
    sort_columns = ['sales_qty', 'price', '库存']
    sort_ascending = [False, True, False]
    
    # 如果存在规格名称列，则加入排序
    if '规格名称' in df_processed.columns:
        sort_columns.append('规格名称')
        sort_ascending.append(True)
    
    df_deduplicated = df_processed.sort_values(
        by=sort_columns, 
        ascending=sort_ascending,
        na_position='last'
    ).drop_duplicates(subset=['product_name'], keep='first').copy()
    df_active = df_deduplicated[df_deduplicated['sales_qty'] > 0].copy()

    print(f"✅ 清洗完成: 共 {len(df_all_skus)} SKU (含规格), 去重后 {len(df_deduplicated)} SKU, 其中动销 {len(df_active)} SKU。")
    return df_all_skus, df_deduplicated, df_active

# ====== 多规格识别辅助：从商品名称解析规格，并归一化基名 ======
def _extract_inferred_spec(name: str) -> str:
    if not isinstance(name, str) or not name:
        return ''
    s = name.lower()
    specs = []
    # 数量*规格，如 12*50g, 6×500ml
    m_iter = re.findall(r'(\d+\s*[x×*]\s*\d+\s*(?:g|kg|ml|l|片|包|袋|支|枚|瓶|听|卷)?)', s)
    specs.extend([re.sub(r'\s+', '', m) for m in m_iter])
    # 体积/重量，如 500ml, 1.5l, 300g, 2kg
    m_iter = re.findall(r'(\d+(?:\.\d+)?\s*(?:ml|l|g|kg))', s)
    specs.extend([re.sub(r'\s+', '', m) for m in m_iter])
    # 计数单位，如 12片, 6包, 24支
    m_iter = re.findall(r'(\d+\s*(?:片|包|袋|支|枚|瓶|听|盒|卷|块|片装|袋装|支装))', s)
    specs.extend([re.sub(r'\s+', '', m) for m in m_iter])
    # 口味/变体关键词（简版）
    flavor_kw = [
        '原味','草莓','香草','巧克力','柠檬','芒果','橙','蓝莓','青柠','葡萄','可乐','零度','乌龙','茉莉','奶绿',
        '微辣','中辣','特辣','麻辣','清爽','无糖','低糖','0糖','少糖','无盐','低盐','海盐','黑糖','红糖','燕麦','全麦','低脂','高钙','高蛋白',
        '大','中','小','迷你','mini','家庭装','分享装','量贩','加大','加厚','便携'
    ]
    for kw in flavor_kw:
        if kw in s:
            specs.append(kw)
    # 合并为去重有序字符串
    if not specs:
        return ''
    uniq = []
    for t in specs:
        if t and t not in uniq:
            uniq.append(t)
    return ' '.join(uniq)

def _normalize_base_name(name: str) -> str:
    if not isinstance(name, str) or not name:
        return ''
    s = name.lower()
    # 去掉括号中的内容（常为口味/规格）
    s = re.sub(r'[\(（\[][^\)）\]]*[\)）\]]', '', s)
    # 去掉数量*规格、数字+单位等
    s = re.sub(r'\d+\s*[x×*]\s*\d+\s*(?:g|kg|ml|l|片|包|袋|支|枚|瓶|听|卷)?', '', s)
    s = re.sub(r'\d+(?:\.\d+)?\s*(?:ml|l|g|kg)', '', s)
    s = re.sub(r'\d+\s*(?:片|包|袋|支|枚|瓶|听|盒|卷|块|片装|袋装|支装)', '', s)
    # 去掉常见变体关键词
    variant_kw = ['原味','草莓','香草','巧克力','柠檬','芒果','微辣','中辣','特辣','无糖','低糖','0糖','家庭装','分享装','量贩','迷你','mini','大','中','小']
    for kw in variant_kw:
        s = s.replace(kw, '')
    # 去掉多余空白与标点
    s = re.sub(r'[^\u4e00-\u9fff0-9a-zA-Z]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def identify_multi_spec_products(df):
    """识别多规格商品。"""
    if df is None or df.empty:
        return pd.DataFrame()
    if 'product_name' not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    # 标准化规格列
    if '规格名称' in work.columns:
        work['规格名称'] = work['规格名称'].where(~work['规格名称'].isna(), None)
        work['规格名称'] = work['规格名称'].apply(lambda x: x.strip() if isinstance(x, str) else x)
        work.loc[work['规格名称'] == '', '规格名称'] = None
    else:
        work['规格名称'] = None

    # 从名称推断规格，并生成基名
    work['inferred_spec'] = work['product_name'].apply(_extract_inferred_spec)
    work['base_name'] = work['product_name'].apply(_normalize_base_name)

    # 组键（门店优先）
    has_store = 'Store' in work.columns
    key_pn = ['Store', 'product_name'] if has_store else ['product_name']
    key_base = ['Store', 'base_name'] if has_store else ['base_name']

    # 信号1：同一 product_name 下的非空规格名称>1
    sig1 = work.dropna(subset=['规格名称']).groupby(key_pn)['规格名称'].nunique(dropna=True)
    sig1_keys = sig1[sig1 > 1].index

    # 信号2：同一 base_name 下的 inferred_spec>1
    sig2 = work[work['inferred_spec'] != ''].groupby(key_base)['inferred_spec'].nunique()
    sig2_keys = sig2[sig2 > 1].index

    # 信号3：同一 base_name 下条码多值（且商品名不完全相同，避免同条重复）
    if 'barcode' in work.columns:
        tmp = work.copy()
        tmp['barcode'] = tmp['barcode'].astype(str)
        sig3 = tmp.groupby(key_base)['barcode'].nunique()
        sig3_keys = sig3[sig3 > 1].index
    else:
        sig3_keys = []

    def idx_to_df(keys, cols):
        if isinstance(keys, pd.MultiIndex):
            return keys.to_frame(index=False).rename(columns={0: cols[0], 1: cols[1]} if len(cols) == 2 else {0: cols[0]})
        else:
            return pd.DataFrame({cols[0]: list(keys)})

    key_pn_df = idx_to_df(sig1_keys, key_pn)
    key_base_df_2 = idx_to_df(sig2_keys, key_base)
    key_base_df_3 = idx_to_df(sig3_keys, key_base)

    # 收集所有被识别为多规格的base_name（优化版本）
    all_multi_base_names = set()
    
    # 从信号1（规格列）提取base_name
    if not key_pn_df.empty:
        # 预先建立product_name到base_name的映射，避免重复查询
        if has_store:
            pn_to_base_map = work.set_index(['Store', 'product_name'])['base_name'].to_dict()
            for _, row in key_pn_df.iterrows():
                key = (row['Store'], row['product_name'])
                if key in pn_to_base_map:
                    all_multi_base_names.add((row['Store'], pn_to_base_map[key]))
        else:
            pn_to_base_map = work.set_index('product_name')['base_name'].to_dict()
            for _, row in key_pn_df.iterrows():
                if row['product_name'] in pn_to_base_map:
                    all_multi_base_names.add(pn_to_base_map[row['product_name']])
    
    # 从信号2（名称解析）提取base_name
    if not key_base_df_2.empty:
        for _, row in key_base_df_2.iterrows():
            if has_store:
                all_multi_base_names.add((row['Store'], row['base_name']))
            else:
                all_multi_base_names.add(row['base_name'])
    
    # 从信号3（条码多值）提取base_name
    if not key_base_df_3.empty:
        for _, row in key_base_df_3.iterrows():
            if has_store:
                all_multi_base_names.add((row['Store'], row['base_name']))
            else:
                all_multi_base_names.add(row['base_name'])
    
    if not all_multi_base_names:
        return pd.DataFrame()
    
    # 使用向量化操作筛选结果，避免多次循环
    if has_store:
        # 创建一个标记列来标识多规格商品
        work['is_multi_spec'] = work.apply(
            lambda row: (row['Store'], row['base_name']) in all_multi_base_names, 
            axis=1
        )
    else:
        work['is_multi_spec'] = work['base_name'].isin(all_multi_base_names)
    
    result = work[work['is_multi_spec']].copy()
    result = result.drop('is_multi_spec', axis=1)
    
    if result.empty:
        return pd.DataFrame()
    # 为完整的结果计算规格种类数和多规格依据（简化版本）
    # 变体键：优先 规格名称，其次 inferred_spec，再次 barcode
    def _coalesce_variant(row):
        for c in ['规格名称', 'inferred_spec', 'barcode']:
            v = row.get(c, None)
            if isinstance(v, str):
                v = v.strip()
            if v not in (None, '', 'nan') and not (isinstance(v, float) and np.isnan(v)):
                return v
        return None
    
    print(f"ℹ️ 开始计算变体键...")
    result['variant_key'] = result.apply(_coalesce_variant, axis=1)
    
    print(f"ℹ️ 开始计算规格种类数...")
    # 使用更简单的规格种类数计算方法
    if has_store:
        vk_cnt = result.dropna(subset=['variant_key']).groupby(['Store', 'base_name'])['variant_key'].nunique().reset_index()
        vk_cnt.columns = ['Store', 'base_name', '规格种类数']
        result = result.merge(vk_cnt, on=['Store', 'base_name'], how='left')
    else:
        vk_cnt = result.dropna(subset=['variant_key']).groupby('base_name')['variant_key'].nunique().reset_index()
        vk_cnt.columns = ['base_name', '规格种类数']
        result = result.merge(vk_cnt, on='base_name', how='left')
    
    result['规格种类数'] = result['规格种类数'].fillna(2)  # 至少为2的多规格假设
    
    print(f"ℹ️ 开始添加多规格依据...")
    # 简化多规格依据的计算
    def get_trigger_for_row(row):
        triggers = []
        
        if has_store:
            store_name = row['Store']
            base_name = row['base_name']
            product_name = row['product_name']
            
            # 检查信号来源（简化版）
            if not key_pn_df.empty and any((key_pn_df['Store'] == store_name) & (key_pn_df['product_name'] == product_name)):
                triggers.append('规格列')
            if not key_base_df_2.empty and any((key_base_df_2['Store'] == store_name) & (key_base_df_2['base_name'] == base_name)):
                triggers.append('名称解析')
            if not key_base_df_3.empty and any((key_base_df_3['Store'] == store_name) & (key_base_df_3['base_name'] == base_name)):
                triggers.append('条码多值')
        else:
            base_name = row['base_name']
            product_name = row['product_name']
            
            if not key_pn_df.empty and product_name in key_pn_df['product_name'].values:
                triggers.append('规格列')
            if not key_base_df_2.empty and base_name in key_base_df_2['base_name'].values:
                triggers.append('名称解析')
            if not key_base_df_3.empty and base_name in key_base_df_3['base_name'].values:
                triggers.append('条码多值')
        
        return ', '.join(triggers) if triggers else '未知'
    
    # 只对前1000行计算多规格依据，避免性能问题
    if len(result) > 1000:
        result['多规格依据'] = '批量识别'
        print(f"⚠️ 由于数据量较大({len(result)}行)，简化多规格依据标注")
    else:
        result['多规格依据'] = result.apply(get_trigger_for_row, axis=1)
    
    print(f"ℹ️ 多规格商品识别完成，共{len(result)}行")
    return result

def analyze_store_performance(all_skus, deduplicated, active):
    """对单个门店数据进行所有维度的聚合分析。"""
    if deduplicated.empty:
        print("⚠️ deduplicated DataFrame 为空，跳过分析。")
        return None
    # ... (省略与v3.3版完全相同的分析逻辑) ...
    # (This function is complete and does not need changes)
    store_name = deduplicated['Store'].iloc[0]
    analysis_suite = {}
    
    # ====== 成本分析计算 ======
    # 检查是否有成本数据
    has_cost_data = 'cost' in all_skus.columns and all_skus['cost'].notna().any()
    
    if has_cost_data:
        print("ℹ️ 检测到成本数据，开始计算成本相关指标...")
        
        # 确保cost列为数值型
        all_skus['cost'] = pd.to_numeric(all_skus['cost'], errors='coerce').fillna(0)
        
        # SKU级成本计算
        all_skus['成本销售额'] = all_skus['cost'] * all_skus['sales_qty']
        all_skus['毛利'] = all_skus['revenue'] - all_skus['成本销售额']
        
        # 售价毛利率（按实际售价计算）
        all_skus['售价毛利率'] = all_skus.apply(
            lambda row: (row['毛利'] / row['revenue']) if row['revenue'] > 0 else 0, 
            axis=1
        )
        
        # 定价毛利率（按原价计算）
        all_skus['原价销售额'] = all_skus['original_price'] * all_skus['sales_qty']
        all_skus['定价毛利'] = all_skus['original_price_revenue'] - all_skus['成本销售额']
        all_skus['定价毛利率'] = all_skus.apply(
            lambda row: ((row['original_price'] - row['cost']) / row['original_price']) 
                        if row['original_price'] > 0 else 0, 
            axis=1
        )
        
        # 保留旧的"毛利率"列以兼容现有代码（指向售价毛利率）
        all_skus['毛利率'] = all_skus['售价毛利率']
        
        # 价格倍率和加价率
        all_skus['价格倍率'] = all_skus.apply(
            lambda row: (row['price'] / row['cost']) if row['cost'] > 0 else 0, 
            axis=1
        )
        all_skus['加价率'] = all_skus.apply(
            lambda row: ((row['price'] - row['cost']) / row['cost']) if row['cost'] > 0 else 0, 
            axis=1
        )
        
        print(f"✅ 成本指标计算完成：")
        print(f"   - 平均售价毛利率: {all_skus['售价毛利率'].mean():.2%}")
        print(f"   - 平均定价毛利率: {all_skus['定价毛利率'].mean():.2%}")
    else:
        print("⚠️ 未检测到成本数据，跳过成本分析")
    
    # 关键指标：用更稳健的口径计算，避免空值导致的对齐/空白
    total_revenue_dedup = float(deduplicated['revenue'].sum())
    # 总SKU数(含规格)口径调整：跨分类去重 + 以“单规格SPU数 + 多规格SKU总数”计数
    def _norm(s: str) -> str:
        if not isinstance(s, str):
            return ''
        s = s.strip().lower()
        s = re.sub(r"\s+", " ", s)
        return s
    def _spec_or_infer(row):
        spec = row.get('规格名称', None)
        spec = spec if isinstance(spec, str) and spec.strip() != '' else ''
        if not spec:
            spec = _extract_inferred_spec(row.get('product_name', ''))
        return _norm(spec)
    def _sku_key(row):
        bc = row.get('barcode', None)
        if isinstance(bc, (int, float)):
            bc = str(bc)
        if isinstance(bc, str):
            bc = bc.strip()
        if bc and bc.lower() not in ('nan', 'none'):
            return f"bc:{bc}"
        pn = _norm(row.get('product_name', ''))
        sp = _spec_or_infer(row)
        return f"pn:{pn}|sp:{sp}"
    single_spu = 0
    multi_spu = 0
    multi_sku_sum = 0
    try:
        # 变体键与基名
        work = all_skus.copy()
        work['base_name'] = work['product_name'].apply(_normalize_base_name)
        def _variant_key(row):
            v = row.get('规格名称', None)
            v = v if isinstance(v, str) and v.strip() != '' else None
            if not v:
                v = _extract_inferred_spec(row.get('product_name', ''))
            if not v:
                bc = row.get('barcode', None)
                bc = str(bc).strip() if isinstance(bc, (int, float, str)) else None
                if bc and bc.lower() not in ('nan', 'none'):
                    v = bc
            return _norm(v) if isinstance(v, str) else v
        work['variant_key'] = work.apply(_variant_key, axis=1)
        # 基于 base_name 的变体计数
        vc = work.groupby('base_name')['variant_key'].nunique(dropna=True)
        single_spu = int((vc == 1).sum())
        multi_spu = int((vc > 1).sum())
        multi_sku_sum = int(vc[vc > 1].sum())
        # 最终含规格总数 = 单规格SPU数(每个算1) + 多规格SKU总数(各自变体数相加)
        all_skus_count = single_spu + multi_sku_sum
        # 参考：跨类去重的唯一键计数（供日志比对）
        unique_keys = all_skus.apply(_sku_key, axis=1)
        uniq_key_cnt = int(unique_keys.nunique())
        dup_diff = int(len(all_skus) - uniq_key_cnt)
        if dup_diff > 0:
            print(f"ℹ️ 含规格去重：原行数 {len(all_skus)} -> 去重后 {uniq_key_cnt}（跨分类重复 {dup_diff}） | 口径(单规格+多规格SKU总数)={all_skus_count}，单规格SPU={single_spu}，多规格SPU={multi_spu}，多规格SKU总数={multi_sku_sum}")
    except Exception:
        # 兜底：回退为原始行数
        all_skus_count = int(len(all_skus))
        single_spu = all_skus_count
        multi_sku_sum = 0
    dedup_count = int(len(deduplicated))
    # 动销按 deduplicated 的销量>0 计数，避免上游 active 异常导致错位
    sales_series = deduplicated['sales_qty'] if 'sales_qty' in deduplicated.columns else pd.Series([], dtype=float)
    # 兜底：将缺失值视为 0
    sales_series = pd.to_numeric(sales_series, errors='coerce').fillna(0)
    active_count = int((sales_series > 0).sum()) if len(sales_series) else int(len(active))
    inactive_count = max(0, dedup_count - active_count)
    # 多规格唯一商品数：安全计算，确保与报告(全)中的数据完全一致
    try:
        multi_spec_df = identify_multi_spec_products(all_skus)
        if not multi_spec_df.empty:
            # 多规格SKU总数：直接使用识别结果的行数，确保与"多规格商品报告(全)"完全一致
            multi_sku_sum = int(len(multi_spec_df))
            # 多规格SPU数：按base_name去重计算
            if 'base_name' in multi_spec_df.columns:
                multi_spu = int(multi_spec_df['base_name'].nunique())
            elif 'product_name' in multi_spec_df.columns:
                multi_spu = int(multi_spec_df['product_name'].nunique())
            else:
                multi_spu = 0
            # 唯一多规格商品数：优先按 product_name 唯一，缺失时退回 base_name
            if 'product_name' in multi_spec_df.columns:
                multi_spec_unique = int(multi_spec_df['product_name'].nunique())
            elif 'base_name' in multi_spec_df.columns:
                multi_spec_unique = int(multi_spec_df['base_name'].nunique())
            else:
                multi_spec_unique = int(len(multi_spec_df))
        else:
            multi_sku_sum = 0
            multi_spu = 0
            multi_spec_unique = 0
    except Exception:
        multi_sku_sum = 0
        multi_spu = 0
        multi_spec_unique = 0

    # 计算单规格SKU数：总SKU数 - 多规格SKU总数
    single_sku_count = all_skus_count - multi_sku_sum
    
    # 更新单规格SPU数的计算逻辑，确保 单规格SPU + 多规格SPU = 总SPU数的一致性
    single_spu = max(0, dedup_count - multi_spec_unique)

    kpi_df = pd.DataFrame({
        "总SKU数(含规格)": [all_skus_count],
        "单规格SPU数": [single_spu],
        "单规格SKU数": [single_sku_count],  # 新增：单规格SKU数
        "多规格SKU总数": [multi_sku_sum],  # 使用直接统计的结果，确保与报告(全)一致
        "总SKU数(去重后)": [dedup_count],
        "动销SKU数": [active_count],
        "滞销SKU数": [inactive_count],
        "总销售额(去重后)": [total_revenue_dedup],
        "动销率": [active_count / dedup_count if dedup_count > 0 else 0.0],
        "唯一多规格商品数": [multi_spec_unique]
    }, index=[store_name])
    kpi_df.index.name = "门店"
    analysis_suite['总体指标'] = kpi_df

    # 关键数字日志，便于与导出表核对 (更新版：确保一致性)
    print(
        f"📌 KPI 汇总 | 门店: {store_name} | 含规格: {all_skus_count} | 去重: {dedup_count} | 动销: {active_count} | 滞销: {inactive_count} | 单规格SKU: {single_sku_count} | 多规格SKU总数: {multi_sku_sum} | 多规格唯一: {multi_spec_unique} | 销售额(去重): {total_revenue_dedup:.2f} | 动销率: {kpi_df['动销率'].iloc[0]:.2%}"
    )
    # 诊断：如出现动销=去重/滞销=0，打印进一步信息便于排查
    if dedup_count > 0 and active_count == dedup_count:
        zero_sales_dedup = int((sales_series == 0).sum())
        print(f"🔎 诊断提示: 动销SKU数与去重SKU数相等，滞销为0。去重集内销量为0的SKU数量: {zero_sales_dedup}。")
        # 抽样显示销量为0的SKU（最多5条）
        if zero_sales_dedup > 0 and 'product_name' in deduplicated.columns:
            sample_zero = deduplicated.loc[sales_series == 0, 'product_name'].head(5).tolist()
            print(f"   示例销量为0的SKU（前5）: {sample_zero}")
    if not active.empty:
        price_analysis = active.groupby('price_band', observed=True).agg(SKU数量=('product_name', 'nunique'), 销售额=('revenue', 'sum'))
        price_analysis['销售额占比'] = price_analysis['销售额'] / total_revenue_dedup if total_revenue_dedup > 0 else 0
        price_analysis['SKU占比'] = price_analysis['SKU数量'] / active_count if active_count > 0 else 0
        analysis_suite['价格带分析'] = price_analysis
        role_analysis = active.groupby('role').agg(SKU数量=('product_name', 'nunique'), 销售额=('revenue', 'sum'))
        role_analysis['销售额占比'] = role_analysis['销售额'] / total_revenue_dedup if total_revenue_dedup > 0 else 0
        role_analysis['SKU占比'] = role_analysis['SKU数量'] / active_count if active_count > 0 else 0
        analysis_suite['商品角色分析'] = role_analysis
        # 轻量一致性校验：两张表的汇总应与动销/去重总额一致
        try:
            role_sku_sum = int(pd.to_numeric(role_analysis['SKU数量'], errors='coerce').fillna(0).sum())
            price_sku_sum = int(pd.to_numeric(price_analysis['SKU数量'], errors='coerce').fillna(0).sum())
            role_rev_sum = float(pd.to_numeric(role_analysis['销售额'], errors='coerce').fillna(0).sum())
            price_rev_sum = float(pd.to_numeric(price_analysis['销售额'], errors='coerce').fillna(0).sum())
            print(f"🔎 角色分析校验 | SKU汇总={role_sku_sum} vs 动销SKU数={active_count} | 销售额汇总={role_rev_sum:.2f} vs 去重销售额={total_revenue_dedup:.2f}")
            print(f"🔎 价格带分析校验 | SKU汇总={price_sku_sum} vs 动销SKU数={active_count} | 销售额汇总={price_rev_sum:.2f} vs 去重销售额={total_revenue_dedup:.2f}")
        except Exception as ce:
            print(f"⚠️ 角色/价格带校验失败：{ce}")
    # 先按旧方式聚合0库存数
    l1_analysis = all_skus.groupby('l1_category').agg(美团一级分类sku数=('product_name', 'size'), 美团一级分类0库存数=('库存', lambda x: (x == 0).sum()))
    # 用与“总SKU数(含规格)”一致的口径替换分类sku数：
    # 每个 base_name 在分类内的变体数 = variant_key nunique（优先规格名称→名称解析→条码），
    # 分类sku数 = sum(max(1, 变体数))
    work_cat = all_skus.copy()
    work_cat['base_name'] = work_cat['product_name'].apply(_normalize_base_name)
    def _vk_cat(row):
        v = row.get('规格名称', None)
        v = v if isinstance(v, str) and v.strip() != '' else None
        if not v:
            v = _extract_inferred_spec(row.get('product_name', ''))
        if not v:
            bc = row.get('barcode', None)
            bc = str(bc).strip() if isinstance(bc, (int, float, str)) else None
            if bc and bc.lower() not in ('nan', 'none'):
                v = bc
        return v
    work_cat['variant_key'] = work_cat.apply(_vk_cat, axis=1)
    
    # 为每个 base_name 标记主分类（首次出现的分类）
    work_cat['primary_category'] = work_cat.groupby('base_name')['l1_category'].transform('first')
    
    # 标记是否为跨分类商品（同一商品出现在多个分类中）
    work_cat['is_cross_category'] = work_cat.groupby('base_name')['l1_category'].transform('nunique') > 1
    
    # 只保留主分类的记录进行统计（避免跨分类重复计数）
    work_cat_dedup = work_cat[work_cat['l1_category'] == work_cat['primary_category']].copy()
    
    # 统计跨分类商品数（用于日志校验）
    total_cross_cat = work_cat[work_cat['is_cross_category']]['base_name'].nunique()
    print(f"🔎 跨分类去重：检测到 {total_cross_cat} 个商品出现在多个分类中，已按主分类归类避免重复计数")
    
    # 基于去重后的数据计算分类SKU数
    vc_cat = work_cat_dedup.groupby(['l1_category','base_name'])['variant_key'].nunique(dropna=True).reset_index(name='vc')
    vc_cat['sku_contrib'] = vc_cat['vc'].apply(lambda x: int(x) if (pd.notna(x) and int(x) > 0) else 1)
    cat_sku_series = vc_cat.groupby('l1_category')['sku_contrib'].sum()
    # 新增：分类内多规格SKU总数（不是唯一多规格SPU数），定义为 ∑vc（vc>1）
    multi_sku_series = vc_cat.loc[vc_cat['vc'] > 1].groupby('l1_category')['vc'].sum()
    # 恢复：分类内多规格SPU数（vc>1 的 base_name 个数）
    multi_spu_series = vc_cat.assign(is_multi=vc_cat['vc'] > 1).groupby('l1_category')['is_multi'].sum()
    # 覆盖老口径
    l1_analysis['美团一级分类sku数'] = cat_sku_series
    # 写回：分类总SKU口径与多规格SKU/SPU数
    l1_analysis['美团一级分类多规格SKU数'] = multi_sku_series
    l1_analysis['美团一级分类多规格SKU数'] = l1_analysis['美团一级分类多规格SKU数'].fillna(0)
    l1_analysis['美团一级分类多规格SPU数'] = multi_spu_series
    l1_analysis['美团一级分类多规格SPU数'] = l1_analysis['美团一级分类多规格SPU数'].fillna(0)
    l1_analysis['美团一级分类0库存率'] = l1_analysis['美团一级分类0库存数'] / l1_analysis['美团一级分类sku数']
    l1_analysis['美团一级分类sku占比'] = (l1_analysis['美团一级分类sku数'] / all_skus_count) if all_skus_count > 0 else 0
    dedup_l1_counts = deduplicated.groupby('l1_category')['product_name'].nunique()
    active_l1_counts = active.groupby('l1_category')['product_name'].nunique()
    l1_analysis['美团一级分类动销sku数'] = active_l1_counts
    # 类内动销率：分类内动销SKU / 分类内去重SKU
    l1_analysis['美团一级分类去重SKU数(口径同动销率)'] = dedup_l1_counts
    l1_analysis['美团一级分类动销率(类内)'] = (active_l1_counts / dedup_l1_counts).fillna(0)
    
    # 活动SKU计算：使用与动销SKU相同的去重口径
    # 先从去重数据中筛选出有折扣的商品，再按分类统计
    
    # 🔧 临时调试：测试不同折扣阈值
    thresholds_to_test = [0, 0.01, 0.05, 0.1, 0.2]  # 0%, 1%, 5%, 10%, 20%
    
    print(f"🔎 活动SKU诊断信息:")
    print(f"   去重后总商品数: {len(deduplicated)}")
    
    # 分析折扣分布
    discount_stats = deduplicated['discount'].describe()
    print(f"   折扣分布统计: min={discount_stats['min']:.3f}, max={discount_stats['max']:.3f}, mean={discount_stats['mean']:.3f}")
    
    # 测试不同阈值的结果
    threshold_results = {}
    for threshold in thresholds_to_test:
        count = len(deduplicated[deduplicated['discount'] > threshold])
        threshold_results[f'>{threshold*100:.0f}%'] = count
        
    print(f"   不同折扣阈值商品数: {threshold_results}")
    
    # 检查原价和售价的关系
    same_price_count = len(deduplicated[deduplicated['original_price'] == deduplicated['price']])
    price_diff_count = len(deduplicated[deduplicated['original_price'] != deduplicated['price']])
    
    print(f"   原价=售价的商品数: {same_price_count}")
    print(f"   原价≠售价的商品数: {price_diff_count}")
    
    # 如果原价=售价的商品很多，给出警告
    if same_price_count > len(deduplicated) * 0.8:
        print(f"   ⚠️  警告: {same_price_count/len(deduplicated)*100:.1f}% 的商品原价=售价")
        print(f"   💡 建议: 检查Excel中是否有其他活动标识字段")
        
    # 🔧 活动商品定义：折扣率>=10% 才算真正的促销活动
    # 阈值说明：
    # - 0.10 = 10%折扣（如原价10元，售价9元）
    # - 0.20 = 20%折扣（如原价10元，售价8元）
    # - 低于10%的价格差异可能是定价策略，不算促销活动
    ACTIVITY_THRESHOLD = 0.10  # 10%折扣阈值，符合零售行业常见促销定义
    
    deduplicated_with_discount = deduplicated[deduplicated['discount'] > ACTIVITY_THRESHOLD]
    print(f"   ✅ 使用阈值 >{ACTIVITY_THRESHOLD*100:.0f}% 的活动商品数: {len(deduplicated_with_discount)}")
    print(f"   📊 活动商品占比: {len(deduplicated_with_discount)/len(deduplicated)*100:.1f}%")
    
    l1_analysis['美团一级分类活动sku数'] = deduplicated_with_discount.groupby('l1_category')['product_name'].nunique()
    # 活动占比（类内）：活动SKU / 分类内去重SKU
    l1_analysis['美团一级分类活动去重SKU数(口径同占比)'] = dedup_l1_counts
    l1_analysis['美团一级分类活动SKU占比(类内)'] = (l1_analysis['美团一级分类活动sku数'] / dedup_l1_counts).fillna(0)
    
    # 爆品SKU和折扣SKU也使用相同的去重口径和一致的阈值
    l1_analysis['美团一级分类爆品sku数'] = deduplicated[deduplicated['discount'] > 0.701].groupby('l1_category')['product_name'].nunique()
    l1_analysis['美团一级分类折扣sku数'] = deduplicated[deduplicated['discount'] > ACTIVITY_THRESHOLD].groupby('l1_category')['product_name'].nunique()
    # 月售、原价销售额、售价销售额均改为“分类内SPU口径去重”
    # 先构造 base_name
    work_ms = all_skus.copy()
    work_ms['base_name'] = work_ms['product_name'].apply(_normalize_base_name)
    # 对每个SPU，取最佳代表规格的原价/售价销售额（多级排序：销量、价格、库存、规格名）
    # 先进行多级排序，再取每组第一行
    work_ms_sorted = work_ms.sort_values(
        by=['sales_qty', 'price', '库存', '规格名称'], 
        ascending=[False, True, False, True],
        na_position='last'
    )
    idx = work_ms_sorted.groupby(['l1_category','base_name']).head(1).index
    spu_ms = work_ms.loc[idx, ['l1_category','base_name','sales_qty','original_price_revenue','revenue']].copy()
    spu_ms = spu_ms.rename(columns={'sales_qty':'spu月售','original_price_revenue':'spu原价销售额','revenue':'spu售价销售额'})
    # 按一级分类聚合
    l1_month_sales_dedup = spu_ms.groupby('l1_category')['spu月售'].sum()
    l1_sales_dedup = spu_ms.groupby('l1_category').agg(原价销售额=('spu原价销售额','sum'), 售价销售额=('spu售价销售额','sum'))
    # 合并回分析表
    l1_analysis = l1_analysis.join(l1_sales_dedup, how='left')
    l1_analysis['月售'] = l1_month_sales_dedup
    l1_analysis['月售'] = pd.to_numeric(l1_analysis['月售'], errors='coerce').fillna(0)
    # 月售占比分母也改为去重后的总月售
    total_month_sales_dedup = float(l1_month_sales_dedup.sum()) if hasattr(l1_month_sales_dedup, 'sum') else 0.0
    l1_analysis['美团一级分类月售占比'] = (l1_analysis['月售'] / total_month_sales_dedup) if total_month_sales_dedup > 0 else 0
    # 校验日志：未去重总月售 vs SPU口径总月售
    try:
        raw_total_month = float(pd.to_numeric(all_skus['sales_qty'], errors='coerce').fillna(0).sum())
        print(f"🔎 月售口径 | 未去重总月售={raw_total_month:.0f} | 分类内SPU去重总月售={total_month_sales_dedup:.0f}")
    except Exception:
        pass
    l1_analysis['美团一级分类原价销售额占比'] = l1_analysis['原价销售额'] / all_skus['original_price_revenue'].sum() if all_skus['original_price_revenue'].sum() > 0 else 0
    l1_analysis['美团一级分类原价销售件单价'] = (l1_analysis['原价销售额'] / l1_analysis['月售']).replace([np.inf, -np.inf], 0).fillna(0)
    l1_analysis['美团一级分类售价销售额占比'] = l1_analysis['售价销售额'] / all_skus['revenue'].sum() if all_skus['revenue'].sum() > 0 else 0
    # 将“折扣率(百分比)”改为“折扣(折)”展示：加权折扣 = 售价销售额 / 原价销售额，然后乘以10得到 x.x 折
    _ratio = (l1_analysis['售价销售额'] / l1_analysis['原价销售额']).replace([np.inf, -np.inf], 0).fillna(0)
    l1_analysis['美团一级分类折扣'] = (_ratio * 10.0).clip(lower=0, upper=10)
    
    # ====== 分类成本聚合 ======
    if has_cost_data:
        # 使用SPU去重后的成本销售额和毛利汇总
        spu_ms['spu成本销售额'] = work_ms.loc[idx, '成本销售额'].values
        spu_ms['spu毛利'] = work_ms.loc[idx, '毛利'].values
        spu_ms['spu定价毛利'] = work_ms.loc[idx, '定价毛利'].values
        
        l1_cost_agg = spu_ms.groupby('l1_category').agg(
            成本销售额=('spu成本销售额', 'sum'),
            毛利=('spu毛利', 'sum'),
            定价毛利=('spu定价毛利', 'sum')
        )
        
        l1_analysis = l1_analysis.join(l1_cost_agg, how='left')
        
        # 售价毛利率：毛利 / 售价销售额（实际销售情况）
        l1_analysis['美团一级分类售价毛利率'] = l1_analysis.apply(
            lambda row: (row['毛利'] / row['售价销售额']) if row['售价销售额'] > 0 else 0,
            axis=1
        )
        
        # 定价毛利率：定价毛利 / 原价销售额（按原价计算）
        l1_analysis['美团一级分类定价毛利率'] = l1_analysis.apply(
            lambda row: (row['定价毛利'] / row['原价销售额']) if row['原价销售额'] > 0 else 0,
            axis=1
        )
        
        # 保留旧的"毛利率"列以兼容现有代码（指向售价毛利率）
        l1_analysis['美团一级分类毛利率'] = l1_analysis['美团一级分类售价毛利率']
        
        # 分类毛利贡献度：本分类毛利 / 总毛利
        total_profit = l1_analysis['毛利'].sum()
        l1_analysis['美团一级分类毛利贡献度'] = l1_analysis.apply(
            lambda row: (row['毛利'] / total_profit) if total_profit > 0 else 0,
            axis=1
        )
        
        print(f"✅ 分类成本聚合完成：总毛利 ¥{total_profit:,.2f}")
    
    # 跨类动销占比：该分类动销SKU / 全部分类动销SKU
    total_active = float(active_l1_counts.sum()) if hasattr(active_l1_counts, 'sum') else 0.0
    l1_analysis['美团一级分类动销SKU占比(跨类)'] = (active_l1_counts / total_active).fillna(0) if total_active > 0 else 0

    # 跨类活动占比：该分类活动SKU / 全部分类活动SKU
    total_campaign = float(l1_analysis['美团一级分类活动sku数'].sum()) if '美团一级分类活动sku数' in l1_analysis.columns else 0.0
    l1_analysis['美团一级分类活动SKU占比(跨类)'] = (l1_analysis['美团一级分类活动sku数'] / total_campaign).fillna(0) if total_campaign > 0 else 0

    # 重排列顺序：将动销/活动的计数与占比贴近摆放，提升可读性
    try:
        preferred_order = [
            '美团一级分类sku数',
            '美团一级分类多规格SKU数',
            '美团一级分类多规格SPU数',
            '美团一级分类去重SKU数(口径同动销率)',
            '美团一级分类动销sku数',
            '美团一级分类动销率(类内)',
            '美团一级分类动销SKU占比(跨类)',
            '美团一级分类活动去重SKU数(口径同占比)',
            '美团一级分类活动sku数',
            '美团一级分类活动SKU占比(类内)',
            '美团一级分类活动SKU占比(跨类)',
            '美团一级分类0库存数',
            '美团一级分类0库存率',
            '美团一级分类sku占比',
            '月售',
            '美团一级分类月售占比',
            '原价销售额',
            '售价销售额',
            '成本销售额',  # 新增
            '毛利',  # 新增
            '美团一级分类原价销售额占比',
            '美团一级分类售价销售额占比',
            '美团一级分类毛利率',  # 新增
            '美团一级分类毛利贡献度',  # 新增
            '美团一级分类原价销售件单价',
            '美团一级分类折扣sku数',
            '美团一级分类爆品sku数',
            '美团一级分类折扣',
        ]
        existing_pref = [c for c in preferred_order if c in l1_analysis.columns]
        remainder = [c for c in l1_analysis.columns if c not in existing_pref]
        l1_analysis = l1_analysis[existing_pref + remainder]
    except Exception:
        pass

    analysis_suite['美团一级分类详细指标'] = l1_analysis.fillna(0).reset_index()
    
    # === 美团三级分类详细指标分析 ===
    # 检查是否有三级分类数据
    if 'l3_category' in all_skus.columns and not all_skus['l3_category'].isna().all():
        print(f"ℹ️ 开始计算美团三级分类详细指标...")
        
        # 先按旧方式聚合0库存数
        l3_analysis = all_skus.groupby('l3_category').agg(美团三级分类sku数=('product_name', 'size'), 美团三级分类0库存数=('库存', lambda x: (x == 0).sum()))
        
        # 🔧 方案A：跨分类去重逻辑（与核心指标保持一致）
        work_cat_l3 = all_skus.copy()
        work_cat_l3['base_name'] = work_cat_l3['product_name'].apply(_normalize_base_name)
        work_cat_l3['variant_key'] = work_cat_l3.apply(_vk_cat, axis=1)
        
        # 为每个 base_name 标记主分类（首次出现的三级分类）
        work_cat_l3['primary_category_l3'] = work_cat_l3.groupby('base_name')['l3_category'].transform('first')
        
        # 只保留主分类的记录进行统计（避免跨分类重复计数）
        work_cat_l3_dedup = work_cat_l3[work_cat_l3['l3_category'] == work_cat_l3['primary_category_l3']].copy()
        
        vc_cat_l3 = work_cat_l3_dedup.groupby(['l3_category','base_name'])['variant_key'].nunique(dropna=True).reset_index(name='vc')
        vc_cat_l3['sku_contrib'] = vc_cat_l3['vc'].apply(lambda x: int(x) if (pd.notna(x) and int(x) > 0) else 1)
        cat_sku_series_l3 = vc_cat_l3.groupby('l3_category')['sku_contrib'].sum()
        
        # 分类内多规格SKU总数和多规格SPU数
        multi_sku_series_l3 = vc_cat_l3.loc[vc_cat_l3['vc'] > 1].groupby('l3_category')['vc'].sum()
        multi_spu_series_l3 = vc_cat_l3.assign(is_multi=vc_cat_l3['vc'] > 1).groupby('l3_category')['is_multi'].sum()
        
        # 覆盖老口径
        l3_analysis['美团三级分类sku数'] = cat_sku_series_l3
        l3_analysis['美团三级分类多规格SKU数'] = multi_sku_series_l3.fillna(0)
        l3_analysis['美团三级分类多规格SPU数'] = multi_spu_series_l3.fillna(0)
        l3_analysis['美团三级分类0库存率'] = l3_analysis['美团三级分类0库存数'] / l3_analysis['美团三级分类sku数']
        l3_analysis['美团三级分类sku占比'] = (l3_analysis['美团三级分类sku数'] / all_skus_count) if all_skus_count > 0 else 0
        
        dedup_l3_counts = deduplicated.groupby('l3_category')['product_name'].nunique()
        active_l3_counts = active.groupby('l3_category')['product_name'].nunique()
        l3_analysis['美团三级分类动销sku数'] = active_l3_counts
        l3_analysis['美团三级分类去重SKU数(口径同动销率)'] = dedup_l3_counts
        l3_analysis['美团三级分类动销率(类内)'] = (active_l3_counts / dedup_l3_counts).fillna(0)
        
        # 活动SKU计算：使用与一级分类相同的阈值和逻辑
        l3_analysis['美团三级分类活动sku数'] = deduplicated_with_discount.groupby('l3_category')['product_name'].nunique()
        l3_analysis['美团三级分类活动去重SKU数(口径同占比)'] = dedup_l3_counts
        l3_analysis['美团三级分类活动SKU占比(类内)'] = (l3_analysis['美团三级分类活动sku数'] / dedup_l3_counts).fillna(0)
        
        # 爆品SKU和折扣SKU
        l3_analysis['美团三级分类爆品sku数'] = deduplicated[deduplicated['discount'] > 0.701].groupby('l3_category')['product_name'].nunique()
        l3_analysis['美团三级分类折扣sku数'] = deduplicated[deduplicated['discount'] > ACTIVITY_THRESHOLD].groupby('l3_category')['product_name'].nunique()
        
        # 月售、原价销售额、售价销售额（SPU口径去重）
        work_ms_l3 = all_skus.copy()
        work_ms_l3['base_name'] = work_ms_l3['product_name'].apply(_normalize_base_name)
        work_ms_sorted_l3 = work_ms_l3.sort_values(
            by=['sales_qty', 'price', '库存', '规格名称'], 
            ascending=[False, True, False, True],
            na_position='last'
        )
        idx_l3 = work_ms_sorted_l3.groupby(['l3_category','base_name']).head(1).index
        spu_ms_l3 = work_ms_l3.loc[idx_l3, ['l3_category','base_name','sales_qty','original_price_revenue','revenue']].copy()
        spu_ms_l3 = spu_ms_l3.rename(columns={'sales_qty':'spu月售','original_price_revenue':'spu原价销售额','revenue':'spu售价销售额'})
        
        # 按三级分类聚合
        l3_month_sales_dedup = spu_ms_l3.groupby('l3_category')['spu月售'].sum()
        l3_sales_dedup = spu_ms_l3.groupby('l3_category').agg(原价销售额=('spu原价销售额','sum'), 售价销售额=('spu售价销售额','sum'))
        
        # 合并回分析表
        l3_analysis = l3_analysis.join(l3_sales_dedup, how='left')
        l3_analysis['月售'] = l3_month_sales_dedup
        l3_analysis['月售'] = pd.to_numeric(l3_analysis['月售'], errors='coerce').fillna(0)
        
        # 月售占比
        total_month_sales_dedup_l3 = float(l3_month_sales_dedup.sum()) if hasattr(l3_month_sales_dedup, 'sum') else 0.0
        l3_analysis['美团三级分类月售占比'] = (l3_analysis['月售'] / total_month_sales_dedup_l3) if total_month_sales_dedup_l3 > 0 else 0
        
        # 销售额占比和件单价
        l3_analysis['美团三级分类原价销售额占比'] = l3_analysis['原价销售额'] / all_skus['original_price_revenue'].sum() if all_skus['original_price_revenue'].sum() > 0 else 0
        l3_analysis['美团三级分类原价销售件单价'] = (l3_analysis['原价销售额'] / l3_analysis['月售']).replace([np.inf, -np.inf], 0).fillna(0)
        l3_analysis['美团三级分类售价销售额占比'] = l3_analysis['售价销售额'] / all_skus['revenue'].sum() if all_skus['revenue'].sum() > 0 else 0
        
        # 折扣（折）展示
        _ratio_l3 = (l3_analysis['售价销售额'] / l3_analysis['原价销售额']).replace([np.inf, -np.inf], 0).fillna(0)
        l3_analysis['美团三级分类折扣'] = (_ratio_l3 * 10.0).clip(lower=0, upper=10)
        
        # 跨类动销占比和活动占比
        total_active_l3 = float(active_l3_counts.sum()) if hasattr(active_l3_counts, 'sum') else 0.0
        l3_analysis['美团三级分类动销SKU占比(跨类)'] = (active_l3_counts / total_active_l3).fillna(0) if total_active_l3 > 0 else 0
        
        total_campaign_l3 = float(l3_analysis['美团三级分类活动sku数'].sum()) if '美团三级分类活动sku数' in l3_analysis.columns else 0.0
        l3_analysis['美团三级分类活动SKU占比(跨类)'] = (l3_analysis['美团三级分类活动sku数'] / total_campaign_l3).fillna(0) if total_campaign_l3 > 0 else 0
        
        # 重排列顺序（与一级分类保持一致的逻辑）
        try:
            preferred_order_l3 = [
                '美团三级分类sku数',
                '美团三级分类多规格SKU数',
                '美团三级分类多规格SPU数',
                '美团三级分类去重SKU数(口径同动销率)',
                '美团三级分类动销sku数',
                '美团三级分类动销率(类内)',
                '美团三级分类动销SKU占比(跨类)',
                '美团三级分类活动去重SKU数(口径同占比)',
                '美团三级分类活动sku数',
                '美团三级分类活动SKU占比(类内)',
                '美团三级分类活动SKU占比(跨类)',
                '美团三级分类0库存数',
                '美团三级分类0库存率',
                '美团三级分类sku占比',
                '月售',
                '美团三级分类月售占比',
                '原价销售额',
                '售价销售额',
                '美团三级分类原价销售额占比',
                '美团三级分类售价销售额占比',
                '美团三级分类原价销售件单价',
                '美团三级分类折扣sku数',
                '美团三级分类爆品sku数',
                '美团三级分类折扣',
            ]
            existing_pref_l3 = [c for c in preferred_order_l3 if c in l3_analysis.columns]
            remainder_l3 = [c for c in l3_analysis.columns if c not in existing_pref_l3]
            l3_analysis = l3_analysis[existing_pref_l3 + remainder_l3]
        except Exception:
            pass

        analysis_suite['美团三级分类详细指标'] = l3_analysis.fillna(0).reset_index()
        print(f"✅ 美团三级分类详细指标分析完成，共 {len(l3_analysis)} 个三级分类。")
    else:
        print(f"⚠️ 未找到有效的三级分类数据，跳过三级分类分析。")
    
    # ====== 成本分析汇总Sheet ======
    if has_cost_data and 'l1_category' in all_skus.columns:
        print(f"ℹ️ 开始生成成本分析汇总...")
        
        cost_summary_df = l1_analysis[[
            '成本销售额', '售价销售额', '原价销售额', '毛利', '定价毛利',
            '美团一级分类售价毛利率', '美团一级分类定价毛利率', '美团一级分类毛利贡献度'
        ]].copy() if has_cost_data else pd.DataFrame()
        
        if not cost_summary_df.empty:
            # 添加分类名称作为列
            cost_summary_df.insert(0, '美团一级分类', cost_summary_df.index)
            
            # 排序：按售价毛利率降序
            cost_summary_df = cost_summary_df.sort_values('美团一级分类售价毛利率', ascending=False)
            
            # 添加高低毛利商品统计
            high_margin_count = (all_skus['售价毛利率'] >= 0.5).sum()
            low_margin_count = (all_skus['售价毛利率'] < 0.1).sum()
            
            # 在Sheet中添加汇总行
            total_row = pd.DataFrame({
                '美团一级分类': ['全部分类汇总'],
                '成本销售额': [cost_summary_df['成本销售额'].sum()],
                '售价销售额': [cost_summary_df['售价销售额'].sum()],
                '原价销售额': [cost_summary_df['原价销售额'].sum()],
                '毛利': [cost_summary_df['毛利'].sum()],
                '定价毛利': [cost_summary_df['定价毛利'].sum()],
                '美团一级分类售价毛利率': [cost_summary_df['毛利'].sum() / cost_summary_df['售价销售额'].sum() if cost_summary_df['售价销售额'].sum() > 0 else 0],
                '美团一级分类定价毛利率': [cost_summary_df['定价毛利'].sum() / cost_summary_df['原价销售额'].sum() if cost_summary_df['原价销售额'].sum() > 0 else 0],
                '美团一级分类毛利贡献度': [1.0]
            })
            
            cost_summary_df = pd.concat([total_row, cost_summary_df], ignore_index=True)
            
            analysis_suite['成本分析汇总'] = cost_summary_df
            
            # 高毛利商品TOP50（按售价毛利率筛选）
            high_margin_skus = all_skus[all_skus['售价毛利率'] >= 0.3].copy()
            if not high_margin_skus.empty:
                high_margin_skus = high_margin_skus.sort_values('毛利', ascending=False).head(50)
                high_margin_top50 = high_margin_skus[[
                    'product_name', 'l1_category', 'price', 'original_price', 'cost', 
                    '毛利', '售价毛利率', '定价毛利率', 
                    'sales_qty', 'revenue', '成本销售额'
                ]].copy()
                # 重命名列便于理解
                high_margin_top50 = high_margin_top50.rename(columns={
                    'price': '售价',
                    'original_price': '原价',
                    'sales_qty': '月售',
                    'revenue': '售价销售额'
                })
                analysis_suite['高毛利商品TOP50'] = high_margin_top50
            
            # 低毛利预警商品（按售价毛利率筛选）
            low_margin_skus = all_skus[all_skus['售价毛利率'] < 0.1].copy()
            if not low_margin_skus.empty:
                low_margin_skus = low_margin_skus.sort_values('revenue', ascending=False).head(100)
                low_margin_warning = low_margin_skus[[
                    'product_name', 'l1_category', 'price', 'original_price', 'cost', 
                    '毛利', '售价毛利率', '定价毛利率',
                    'sales_qty', 'revenue', '成本销售额'
                ]].copy()
                # 重命名列便于理解
                low_margin_warning = low_margin_warning.rename(columns={
                    'price': '售价',
                    'original_price': '原价',
                    'sales_qty': '月售',
                    'revenue': '售价销售额'
                })
                analysis_suite['低毛利预警商品'] = low_margin_warning
            
            print(f"✅ 成本分析汇总完成：高毛利商品{len(high_margin_skus)}个，低毛利商品{len(low_margin_skus)}个")
    
    return analysis_suite

def export_full_report_to_excel(all_results, all_store_data, output_filename):
    """将所有分析结果和详细报告导出到Excel。"""
    # 规范化输出路径与占用处理
    output_path = Path(output_filename).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 若同名文件已存在，尝试删除；若被占用，则改为时间戳文件名
    if output_path.exists():
        try:
            os.remove(output_path)
        except Exception as e:
            ts = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
            alt = output_path.with_name(f"{output_path.stem}_{ts}{output_path.suffix}")
            print(f"⚠️ 目标文件被占用或无法覆盖（{e}）。将改为输出: {alt.name}")
            output_path = alt

    print(f"\n⏳ 正在生成Excel报告: {output_path.name}...")

    # 优先使用 xlsxwriter，不可用时回退 openpyxl；如仍失败，附带时间戳重试一次
    engine_name = 'xlsxwriter'
    try:
        writer = pd.ExcelWriter(str(output_path), engine='xlsxwriter')
    except Exception:
        print("⚠️ xlsxwriter 不可用，回退到 openpyxl。建议: pip install XlsxWriter 以获得更佳兼容与格式支持。")
        engine_name = 'openpyxl'
        try:
            writer = pd.ExcelWriter(str(output_path), engine='openpyxl')
        except PermissionError as e:
            ts = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
            alt = output_path.with_name(f"{output_path.stem}_{ts}{output_path.suffix}")
            print(f"⚠️ 打开文件失败（{e}）。可能被占用，将改为输出: {alt.name}")
            writer = pd.ExcelWriter(str(alt), engine='openpyxl')
    with writer:
        # 按 Sheet 白名单识别百分比列；若白名单缺失则回退到数值范围(0..1)判断
        def get_sheet_pct_cols(sheet_name, df):
            whitelist = {
                '商品角色分析': ['销售额占比', 'SKU占比'],
                '价格带分析': ['销售额占比', 'SKU占比'],
                '美团一级分类详细指标': [
                    '美团一级分类0库存率',
                    '美团一级分类sku占比',
                    '美团一级分类动销率(类内)',
                    '美团一级分类动销SKU占比(跨类)',
                    '美团一级分类活动SKU占比(类内)',
                    '美团一级分类活动SKU占比(跨类)',
                    '美团一级分类月售占比',
                    '美团一级分类原价销售额占比',
                    '美团一级分类售价销售额占比',
                    '美团一级分类售价毛利率',  # 新增
                    '美团一级分类定价毛利率',  # 新增
                    '美团一级分类毛利率',  # 兼容旧代码
                    '美团一级分类毛利贡献度',  # 新增
                ],
                '美团三级分类详细指标': [
                    '美团三级分类0库存率',
                    '美团三级分类sku占比',
                    '美团三级分类动销率(类内)',
                    '美团三级分类动销SKU占比(跨类)',
                    '美团三级分类活动SKU占比(类内)',
                    '美团三级分类活动SKU占比(跨类)',
                    '美团三级分类月售占比',
                    '美团三级分类原价销售额占比',
                    '美团三级分类售价销售额占比',
                ],
                '核心指标对比': ['动销率'],
                '成本分析汇总': ['美团一级分类售价毛利率', '美团一级分类定价毛利率', '美团一级分类毛利率', '美团一级分类毛利贡献度'],  # 新增
                '高毛利商品TOP50': ['售价毛利率', '定价毛利率', '毛利率'],  # 新增
                '低毛利预警商品': ['售价毛利率', '定价毛利率', '毛利率'],  # 新增
            }
            wl = whitelist.get(sheet_name, [])
            pct_cols = [c for c in wl if c in df.columns]
            # 兜底：选择 dtype 为浮点，且值域在 0..1 的列
            if not pct_cols:
                for c in df.columns:
                    if '单价' in str(c):
                        continue
                    s = df[c]
                    if pd.api.types.is_float_dtype(s):
                        try:
                            s_non_null = s.dropna()
                            if not s_non_null.empty:
                                vmin = float(s_non_null.min())
                                vmax = float(s_non_null.max())
                                if vmin >= 0.0 and vmax <= 1.000001:
                                    pct_cols.append(c)
                        except Exception:
                            pass
            return pct_cols

        # xlsxwriter：按列名列表设置 0.00%（考虑索引层数偏移）
        def apply_pct_xlsxwriter(ws, df, pct_cols, index_written=True):
            if ws is None or not pct_cols:
                return
            wb = writer.book
            fmt_pct = wb.add_format({'num_format': '0.00%'})
            offset = df.index.nlevels if index_written else 0
            for col_name in pct_cols:
                try:
                    col_idx = int(df.columns.get_loc(col_name)) + offset
                    ws.set_column(col_idx, col_idx, None, fmt_pct)
                except Exception:
                    pass

        # openpyxl：按列名列表设置 0.00%
        def apply_pct_openpyxl(ws, pct_cols):
            if ws is None or not pct_cols:
                return
            header_map = {}
            for cell in ws[1]:
                header_map[str(cell.value)] = cell.column
            max_row = ws.max_row
            for name in pct_cols:
                c = header_map.get(str(name))
                if c is None:
                    continue
                for r in range(2, max_row + 1):
                    ws.cell(row=r, column=c).number_format = '0.00%'

        # 写入各 Sheet (中文化表头)
        # 定义列名中文化映射
        column_cn_mapping = {
            # 核心指标
            '总SKU数(含规格)': '总SKU数(含规格)',
            '单规格SPU数': '单规格SPU数', 
            '单规格SKU数': '单规格SKU数',
            '多规格SKU总数': '多规格SKU总数',
            '总SKU数(去重后)': '总SKU数(去重后)',
            '动销SKU数': '动销SKU数',
            '滞销SKU数': '滞销SKU数', 
            '总销售额(去重后)': '总销售额(去重后)',
            '动销率': '动销率',
            '唯一多规格商品数': '唯一多规格商品数',
            # 角色/价格带分析
            'SKU数量': 'SKU数量',
            '销售额': '销售额',
            '销售额占比': '销售额占比',
            'SKU占比': 'SKU占比',
            # 多规格相关 - 扩展映射
            'Store': '门店',
            'product_name': '商品名称', 
            'base_name': '基础名称',
            'l1_category': '一级分类',
            'l3_category': '三级分类',
            '规格种类数': '规格种类数',
            '多规格依据': '多规格依据',
            'sales_qty': '月售',
            # 其他可能用到的列
            'price': '售价',
            'original_price': '原价',
            'revenue': '售价销售额',
            'original_price_revenue': '原价销售额',
            'price_band': '价格带',
            'role': '商品角色',
            'discount': '折扣',
            '库存': '库存',
            '规格名称': '规格名称',
            'barcode': '条码',
            '商家分类': '商家分类',
            'variant_key': '变体键',
            'inferred_spec': '推断规格'
        }
        
        # 应用中文列名映射函数
        def apply_cn_columns(df):
            df_copy = df.copy()
            df_copy.columns = [column_cn_mapping.get(col, col) for col in df_copy.columns]
            return df_copy
        
        core_kpi_df = pd.concat([res['总体指标'] for res in all_results.values() if '总体指标' in res])
        core_kpi_df = apply_cn_columns(core_kpi_df)
        core_kpi_df.to_excel(writer, sheet_name='核心指标对比')

        role_df = pd.concat([res['商品角色分析'] for res in all_results.values() if '商品角色分析' in res], keys=all_results.keys())
        role_df = apply_cn_columns(role_df)
        role_df.to_excel(writer, sheet_name='商品角色分析')

        price_df = pd.concat([res['价格带分析'] for res in all_results.values() if '价格带分析' in res], keys=all_results.keys())
        price_df = apply_cn_columns(price_df)
        price_df.to_excel(writer, sheet_name='价格带分析')

        # 生成一致性校验表：角色/价格带的SKU与销售额汇总需分别等于 动销SKU数/去重总销售额
        try:
            # 按门店聚合两张表
            role_agg = role_df.groupby(level=0).agg(角色SKU汇总=('SKU数量', 'sum'), 角色销售额汇总=('销售额', 'sum'))
            price_agg = price_df.groupby(level=0).agg(价格带SKU汇总=('SKU数量', 'sum'), 价格带销售额汇总=('销售额', 'sum'))
            # KPI 基准
            kpi_base = core_kpi_df[['动销SKU数', '总销售额(去重后)']].copy()
            # 合并
            chk = kpi_base.join(role_agg, how='left').join(price_agg, how='left')
            # 计算一致性布尔项（销售额允许少量浮点误差）
            def _isclose(a, b):
                try:
                    return bool(np.isclose(float(a), float(b), rtol=1e-6, atol=0.01))
                except Exception:
                    return False
            chk['校验_角色SKU一致'] = (pd.to_numeric(chk['角色SKU汇总'], errors='coerce').fillna(0).astype(int) == pd.to_numeric(chk['动销SKU数'], errors='coerce').fillna(0).astype(int))
            chk['校验_价格带SKU一致'] = (pd.to_numeric(chk['价格带SKU汇总'], errors='coerce').fillna(0).astype(int) == pd.to_numeric(chk['动销SKU数'], errors='coerce').fillna(0).astype(int))
            chk['校验_角色销售额一致'] = [
                _isclose(a, b) for a, b in zip(pd.to_numeric(chk['角色销售额汇总'], errors='coerce').fillna(0), pd.to_numeric(chk['总销售额(去重后)'], errors='coerce').fillna(0))
            ]
            chk['校验_价格带销售额一致'] = [
                _isclose(a, b) for a, b in zip(pd.to_numeric(chk['价格带销售额汇总'], errors='coerce').fillna(0), pd.to_numeric(chk['总销售额(去重后)'], errors='coerce').fillna(0))
            ]
            # 输出
            chk.index.name = '门店'
            # 友好列序
            col_order = ['动销SKU数', '角色SKU汇总', '价格带SKU汇总', '总销售额(去重后)', '角色销售额汇总', '价格带销售额汇总', '校验_角色SKU一致', '校验_价格带SKU一致', '校验_角色销售额一致', '校验_价格带销售额一致']
            exist_cols = [c for c in col_order if c in chk.columns]
            chk = chk[exist_cols]
            chk = apply_cn_columns(chk)
            # chk.to_excel(writer, sheet_name='校验-角色与价格带一致性')  # 【已禁用】用户要求删除此Sheet
        except Exception as ce:
            print(f"⚠️ 生成‘校验-角色与价格带一致性’失败：{ce}")
        all_l1_analysis = pd.concat([
            res['美团一级分类详细指标'].assign(门店=store)
            for store, res in all_results.items() if '美团一级分类详细指标' in res
        ])
        all_l1_analysis = apply_cn_columns(all_l1_analysis)
        all_l1_analysis.to_excel(writer, sheet_name='美团一级分类详细指标', index=False)
        
        # 美团三级分类详细指标
        l3_results = [
            res['美团三级分类详细指标'].assign(门店=store)
            for store, res in all_results.items() if '美团三级分类详细指标' in res
        ]
        if l3_results:
            all_l3_analysis = pd.concat(l3_results)
            all_l3_analysis = apply_cn_columns(all_l3_analysis)
            all_l3_analysis.to_excel(writer, sheet_name='美团三级分类详细指标', index=False)
            print(f"ℹ️ 美团三级分类详细指标Sheet已生成，包含 {len(all_l3_analysis)} 条记录。")
        else:
            print(f"⚠️ 未找到三级分类数据，跳过三级分类Sheet生成。")
        
        all_deduplicated_dfs = pd.concat([data['deduplicated'] for data in all_store_data.values()], ignore_index=True)
        all_deduplicated_dfs = apply_cn_columns(all_deduplicated_dfs)
        all_deduplicated_dfs.to_excel(writer, sheet_name='详细SKU报告(去重后)', index=False)
        
        all_skus_combined = pd.concat([data['all_skus'] for data in all_store_data.values()], ignore_index=True)
        multi_spec_report = identify_multi_spec_products(all_skus_combined)
        # 先完成所有使用英文列名的操作，再应用中文化
        multi_spec_report_cn = apply_cn_columns(multi_spec_report)
        multi_spec_report_cn.to_excel(writer, sheet_name='多规格商品报告(全)', index=False)
        # SKU结构概览：按门店+base_name 的变体结构
        try:
            sku_structure_rows = []
            for store, data in all_store_data.items():
                dfw = data['all_skus'].copy()
                dfw['base_name'] = dfw['product_name'].apply(_normalize_base_name)
                def _vk(row):
                    v = row.get('规格名称', None)
                    v = v if isinstance(v, str) and v.strip() != '' else None
                    if not v:
                        v = _extract_inferred_spec(row.get('product_name', ''))
                    if not v:
                        bc = row.get('barcode', None)
                        bc = str(bc).strip() if isinstance(bc, (int, float, str)) else None
                        if bc and bc.lower() not in ('nan', 'none'):
                            v = bc
                    return v
                dfw['variant_key'] = dfw.apply(_vk, axis=1)
                # 变体计数与示例
                g = dfw.groupby('base_name')['variant_key'].agg(['nunique', lambda x: ', '.join(pd.Series(x).dropna().astype(str).unique()[:5])]).reset_index()
                g.columns = ['base_name', '变体数', '示例变体(≤5)']
                g['结构类型'] = np.where(g['变体数'] > 1, '多规格', '单规格')
                g['门店'] = store
                sku_structure_rows.append(g)
            if sku_structure_rows:
                sku_structure_df = pd.concat(sku_structure_rows, ignore_index=True)
                sku_structure_df = sku_structure_df[['门店', 'base_name', '结构类型', '变体数', '示例变体(≤5)']]
                # 应用中文化列名映射
                sku_structure_df = sku_structure_df.rename(columns={'base_name': '基础名称'})
                sku_structure_df.to_excel(writer, sheet_name='SKU结构概览', index=False)
        except Exception as se:
            print(f"⚠️ 生成SKU结构概览失败：{se}")
        # 供一致性校验用的“去重后多规格变体计数”：每个 (Store, base_name) 的 variant_key 数
        if not multi_spec_report.empty and all(col in multi_spec_report.columns for col in ['base_name', 'variant_key']):
            m_count_df = multi_spec_report.dropna(subset=['variant_key']).copy()
            g_keys = ['Store', 'base_name'] if 'Store' in m_count_df.columns else ['base_name']
            var_cnt = m_count_df.groupby(g_keys)['variant_key'].nunique().rename('规格种类数_按变体键').reset_index()
        else:
            var_cnt = pd.DataFrame()
        if not multi_spec_report.empty:
            # 动态选择可用的唯一键：优先 product_name，不存在则回退 base_name
            has_store = 'Store' in multi_spec_report.columns
            keys_candidates = []
            if has_store and 'product_name' in multi_spec_report.columns:
                keys_candidates = ['Store', 'product_name']
            elif has_store and 'base_name' in multi_spec_report.columns:
                keys_candidates = ['Store', 'base_name']
            elif 'product_name' in multi_spec_report.columns:
                keys_candidates = ['product_name']
            elif 'base_name' in multi_spec_report.columns:
                keys_candidates = ['base_name']
            else:
                # 兜底：使用首列
                keys_candidates = [multi_spec_report.columns[0]]

            # 先准备分类和月售信息（使用英文列名）
            category_sales_info = None
            if not multi_spec_report.empty:
                # 构建聚合字典，只包含存在的列
                agg_dict = {}
                if 'l1_category' in multi_spec_report.columns:
                    agg_dict['l1_category'] = 'first'
                if 'l3_category' in multi_spec_report.columns:
                    agg_dict['l3_category'] = 'first'
                if 'sales_qty' in multi_spec_report.columns:
                    agg_dict['sales_qty'] = 'first'  # 占位，实际会特殊处理
                # 添加价格和库存相关字段 - 修正：按最佳代表规格取值（多级排序）
                # 对于价格和销售额，不能用平均值，应该以销量最高的规格为准
                # 这里先用 'first' 作为占位，后面会特殊处理
                if 'price' in multi_spec_report.columns:
                    agg_dict['price'] = 'first'  # 占位，实际会特殊处理
                if 'original_price' in multi_spec_report.columns:
                    agg_dict['original_price'] = 'first'  # 占位，实际会特殊处理
                if '库存' in multi_spec_report.columns:
                    agg_dict['库存'] = 'sum'  # 库存仍然取总和
                # 销售额字段也需要特殊处理
                if 'revenue' in multi_spec_report.columns:
                    agg_dict['revenue'] = 'first'  # 占位，实际会特殊处理
                if 'original_price_revenue' in multi_spec_report.columns:
                    agg_dict['original_price_revenue'] = 'first'  # 占位，实际会特殊处理
                
                if agg_dict:  # 只在有可用列时进行聚合
                    category_sales_info = multi_spec_report.groupby(keys_candidates).agg(agg_dict).reset_index()
                    
                    # 特殊处理：对于价格和销售额字段，取最佳代表规格的数据（多级排序）
                    price_revenue_fields = ['price', 'original_price', 'revenue', 'original_price_revenue']
                    existing_fields = [f for f in price_revenue_fields if f in multi_spec_report.columns]
                    
                    if existing_fields:
                        print(f"ℹ️ 正在为多规格商品重新计算价格和销售额（多级排序选择最佳代表规格）...")
                        
                        # 为每个商品组找到最佳代表规格
                        max_sales_data = []
                        for group_key in category_sales_info[keys_candidates].to_dict('records'):
                            # 使用直接筛选方法，避免 query 字符串构造问题
                            mask = pd.Series([True] * len(multi_spec_report))
                            for key, value in group_key.items():
                                mask = mask & (multi_spec_report[key] == value)
                            
                            product_variants = multi_spec_report[mask]
                            
                            if not product_variants.empty:
                                # 多级排序选择最佳代表规格：销量降序、价格升序、库存降序、规格名称升序
                                sorted_variants = product_variants.sort_values(
                                    by=['sales_qty', 'price', '库存', '规格名称'], 
                                    ascending=[False, True, False, True],
                                    na_position='last'
                                )
                                max_sales_row = sorted_variants.iloc[0]
                                
                                # 保存该规格的价格和销售额数据
                                max_sales_record = {**group_key}
                                for field in existing_fields:
                                    max_sales_record[field] = max_sales_row[field]
                                
                                max_sales_data.append(max_sales_record)
                        
                        # 将特殊处理的数据合并回 category_sales_info
                        if max_sales_data:
                            max_sales_df = pd.DataFrame(max_sales_data)
                            
                            # 用新数据更新 category_sales_info 中的对应字段
                            for field in existing_fields:
                                if field in max_sales_df.columns:
                                    # 删除原有列，用新数据替换
                                    category_sales_info = category_sales_info.drop(columns=[field], errors='ignore')
                                    category_sales_info = category_sales_info.merge(
                                        max_sales_df[keys_candidates + [field]], 
                                        on=keys_candidates, 
                                        how='left'
                                    )

            # 使用英文列名确定要保留的列，添加价格、库存和销售额相关字段
            keep_cols_en = [c for c in ['Store', 'product_name', '规格种类数', '多规格依据', 'l1_category', 'l3_category', 'sales_qty', 'price', 'original_price', '库存', 'revenue', 'original_price_revenue'] if c in multi_spec_report.columns]
            
            # 使用多级排序进行去重，确保选择最佳代表规格：销量降序、价格升序、库存降序、规格名称升序
            unique_multi_spec_list = multi_spec_report.sort_values(
                by=['sales_qty', 'price', '库存', '规格名称'], 
                ascending=[False, True, False, True],
                na_position='last'
            )
            unique_multi_spec_list = unique_multi_spec_list.drop_duplicates(subset=keys_candidates, keep='first')
            
            # 合并分类和月售信息（如果存在）
            if category_sales_info is not None and not category_sales_info.empty:
                unique_multi_spec_list = unique_multi_spec_list.merge(
                    category_sales_info, 
                    on=keys_candidates, 
                    how='left',
                    suffixes=('', '_agg')
                )
                # 删除重复的聚合列（保留原始列）
                for col in ['l1_category_agg', 'l3_category_agg', 'sales_qty_agg', 'price_agg', 'original_price_agg', '库存_agg', 'revenue_agg', 'original_price_revenue_agg']:
                    if col in unique_multi_spec_list.columns:
                        base_col = col.replace('_agg', '')
                        if base_col in unique_multi_spec_list.columns:
                            unique_multi_spec_list = unique_multi_spec_list.drop(columns=[col])
            
            # 只导出关键列，若缺失则导出全量
            if keep_cols_en:
                available_cols = [c for c in keep_cols_en if c in unique_multi_spec_list.columns]
                if available_cols:
                    unique_multi_spec_list = unique_multi_spec_list[available_cols]
            
            # 补充缺失的价格、库存和销售额字段（如果聚合中没有获取到）
            missing_fields = ['price', 'original_price', '库存', 'revenue', 'original_price_revenue']
            price_revenue_fields = ['price', 'original_price', 'revenue', 'original_price_revenue']
            
            for field in missing_fields:
                if field not in unique_multi_spec_list.columns and field in multi_spec_report.columns:
                    # 对于价格和销售额字段，取最佳代表规格的数据（多级排序）
                    if field in price_revenue_fields:
                        # 找到每个商品组中销量最高规格的数据
                        field_values_list = []
                        for _, group_row in unique_multi_spec_list.iterrows():
                            group_key = {k: group_row[k] for k in keys_candidates if k in group_row.index}
                            
                            # 使用直接筛选方法，避免 query 字符串构造问题
                            mask = pd.Series([True] * len(multi_spec_report))
                            for key, value in group_key.items():
                                mask = mask & (multi_spec_report[key] == value)
                            
                            product_variants = multi_spec_report[mask]
                            
                            if not product_variants.empty:
                                # 多级排序选择最佳代表规格：销量降序、价格升序、库存降序、规格名称升序
                                sorted_variants = product_variants.sort_values(
                                    by=['sales_qty', 'price', '库存', '规格名称'], 
                                    ascending=[False, True, False, True],
                                    na_position='last'
                                )
                                max_sales_row = sorted_variants.iloc[0]
                                field_value = max_sales_row[field]
                            else:
                                field_value = 0
                                
                            field_record = {**group_key, field: field_value}
                            field_values_list.append(field_record)
                        
                        if field_values_list:
                            field_values = pd.DataFrame(field_values_list)
                            unique_multi_spec_list = unique_multi_spec_list.merge(
                                field_values, 
                                on=keys_candidates, 
                                how='left'
                            )
                    elif field == '库存':
                        # 库存仍然取总和
                        field_values = multi_spec_report.groupby(keys_candidates)[field].sum().reset_index()
                        unique_multi_spec_list = unique_multi_spec_list.merge(
                            field_values, 
                            on=keys_candidates, 
                            how='left'
                        )
                    else:
                        # 其他字段取首个值
                        field_values = multi_spec_report.groupby(keys_candidates)[field].first().reset_index()
                        unique_multi_spec_list = unique_multi_spec_list.merge(
                            field_values, 
                            on=keys_candidates, 
                            how='left'
                        )
            
            # 现在应用中文化列名
            unique_multi_spec_list = apply_cn_columns(unique_multi_spec_list)
            
            # 调整列顺序，将关键信息放在前面
            preferred_cols_order = ['门店', '商品名称', '一级分类', '三级分类', '月售', '售价', '原价', '售价销售额', '原价销售额', '库存', '规格种类数', '多规格依据']
            available_preferred_cols = [c for c in preferred_cols_order if c in unique_multi_spec_list.columns]
            remaining_cols = [c for c in unique_multi_spec_list.columns if c not in available_preferred_cols]
            if available_preferred_cols:
                unique_multi_spec_list = unique_multi_spec_list[available_preferred_cols + remaining_cols]
            
            # 问题2：删除重复列（C、H、I列对应的可能是基础名称等重复信息）
            # 删除可能重复的列
            duplicate_cols_to_remove = ['基础名称']  # 基于实际情况调整
            for col in duplicate_cols_to_remove:
                if col in unique_multi_spec_list.columns:
                    unique_multi_spec_list = unique_multi_spec_list.drop(columns=[col])
            
            unique_multi_spec_list.to_excel(writer, sheet_name='唯一多规格商品列表', index=False)

            # === 校验：KPI vs 唯一多规格商品列表 ===
            try:
                # 核心指标对比中的多规格数
                kpi_multi = core_kpi_df[['唯一多规格商品数']].copy()
                kpi_multi = kpi_multi.reset_index().rename(columns={'index': '门店'})
                if '门店' not in kpi_multi.columns:
                    # 若索引名非“门店”，将第一列视为门店
                    kpi_multi.columns = ['门店'] + list(kpi_multi.columns[1:])

                # 唯一多规格商品列表中的计数 (健壮版) - 使用中文列名
                list_multi_col = None
                if '商品名称' in unique_multi_spec_list.columns:
                    list_multi_col = '商品名称'
                elif '基础名称' in unique_multi_spec_list.columns:
                    list_multi_col = '基础名称'

                if '门店' in unique_multi_spec_list.columns and list_multi_col:
                    list_multi = unique_multi_spec_list.groupby('门店')[list_multi_col].nunique().reset_index()
                    list_multi = list_multi.rename(columns={list_multi_col: '唯一多规格商品数(列表)'})
                elif list_multi_col:
                    count = unique_multi_spec_list[list_multi_col].nunique()
                    store_name = kpi_multi['门店'].iloc[0] if len(kpi_multi) > 0 else '门店A'
                    list_multi = pd.DataFrame({'门店': [store_name], '唯一多规格商品数(列表)': [count]})
                else:
                    # 如果两个关键列都不存在，则创建一个空的DataFrame以避免错误
                    list_multi = pd.DataFrame(columns=['门店', '唯一多规格商品数(列表)'])

                check_df = kpi_multi.merge(list_multi, on='门店', how='outer')
                check_df['唯一多规格商品数'] = pd.to_numeric(check_df['唯一多规格商品数'], errors='coerce').fillna(0).astype(int)
                check_df['唯一多规格商品数(列表)'] = pd.to_numeric(check_df['唯一多规格商品数(列表)'], errors='coerce').fillna(0).astype(int)
                check_df['差异(列表-指标)'] = check_df['唯一多规格商品数(列表)'] - check_df['唯一多规格商品数']

                # 进一步校验：规格种类数(按变体键)之和 vs 唯一列表总和
                if not var_cnt.empty:
                    if 'Store' in var_cnt.columns:
                        var_sum = var_cnt.groupby('Store')['规格种类数_按变体键'].sum().reset_index().rename(columns={'Store':'门店','规格种类数_按变体键':'规格种类数合计(变体)'} )
                    else:
                        var_sum = pd.DataFrame({'门店': [check_df['门店'].iloc[0] if len(check_df)>0 else '门店A'], '规格种类数合计(变体)': [int(var_cnt['规格种类数_按变体键'].sum())]})
                    check_df = check_df.merge(var_sum, on='门店', how='left')

                # 添加样例：仅在KPI/仅在列表 (健壮版)
                samples_only_kpi = []
                samples_only_list = []

                # 辅助函数，安全地获取用于比较的名称集合
                def get_name_set(df, store_filter=None, use_chinese_cols=False):
                    if df is None or df.empty:
                        return set()
                    
                    # 根据列名类型选择正确的列名
                    if use_chinese_cols:
                        store_col = '门店'
                        product_col = '商品名称'
                        base_col = '基础名称'
                    else:
                        store_col = 'Store'
                        product_col = 'product_name'
                        base_col = 'base_name'
                    
                    # 如果有门店筛选，先应用
                    if store_filter and store_col in df.columns:
                        df = df[df[store_col] == store_filter]

                    if product_col in df.columns:
                        return set(df[product_col].unique())
                    elif base_col in df.columns:
                        return set(df[base_col].unique())
                    return set()

                for _, row in check_df.iterrows():
                    store = row['门店']
                    
                    # KPI 集合 (使用英文列名)
                    ms_kpi_df = pd.DataFrame()
                    if store in all_store_data:
                        ms_kpi_df = identify_multi_spec_products(all_store_data[store]['all_skus'])
                    set_kpi = get_name_set(ms_kpi_df, use_chinese_cols=False)

                    # 列表集合 (使用中文列名)
                    set_list = get_name_set(unique_multi_spec_list, store_filter=store, use_chinese_cols=True)

                    only_kpi = list(set_kpi - set_list)[:5]
                    only_list = list(set_list - set_kpi)[:5]
                    samples_only_kpi.append(', '.join(map(str, only_kpi)))
                    samples_only_list.append(', '.join(map(str, only_list)))

                check_df['示例仅在KPI中(≤5)'] = samples_only_kpi
                check_df['示例仅在列表中(≤5)'] = samples_only_list
                check_df = apply_cn_columns(check_df)
                # check_df.to_excel(writer, sheet_name='校验-多规格一致性', index=False)  # 【已禁用】用户要求删除此Sheet
            except Exception as ve:
                print(f"⚠️ 生成‘校验-多规格一致性’失败：{ve}")

        # 应用列格式：核心指标（整数/金额/百分比）+ 其它 Sheet 的百分比统一为 0.00%
        try:
            ws = writer.sheets.get('核心指标对比')
            if ws is not None:
                int_cols = [
                    '总SKU数(含规格)', '总SKU数(去重后)', '动销SKU数', '滞销SKU数', '唯一多规格商品数'
                ]
                money_cols = ['总销售额(去重后)']
                pct_cols = ['动销率']

                if engine_name == 'xlsxwriter':
                    wb = writer.book
                    fmt_int = wb.add_format({'num_format': '0'})
                    fmt_money = wb.add_format({'num_format': '#,##0.00'})
                    fmt_pct = wb.add_format({'num_format': '0.00%'})
                    # 偏移 = 索引层级数
                    offset = core_kpi_df.index.nlevels
                    def idx_of(col_name):
                        try:
                            return int(core_kpi_df.columns.get_loc(col_name)) + offset
                        except Exception:
                            return None
                    for name in int_cols:
                        ci = idx_of(name)
                        if ci is not None:
                            ws.set_column(ci, ci, None, fmt_int)
                    for name in money_cols:
                        ci = idx_of(name)
                        if ci is not None:
                            ws.set_column(ci, ci, None, fmt_money)
                    for name in pct_cols:
                        ci = idx_of(name)
                        if ci is not None:
                            ws.set_column(ci, ci, None, fmt_pct)
                else:  # openpyxl
                    # 读取表头映射：value->column index
                    header_map = {}
                    for cell in ws[1]:
                        header_map[str(cell.value)] = cell.column
                    max_row = ws.max_row
                    def apply_number_format(col_names, fmt):
                        for n in col_names:
                            c = header_map.get(n)
                            if c is None:
                                continue
                            for r in range(2, max_row + 1):
                                cell = ws.cell(row=r, column=c)
                                cell.number_format = fmt
                    apply_number_format(int_cols, '0')
                    apply_number_format(money_cols, '#,##0.00')
                    apply_number_format(pct_cols, '0.00%')

            # 其它 Sheet：统一百分比格式（按白名单/数值域判定）
            # 商品角色分析
            ws_role = writer.sheets.get('商品角色分析')
            # 价格带分析
            ws_price = writer.sheets.get('价格带分析')
            # 美团一级分类详细指标
            ws_l1 = writer.sheets.get('美团一级分类详细指标')
            # 美团三级分类详细指标
            ws_l3 = writer.sheets.get('美团三级分类详细指标')

            if engine_name == 'xlsxwriter':
                apply_pct_xlsxwriter(ws_role, role_df, get_sheet_pct_cols('商品角色分析', role_df), index_written=True)
                apply_pct_xlsxwriter(ws_price, price_df, get_sheet_pct_cols('价格带分析', price_df), index_written=True)
                apply_pct_xlsxwriter(ws_l1, all_l1_analysis, get_sheet_pct_cols('美团一级分类详细指标', all_l1_analysis), index_written=False)
                if 'all_l3_analysis' in locals() and not all_l3_analysis.empty:
                    apply_pct_xlsxwriter(ws_l3, all_l3_analysis, get_sheet_pct_cols('美团三级分类详细指标', all_l3_analysis), index_written=False)

                # 强制整数格式：L1明细中的计数字段
                if ws_l1 is not None:
                    wb = writer.book
                    fmt_int2 = wb.add_format({'num_format': '#,##0'})
                    fmt_discount_zhe = wb.add_format({'num_format': '0.0"折"'})
                    int_cols_l1 = [
                        '美团一级分类sku数',
                        '美团一级分类多规格SKU数',
                        '美团一级分类多规格SPU数',
                        '美团一级分类0库存数',
                        '月售',
                        '美团一级分类动销sku数',
                        '美团一级分类活动sku数',
                        '美团一级分类爆品sku数',
                        '美团一级分类折扣sku数',
                        '美团一级分类去重SKU数(口径同动销率)',
                        '美团一级分类活动去重SKU数(口径同占比)'
                    ]
                    # 此 Sheet 写入时没有索引列，偏移=0
                    for name in int_cols_l1:
                        if name in all_l1_analysis.columns:
                            ci = int(all_l1_analysis.columns.get_loc(name))
                            ws_l1.set_column(ci, ci, None, fmt_int2)
                    # 折扣列格式化为 x.x 折
                    if '美团一级分类折扣' in all_l1_analysis.columns:
                        ci = int(all_l1_analysis.columns.get_loc('美团一级分类折扣'))
                        ws_l1.set_column(ci, ci, None, fmt_discount_zhe)
                
                # 强制整数格式：L3明细中的计数字段
                if ws_l3 is not None and 'all_l3_analysis' in locals() and not all_l3_analysis.empty:
                    wb = writer.book
                    fmt_int2 = wb.add_format({'num_format': '#,##0'})
                    fmt_discount_zhe = wb.add_format({'num_format': '0.0"折"'})
                    int_cols_l3 = [
                        '美团三级分类sku数',
                        '美团三级分类多规格SKU数',
                        '美团三级分类多规格SPU数',
                        '美团三级分类0库存数',
                        '月售',
                        '美团三级分类动销sku数',
                        '美团三级分类活动sku数',
                        '美团三级分类爆品sku数',
                        '美团三级分类折扣sku数',
                        '美团三级分类去重SKU数(口径同动销率)',
                        '美团三级分类活动去重SKU数(口径同占比)'
                    ]
                    for name in int_cols_l3:
                        if name in all_l3_analysis.columns:
                            ci = int(all_l3_analysis.columns.get_loc(name))
                            ws_l3.set_column(ci, ci, None, fmt_int2)
                    # 折扣列格式化为 x.x 折
                    if '美团三级分类折扣' in all_l3_analysis.columns:
                        ci = int(all_l3_analysis.columns.get_loc('美团三级分类折扣'))
                        ws_l3.set_column(ci, ci, None, fmt_discount_zhe)
            else:
                apply_pct_openpyxl(ws_role, get_sheet_pct_cols('商品角色分析', role_df))
                apply_pct_openpyxl(ws_price, get_sheet_pct_cols('价格带分析', price_df))
                apply_pct_openpyxl(ws_l1, get_sheet_pct_cols('美团一级分类详细指标', all_l1_analysis))
                if 'all_l3_analysis' in locals() and not all_l3_analysis.empty:
                    apply_pct_openpyxl(ws_l3, get_sheet_pct_cols('美团三级分类详细指标', all_l3_analysis))

                # 强制整数格式：L1明细中的计数字段（openpyxl）
                if ws_l1 is not None:
                    header_map = {str(cell.value): cell.column for cell in ws_l1[1]}
                    max_row = ws_l1.max_row
                    int_cols_l1 = [
                        '美团一级分类sku数',
                        '美团一级分类多规格SKU数',
                        '美团一级分类多规格SPU数',
                        '美团一级分类0库存数',
                        '月售',
                        '美团一级分类动销sku数',
                        '美团一级分类活动sku数',
                        '美团一级分类爆品sku数',
                        '美团一级分类折扣sku数',
                        '美团一级分类去重SKU数(口径同动销率)',
                        '美团一级分类活动去重SKU数(口径同占比)'
                    ]
                    for name in int_cols_l1:
                        c = header_map.get(name)
                        if c is None:
                            continue
                        for r in range(2, max_row + 1):
                            ws_l1.cell(row=r, column=c).number_format = '#,##0'
                    # 折扣列设置为 0.0"折"
                    if '美团一级分类折扣' in header_map:
                        c = header_map['美团一级分类折扣']
                        for r in range(2, max_row + 1):
                            ws_l1.cell(row=r, column=c).number_format = '0.0"折"'
                
                # 强制整数格式：L3明细中的计数字段（openpyxl）
                if ws_l3 is not None and 'all_l3_analysis' in locals() and not all_l3_analysis.empty:
                    header_map_l3 = {str(cell.value): cell.column for cell in ws_l3[1]}
                    max_row_l3 = ws_l3.max_row
                    int_cols_l3 = [
                        '美团三级分类sku数',
                        '美团三级分类多规格SKU数',
                        '美团三级分类多规格SPU数',
                        '美团三级分类0库存数',
                        '月售',
                        '美团三级分类动销sku数',
                        '美团三级分类活动sku数',
                        '美团三级分类爆品sku数',
                        '美团三级分类折扣sku数',
                        '美团三级分类去重SKU数(口径同动销率)',
                        '美团三级分类活动去重SKU数(口径同占比)'
                    ]
                    for name in int_cols_l3:
                        c = header_map_l3.get(name)
                        if c is None:
                            continue
                        for r in range(2, max_row_l3 + 1):
                            ws_l3.cell(row=r, column=c).number_format = '#,##0'
                    # 折扣列设置为 0.0"折"
                    if '美团三级分类折扣' in header_map_l3:
                        c = header_map_l3['美团三级分类折扣']
                        for r in range(2, max_row_l3 + 1):
                            ws_l3.cell(row=r, column=c).number_format = '0.0"折"'
            
            # 为唯一多规格商品列表设置数值格式
            ws_multi_unique = writer.sheets.get('唯一多规格商品列表')
            if ws_multi_unique is not None:
                if engine_name == 'xlsxwriter':
                    wb = writer.book
                    fmt_price = wb.add_format({'num_format': '0.00'})
                    fmt_int = wb.add_format({'num_format': '0'})
                    
                    # 为售价、原价设置价格格式，为销售额设置货币格式，为月售、库存设置整数格式
                    fmt_money = wb.add_format({'num_format': '#,##0.00'})
                    
                    price_cols = ['售价', '原价']
                    money_cols = ['售价销售额', '原价销售额']
                    int_cols = ['月售', '库存', '规格种类数']
                    
                    for col_name in price_cols:
                        if col_name in unique_multi_spec_list.columns:
                            try:
                                col_idx = int(unique_multi_spec_list.columns.get_loc(col_name))
                                ws_multi_unique.set_column(col_idx, col_idx, None, fmt_price)
                            except Exception:
                                pass
                    
                    for col_name in money_cols:
                        if col_name in unique_multi_spec_list.columns:
                            try:
                                col_idx = int(unique_multi_spec_list.columns.get_loc(col_name))
                                ws_multi_unique.set_column(col_idx, col_idx, None, fmt_money)
                            except Exception:
                                pass
                    
                    for col_name in int_cols:
                        if col_name in unique_multi_spec_list.columns:
                            try:
                                col_idx = int(unique_multi_spec_list.columns.get_loc(col_name))
                                ws_multi_unique.set_column(col_idx, col_idx, None, fmt_int)
                            except Exception:
                                pass
                else:  # openpyxl
                    header_map_unique = {str(cell.value): cell.column for cell in ws_multi_unique[1]}
                    max_row_unique = ws_multi_unique.max_row
                    
                    # 价格格式
                    price_cols = ['售价', '原价']
                    for col_name in price_cols:
                        c = header_map_unique.get(col_name)
                        if c is not None:
                            for r in range(2, max_row_unique + 1):
                                ws_multi_unique.cell(row=r, column=c).number_format = '0.00'
                    
                    # 销售额格式（货币格式）
                    money_cols = ['售价销售额', '原价销售额']
                    for col_name in money_cols:
                        c = header_map_unique.get(col_name)
                        if c is not None:
                            for r in range(2, max_row_unique + 1):
                                ws_multi_unique.cell(row=r, column=c).number_format = '#,##0.00'
                    
                    # 整数格式
                    int_cols = ['月售', '库存', '规格种类数']
                    for col_name in int_cols:
                        c = header_map_unique.get(col_name)
                        if c is not None:
                            for r in range(2, max_row_unique + 1):
                                ws_multi_unique.cell(row=r, column=c).number_format = '0'
        except Exception as fe:
            print(f"⚠️ KPI列格式设置失败：{fe}")
        
        # ========== 导出成本分析相关Sheet（新增） ==========
        try:
            # 合并所有门店的成本分析数据
            cost_summary_list = []
            high_margin_list = []
            low_margin_list = []
            
            for store, res in all_results.items():
                if '成本分析汇总' in res:
                    df_cost = res['成本分析汇总'].copy()
                    df_cost.insert(0, '门店', store)
                    cost_summary_list.append(df_cost)
                
                if '高毛利商品TOP50' in res:
                    df_high = res['高毛利商品TOP50'].copy()
                    df_high.insert(0, '门店', store)
                    high_margin_list.append(df_high)
                
                if '低毛利预警商品' in res:
                    df_low = res['低毛利预警商品'].copy()
                    df_low.insert(0, '门店', store)
                    low_margin_list.append(df_low)
            
            # 导出成本分析汇总
            if cost_summary_list:
                cost_summary_combined = pd.concat(cost_summary_list, ignore_index=True)
                cost_summary_combined = apply_cn_columns(cost_summary_combined)
                cost_summary_combined.to_excel(writer, sheet_name='成本分析汇总', index=False)
                
                # 应用百分比格式
                ws_cost = writer.sheets.get('成本分析汇总')
                if ws_cost and engine_name == 'xlsxwriter':
                    apply_pct_xlsxwriter(ws_cost, cost_summary_combined, get_sheet_pct_cols('成本分析汇总', cost_summary_combined), index_written=False)
                elif ws_cost and engine_name == 'openpyxl':
                    apply_pct_openpyxl(ws_cost, get_sheet_pct_cols('成本分析汇总', cost_summary_combined))
                
                print(f"ℹ️ 成本分析汇总Sheet已生成")
            
            # 导出高毛利商品TOP50
            if high_margin_list:
                high_margin_combined = pd.concat(high_margin_list, ignore_index=True)
                high_margin_combined = apply_cn_columns(high_margin_combined)
                high_margin_combined.to_excel(writer, sheet_name='高毛利商品TOP50', index=False)
                
                # 应用百分比格式
                ws_high = writer.sheets.get('高毛利商品TOP50')
                if ws_high and engine_name == 'xlsxwriter':
                    apply_pct_xlsxwriter(ws_high, high_margin_combined, get_sheet_pct_cols('高毛利商品TOP50', high_margin_combined), index_written=False)
                elif ws_high and engine_name == 'openpyxl':
                    apply_pct_openpyxl(ws_high, get_sheet_pct_cols('高毛利商品TOP50', high_margin_combined))
                
                print(f"ℹ️ 高毛利商品TOP50Sheet已生成")
            
            # 导出低毛利预警商品
            if low_margin_list:
                low_margin_combined = pd.concat(low_margin_list, ignore_index=True)
                low_margin_combined = apply_cn_columns(low_margin_combined)
                low_margin_combined.to_excel(writer, sheet_name='低毛利预警商品', index=False)
                
                # 应用百分比格式
                ws_low = writer.sheets.get('低毛利预警商品')
                if ws_low and engine_name == 'xlsxwriter':
                    apply_pct_xlsxwriter(ws_low, low_margin_combined, get_sheet_pct_cols('低毛利预警商品', low_margin_combined), index_written=False)
                elif ws_low and engine_name == 'openpyxl':
                    apply_pct_openpyxl(ws_low, get_sheet_pct_cols('低毛利预警商品', low_margin_combined))
                
                print(f"ℹ️ 低毛利预警商品Sheet已生成")
        
        except Exception as ce:
            print(f"⚠️ 导出成本分析Sheet失败：{ce}")
            import traceback
            traceback.print_exc()
    
    print(f"✅ 报告生成成功！已保存至: '{output_path}'。")

# ----------------------------------------
# 4. 主执行流程 (v3.4 交互式)
# ----------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="门店基础数据分析（本地运行版，保持原有逻辑）")
    parser.add_argument("--inputs", nargs='*', help="按 STORES_TO_ANALYZE 顺序提供每个门店的文件路径 (.csv/.xlsx)")
    parser.add_argument("--output", help="输出 Excel 文件名或完整路径（可选，默认使用脚本内配置）")
    parser.add_argument("--output-dir", help="输出目录（可选，默认写入脚本同目录的 reports/）")
    return parser.parse_args()


if __name__ == "__main__":
    # --- 配置区 ---
    # 检查是否为自动测试模式
    AUTO_TEST = len(sys.argv) > 1 and sys.argv[1] == "--auto-test"
    
    if AUTO_TEST:
        # 自动测试模式配置
        STORES_TO_ANALYZE = ["惠宜选测试店"]
        test_file = Path(__file__).parent.parent / "惠宜选.xlsx"
        if not test_file.exists():
            print(f"❌ 测试文件不存在: {test_file}")
            sys.exit(1)
        print(f"🧪 自动测试模式，使用文件: {test_file.name}")
    else:
        # 正常交互模式配置
        STORES_TO_ANALYZE = [
            "可以选"
            # "松鼠便利",
            # "门店D",
        ]
    OUTPUT_FILENAME = "竞对分析报告_v3.4_FINAL.xlsx"
    CONSUMPTION_SCENARIOS = {
        "早餐快手": ["早餐", "牛奶", "面包", "麦片", "鸡蛋"],
        "加班能量补给": ["咖啡", "能量饮料", "巧克力", "饼干", "能量棒"],
        "家庭囤货": ["大包装", "家庭装", "组合装", "箱", "量贩"],
        "聚会零食": ["薯片", "膨化", "糖果", "坚果", "汽水", "啤酒"],
    }
    # --- 配置结束 ---

    args = parse_args()
    # 计算输出路径：默认写入脚本目录下的 reports/
    script_dir = Path(__file__).parent.resolve()
    default_out_dir = script_dir / "reports"
    out_dir = Path(args.output_dir).resolve() if getattr(args, 'output_dir', None) else default_out_dir

    # 确定输出文件名：
    if args.output:
        user_out = Path(args.output)
        if user_out.is_absolute() or str(user_out.parent) not in (".", ""):
            final_output_path = user_out
        else:
            final_output_path = out_dir / user_out.name
    else:
        final_output_path = out_dir / OUTPUT_FILENAME

    print("🚀 欢迎使用全维度竞对分析引擎 v3.4 (本地运行版)")

    all_store_results = {}
    all_processed_data = {}

    for idx, store_name in enumerate(STORES_TO_ANALYZE, start=1):
        print("-" * 50)
        print(f"步骤 {idx}/{len(STORES_TO_ANALYZE)}: 为【{store_name}】提供数据文件 (支持 .csv 或 .xlsx)")
        try:
            if AUTO_TEST and store_name == "惠宜选测试店":
                # 自动测试模式使用预设文件
                file_path = str(test_file)
            elif args.inputs and len(args.inputs) >= idx:
                file_path = args.inputs[idx - 1]
            else:
                print(f"\n💡 提示: 直接拖拽Excel文件到终端,然后按回车即可")
                print(f"   (PowerShell用户: 拖拽后会自动添加 '& ' 前缀,无需手动删除)")
                print(f"   或手动输入文件路径:")
                file_path = input(f"【{store_name}】文件路径: ").strip()
                
                # 处理Windows路径中的引号、空格和PowerShell命令符号
                file_path = file_path.strip()
                # 移除PowerShell的命令执行符号 & 
                if file_path.startswith('& '):
                    file_path = file_path[2:].strip()
                # 移除外层引号
                file_path = file_path.strip('"').strip("'").strip()
            
            if not file_path:
                print(f"⚠️ 未提供文件路径，跳过店铺: {store_name}")
                continue

            processed = load_and_clean_data(file_path, store_name, CONSUMPTION_SCENARIOS)
            if processed and not processed[1].empty:
                df_all, df_dedup, df_act = processed
                all_processed_data[store_name] = {
                    'all_skus': df_all,
                    'deduplicated': df_dedup,
                    'active': df_act
                }
                analysis_results = analyze_store_performance(df_all, df_dedup, df_act)
                if analysis_results:
                    all_store_results[store_name] = analysis_results
        except Exception as e:
            print(f"❌ 处理店铺 {store_name} 时发生未知错误: {e}")
            traceback.print_exc()

    if all_store_results:
        export_full_report_to_excel(all_store_results, all_processed_data, str(final_output_path))
        if len(all_store_results) > 1:
            print("\n📊 正在生成对比图表...")
            # TODO: 如需，可在此补充图表输出逻辑
    else:
        print("\n⏹️ 没有可供分析的数据，程序结束。")