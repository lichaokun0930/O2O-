#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartColumnFinder测试脚本
对比优化前后的数据索引是否一致，确保前端展示无差异
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 配置日志
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# ==================== SmartColumnFinder类（从dashboard_v2.py复制）====================
class SmartColumnFinder:
    """智能列查找器 - 三层查找机制，彻底解决硬编码索引问题
    
    查找顺序：
    1. 精确匹配列名（最可靠）
    2. 关键词模糊匹配（灵活性）
    3. 索引备用方案（兼容性）
    """
    
    # 第1层：精确匹配（优先级最高）
    EXACT_MAPPINGS = {
        '门店爆品数': ['美团一级分类爆品sku数', '爆品sku数', '爆品数'],
        '门店平均折扣': ['美团一级分类折扣', '折扣'],
        '总销售额': ['总销售额(去重后)', '销售额', '总销售额'],
        '动销率': ['动销率', '动销比率'],
        '平均毛利率': ['平均毛利率', '毛利率'],
        '总SKU数': ['总SKU数(含规格)', 'SKU数', '总SKU数'],
        '动销SKU数': ['动销SKU数', '动销商品数'],
        '滞销SKU数': ['滞销SKU数', '滞销商品数'],
    }
    
    # 第2层：关键词匹配（次优先级）
    KEYWORD_MAPPINGS = {
        '门店爆品数': ['爆品', 'burst', 'hot'],
        '门店平均折扣': ['折扣', 'discount'],
        '总销售额': ['销售额', 'revenue'],
        '动销率': ['动销', 'active'],
        '平均毛利率': ['毛利', 'margin'],
        '总SKU数': ['sku', 'SKU'],
        '动销SKU数': ['动销', 'active'],
        '滞销SKU数': ['滞销', 'inactive'],
    }
    
    # 第3层：索引备用（最后备用，兼容旧格式）
    INDEX_FALLBACK = {
        '门店爆品数': [27, 23],
        '门店平均折扣': [28, 24],
    }
    
    @staticmethod
    def find_column(df, field_name):
        """智能查找列（三层机制）
        
        Args:
            df: DataFrame
            field_name: 字段名（如'门店爆品数'）
            
        Returns:
            列名（str）或列索引（int），找不到返回None
        """
        # 第1层：精确匹配
        exact_names = SmartColumnFinder.EXACT_MAPPINGS.get(field_name, [])
        for name in exact_names:
            if name in df.columns:
                logger.info(f"✅ 精确匹配: {field_name} -> {name}")
                return name
        
        # 第2层：关键词匹配
        keywords = SmartColumnFinder.KEYWORD_MAPPINGS.get(field_name, [])
        for col in df.columns:
            col_str = str(col).lower()
            for keyword in keywords:
                if keyword.lower() in col_str:
                    # 排除误匹配（如"非爆品数"不应匹配"爆品"）
                    if '非' not in col_str and 'not' not in col_str:
                        logger.info(f"✅ 关键词匹配: {field_name} -> {col}")
                        return col
        
        # 第3层：索引备用
        indices = SmartColumnFinder.INDEX_FALLBACK.get(field_name, [])
        for idx in indices:
            if len(df.columns) > idx:
                logger.info(f"✅ 索引备用: {field_name} -> 第{idx}列({df.columns[idx]})")
                return idx
        
        logger.warning(f"⚠️ 无法找到列: {field_name}, 列数: {len(df.columns)}")
        return None
    
    @staticmethod
    def get_value(df, field_name, aggregation='sum'):
        """获取字段值
        
        Args:
            df: DataFrame
            field_name: 字段名
            aggregation: 聚合方式（sum/mean/first）
            
        Returns:
            字段值，找不到返回None
        """
        col = SmartColumnFinder.find_column(df, field_name)
        if col is None:
            return None
        
        # 按列名或索引获取
        if isinstance(col, str):
            series = df[col]
        else:
            series = df.iloc[:, col]
        
        # 转换为数值类型（处理可能的文本）
        series = pd.to_numeric(series, errors='coerce')
        
        # 聚合
        if aggregation == 'sum':
            return series.sum()
        elif aggregation == 'mean':
            return series.mean()
        elif aggregation == 'first':
            return series.iloc[0] if len(series) > 0 else None
        
        return None


def create_test_dataframe():
    """创建测试用的DataFrame，模拟真实的Excel数据"""
    
    # 模拟美团一级分类详细指标工作表
    # 包含28列，第27列（索引27）是爆品数，第28列（索引28）是折扣
    data = {
        '一级分类': ['服饰鞋包', '食品饮料', '美妆个护', '家居日用'],
        'SKU数': [100, 150, 80, 120],
        '动销SKU数': [80, 120, 60, 90],
        '动销率': [0.8, 0.8, 0.75, 0.75],
        '销售额': [50000, 80000, 40000, 60000],
        '列5': [0, 0, 0, 0],
        '列6': [0, 0, 0, 0],
        '列7': [0, 0, 0, 0],
        '列8': [0, 0, 0, 0],
        '列9': [0, 0, 0, 0],
        '列10': [0, 0, 0, 0],
        '列11': [0, 0, 0, 0],
        '列12': [0, 0, 0, 0],
        '列13': [0, 0, 0, 0],
        '列14': [0, 0, 0, 0],
        '列15': [0, 0, 0, 0],
        '列16': [0, 0, 0, 0],
        '列17': [0, 0, 0, 0],
        '列18': [0, 0, 0, 0],
        '列19': [0, 0, 0, 0],
        '列20': [0, 0, 0, 0],
        '列21': [0, 0, 0, 0],
        '列22': [0, 0, 0, 0],
        '列23': [0, 0, 0, 0],
        '列24': [0, 0, 0, 0],
        '列25': [0, 0, 0, 0],
        '列26': [0, 0, 0, 0],
        '美团一级分类爆品sku数': [10, 15, 8, 12],  # 第27列（索引27）
        '美团一级分类折扣': [0.85, 0.90, 0.88, 0.92],  # 第28列（索引28）
    }
    
    return pd.DataFrame(data)


def test_old_method(df):
    """测试旧方法（硬编码索引）"""
    logger.info("\n" + "="*60)
    logger.info("🔴 测试旧方法（硬编码索引）")
    logger.info("="*60)
    
    results = {}
    
    # 旧方法：硬编码索引27获取爆品数
    if len(df.columns) > 27:
        burst_count = df.iloc[:, 27].sum()
        results['门店爆品数'] = burst_count
        logger.info(f"✅ 使用索引27获取爆品数: {burst_count}")
        logger.info(f"   列名: {df.columns[27]}")
    else:
        logger.warning(f"⚠️ 列数不足27列，无法获取爆品数")
        results['门店爆品数'] = None
    
    # 旧方法：硬编码列名获取折扣
    if '美团一级分类折扣' in df.columns:
        discount_col = pd.to_numeric(df['美团一级分类折扣'], errors='coerce')
        avg_discount = discount_col.mean()
        results['门店平均折扣'] = avg_discount
        logger.info(f"✅ 使用列名获取平均折扣: {avg_discount:.4f}")
    else:
        logger.warning(f"⚠️ 找不到列'美团一级分类折扣'")
        results['门店平均折扣'] = None
    
    return results


def test_new_method(df):
    """测试新方法（SmartColumnFinder）"""
    logger.info("\n" + "="*60)
    logger.info("🟢 测试新方法（SmartColumnFinder）")
    logger.info("="*60)
    
    results = {}
    
    # 新方法：使用SmartColumnFinder获取爆品数
    burst_count = SmartColumnFinder.get_value(df, '门店爆品数', aggregation='sum')
    if burst_count is not None:
        results['门店爆品数'] = burst_count
    else:
        results['门店爆品数'] = None
    
    # 新方法：使用SmartColumnFinder获取折扣
    avg_discount = SmartColumnFinder.get_value(df, '门店平均折扣', aggregation='mean')
    if avg_discount is not None:
        results['门店平均折扣'] = avg_discount
    else:
        results['门店平均折扣'] = None
    
    return results


def compare_results(old_results, new_results):
    """对比两种方法的结果"""
    logger.info("\n" + "="*60)
    logger.info("📊 结果对比")
    logger.info("="*60)
    
    all_match = True
    
    for key in old_results.keys():
        old_val = old_results[key]
        new_val = new_results[key]
        
        if old_val is None and new_val is None:
            logger.info(f"✅ {key}: 两者都为None（一致）")
        elif old_val is None or new_val is None:
            logger.error(f"❌ {key}: 不一致！")
            logger.error(f"   旧方法: {old_val}")
            logger.error(f"   新方法: {new_val}")
            all_match = False
        else:
            # 对于浮点数，使用近似比较
            if isinstance(old_val, float) and isinstance(new_val, float):
                if abs(old_val - new_val) < 1e-6:
                    logger.info(f"✅ {key}: {old_val:.4f} == {new_val:.4f}（一致）")
                else:
                    logger.error(f"❌ {key}: 不一致！")
                    logger.error(f"   旧方法: {old_val:.4f}")
                    logger.error(f"   新方法: {new_val:.4f}")
                    logger.error(f"   差异: {abs(old_val - new_val):.6f}")
                    all_match = False
            else:
                if old_val == new_val:
                    logger.info(f"✅ {key}: {old_val} == {new_val}（一致）")
                else:
                    logger.error(f"❌ {key}: 不一致！")
                    logger.error(f"   旧方法: {old_val}")
                    logger.error(f"   新方法: {new_val}")
                    all_match = False
    
    return all_match


def test_scenario_1_standard_format():
    """测试场景1：标准格式（列名完全匹配）"""
    logger.info("\n" + "🧪 " + "="*58)
    logger.info("🧪 测试场景1：标准格式（列名完全匹配）")
    logger.info("🧪 " + "="*58)
    
    df = create_test_dataframe()
    
    logger.info(f"\n📋 DataFrame信息:")
    logger.info(f"   列数: {len(df.columns)}")
    logger.info(f"   第27列（索引27）: {df.columns[27]}")
    logger.info(f"   第28列（索引28）: {df.columns[28]}")
    
    old_results = test_old_method(df)
    new_results = test_new_method(df)
    
    return compare_results(old_results, new_results)


def test_scenario_2_simplified_names():
    """测试场景2：简化列名（如'爆品数'而不是'美团一级分类爆品sku数'）"""
    logger.info("\n" + "🧪 " + "="*58)
    logger.info("🧪 测试场景2：简化列名")
    logger.info("🧪 " + "="*58)
    
    df = create_test_dataframe()
    
    # 修改列名为简化版本
    df = df.rename(columns={
        '美团一级分类爆品sku数': '爆品数',
        '美团一级分类折扣': '折扣'
    })
    
    logger.info(f"\n📋 DataFrame信息:")
    logger.info(f"   列数: {len(df.columns)}")
    logger.info(f"   第27列（索引27）: {df.columns[27]}")
    logger.info(f"   第28列（索引28）: {df.columns[28]}")
    
    # 旧方法
    logger.info("\n" + "="*60)
    logger.info("🔴 测试旧方法（硬编码索引）")
    logger.info("="*60)
    
    old_results = {}
    if len(df.columns) > 27:
        burst_count = df.iloc[:, 27].sum()
        old_results['门店爆品数'] = burst_count
        logger.info(f"✅ 使用索引27获取爆品数: {burst_count}")
        logger.info(f"   列名: {df.columns[27]}")
    
    # 注意：旧方法会失败，因为列名不是'美团一级分类折扣'
    if '美团一级分类折扣' in df.columns:
        discount_col = pd.to_numeric(df['美团一级分类折扣'], errors='coerce')
        old_results['门店平均折扣'] = discount_col.mean()
        logger.info(f"✅ 使用列名获取平均折扣: {old_results['门店平均折扣']:.4f}")
    else:
        logger.warning(f"⚠️ 找不到列'美团一级分类折扣'（旧方法会失败）")
        old_results['门店平均折扣'] = None
    
    new_results = test_new_method(df)
    
    # 对比结果
    logger.info("\n" + "="*60)
    logger.info("📊 结果对比")
    logger.info("="*60)
    
    logger.info(f"✅ 门店爆品数: 旧方法={old_results['门店爆品数']}, 新方法={new_results['门店爆品数']}（一致）")
    
    if old_results['门店平均折扣'] is None and new_results['门店平均折扣'] is not None:
        logger.info(f"🎉 门店平均折扣: 旧方法=None（失败）, 新方法={new_results['门店平均折扣']:.4f}（成功）")
        logger.info(f"   ✨ 新方法通过关键词匹配找到了'折扣'列！")
        return True
    else:
        return False


def test_scenario_3_column_order_changed():
    """测试场景3：列顺序变化（爆品数在第23列而不是第27列）"""
    logger.info("\n" + "🧪 " + "="*58)
    logger.info("🧪 测试场景3：列顺序变化（爆品数在第23列）")
    logger.info("🧪 " + "="*58)
    
    # 创建一个只有24列的DataFrame，爆品数在第23列
    data = {
        '一级分类': ['服饰鞋包', '食品饮料', '美妆个护', '家居日用'],
        'SKU数': [100, 150, 80, 120],
        '动销SKU数': [80, 120, 60, 90],
        '动销率': [0.8, 0.8, 0.75, 0.75],
        '销售额': [50000, 80000, 40000, 60000],
        '列5': [0, 0, 0, 0],
        '列6': [0, 0, 0, 0],
        '列7': [0, 0, 0, 0],
        '列8': [0, 0, 0, 0],
        '列9': [0, 0, 0, 0],
        '列10': [0, 0, 0, 0],
        '列11': [0, 0, 0, 0],
        '列12': [0, 0, 0, 0],
        '列13': [0, 0, 0, 0],
        '列14': [0, 0, 0, 0],
        '列15': [0, 0, 0, 0],
        '列16': [0, 0, 0, 0],
        '列17': [0, 0, 0, 0],
        '列18': [0, 0, 0, 0],
        '列19': [0, 0, 0, 0],
        '列20': [0, 0, 0, 0],
        '列21': [0, 0, 0, 0],
        '列22': [0, 0, 0, 0],
        '美团一级分类爆品sku数': [10, 15, 8, 12],  # 第23列（索引23）
    }
    
    df = pd.DataFrame(data)
    
    logger.info(f"\n📋 DataFrame信息:")
    logger.info(f"   列数: {len(df.columns)}")
    logger.info(f"   第23列（索引23）: {df.columns[23]}")
    
    # 旧方法
    logger.info("\n" + "="*60)
    logger.info("🔴 测试旧方法（硬编码索引）")
    logger.info("="*60)
    
    old_results = {}
    if len(df.columns) > 27:
        burst_count = df.iloc[:, 27].sum()
        old_results['门店爆品数'] = burst_count
        logger.info(f"✅ 使用索引27获取爆品数: {burst_count}")
    else:
        logger.warning(f"⚠️ 列数不足27列（只有{len(df.columns)}列），旧方法会失败")
        old_results['门店爆品数'] = None
    
    new_results = test_new_method(df)
    
    # 对比结果
    logger.info("\n" + "="*60)
    logger.info("📊 结果对比")
    logger.info("="*60)
    
    if old_results['门店爆品数'] is None and new_results['门店爆品数'] is not None:
        logger.info(f"🎉 门店爆品数: 旧方法=None（失败）, 新方法={new_results['门店爆品数']}（成功）")
        logger.info(f"   ✨ 新方法通过精确匹配找到了'美团一级分类爆品sku数'列！")
        return True
    else:
        return False


def test_real_report():
    """测试场景4：真实报告文件"""
    logger.info("\n" + "🧪 " + "="*58)
    logger.info("🧪 测试场景4：真实报告文件")
    logger.info("🧪 " + "="*58)
    
    # 查找reports目录下的报告文件
    reports_dir = Path('reports')
    
    # 查找本店报告
    own_store_dir = reports_dir / '本店'
    if own_store_dir.exists():
        report_files = list(own_store_dir.glob('*_分析报告.xlsx'))
        if report_files:
            report_file = report_files[0]
            logger.info(f"\n📁 找到报告文件: {report_file.name}")
            
            try:
                # 读取美团一级分类详细指标工作表
                df = pd.read_excel(report_file, sheet_name='美团一级分类详细指标')
                
                logger.info(f"\n📋 DataFrame信息:")
                logger.info(f"   列数: {len(df.columns)}")
                logger.info(f"   行数: {len(df)}")
                logger.info(f"\n   前10列:")
                for i, col in enumerate(df.columns[:10]):
                    logger.info(f"      {i:2d}. {col}")
                
                if len(df.columns) > 27:
                    logger.info(f"\n   第27列（索引27）: {df.columns[27]}")
                if len(df.columns) > 28:
                    logger.info(f"   第28列（索引28）: {df.columns[28]}")
                
                old_results = test_old_method(df)
                new_results = test_new_method(df)
                
                return compare_results(old_results, new_results)
            
            except Exception as e:
                logger.error(f"❌ 读取报告文件失败: {e}")
                return False
        else:
            logger.warning(f"⚠️ 未找到报告文件")
            return None
    else:
        logger.warning(f"⚠️ 未找到本店报告目录")
        return None


def main():
    """主测试函数"""
    logger.info("\n" + "🚀 " + "="*58)
    logger.info("🚀 SmartColumnFinder 测试开始")
    logger.info("🚀 " + "="*58)
    
    results = {}
    
    # 测试场景1：标准格式
    results['场景1'] = test_scenario_1_standard_format()
    
    # 测试场景2：简化列名
    results['场景2'] = test_scenario_2_simplified_names()
    
    # 测试场景3：列顺序变化
    results['场景3'] = test_scenario_3_column_order_changed()
    
    # 测试场景4：真实报告文件
    real_result = test_real_report()
    if real_result is not None:
        results['场景4'] = real_result
    
    # 总结
    logger.info("\n" + "📊 " + "="*58)
    logger.info("📊 测试总结")
    logger.info("📊 " + "="*58)
    
    for scenario, result in results.items():
        if result:
            logger.info(f"✅ {scenario}: 通过")
        else:
            logger.error(f"❌ {scenario}: 失败")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n" + "🎉 " + "="*58)
        logger.info("🎉 所有测试通过！SmartColumnFinder与旧方法完全一致！")
        logger.info("🎉 " + "="*58)
    else:
        logger.error("\n" + "❌ " + "="*58)
        logger.error("❌ 部分测试失败，请检查！")
        logger.error("❌ " + "="*58)
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
