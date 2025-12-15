# -*- coding: utf-8 -*-
"""
城市新增竞对数据加载器
负责从Excel文件加载和验证竞对数据
"""

import pandas as pd
from pathlib import Path
import logging
import re

logger = logging.getLogger('dashboard')


class CompetitorDataLoader:
    """竞对数据加载器 - 负责从Excel文件加载原始数据"""
    
    # 必需的基础列
    REQUIRED_COLUMNS = [
        '门店名称', '城市', '运营', '商圈类型',
        '5km内竞对数量', '近15天5km内新增竞对数量'
    ]
    
    # 竞对列模式
    COMPETITOR_PATTERN = r'^新增竞对\d*$'
    
    def __init__(self, file_path: str):
        """初始化数据加载器
        
        Args:
            file_path: Excel文件路径
        """
        self.file_path = Path(file_path)
        self._df = None
    
    def load_data(self) -> pd.DataFrame:
        """加载Excel数据
        
        Returns:
            原始DataFrame
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误或必需列缺失
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")
        
        if not self.file_path.suffix.lower() in ['.xlsx', '.xls']:
            raise ValueError(f"不支持的文件格式: {self.file_path.suffix}")
        
        try:
            self._df = pd.read_excel(self.file_path)
            logger.info(f"✅ 加载竞对数据: {self.file_path.name}, {len(self._df)}行")
        except Exception as e:
            raise ValueError(f"读取Excel文件失败: {e}")
        
        # 验证必需列
        is_valid, missing = self.validate_columns(self._df)
        if not is_valid:
            raise ValueError(f"缺少必需列: {', '.join(missing)}")
        
        return self._df
    
    def validate_columns(self, df: pd.DataFrame) -> tuple:
        """验证必需列是否存在
        
        Args:
            df: DataFrame
            
        Returns:
            (是否有效, 缺失列列表)
        """
        missing = []
        for col in self.REQUIRED_COLUMNS:
            if col not in df.columns:
                missing.append(col)
        
        # 检查是否至少有一个竞对列
        has_competitor_col = any(
            re.match(self.COMPETITOR_PATTERN, str(col)) 
            for col in df.columns
        )
        
        if not has_competitor_col:
            missing.append('新增竞对列(如新增竞对1)')
        
        return len(missing) == 0, missing
    
    def get_data(self) -> pd.DataFrame:
        """获取已加载的数据
        
        Returns:
            DataFrame，如果未加载则先加载
        """
        if self._df is None:
            return self.load_data()
        return self._df


class CompetitorDataParser:
    """竞对数据解析器 - 将宽表转换为长表格式"""
    
    # 竞对属性列后缀模式
    ATTRIBUTE_SUFFIXES = {
        'brand': ['品牌特性'],
        'sku': ['sku数', 'SKU数'],
        'subsidy': ['商补率']
    }
    
    def __init__(self, df: pd.DataFrame):
        """初始化解析器
        
        Args:
            df: 原始宽表DataFrame
        """
        self.df = df
        self._competitor_columns = None
    
    def detect_competitor_columns(self) -> list:
        """动态检测竞对列及其属性列
        
        Returns:
            [{'competitor_col': '新增竞对1', 'brand_col': '品牌特性', 
              'sku_col': 'sku数', 'subsidy_col': '商补率'}, ...]
        """
        if self._competitor_columns is not None:
            return self._competitor_columns
        
        result = []
        columns = list(self.df.columns)
        
        # 找到所有竞对列
        competitor_cols = []
        for i, col in enumerate(columns):
            if re.match(r'^新增竞对\d*$', str(col)):
                competitor_cols.append((i, col))
        
        # 为每个竞对列找到对应的属性列
        for idx, comp_col in competitor_cols:
            mapping = {'competitor_col': comp_col}
            
            # 查找后续的属性列（在下一个竞对列之前）
            next_comp_idx = len(columns)
            for next_idx, next_col in competitor_cols:
                if next_idx > idx:
                    next_comp_idx = next_idx
                    break
            
            # 在当前竞对列和下一个竞对列之间查找属性列
            for attr_idx in range(idx + 1, min(next_comp_idx, idx + 4)):
                if attr_idx >= len(columns):
                    break
                attr_col = columns[attr_idx]
                attr_col_lower = str(attr_col).lower()
                
                # 匹配品牌特性
                if '品牌特性' in str(attr_col):
                    mapping['brand_col'] = attr_col
                # 匹配SKU数
                elif 'sku' in attr_col_lower or 'SKU' in str(attr_col):
                    mapping['sku_col'] = attr_col
                # 匹配商补率
                elif '商补率' in str(attr_col):
                    mapping['subsidy_col'] = attr_col
            
            result.append(mapping)
        
        self._competitor_columns = result
        logger.info(f"✅ 检测到 {len(result)} 个竞对列组")
        return result
    
    def parse_wide_to_long(self) -> pd.DataFrame:
        """将宽表转换为长表格式
        
        Returns:
            长表格式DataFrame，包含列：
            门店名称, 城市, 运营, 商圈类型, 5km内竞对数量, 
            近15天5km内新增竞对数量, 竞对名称, 品牌特性, SKU数, 商补率, 竞对序号
        """
        competitor_mappings = self.detect_competitor_columns()
        
        if not competitor_mappings:
            logger.warning("⚠️ 未检测到竞对列")
            return pd.DataFrame()
        
        # 基础列
        base_cols = ['门店名称', '城市', '运营', '商圈类型', 
                     '5km内竞对数量', '近15天5km内新增竞对数量']
        
        records = []
        
        for _, row in self.df.iterrows():
            base_data = {col: row.get(col) for col in base_cols}
            
            for seq, mapping in enumerate(competitor_mappings, 1):
                comp_name = row.get(mapping['competitor_col'])
                
                # 跳过空的竞对
                if pd.isna(comp_name) or str(comp_name).strip() == '':
                    continue
                
                record = base_data.copy()
                record['竞对名称'] = comp_name
                record['品牌特性'] = row.get(mapping.get('brand_col'))
                record['SKU数'] = row.get(mapping.get('sku_col'))
                record['商补率'] = row.get(mapping.get('subsidy_col'))
                record['竞对序号'] = seq
                
                records.append(record)
        
        result_df = pd.DataFrame(records)
        logger.info(f"✅ 宽表转长表完成: {len(self.df)}行 -> {len(result_df)}条竞对记录")
        
        return result_df
    
    def get_store_summary(self) -> pd.DataFrame:
        """获取门店汇总数据（不展开竞对）
        
        Returns:
            门店级别的汇总DataFrame
        """
        base_cols = ['门店名称', '城市', '运营', '商圈类型', 
                     '5km内竞对数量', '近15天5km内新增竞对数量']
        return self.df[base_cols].copy()
