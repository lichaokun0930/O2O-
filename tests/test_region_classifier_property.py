# -*- coding: utf-8 -*-
"""
区域分类器属性测试
"""

import pytest
import pandas as pd
from hypothesis import given, settings, assume
from hypothesis import strategies as st

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.utils.region_classifier import RegionClassifier, get_region_classifier


# ==================== Property 6: 区域类型识别一致性 ====================

# **Feature: city-competitor-analysis, Property 6: 区域类型识别一致性**
@given(county_name=st.sampled_from(RegionClassifier.COUNTY_LIST))
@settings(max_examples=100)
def test_county_list_priority(county_name):
    """验证县级名单优先于关键词规则
    
    Property: 如果名称包含县级行政区划名单中的地名，则应识别为"县城"
    """
    classifier = get_region_classifier()
    
    # 构造包含县名的门店名称
    store_name = f"惠宜选-{county_name}店"
    result = classifier.classify(store_name)
    
    assert result == '县城', f"包含县名'{county_name}'的门店应识别为县城，实际为{result}"


# **Feature: city-competitor-analysis, Property 6: 区域类型识别一致性**
@given(district_name=st.sampled_from(RegionClassifier.DISTRICT_LIST))
@settings(max_examples=100)
def test_district_list_priority(district_name):
    """验证市区名单匹配
    
    Property: 如果名称包含市区区名列表中的地名，则应识别为"市区"
    """
    classifier = get_region_classifier()
    
    # 构造包含区名的门店名称（确保不包含县名）
    store_name = f"惠宜选-{district_name}万达店"
    
    # 排除同时在县名单中的情况
    if any(county in store_name for county in classifier.COUNTY_LIST):
        return
    
    result = classifier.classify(store_name)
    
    assert result == '市区', f"包含区名'{district_name}'的门店应识别为市区，实际为{result}"


# **Feature: city-competitor-analysis, Property 6: 区域类型识别一致性**
@given(random_text=st.text(min_size=5, max_size=20, alphabet='测试门店名称'))
@settings(max_examples=100)
def test_unknown_fallback(random_text):
    """验证未匹配时默认返回"县城"
    
    Property: 当无法通过名单或关键词匹配时，默认返回"县城"（业务逻辑：县城门店更需关注）
    """
    classifier = get_region_classifier()
    
    # 确保不包含任何已知地名或关键词
    store_name = f"随机{random_text}"
    
    # 排除包含已知地名的情况
    if any(county in store_name for county in classifier.COUNTY_LIST):
        return
    if any(district in store_name for district in classifier.DISTRICT_LIST):
        return
    if any(kw in store_name for kw in classifier.COUNTY_KEYWORDS):
        return
    if any(kw in store_name for kw in classifier.CITY_KEYWORDS):
        return
    
    result = classifier.classify(store_name)
    assert result == '县城', f"无法匹配的门店应默认返回'县城'，实际为{result}"


# **Feature: city-competitor-analysis, Property 6: 区域类型识别一致性**
def test_county_keyword_fallback():
    """验证县城关键词规则"""
    classifier = get_region_classifier()
    
    # 包含"县"关键词但不在名单中
    result = classifier.classify("某某县超市")
    assert result == '县城'
    
    # 包含"镇"关键词
    result = classifier.classify("某某镇便利店")
    assert result == '县城'


def test_city_keyword_fallback():
    """验证市区关键词规则"""
    classifier = get_region_classifier()
    
    # 包含"路"关键词
    result = classifier.classify("人民路店")
    assert result == '市区'
    
    # 包含"广场"关键词
    result = classifier.classify("中心广场店")
    assert result == '市区'
    
    # 包含"万达"关键词
    result = classifier.classify("某某万达店")
    assert result == '市区'


def test_county_priority_over_city_keyword():
    """验证县名单优先于市区关键词"""
    classifier = get_region_classifier()
    
    # 句容是县，即使包含"路"也应识别为县城
    result = classifier.classify("句容人民路店")
    assert result == '县城', "县名单应优先于市区关键词"


def test_batch_classify():
    """测试批量分类"""
    classifier = get_region_classifier()
    
    df = pd.DataFrame({
        '门店名称': ['惠宜选-江宁店', '惠宜选-句容店', '随机店名'],
        '城市': ['南京市', '镇江市', '未知市']
    })
    
    result_df = classifier.classify_batch(df)
    
    assert '区域类型' in result_df.columns
    assert result_df.iloc[0]['区域类型'] == '市区'  # 江宁是市区
    assert result_df.iloc[1]['区域类型'] == '县城'  # 句容是县城


def test_empty_input():
    """测试空输入 - 默认返回县城"""
    classifier = get_region_classifier()
    
    # 空输入默认返回县城（业务逻辑）
    assert classifier.classify(None) == '县城'
    assert classifier.classify('') == '县城'
    assert classifier.classify(pd.NA) == '县城'


def test_real_data_classification():
    """测试真实数据分类"""
    file_path = Path('城市新增竞对数据/新增竞对.xlsx')
    if not file_path.exists():
        pytest.skip("测试数据文件不存在")
    
    df = pd.read_excel(file_path)
    classifier = get_region_classifier()
    
    result_df = classifier.classify_batch(df)
    
    # 验证分类结果
    counts = result_df['区域类型'].value_counts()
    assert '市区' in counts.index or '县城' in counts.index, "应该有市区或县城分类结果"
    
    # 验证已知门店的分类
    jiangning_stores = result_df[result_df['门店名称'].str.contains('江宁', na=False)]
    if len(jiangning_stores) > 0:
        assert all(jiangning_stores['区域类型'] == '市区'), "江宁应识别为市区"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
