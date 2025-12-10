#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
门店分析器模块 - 从untitled1.py提取的核心分析功能

用于Dashboard集成，提供：
- 门店数据加载与清洗
- 多规格商品识别
- 商品角色分析
- 多维度统计分析
- Excel报告生成
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict, Tuple, Optional, Any
import traceback

# 从untitled1.py导入核心函数
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 导入untitled1.py中的核心函数
from untitled1 import (
    load_and_clean_data,
    analyze_store_performance,
    export_full_report_to_excel
)


class StoreAnalyzer:
    """门店分析器 - Dashboard集成版"""
    
    def __init__(self):
        """初始化分析器"""
        self.consumption_scenarios = {
            "早餐快手": ["早餐", "牛奶", "面包", "麦片", "鸡蛋"],
            "加班能量补给": ["咖啡", "能量饮料", "巧克力", "饼干", "能量棒"],
            "家庭囤货": ["大包装", "家庭装", "组合装", "箱", "量贩"],
            "聚会零食": ["薯片", "膨化", "糖果", "坚果", "汽水", "啤酒"],
        }
        self.analyzed_stores = {}  # 存储分析结果
        self.store_data = {}       # 存储原始数据
    
    def analyze_file(self, file_path: str, store_name: str) -> Optional[Dict[str, Any]]:
        """
        分析单个门店文件
        
        Args:
            file_path: Excel/CSV文件路径
            store_name: 门店名称
            
        Returns:
            分析结果字典，包含所有统计指标和明细数据
        """
        try:
            print(f"\n🔍 开始分析门店: {store_name}")
            print(f"📁 文件路径: {file_path}")
            
            # 0. 预检查: 读取文件并显示列名 (用于调试)
            import pandas as pd
            import os
            
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                return None
            
            try:
                # 尝试读取文件的前几行以检查列名
                print(f"\n🔍 预检查: 读取文件列名...")
                if file_path.endswith('.csv'):
                    temp_df = pd.read_csv(file_path, nrows=5)
                else:
                    temp_df = pd.read_excel(file_path, nrows=5)
                
                # 去除列名首尾空格
                temp_df.columns = temp_df.columns.str.strip()
                
                print(f"✅ 文件读取成功！")
                print(f"📋 文件包含以下列名 (共 {len(temp_df.columns)} 列):")
                for i, col in enumerate(temp_df.columns, 1):
                    print(f"   {i:2d}. '{col}'")
                
                # 检查必要列是否可能存在
                essential_keywords = {
                    'product_name': ['product_name', '商品名称', '品名', '名称'],
                    'price': ['price', '售价', '现价', '销售价', '价格'],
                    'sales_qty': ['sales_qty', '月售', '销量', '月销量', '销售数量'],
                    'l1_category': ['l1_category', '一级分类', '美团一级分类', '大类', '分类', '一级品类'],
                    'original_price': ['original_price', '原价', '划线价', '参考价'],
                    '库存': ['库存', '剩余库存', '库存数', '库存数量', 'stock', 'Stock']
                }
                
                print(f"\n🔍 必要列检查:")
                missing_essential = []
                for essential_col, keywords in essential_keywords.items():
                    found = any(kw in temp_df.columns for kw in keywords)
                    status = "✅" if found else "❌"
                    matched = [kw for kw in keywords if kw in temp_df.columns]
                    if found:
                        print(f"   {status} {essential_col:20s} → 找到: {matched}")
                    else:
                        print(f"   {status} {essential_col:20s} → 未找到 (期望: {keywords[:3]}...)")
                        missing_essential.append(essential_col)
                
                if missing_essential:
                    print(f"\n⚠️ 警告: 可能缺少以下必要列: {missing_essential}")
                    print(f"   分析可能会失败，请检查文件格式是否正确")
                else:
                    print(f"\n✅ 所有必要列均可映射！")
                
                del temp_df  # 释放内存
                
            except Exception as pre_check_error:
                print(f"⚠️ 预检查失败 (将继续尝试分析): {pre_check_error}")
            
            # 1. 加载和清洗数据
            print(f"🔄 调用 load_and_clean_data()...")
            processed = load_and_clean_data(
                file_path, 
                store_name, 
                self.consumption_scenarios
            )
            
            # 检查 load_and_clean_data 的返回值
            if processed is None:
                print(f"❌ load_and_clean_data() 返回了 None")
                print(f"   这通常意味着:")
                print(f"   1. 文件不存在或无法读取")
                print(f"   2. 文件缺少必要的列 (product_name, price, sales_qty, l1_category, original_price, 库存)")
                print(f"   3. Excel 锁文件存在 (~$...)")
                return None
            
            if not isinstance(processed, tuple) or len(processed) != 3:
                print(f"❌ load_and_clean_data() 返回了非预期的数据类型: {type(processed)}")
                return None
            
            df_all, df_dedup, df_act = processed
            
            # 检查 DataFrame 是否有效
            if df_all is None or df_dedup is None or df_act is None:
                print(f"❌ 返回的 DataFrame 包含 None 值")
                return None
            
            if df_dedup.empty:
                print(f"❌ 去重后的数据为空，无法继续分析")
                return None
            
            print(f"✅ 数据加载成功:")
            print(f"   - 全部SKU: {len(df_all)}")
            print(f"   - 去重后: {len(df_dedup)}")
            print(f"   - 动销SKU: {len(df_act)}")
            
            # 2. 执行多维度分析
            analysis_results = analyze_store_performance(df_all, df_dedup, df_act)
            
            if not analysis_results:
                print(f"❌ 分析执行失败")
                return None
            
            # 3. 存储结果
            self.analyzed_stores[store_name] = analysis_results
            self.store_data[store_name] = {
                'all_skus': df_all,
                'deduplicated': df_dedup,
                'active': df_act
            }
            
            # 从分析结果中提取核心指标
            summary = self.get_summary(store_name)
            if summary:
                print(f"✅ 分析完成！")
                print(f"   - 总SKU数(含规格): {summary.get('总SKU数(含规格)', 0)}")
                print(f"   - 多规格SKU总数: {summary.get('多规格SKU总数', 0)}")
                print(f"   - 动销SKU数: {summary.get('动销SKU数', 0)}")
                print(f"   - 总销售额: ¥{summary.get('总销售额(去重后)', 0):,.2f}")
            else:
                print(f"✅ 分析完成！（核心指标提取失败）")
            
            return analysis_results
            
        except Exception as e:
            print(f"❌ 分析门店 {store_name} 时发生错误: {e}")
            traceback.print_exc()
            return None
    
    def get_store_list(self) -> list:
        """获取已分析门店列表"""
        return list(self.analyzed_stores.keys())
    
    def get_analysis(self, store_name: str) -> Optional[Dict[str, Any]]:
        """获取指定门店的分析结果"""
        return self.analyzed_stores.get(store_name)
    
    def get_summary(self, store_name: str) -> Optional[Dict[str, Any]]:
        """
        获取门店核心指标摘要
        
        Returns:
            包含核心KPI的字典
        """
        analysis = self.get_analysis(store_name)
        if not analysis:
            return None
        
        # analyze_store_performance() 返回的核心指标在 '总体指标' DataFrame 中
        core_df = analysis.get('总体指标', pd.DataFrame())
        
        if core_df.empty:
            print(f"⚠️ 警告: '{store_name}' 的总体指标为空")
            return None
        
        # DataFrame 是以门店为索引的,直接访问第一行
        # 使用 .loc[store_name] 或 .iloc[0] 获取 Series,然后转为字典
        row_data = core_df.iloc[0].to_dict() if len(core_df) > 0 else {}
        
        summary = {
            # SKU统计
            '总SKU数(含规格)': int(row_data.get('总SKU数(含规格)', 0)),
            '总SKU数(去重后)': int(row_data.get('总SKU数(去重后)', 0)),
            '单规格SPU数': int(row_data.get('单规格SPU数', 0)),
            '单规格SKU数': int(row_data.get('单规格SKU数', 0)),
            '多规格SKU总数': int(row_data.get('多规格SKU总数', 0)),
            '唯一多规格商品数': int(row_data.get('唯一多规格商品数', 0)),
            
            # 动销数据
            '动销SKU数': int(row_data.get('动销SKU数', 0)),
            '滞销SKU数': int(row_data.get('滞销SKU数', 0)),
            '动销率': float(row_data.get('动销率', 0)),
            
            # 销售数据
            '总销售额(去重后)': float(row_data.get('总销售额(去重后)', 0)),
        }
        
        return summary
    
    def get_multispec_products(self, store_name: str, limit: int = None) -> Optional[pd.DataFrame]:
        """
        获取多规格商品明细
        
        Args:
            store_name: 门店名称
            limit: 返回行数限制（None表示全部）
            
        Returns:
            多规格商品DataFrame
        """
        analysis = self.get_analysis(store_name)
        if not analysis:
            return None
        
        multispec_df = analysis.get('多规格商品报告(全)', pd.DataFrame())
        
        if limit and not multispec_df.empty:
            return multispec_df.head(limit)
        
        return multispec_df
    
    def get_category_analysis(self, store_name: str) -> Optional[pd.DataFrame]:
        """获取美团一级分类详细指标"""
        analysis = self.get_analysis(store_name)
        if not analysis:
            return None
        
        return analysis.get('美团一级分类详细指标', pd.DataFrame())
    
    def get_price_band_analysis(self, store_name: str) -> Optional[pd.DataFrame]:
        """获取价格带分析"""
        analysis = self.get_analysis(store_name)
        if not analysis:
            return None
        
        # 从分析结果中提取价格带数据
        # 注: 需要确认untitled1.py中是否有价格带维度的分析
        return analysis.get('价格带分析', pd.DataFrame())
    
    def get_product_role_analysis(self, store_name: str) -> Optional[Dict[str, int]]:
        """获取商品角色分布"""
        summary = self.get_summary(store_name)
        if not summary:
            return None
        
        return {
            '引流品': summary['引流品数'],
            '利润品': summary['利润品数'],
            '形象品': summary['形象品数'],
            '劣势品': summary['劣势品数']
        }
    
    def export_report(self, store_names = None, output_path: str = None) -> str:
        """
        导出Excel报告
        
        Args:
            store_names: 要导出的门店名称(字符串)或列表（None表示全部）
            output_path: 输出文件路径
            
        Returns:
            实际输出文件路径
        """
        # 处理参数: 支持字符串或列表
        if store_names is None:
            store_names = self.get_store_list()
        elif isinstance(store_names, str):
            store_names = [store_names]  # 转换为列表
        
        if not store_names:
            raise ValueError("没有可导出的门店数据")
        
        # 筛选要导出的数据
        export_results = {name: self.analyzed_stores[name] for name in store_names if name in self.analyzed_stores}
        export_data = {name: self.store_data[name] for name in store_names if name in self.store_data}
        
        # 确定输出路径
        if output_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"./reports/门店深度分析_{timestamp}.xlsx"
        
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 调用导出函数
        export_full_report_to_excel(export_results, export_data, output_path)
        
        print(f"✅ 报告已导出: {output_path}")
        return output_path
    
    def clear_analysis(self, store_name: str = None):
        """清除分析结果"""
        if store_name:
            self.analyzed_stores.pop(store_name, None)
            self.store_data.pop(store_name, None)
        else:
            self.analyzed_stores.clear()
            self.store_data.clear()


# 创建全局分析器实例
_analyzer_instance = None


def get_store_analyzer() -> StoreAnalyzer:
    """获取全局分析器实例（单例模式）"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = StoreAnalyzer()
    return _analyzer_instance


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("门店分析器模块测试")
    print("=" * 60)
    
    analyzer = get_store_analyzer()
    print(f"✅ 分析器已创建")
    print(f"当前已分析门店: {analyzer.get_store_list()}")
