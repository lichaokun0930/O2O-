"""
Property-Based Test for Difference Analyzer
Feature: store-comparison, Property 7: 差异分析自动生成
Feature: store-comparison, Property 10: 分类级差异识别
Validates: Requirements 5.1, 5.2, 3.6

This test verifies that the DifferenceAnalyzer functions:
- analyze_kpi_differences: automatically generates difference analysis insights 
  when competitor metrics exceed own-store metrics.
- analyze_category_differences: identifies category-level differences and generates
  insights with category names and difference values/ratios.
"""

import unittest
from hypothesis import given, strategies as st, settings, assume
import re
from dashboard_v2 import DifferenceAnalyzer


# Strategy for generating valid KPI data
def kpi_data_strategy():
    """Generate random but valid KPI data dictionaries"""
    return st.fixed_dictionaries({
        # 核心4个指标
        '总销售额(去重后)': st.floats(min_value=0.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
        '总SKU数(去重后)': st.integers(min_value=0, max_value=10000),
        '动销率': st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        '平均毛利率': st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    })


def kpi_data_with_competitor_leading_strategy():
    """Generate KPI data where competitor leads in at least one metric"""
    return st.tuples(
        # Own KPI - lower values
        st.fixed_dictionaries({
            '总销售额(去重后)': st.floats(min_value=100.0, max_value=500000.0, allow_nan=False, allow_infinity=False),
            '总SKU数(去重后)': st.integers(min_value=10, max_value=500),
            '动销率': st.floats(min_value=0.1, max_value=0.5, allow_nan=False, allow_infinity=False),
            '平均毛利率': st.floats(min_value=0.1, max_value=0.3, allow_nan=False, allow_infinity=False),
        }),
        # Competitor KPI - higher values (guaranteed to be higher)
        st.fixed_dictionaries({
            '总销售额(去重后)': st.floats(min_value=500001.0, max_value=10000000.0, allow_nan=False, allow_infinity=False),
            '总SKU数(去重后)': st.integers(min_value=501, max_value=10000),
            '动销率': st.floats(min_value=0.51, max_value=1.0, allow_nan=False, allow_infinity=False),
            '平均毛利率': st.floats(min_value=0.31, max_value=1.0, allow_nan=False, allow_infinity=False),
        })
    )


class TestDifferenceAnalyzerProperty(unittest.TestCase):
    """
    Property 7: 差异分析自动生成
    
    For any comparison view, the Dashboard should automatically generate 
    difference analysis insights when competitor metrics exceed own-store metrics.
    """
    
    @given(data=kpi_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_generated_when_competitor_leads(self, data):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: When competitor metrics exceed own-store metrics,
        the analyze_kpi_differences function should generate non-empty insights.
        """
        own_kpi, competitor_kpi = data
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Verify insights list is not empty (since competitor leads in all metrics)
        self.assertIsInstance(insights, list, "Result should be a list")
        self.assertGreater(len(insights), 0, 
                          "Should generate at least one insight when competitor leads")
    
    @given(data=kpi_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_contain_competitor_keyword(self, data):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: Each generated insight should contain the keyword "竞对".
        """
        own_kpi, competitor_kpi = data
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Verify each insight contains "竞对"
        for insight in insights:
            self.assertIn('text', insight, "Insight should have 'text' field")
            self.assertIn('竞对', insight['text'], 
                         f"Insight text should contain '竞对': {insight['text']}")
    
    @given(data=kpi_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_contain_numeric_values(self, data):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: Each generated insight should contain numeric values.
        """
        own_kpi, competitor_kpi = data
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Pattern to match numbers (including formatted numbers like 1,234 or 12.5)
        number_pattern = r'[\d,]+\.?\d*'
        
        # Verify each insight contains numbers
        for insight in insights:
            text = insight['text']
            matches = re.findall(number_pattern, text)
            self.assertGreater(len(matches), 0, 
                              f"Insight should contain numeric values: {text}")
    
    @given(data=kpi_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_contain_percentage(self, data):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: Each generated insight should contain a percentage value.
        """
        own_kpi, competitor_kpi = data
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Pattern to match percentage (number followed by %)
        percentage_pattern = r'[\d,]+\.?\d*%'
        
        # Verify each insight contains percentage
        for insight in insights:
            text = insight['text']
            matches = re.findall(percentage_pattern, text)
            self.assertGreater(len(matches), 0, 
                              f"Insight should contain percentage: {text}")
    
    @given(own_kpi=kpi_data_strategy(), competitor_kpi=kpi_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_max_count_is_three(self, own_kpi, competitor_kpi):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: The number of insights should never exceed 3.
        """
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Verify max count is 3
        self.assertLessEqual(len(insights), 3, 
                            "Should return at most 3 insights")
    
    @given(own_kpi=kpi_data_strategy(), competitor_kpi=kpi_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_structure_is_valid(self, own_kpi, competitor_kpi):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: Each insight should have the required structure with
        'icon', 'text', and 'level' fields.
        """
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Verify structure of each insight
        for insight in insights:
            self.assertIn('icon', insight, "Insight should have 'icon' field")
            self.assertIn('text', insight, "Insight should have 'text' field")
            self.assertIn('level', insight, "Insight should have 'level' field")
            
            # Verify types
            self.assertIsInstance(insight['icon'], str, "Icon should be a string")
            self.assertIsInstance(insight['text'], str, "Text should be a string")
            self.assertIsInstance(insight['level'], str, "Level should be a string")
            
            # Verify level is valid
            valid_levels = ['warning', 'info', 'success', 'danger', 'primary']
            self.assertIn(insight['level'], valid_levels, 
                         f"Level should be one of {valid_levels}")
    
    @given(own_kpi=kpi_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_no_insights_when_own_leads(self, own_kpi):
        """
        **Feature: store-comparison, Property 7: 差异分析自动生成**
        **Validates: Requirements 5.1, 5.2**
        
        Property: When own-store leads in all metrics, no insights should be generated.
        """
        # Create competitor KPI with lower values
        competitor_kpi = {
            '总销售额(去重后)': max(0, own_kpi['总销售额(去重后)'] * 0.5),
            '总SKU数(去重后)': max(0, own_kpi['总SKU数(去重后)'] // 2),
            '动销率': max(0, own_kpi['动销率'] * 0.5),
            '平均毛利率': max(0, own_kpi['平均毛利率'] * 0.5),
        }
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Verify no insights generated (own leads in all metrics)
        self.assertEqual(len(insights), 0, 
                        "Should not generate insights when own-store leads in all metrics")


# ============================================================================
# Property 10: 分类级差异识别
# ============================================================================

# Strategy for generating category data
def category_data_strategy():
    """Generate random but valid category data list"""
    category_names = ['服饰鞋包', '食品饮料', '美妆护肤', '家居用品', '数码电器', 
                      '母婴用品', '运动户外', '图书文具', '宠物用品', '生鲜果蔬']
    
    return st.lists(
        st.fixed_dictionaries({
            '分类': st.sampled_from(category_names),
            'SKU数': st.integers(min_value=0, max_value=500)
        }),
        min_size=3,
        max_size=8,
        unique_by=lambda x: x['分类']  # Ensure unique categories
    )


def category_data_with_competitor_leading_strategy():
    """Generate category data where competitor leads in at least one category"""
    category_names = ['服饰鞋包', '食品饮料', '美妆护肤', '家居用品', '数码电器']
    
    # Generate own data with lower SKU counts
    own_data = st.lists(
        st.fixed_dictionaries({
            '分类': st.sampled_from(category_names),
            'SKU数': st.integers(min_value=1, max_value=50)
        }),
        min_size=3,
        max_size=5,
        unique_by=lambda x: x['分类']
    )
    
    # Generate competitor data with higher SKU counts
    comp_data = st.lists(
        st.fixed_dictionaries({
            '分类': st.sampled_from(category_names),
            'SKU数': st.integers(min_value=51, max_value=200)
        }),
        min_size=3,
        max_size=5,
        unique_by=lambda x: x['分类']
    )
    
    return st.tuples(own_data, comp_data)


class TestCategoryDifferenceAnalyzerProperty(unittest.TestCase):
    """
    Property 10: 分类级差异识别
    
    For any category where competitor metric > own-store metric, the Dashboard 
    should generate a difference insight indicating the gap and improvement suggestions.
    """
    
    @given(data=category_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_generated_when_competitor_leads_in_category(self, data):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: When competitor leads in at least one category,
        the analyze_category_differences function should generate non-empty insights.
        """
        own_category, competitor_category = data
        
        # Ensure there's at least one overlapping category where competitor leads
        own_categories = {item['分类'] for item in own_category}
        comp_categories = {item['分类'] for item in competitor_category}
        overlapping = own_categories & comp_categories
        
        # Skip if no overlapping categories
        assume(len(overlapping) > 0)
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Verify insights list is not empty (since competitor leads in all overlapping categories)
        self.assertIsInstance(insights, list, "Result should be a list")
        self.assertGreater(len(insights), 0, 
                          "Should generate at least one insight when competitor leads in categories")
    
    @given(data=category_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_contain_category_name(self, data):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: Each generated insight should contain a category name.
        """
        own_category, competitor_category = data
        
        # Ensure there's at least one overlapping category
        own_categories = {item['分类'] for item in own_category}
        comp_categories = {item['分类'] for item in competitor_category}
        overlapping = own_categories & comp_categories
        assume(len(overlapping) > 0)
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # All possible category names
        all_categories = ['服饰鞋包', '食品饮料', '美妆护肤', '家居用品', '数码电器', 
                          '母婴用品', '运动户外', '图书文具', '宠物用品', '生鲜果蔬']
        
        # Verify each insight contains a category name
        for insight in insights:
            self.assertIn('text', insight, "Insight should have 'text' field")
            text = insight['text']
            
            # Check if any category name is in the text
            contains_category = any(cat in text for cat in all_categories)
            self.assertTrue(contains_category, 
                           f"Insight text should contain a category name: {text}")
    
    @given(data=category_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_contain_difference_value_or_ratio(self, data):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: Each generated insight should contain difference ratio (倍) or difference value.
        """
        own_category, competitor_category = data
        
        # Ensure there's at least one overlapping category
        own_categories = {item['分类'] for item in own_category}
        comp_categories = {item['分类'] for item in competitor_category}
        overlapping = own_categories & comp_categories
        assume(len(overlapping) > 0)
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Pattern to match ratio (X.X倍) or "vs" comparison or "本店为0"
        ratio_pattern = r'\d+\.?\d*倍'
        vs_pattern = r'\d+\s*vs\s*\d+'
        zero_pattern = r'本店为0'
        
        # Verify each insight contains ratio or difference value
        for insight in insights:
            text = insight['text']
            
            has_ratio = bool(re.search(ratio_pattern, text))
            has_vs = bool(re.search(vs_pattern, text))
            has_zero = bool(re.search(zero_pattern, text))
            
            self.assertTrue(has_ratio or has_vs or has_zero, 
                           f"Insight should contain ratio (倍), vs comparison, or '本店为0': {text}")
    
    @given(own_category=category_data_strategy(), competitor_category=category_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_max_count_is_three(self, own_category, competitor_category):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: The number of insights should never exceed 3.
        """
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Verify max count is 3
        self.assertLessEqual(len(insights), 3, 
                            "Should return at most 3 insights")
    
    @given(own_category=category_data_strategy(), competitor_category=category_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_insights_structure_is_valid(self, own_category, competitor_category):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: Each insight should have the required structure with
        'icon', 'text', and 'level' fields.
        """
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Verify structure of each insight
        for insight in insights:
            self.assertIn('icon', insight, "Insight should have 'icon' field")
            self.assertIn('text', insight, "Insight should have 'text' field")
            self.assertIn('level', insight, "Insight should have 'level' field")
            
            # Verify types
            self.assertIsInstance(insight['icon'], str, "Icon should be a string")
            self.assertIsInstance(insight['text'], str, "Text should be a string")
            self.assertIsInstance(insight['level'], str, "Level should be a string")
    
    @given(own_category=category_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_no_insights_when_own_leads(self, own_category):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: When own-store leads in all categories, no insights should be generated.
        """
        # Create competitor data with lower SKU counts
        competitor_category = [
            {'分类': item['分类'], 'SKU数': max(0, item['SKU数'] // 2)}
            for item in own_category
        ]
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Verify no insights generated (own leads in all categories)
        self.assertEqual(len(insights), 0, 
                        "Should not generate insights when own-store leads in all categories")
    
    @given(data=category_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_empty_data_returns_empty_insights(self, data):
        """
        **Feature: store-comparison, Property 10: 分类级差异识别**
        **Validates: Requirements 3.6**
        
        Property: Empty input data should return empty insights list.
        """
        # Test with empty own data
        insights1 = DifferenceAnalyzer.analyze_category_differences([], data[1])
        self.assertEqual(len(insights1), 0, "Empty own data should return empty insights")
        
        # Test with empty competitor data
        insights2 = DifferenceAnalyzer.analyze_category_differences(data[0], [])
        self.assertEqual(len(insights2), 0, "Empty competitor data should return empty insights")
        
        # Test with both empty
        insights3 = DifferenceAnalyzer.analyze_category_differences([], [])
        self.assertEqual(len(insights3), 0, "Both empty should return empty insights")


# ============================================================================
# Property 12: 差异洞察数量限制
# ============================================================================

class TestInsightCountLimitProperty(unittest.TestCase):
    """
    Property 12: 差异洞察数量限制
    
    For any difference analysis that generates more than 3 insights, 
    the Dashboard should display only the top 3 most important insights.
    **Validates: Requirements 5.5**
    """
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_kpi_insights_never_exceed_three(self, data):
        """
        **Feature: store-comparison, Property 12: 差异洞察数量限制**
        **Validates: Requirements 5.5**
        
        Property: KPI difference analysis should never return more than 3 insights,
        even when competitor leads in all 4 metrics.
        """
        # Generate own KPI with low values
        own_kpi = {
            '总销售额(去重后)': data.draw(st.floats(min_value=100.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
            '总SKU数(去重后)': data.draw(st.integers(min_value=1, max_value=50)),
            '动销率': data.draw(st.floats(min_value=0.01, max_value=0.3, allow_nan=False, allow_infinity=False)),
            '平均毛利率': data.draw(st.floats(min_value=0.01, max_value=0.2, allow_nan=False, allow_infinity=False)),
        }
        
        # Generate competitor KPI with higher values (guaranteed to lead in all 4 metrics)
        competitor_kpi = {
            '总销售额(去重后)': own_kpi['总销售额(去重后)'] * data.draw(st.floats(min_value=2.0, max_value=10.0, allow_nan=False, allow_infinity=False)),
            '总SKU数(去重后)': own_kpi['总SKU数(去重后)'] * data.draw(st.integers(min_value=2, max_value=10)),
            '动销率': min(1.0, own_kpi['动销率'] + data.draw(st.floats(min_value=0.2, max_value=0.5, allow_nan=False, allow_infinity=False))),
            '平均毛利率': min(1.0, own_kpi['平均毛利率'] + data.draw(st.floats(min_value=0.2, max_value=0.5, allow_nan=False, allow_infinity=False))),
        }
        
        # Call the analyzer - competitor leads in all 4 metrics, but should only return 3
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Verify max count is 3
        self.assertLessEqual(len(insights), 3, 
                            f"Should return at most 3 insights even when competitor leads in all 4 metrics. Got {len(insights)}")
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_category_insights_never_exceed_three(self, data):
        """
        **Feature: store-comparison, Property 12: 差异洞察数量限制**
        **Validates: Requirements 5.5**
        
        Property: Category difference analysis should never return more than 3 insights,
        even when competitor leads in many categories.
        """
        category_names = ['服饰鞋包', '食品饮料', '美妆护肤', '家居用品', '数码电器', 
                          '母婴用品', '运动户外', '图书文具']
        
        # Generate own category data with low SKU counts
        own_category = [
            {'分类': cat, 'SKU数': data.draw(st.integers(min_value=1, max_value=20))}
            for cat in category_names
        ]
        
        # Generate competitor category data with higher SKU counts (leads in all categories)
        competitor_category = [
            {'分类': cat, 'SKU数': own_category[i]['SKU数'] * data.draw(st.integers(min_value=2, max_value=10))}
            for i, cat in enumerate(category_names)
        ]
        
        # Call the analyzer - competitor leads in all 8 categories, but should only return 3
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Verify max count is 3
        self.assertLessEqual(len(insights), 3, 
                            f"Should return at most 3 insights even when competitor leads in all 8 categories. Got {len(insights)}")
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_combined_insights_limit(self, data):
        """
        **Feature: store-comparison, Property 12: 差异洞察数量限制**
        **Validates: Requirements 5.5**
        
        Property: Both KPI and category insights should independently respect the 3-insight limit.
        """
        # Generate data where competitor leads in everything
        own_kpi = {
            '总销售额(去重后)': 1000.0,
            '总SKU数(去重后)': 10,
            '动销率': 0.1,
            '平均毛利率': 0.1,
        }
        competitor_kpi = {
            '总销售额(去重后)': 10000.0,
            '总SKU数(去重后)': 100,
            '动销率': 0.9,
            '平均毛利率': 0.9,
        }
        
        category_names = ['服饰鞋包', '食品饮料', '美妆护肤', '家居用品', '数码电器']
        own_category = [{'分类': cat, 'SKU数': 5} for cat in category_names]
        competitor_category = [{'分类': cat, 'SKU数': 50} for cat in category_names]
        
        # Get insights from both methods
        kpi_insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        category_insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Both should be limited to 3
        self.assertLessEqual(len(kpi_insights), 3, "KPI insights should be limited to 3")
        self.assertLessEqual(len(category_insights), 3, "Category insights should be limited to 3")


# ============================================================================
# Property 13: 差异洞察格式规范
# ============================================================================

class TestInsightFormatProperty(unittest.TestCase):
    """
    Property 13: 差异洞察格式规范
    
    For any difference insight containing numerical values, the Dashboard should 
    format it in a readable pattern like "Competitor's SKU count is 2x of own-store (20 vs 10)".
    **Validates: Requirements 5.6**
    """
    
    @given(data=kpi_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_kpi_insights_contain_vs_comparison_or_percentage(self, data):
        """
        **Feature: store-comparison, Property 13: 差异洞察格式规范**
        **Validates: Requirements 5.6**
        
        Property: Each KPI insight should contain percentage comparison.
        """
        own_kpi, competitor_kpi = data
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, competitor_kpi)
        
        # Pattern to match percentage (number followed by %)
        percentage_pattern = r'[\d,]+\.?\d*%'
        
        # Verify each insight contains percentage
        for insight in insights:
            text = insight['text']
            has_percentage = bool(re.search(percentage_pattern, text))
            self.assertTrue(has_percentage, 
                           f"KPI insight should contain percentage: {text}")
    
    @given(data=category_data_with_competitor_leading_strategy())
    @settings(max_examples=100, deadline=None)
    def test_category_insights_contain_vs_comparison_or_ratio(self, data):
        """
        **Feature: store-comparison, Property 13: 差异洞察格式规范**
        **Validates: Requirements 5.6**
        
        Property: Each category insight should contain "vs" comparison or ratio (倍).
        """
        own_category, competitor_category = data
        
        # Ensure there's at least one overlapping category
        own_categories = {item['分类'] for item in own_category}
        comp_categories = {item['分类'] for item in competitor_category}
        overlapping = own_categories & comp_categories
        assume(len(overlapping) > 0)
        
        # Call the analyzer
        insights = DifferenceAnalyzer.analyze_category_differences(own_category, competitor_category)
        
        # Patterns to match
        vs_pattern = r'\d+\s*vs\s*\d+'
        ratio_pattern = r'\d+\.?\d*倍'
        zero_pattern = r'本店为0'
        
        # Verify each insight contains vs comparison or ratio
        for insight in insights:
            text = insight['text']
            has_vs = bool(re.search(vs_pattern, text))
            has_ratio = bool(re.search(ratio_pattern, text))
            has_zero = bool(re.search(zero_pattern, text))
            
            self.assertTrue(has_vs or has_ratio or has_zero, 
                           f"Category insight should contain 'vs' comparison, ratio (倍), or '本店为0': {text}")
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_format_insight_currency_format(self, data):
        """
        **Feature: store-comparison, Property 13: 差异洞察格式规范**
        **Validates: Requirements 5.6**
        
        Property: Currency format should include ¥ symbol and percentage.
        """
        own_value = data.draw(st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
        competitor_value = own_value * data.draw(st.floats(min_value=1.5, max_value=5.0, allow_nan=False, allow_infinity=False))
        
        result = DifferenceAnalyzer.format_insight('销售额', own_value, competitor_value, 'currency')
        
        # Should contain ¥ symbol
        self.assertIn('¥', result, f"Currency format should contain ¥ symbol: {result}")
        # Should contain percentage
        self.assertIn('%', result, f"Currency format should contain percentage: {result}")
        # Should contain "竞对"
        self.assertIn('竞对', result, f"Should contain '竞对': {result}")
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_format_insight_percent_format(self, data):
        """
        **Feature: store-comparison, Property 13: 差异洞察格式规范**
        **Validates: Requirements 5.6**
        
        Property: Percent format should include percentage point difference and percentage.
        """
        own_value = data.draw(st.floats(min_value=0.1, max_value=0.4, allow_nan=False, allow_infinity=False))
        competitor_value = min(1.0, own_value + data.draw(st.floats(min_value=0.1, max_value=0.3, allow_nan=False, allow_infinity=False)))
        
        result = DifferenceAnalyzer.format_insight('动销率', own_value, competitor_value, 'percent')
        
        # Should contain "百分点"
        self.assertIn('百分点', result, f"Percent format should contain '百分点': {result}")
        # Should contain percentage
        self.assertIn('%', result, f"Percent format should contain percentage: {result}")
        # Should contain "竞对"
        self.assertIn('竞对', result, f"Should contain '竞对': {result}")
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_format_insight_number_format(self, data):
        """
        **Feature: store-comparison, Property 13: 差异洞察格式规范**
        **Validates: Requirements 5.6**
        
        Property: Number format should include "个" unit and percentage.
        """
        own_value = data.draw(st.integers(min_value=10, max_value=100))
        competitor_value = own_value * data.draw(st.integers(min_value=2, max_value=5))
        
        result = DifferenceAnalyzer.format_insight('SKU数', own_value, competitor_value, 'number')
        
        # Should contain "个"
        self.assertIn('个', result, f"Number format should contain '个': {result}")
        # Should contain percentage
        self.assertIn('%', result, f"Number format should contain percentage: {result}")
        # Should contain "竞对"
        self.assertIn('竞对', result, f"Should contain '竞对': {result}")
    
    @given(st.data())
    @settings(max_examples=100, deadline=None)
    def test_format_insight_handles_zero_own_value(self, data):
        """
        **Feature: store-comparison, Property 13: 差异洞察格式规范**
        **Validates: Requirements 5.6**
        
        Property: Format insight should handle zero own value gracefully.
        """
        own_value = 0
        competitor_value = data.draw(st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
        
        # Should not raise an exception
        result = DifferenceAnalyzer.format_insight('销售额', own_value, competitor_value, 'currency')
        
        # Should still be a valid string
        self.assertIsInstance(result, str, "Result should be a string")
        self.assertGreater(len(result), 0, "Result should not be empty")
        # Should contain "竞对"
        self.assertIn('竞对', result, f"Should contain '竞对': {result}")


def run_property_tests():
    """Run property-based tests"""
    loader = unittest.TestLoader()
    
    # Load all test classes
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestDifferenceAnalyzerProperty))
    suite.addTests(loader.loadTestsFromTestCase(TestCategoryDifferenceAnalyzerProperty))
    suite.addTests(loader.loadTestsFromTestCase(TestInsightCountLimitProperty))
    suite.addTests(loader.loadTestsFromTestCase(TestInsightFormatProperty))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    print("📊 Property-Based Test Summary")
    print("="*70)
    print(f"✅ Tests Run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 All property-based tests passed!")
        print("\n📈 Properties Validated:")
        print("   ✅ Property 7: 差异分析自动生成")
        print("   ✅ Property 10: 分类级差异识别")
        print("   ✅ Property 12: 差异洞察数量限制")
        print("   ✅ Property 13: 差异洞察格式规范")
        print("   ✅ Requirements 5.1, 5.2, 3.6, 5.5, 5.6")
        return 0
    else:
        print("\n⚠️  Some property tests failed")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(run_property_tests())
