# -*- coding: utf-8 -*-
"""
城市新增竞对数据处理属性测试
使用hypothesis进行属性测试
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from hypothesis.extra.pandas import column, data_frames

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data.competitor_loader import CompetitorDataLoader, CompetitorDataParser


# ==================== 测试数据生成策略 ====================

@st.composite
def competitor_wide_data_strategy(draw, max_competitors=3):
    """生成竞对宽表测试数据"""
    n_rows = draw(st.integers(min_value=1, max_value=20))
    n_competitors = draw(st.integers(min_value=1, max_value=max_competitors))
    
    cities = ['南京市', '苏州市', '无锡市', '常州市', '合肥市']
    business_types = ['强', '中', '弱']
    brands = ['满佳喜', 'AA百货', '糖果喵', '畅淘集市', '惠宜选', None]
    subsidy_rates = ['10%-20%', '20%-30%', '30%-40%', None]
    
    data = {
        '门店名称': [f'测试门店-{i}' for i in range(n_rows)],
        '城市': draw(st.lists(st.sampled_from(cities), min_size=n_rows, max_size=n_rows)),
        '运营': [f'运营{i}' for i in range(n_rows)],
        '商圈类型': draw(st.lists(st.sampled_from(business_types), min_size=n_rows, max_size=n_rows)),
        '5km内竞对数量': draw(st.lists(st.integers(0, 30), min_size=n_rows, max_size=n_rows)),
        '近15天5km内新增竞对数量': draw(st.lists(st.integers(0, 5), min_size=n_rows, max_size=n_rows)),
    }
    
    # 添加竞对列
    for i in range(1, n_competitors + 1):
        suffix = '' if i == 1 else f'.{i-1}'
        comp_col = f'新增竞对{i}'
        brand_col = f'品牌特性{suffix}' if suffix else '品牌特性'
        sku_col = f'sku数{suffix}' if suffix else 'sku数'
        subsidy_col = f'商补率{suffix}' if suffix else '商补率'
        
        # 生成竞对数据（部分为空）
        data[comp_col] = draw(st.lists(
            st.one_of(st.sampled_from(brands), st.none()),
            min_size=n_rows, max_size=n_rows
        ))
        data[brand_col] = draw(st.lists(
            st.one_of(st.text(min_size=0, max_size=20), st.none()),
            min_size=n_rows, max_size=n_rows
        ))
        data[sku_col] = draw(st.lists(
            st.one_of(st.floats(100, 10000), st.none()),
            min_size=n_rows, max_size=n_rows
        ))
        data[subsidy_col] = draw(st.lists(
            st.one_of(st.sampled_from(subsidy_rates), st.none()),
            min_size=n_rows, max_size=n_rows
        ))
    
    return pd.DataFrame(data), n_competitors


# ==================== Property 1: 数据解析完整性 ====================

# **Feature: city-competitor-analysis, Property 1: 数据解析完整性**
@given(data=competitor_wide_data_strategy())
@settings(max_examples=100, deadline=None)
def test_data_parsing_completeness(data):
    """验证宽表转长表的数据完整性
    
    Property: For any 包含N个新增竞对列的Excel文件，解析后的长表应包含所有非空竞对记录
    """
    df, n_competitors = data
    
    parser = CompetitorDataParser(df)
    long_df = parser.parse_wide_to_long()
    
    # 计算原始数据中非空竞对的数量
    expected_count = 0
    for i in range(1, n_competitors + 1):
        comp_col = f'新增竞对{i}'
        if comp_col in df.columns:
            expected_count += df[comp_col].notna().sum()
    
    # 验证长表记录数等于原始非空竞对数
    assert len(long_df) == expected_count, \
        f"长表记录数({len(long_df)})应等于非空竞对数({expected_count})"


# **Feature: city-competitor-analysis, Property 1: 数据解析完整性 - 属性值一致性**
@given(data=competitor_wide_data_strategy(max_competitors=2))
@settings(max_examples=50, deadline=None)
def test_data_parsing_attribute_consistency(data):
    """验证解析后属性字段值与原始数据一致"""
    df, n_competitors = data
    
    parser = CompetitorDataParser(df)
    long_df = parser.parse_wide_to_long()
    
    if len(long_df) == 0:
        return  # 没有竞对数据，跳过
    
    # 验证基础字段保持一致
    for _, long_row in long_df.iterrows():
        store_name = long_row['门店名称']
        original_row = df[df['门店名称'] == store_name].iloc[0]
        
        assert long_row['城市'] == original_row['城市']
        assert long_row['商圈类型'] == original_row['商圈类型']
        assert long_row['5km内竞对数量'] == original_row['5km内竞对数量']


# ==================== 单元测试 ====================

def test_loader_file_not_found():
    """测试文件不存在的错误处理"""
    loader = CompetitorDataLoader('不存在的文件.xlsx')
    with pytest.raises(FileNotFoundError):
        loader.load_data()


def test_loader_with_real_data():
    """测试加载真实数据文件"""
    file_path = Path('城市新增竞对数据/新增竞对.xlsx')
    if not file_path.exists():
        pytest.skip("测试数据文件不存在")
    
    loader = CompetitorDataLoader(str(file_path))
    df = loader.load_data()
    
    assert len(df) > 0
    assert '门店名称' in df.columns
    assert '城市' in df.columns


def test_parser_detect_columns():
    """测试竞对列检测"""
    df = pd.DataFrame({
        '门店名称': ['店1'],
        '城市': ['南京市'],
        '运营': ['张三'],
        '商圈类型': ['强'],
        '5km内竞对数量': [5],
        '近15天5km内新增竞对数量': [1],
        '新增竞对1': ['品牌A'],
        '品牌特性': ['低起送'],
        'sku数': [5000],
        '商补率': ['10%-20%'],
        '新增竞对2': ['品牌B'],
        '品牌特性.1': ['高补贴'],
        'sku数.1': [6000],
        '商补率.1': ['20%-30%'],
    })
    
    parser = CompetitorDataParser(df)
    mappings = parser.detect_competitor_columns()
    
    assert len(mappings) == 2
    assert mappings[0]['competitor_col'] == '新增竞对1'
    assert mappings[1]['competitor_col'] == '新增竞对2'


def test_parser_wide_to_long():
    """测试宽表转长表"""
    df = pd.DataFrame({
        '门店名称': ['店1', '店2'],
        '城市': ['南京市', '苏州市'],
        '运营': ['张三', '李四'],
        '商圈类型': ['强', '中'],
        '5km内竞对数量': [5, 3],
        '近15天5km内新增竞对数量': [1, 0],
        '新增竞对1': ['品牌A', None],
        '品牌特性': ['低起送', None],
        'sku数': [5000, None],
        '商补率': ['10%-20%', None],
    })
    
    parser = CompetitorDataParser(df)
    long_df = parser.parse_wide_to_long()
    
    # 只有店1有竞对数据
    assert len(long_df) == 1
    assert long_df.iloc[0]['竞对名称'] == '品牌A'
    assert long_df.iloc[0]['门店名称'] == '店1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
