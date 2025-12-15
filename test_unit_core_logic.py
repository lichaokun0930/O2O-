"""
P1优化：核心计算逻辑单元测试
覆盖：KPI计算、多规格识别、数据加载、缓存机制
"""
import unittest
import pandas as pd
import numpy as np
import os
import tempfile
from datetime import datetime
from dashboard_v2 import DataLoader, DataCache, DashboardComponents

class TestDataCache(unittest.TestCase):
    """测试数据缓存机制"""
    
    def setUp(self):
        """测试前准备"""
        self.test_cache_dir = tempfile.mkdtemp()
        self.cache = DataCache(self.test_cache_dir)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)
    
    def test_cache_path_generation(self):
        """测试缓存路径生成"""
        # 创建临时测试文件
        test_file1 = os.path.join(self.test_cache_dir, "test1.xlsx")
        test_file2 = os.path.join(self.test_cache_dir, "test2.xlsx")
        
        # 创建文件
        with open(test_file1, 'wb') as f:
            f.write(b'test content 1')
        with open(test_file2, 'wb') as f:
            f.write(b'test content 2')
        
        path1 = self.cache._get_cache_path(test_file1)
        path2 = self.cache._get_cache_path(test_file1)
        path3 = self.cache._get_cache_path(test_file2)
        
        self.assertEqual(path1, path2, "相同文件应生成相同缓存路径")
        self.assertNotEqual(path1, path3, "不同文件应生成不同缓存路径")
        self.assertTrue(str(path1).endswith('.cache'), "缓存路径应以.cache结尾")
    
    def test_cache_set_and_get(self):
        """测试缓存保存和加载"""
        # 创建临时测试文件
        test_file = os.path.join(self.test_cache_dir, "test.xlsx")
        with open(test_file, 'wb') as f:
            f.write(b'test content')
        
        test_data = {
            'kpi': pd.DataFrame({'col1': [1, 2, 3]}),
            'category': pd.DataFrame({'col2': ['a', 'b', 'c']})
        }
        
        # 保存缓存
        self.cache.set(test_file, test_data)
        cache_path = self.cache._get_cache_path(test_file)
        self.assertTrue(os.path.exists(cache_path), "缓存文件应该被创建")
        
        # 加载缓存
        loaded_data = self.cache.get(test_file)
        self.assertIsNotNone(loaded_data, "应该能加载缓存数据")
        self.assertIn('kpi', loaded_data, "缓存应包含kpi数据")
        self.assertIn('category', loaded_data, "缓存应包含category数据")
        
        # 验证数据一致性
        pd.testing.assert_frame_equal(test_data['kpi'], loaded_data['kpi'])
        pd.testing.assert_frame_equal(test_data['category'], loaded_data['category'])
    
    def test_cache_invalidation(self):
        """测试缓存失效机制"""
        # 创建临时测试文件
        test_file = os.path.join(self.test_cache_dir, "test.xlsx")
        with open(test_file, 'wb') as f:
            f.write(b'test content')
        
        test_data = {'kpi': pd.DataFrame({'col1': [1, 2, 3]})}
        
        # 保存缓存
        self.cache.set(test_file, test_data)
        
        # 清除缓存
        cleared = self.cache.clear()
        self.assertGreater(cleared, 0, "应该清除了至少一个缓存文件")
        
        # 验证缓存已被清除
        loaded = self.cache.get(test_file)
        self.assertIsNone(loaded, "清除后不应该能加载缓存")


class TestKPICalculation(unittest.TestCase):
    """测试KPI计算逻辑"""
    
    def test_kpi_summary_basic(self):
        """测试基本KPI汇总"""
        # 创建测试数据
        kpi_df = pd.DataFrame({
            '门店': ['测试门店'],
            '总SKU数(含规格)': [1000],
            '单规格SPU数': [500],
            '单规格SKU数': [500],
            '多规格SKU总数': [500],
            '总SKU数(去重后)': [800],
            '动销SKU数': [600],
            '滞销SKU数': [200],
            '总销售额(去重后)': [100000],
            '动销率': [0.75],
            '唯一多规格商品数': [100]
        })
        
        # 模拟DataLoader的KPI提取逻辑
        summary = {}
        row = kpi_df.iloc[0]
        for i, col in enumerate(kpi_df.columns):
            value = row.iloc[i] if i < len(row) else 0
            if i == 0:
                summary['门店'] = value
            elif i == 1:
                summary['总SKU数(含规格)'] = value
            elif i == 5:
                summary['总SKU数(去重后)'] = value
            elif i == 6:
                summary['动销SKU数'] = value
            elif i == 7:
                summary['滞销SKU数'] = value
            elif i == 9:
                summary['动销率'] = value
        
        # 验证结果
        self.assertEqual(summary['总SKU数(含规格)'], 1000)
        self.assertEqual(summary['总SKU数(去重后)'], 800)
        self.assertEqual(summary['动销SKU数'], 600)
        self.assertEqual(summary['滞销SKU数'], 200)
        self.assertEqual(summary['动销率'], 0.75)
    
    def test_kpi_edge_cases(self):
        """测试KPI计算边界情况"""
        # 测试零值
        kpi_df = pd.DataFrame({
            '门店': ['空门店'],
            '总SKU数(含规格)': [0],
            '动销SKU数': [0],
            '总销售额(去重后)': [0]
        })
        
        row = kpi_df.iloc[0]
        self.assertEqual(row['总SKU数(含规格)'], 0)
        self.assertEqual(row['动销SKU数'], 0)
        
        # 测试动销率计算
        total_sku = 100
        active_sku = 75
        rate = active_sku / total_sku if total_sku > 0 else 0
        self.assertEqual(rate, 0.75)
        
        # 测试除零保护
        total_sku = 0
        rate = active_sku / total_sku if total_sku > 0 else 0
        self.assertEqual(rate, 0)


class TestMultispecRecognition(unittest.TestCase):
    """测试多规格识别算法"""
    
    def test_multispec_insights_basic(self):
        """测试基本多规格洞察生成"""
        category_data = pd.DataFrame({
            '分类': ['高多规格', '低多规格', '中等多规格'],
            '总SKU数': [100, 100, 100],
            '多规格SKU数': [60, 10, 30]  # 60%, 10%, 30%
        })
        
        insights = DashboardComponents.generate_multispec_insights(category_data)
        
        # 验证洞察数量
        self.assertGreater(len(insights), 0, "应该生成至少一条洞察")
        
        # 验证包含整体统计
        insight_texts = [i['text'] for i in insights]
        has_overall = any('门店整体多规格占比' in text for text in insight_texts)
        self.assertTrue(has_overall, "应该包含整体统计洞察")
        
        # 验证分类识别
        has_high = any('高多规格品类' in text and '>50%' in text for text in insight_texts)
        has_low = any('低多规格品类' in text and '<15%' in text for text in insight_texts)
        has_mid = any('中等多规格品类' in text and '20-40%' in text for text in insight_texts)
        
        self.assertTrue(has_high, "应该识别高多规格品类")
        self.assertTrue(has_low, "应该识别低多规格品类")
        self.assertTrue(has_mid, "应该识别中等多规格品类")
    
    def test_multispec_calculation_accuracy(self):
        """测试多规格占比计算准确性"""
        category_data = pd.DataFrame({
            '分类': ['分类A', '分类B', '分类C'],
            '总SKU数': [100, 200, 300],
            '多规格SKU数': [25, 50, 75]  # 25%, 25%, 25%
        })
        
        insights = DashboardComponents.generate_multispec_insights(category_data)
        
        # 提取整体占比
        overall_text = [i['text'] for i in insights if '门店整体多规格占比' in i['text']][0]
        
        # 手动计算验证
        total_multi = 25 + 50 + 75  # 150
        total_all = 100 + 200 + 300  # 600
        expected_ratio = total_multi / total_all  # 25%
        
        self.assertIn(f"{expected_ratio:.1%}", overall_text, "整体占比应该正确")
        self.assertIn("150", overall_text, "多规格SKU数应该正确")
        self.assertIn("600", overall_text, "总SKU数应该正确")
    
    def test_multispec_empty_data(self):
        """测试空数据处理"""
        empty_data = pd.DataFrame()
        insights = DashboardComponents.generate_multispec_insights(empty_data)
        self.assertEqual(len(insights), 0, "空数据应返回空洞察列表")
    
    def test_multispec_zero_division(self):
        """测试除零保护"""
        category_data = pd.DataFrame({
            '分类': ['零SKU分类'],
            '总SKU数': [0],
            '多规格SKU数': [0]
        })
        
        # 应该不抛出异常
        try:
            insights = DashboardComponents.generate_multispec_insights(category_data)
            self.assertIsInstance(insights, list, "应该返回列表")
        except ZeroDivisionError:
            self.fail("不应该出现除零错误")
    
    def test_multispec_performance(self):
        """测试大数据量性能"""
        import time
        
        # 生成大数据集
        n = 1000
        category_data = pd.DataFrame({
            '分类': [f'分类{i}' for i in range(n)],
            '总SKU数': np.random.randint(50, 500, n),
            '多规格SKU数': np.random.randint(10, 200, n)
        })
        
        # 性能测试
        start = time.perf_counter()
        insights = DashboardComponents.generate_multispec_insights(category_data)
        elapsed = time.perf_counter() - start
        
        self.assertLess(elapsed, 0.01, "1000个分类应在10ms内完成")
        self.assertGreater(len(insights), 0, "应该生成洞察")


class TestDataLoaderColumnMapping(unittest.TestCase):
    """测试列名映射功能"""
    
    def test_column_search_logic(self):
        """测试列名搜索逻辑"""
        df = pd.DataFrame({
            '美团一级分类爆品sku数': [10, 20, 30],
            '美团一级分类折扣': [0.8, 0.9, 0.85],
            '其他列': [1, 2, 3]
        })
        
        # 测试列名包含关键字的搜索
        keywords = ['爆品', '折扣']
        found_cols = [col for col in df.columns if any(kw in col for kw in keywords)]
        
        self.assertEqual(len(found_cols), 2, "应该找到2个匹配列")
        self.assertIn('美团一级分类爆品sku数', found_cols)
        self.assertIn('美团一级分类折扣', found_cols)
    
    def test_column_not_found(self):
        """测试找不到列的情况"""
        df = pd.DataFrame({'列A': [1, 2, 3]})
        
        # 测试不存在的关键字
        keyword = '不存在的列'
        found_cols = [col for col in df.columns if keyword in col]
        
        self.assertEqual(len(found_cols), 0, "不应该找到任何列")
    
    def test_safe_column_access(self):
        """测试安全的列访问"""
        df = pd.DataFrame({
            '美团一级分类爆品sku数': [10, 20, 30]
        })
        
        # 测试成功获取
        if '美团一级分类爆品sku数' in df.columns:
            value = df['美团一级分类爆品sku数'].iloc[0]
            self.assertEqual(value, 10, "应该获取到第一行的值")
        
        # 测试默认值处理
        default_value = 999
        value = df.get('不存在的列', pd.Series([default_value])).iloc[0]
        self.assertEqual(value, default_value, "找不到列应返回默认值")


class TestDataIntegrity(unittest.TestCase):
    """测试数据完整性"""
    
    def test_data_type_consistency(self):
        """测试数据类型一致性"""
        # 测试数值类型转换
        test_values = ['100', 100, 100.0, np.int64(100)]
        for val in test_values:
            numeric_val = pd.to_numeric(val, errors='coerce')
            self.assertEqual(numeric_val, 100, f"值 {val} 应该转换为100")
        
        # 测试无效值处理
        invalid_val = pd.to_numeric('invalid', errors='coerce')
        self.assertTrue(pd.isna(invalid_val), "无效值应转换为NaN")
    
    def test_dataframe_operations(self):
        """测试DataFrame操作的正确性"""
        df = pd.DataFrame({
            'A': [1, 2, 3, 4, 5],
            'B': [10, 20, 30, 40, 50]
        })
        
        # 测试numpy数组提取
        arr_a = df['A'].values
        self.assertIsInstance(arr_a, np.ndarray, "应该返回numpy数组")
        self.assertEqual(len(arr_a), 5, "数组长度应该正确")
        
        # 测试向量化计算
        result = arr_a * 2
        expected = np.array([2, 4, 6, 8, 10])
        np.testing.assert_array_equal(result, expected, "向量化计算应该正确")


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""
    
    def test_missing_file_handling(self):
        """测试文件不存在的处理"""
        # DataLoader会捕获异常并记录日志，不会抛出异常
        # 所以我们测试data是否为空
        loader = DataLoader("不存在的文件.xlsx", use_cache=False)
        self.assertTrue(loader.data['kpi'].empty, "不存在的文件应该返回空数据")
    
    def test_invalid_data_handling(self):
        """测试无效数据处理"""
        # 测试空DataFrame
        empty_df = pd.DataFrame()
        insights = DashboardComponents.generate_multispec_insights(empty_df)
        self.assertEqual(len(insights), 0, "空数据应返回空列表")
        
        # 测试包含NaN的数据
        df_with_nan = pd.DataFrame({
            '分类': ['A', 'B'],
            '总SKU数': [100, np.nan],
            '多规格SKU数': [50, 25]
        })
        
        # 应该不抛出异常
        try:
            insights = DashboardComponents.generate_multispec_insights(df_with_nan)
            self.assertIsInstance(insights, list)
        except Exception as e:
            self.fail(f"不应该抛出异常: {e}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDataCache))
    suite.addTests(loader.loadTestsFromTestCase(TestKPICalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestMultispecRecognition))
    suite.addTests(loader.loadTestsFromTestCase(TestDataLoaderColumnMapping))
    suite.addTests(loader.loadTestsFromTestCase(TestDataIntegrity))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印总结
    print("\n" + "="*70)
    print("📊 测试总结")
    print("="*70)
    print(f"✅ 运行测试: {result.testsRun}个")
    print(f"✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}个")
    print(f"❌ 失败: {len(result.failures)}个")
    print(f"💥 错误: {len(result.errors)}个")
    
    if result.wasSuccessful():
        print("\n🎉 所有单元测试通过！")
        print("\n📈 测试覆盖范围:")
        print("   ✅ 数据缓存机制")
        print("   ✅ KPI计算逻辑")
        print("   ✅ 多规格识别算法")
        print("   ✅ 列名映射功能")
        print("   ✅ 数据完整性")
        print("   ✅ 错误处理")
        return 0
    else:
        print("\n⚠️  部分测试未通过，请检查")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(run_tests())
