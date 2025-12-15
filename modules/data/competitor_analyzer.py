# -*- coding: utf-8 -*-
"""
城市新增竞对分析器
提供各种统计分析功能
"""

import pandas as pd
import numpy as np
import logging
import re
from collections import Counter

logger = logging.getLogger('dashboard')


class CompetitorAnalyzer:
    """竞对分析器 - 执行各种统计分析"""
    
    def __init__(self, df: pd.DataFrame, store_df: pd.DataFrame = None):
        """初始化分析器
        
        Args:
            df: 长表格式的竞对数据（每行一个竞对）
            store_df: 门店汇总数据（可选，用于门店级别统计）
        """
        self.df = df
        self.store_df = store_df
        logger.info(f"✅ CompetitorAnalyzer初始化: {len(df)}条竞对记录")
    
    def get_city_summary(self) -> pd.DataFrame:
        """获取城市维度汇总
        
        Returns:
            DataFrame: 城市 | 门店数 | 5km内竞对总数 | 新增竞对数 | 占比
        """
        if len(self.df) == 0:
            return pd.DataFrame(columns=['城市', '门店数', '5km内竞对总数', '新增竞对数', '占比'])
        
        if self.store_df is not None:
            # 使用门店汇总数据
            city_stats = self.store_df.groupby('城市').agg({
                '门店名称': 'count',
                '5km内竞对数量': 'sum',
                '近15天5km内新增竞对数量': 'sum'
            }).reset_index()
            city_stats.columns = ['城市', '门店数', '5km内竞对总数', '新增竞对数']
        else:
            # 从长表数据计算
            city_stats = self.df.groupby('城市').agg({
                '门店名称': 'nunique',
                '5km内竞对数量': 'first',  # 每个门店的值相同
                '竞对名称': 'count'
            }).reset_index()
            city_stats.columns = ['城市', '门店数', '5km内竞对总数', '新增竞对数']
        
        # 计算占比
        total_new = city_stats['新增竞对数'].sum()
        if total_new > 0:
            city_stats['占比'] = (city_stats['新增竞对数'] / total_new * 100).round(2)
        else:
            city_stats['占比'] = 0.0
        
        # 按新增竞对数降序排列
        city_stats = city_stats.sort_values('新增竞对数', ascending=False)
        
        return city_stats
    
    def get_brand_ranking(self, top_n: int = 10) -> pd.DataFrame:
        """获取品牌排行
        
        Args:
            top_n: 返回前N个品牌
            
        Returns:
            DataFrame: 品牌名称 | 出现次数 | 占比
        """
        if len(self.df) == 0:
            return pd.DataFrame(columns=['品牌名称', '出现次数', '占比'])
        
        # 统计品牌出现次数
        brand_counts = self.df['竞对名称'].value_counts().reset_index()
        brand_counts.columns = ['品牌名称', '出现次数']
        
        # 计算占比
        total = brand_counts['出现次数'].sum()
        if total > 0:
            brand_counts['占比'] = (brand_counts['出现次数'] / total * 100).round(2)
        else:
            brand_counts['占比'] = 0.0
        
        return brand_counts.head(top_n)
    
    def get_brand_city_distribution(self, brand_name: str) -> pd.DataFrame:
        """获取指定品牌在各城市的分布
        
        Args:
            brand_name: 品牌名称
            
        Returns:
            DataFrame: 城市 | 数量
        """
        brand_df = self.df[self.df['竞对名称'] == brand_name]
        distribution = brand_df.groupby('城市').size().reset_index(name='数量')
        return distribution.sort_values('数量', ascending=False)
    
    def get_business_circle_analysis(self) -> pd.DataFrame:
        """获取商圈类型分析
        
        Returns:
            DataFrame: 商圈类型 | 门店数 | 平均竞对数 | 平均新增竞对数
        """
        if self.store_df is not None:
            source_df = self.store_df
        else:
            # 从长表去重获取门店数据
            source_df = self.df.drop_duplicates(subset=['门店名称'])
        
        circle_stats = source_df.groupby('商圈类型').agg({
            '门店名称': 'count',
            '5km内竞对数量': 'mean',
            '近15天5km内新增竞对数量': 'mean'
        }).reset_index()
        
        circle_stats.columns = ['商圈类型', '门店数', '平均竞对数', '平均新增竞对数']
        circle_stats['平均竞对数'] = circle_stats['平均竞对数'].round(2)
        circle_stats['平均新增竞对数'] = circle_stats['平均新增竞对数'].round(2)
        
        # 按商圈类型排序（强 > 中 > 弱）
        order = {'强': 0, '中': 1, '弱': 2}
        circle_stats['排序'] = circle_stats['商圈类型'].map(order)
        circle_stats = circle_stats.sort_values('排序').drop('排序', axis=1)
        
        return circle_stats
    
    def get_region_analysis(self) -> pd.DataFrame:
        """获取区域类型分析
        
        Returns:
            DataFrame: 区域类型 | 门店数 | 竞对总数 | 新增竞对数
            - 竞对总数: 该区域门店5km内竞对数量的总和（可能有重复）
            - 新增竞对数: 从长表统计的实际新增竞对记录数（去重后）
        """
        if '区域类型' not in self.df.columns:
            logger.warning("⚠️ 数据中没有'区域类型'列，请先进行区域分类")
            return pd.DataFrame()
        
        # 从长表统计实际的新增竞对数量（每条记录代表一个新增竞对）
        region_competitor_count = self.df.groupby('区域类型').agg({
            '竞对名称': 'count'  # 统计实际的竞对记录数
        }).reset_index()
        region_competitor_count.columns = ['区域类型', '新增竞对数']
        
        # 统计门店数
        if self.store_df is not None and '区域类型' in self.store_df.columns:
            region_store_count = self.store_df.groupby('区域类型').agg({
                '门店名称': 'count',
                '5km内竞对数量': 'sum'
            }).reset_index()
            region_store_count.columns = ['区域类型', '门店数', '竞对总数']
        else:
            store_region = self.df.drop_duplicates(subset=['门店名称'])[['门店名称', '区域类型', '5km内竞对数量']]
            region_store_count = store_region.groupby('区域类型').agg({
                '门店名称': 'count',
                '5km内竞对数量': 'sum'
            }).reset_index()
            region_store_count.columns = ['区域类型', '门店数', '竞对总数']
        
        # 合并结果
        region_stats = region_store_count.merge(region_competitor_count, on='区域类型', how='left')
        region_stats['新增竞对数'] = region_stats['新增竞对数'].fillna(0).astype(int)
        
        return region_stats
    
    def get_competitor_details(self, filters: dict = None, 
                                sort_by: str = None, 
                                ascending: bool = False) -> pd.DataFrame:
        """获取竞对详情表
        
        Args:
            filters: 筛选条件字典
                - city: 城市
                - business_circle: 商圈类型
                - region: 区域类型
                - brand: 品牌名称
            sort_by: 排序字段（'SKU数' 或 '商补率'）
            ascending: 是否升序
            
        Returns:
            DataFrame: 门店名称 | 城市 | 商圈类型 | 区域类型 | 竞对名称 | 品牌特性 | SKU数 | 商补率
        """
        result_df = self.df.copy()
        
        # 应用筛选条件
        if filters:
            if filters.get('city'):
                result_df = result_df[result_df['城市'] == filters['city']]
            if filters.get('business_circle'):
                result_df = result_df[result_df['商圈类型'] == filters['business_circle']]
            if filters.get('region') and '区域类型' in result_df.columns:
                result_df = result_df[result_df['区域类型'] == filters['region']]
            if filters.get('brand'):
                result_df = result_df[result_df['竞对名称'].str.contains(filters['brand'], na=False)]
        
        # 排序
        if sort_by and sort_by in result_df.columns:
            # 处理商补率排序（需要转换为数值）
            if sort_by == '商补率':
                result_df['商补率排序值'] = result_df['商补率'].apply(self._parse_subsidy_rate)
                result_df = result_df.sort_values('商补率排序值', ascending=ascending)
                result_df = result_df.drop('商补率排序值', axis=1)
            else:
                result_df = result_df.sort_values(sort_by, ascending=ascending)
        
        # 选择展示列
        display_cols = ['门店名称', '城市', '商圈类型', '竞对名称', '品牌特性', 'SKU数', '商补率']
        if '区域类型' in result_df.columns:
            display_cols.insert(3, '区域类型')
        
        available_cols = [col for col in display_cols if col in result_df.columns]
        return result_df[available_cols]
    
    def _parse_subsidy_rate(self, rate_str) -> float:
        """解析商补率字符串为数值（用于排序）"""
        if pd.isna(rate_str):
            return 0.0
        
        # 提取数字，如 "10%-20%" -> 15
        numbers = re.findall(r'\d+', str(rate_str))
        if numbers:
            return sum(float(n) for n in numbers) / len(numbers)
        return 0.0
    
    def extract_brand_keywords(self) -> dict:
        """提取品牌特性关键词及频次
        
        Returns:
            dict: {'关键词': 频次, ...}
        """
        # 定义关键词列表
        keywords = [
            '低起送', '低门槛', '新客', '立减', '神券', '神价', '满减',
            '商补', '补贴', '折扣', '爆品', '活动', '配送', '免配',
            '开业', '收货', '营销', '日均', '单量'
        ]
        
        keyword_counts = Counter()
        
        for text in self.df['品牌特性'].dropna():
            text = str(text)
            for keyword in keywords:
                if keyword in text:
                    keyword_counts[keyword] += 1
        
        return dict(keyword_counts.most_common())
    
    def get_overview_stats(self) -> dict:
        """获取概览统计数据"""
        if self.store_df is not None:
            total_stores = len(self.store_df)
            total_competitors = self.store_df['5km内竞对数量'].sum()
            total_new_competitors = self.store_df['近15天5km内新增竞对数量'].sum()
            stores_with_new = (self.store_df['近15天5km内新增竞对数量'] > 0).sum()
        else:
            total_stores = self.df['门店名称'].nunique()
            total_competitors = self.df.drop_duplicates('门店名称')['5km内竞对数量'].sum()
            total_new_competitors = len(self.df)
            stores_with_new = self.df['门店名称'].nunique()
        
        # 计算区域分布
        region_dist = {}
        if '区域类型' in self.df.columns:
            region_counts = self.df['区域类型'].value_counts()
            total = region_counts.sum()
            for region in ['市区', '县城']:
                count = region_counts.get(region, 0)
                region_dist[region] = int(count)
                region_dist[f'{region}占比'] = round(count / total * 100, 1) if total > 0 else 0
        
        # 计算商圈分布
        circle_dist = {}
        circle_counts = self.df['商圈类型'].value_counts()
        total = circle_counts.sum()
        for circle in ['强', '中', '弱']:
            count = circle_counts.get(circle, 0)
            circle_dist[circle] = int(count)
            circle_dist[f'{circle}占比'] = round(count / total * 100, 1) if total > 0 else 0
        
        return {
            '总门店数': total_stores,
            '5km内竞对总数': int(total_competitors),
            '新增竞对总数': int(total_new_competitors),
            '有新增竞对的门店数': int(stores_with_new),
            '新增竞对品牌数': self.df['竞对名称'].nunique() if len(self.df) > 0 else 0,
            '覆盖城市数': self.df['城市'].nunique() if len(self.df) > 0 else 0,
            '区域分布': region_dist,
            '商圈分布': circle_dist
        }
    
    def get_circle_region_cross_analysis(self) -> pd.DataFrame:
        """获取商圈类型×区域类型交叉分析
        
        Returns:
            DataFrame: 商圈类型 | 区域类型 | 门店数 | 平均竞对数 | 平均新增竞对数
        """
        if self.store_df is None or '区域类型' not in self.store_df.columns:
            return pd.DataFrame()
        
        cross_stats = self.store_df.groupby(['商圈类型', '区域类型']).agg({
            '门店名称': 'count',
            '5km内竞对数量': 'mean',
            '近15天5km内新增竞对数量': 'mean'
        }).reset_index()
        
        cross_stats.columns = ['商圈类型', '区域类型', '门店数', '平均竞对数', '平均新增竞对数']
        cross_stats['平均竞对数'] = cross_stats['平均竞对数'].round(2)
        cross_stats['平均新增竞对数'] = cross_stats['平均新增竞对数'].round(2)
        
        return cross_stats
    
    def get_region_circle_distribution(self) -> dict:
        """获取市区/县城的强中弱商圈分布
        
        Returns:
            dict: {
                '市区': {'强': count, '中': count, '弱': count, '强占比': pct, ...},
                '县城': {'强': count, '中': count, '弱': count, '强占比': pct, ...}
            }
        """
        if self.store_df is None or '区域类型' not in self.store_df.columns:
            return {}
        
        result = {}
        for region in ['市区', '县城']:
            region_df = self.store_df[self.store_df['区域类型'] == region]
            total = len(region_df)
            if total == 0:
                result[region] = {'强': 0, '中': 0, '弱': 0, '强占比': 0, '中占比': 0, '弱占比': 0}
                continue
            
            circle_counts = region_df['商圈类型'].value_counts().to_dict()
            result[region] = {
                '强': circle_counts.get('强', 0),
                '中': circle_counts.get('中', 0),
                '弱': circle_counts.get('弱', 0),
                '强占比': round(circle_counts.get('强', 0) / total * 100, 1),
                '中占比': round(circle_counts.get('中', 0) / total * 100, 1),
                '弱占比': round(circle_counts.get('弱', 0) / total * 100, 1),
                '总门店数': total
            }
        
        return result
    
    def get_new_competitor_circle_distribution(self) -> dict:
        """获取市区/县城的新增竞对按商圈类型分布
        
        从长表（每行一个竞对记录）统计新增竞对在不同商圈的分布
        
        Returns:
            dict: {
                '市区': {'强': count, '中': count, '弱': count, '强占比': pct, ..., '总新增竞对数': total},
                '县城': {'强': count, '中': count, '弱': count, '强占比': pct, ..., '总新增竞对数': total}
            }
        """
        if '区域类型' not in self.df.columns or '商圈类型' not in self.df.columns:
            return {}
        
        result = {}
        for region in ['市区', '县城']:
            region_df = self.df[self.df['区域类型'] == region]
            total = len(region_df)
            if total == 0:
                result[region] = {'强': 0, '中': 0, '弱': 0, '强占比': 0, '中占比': 0, '弱占比': 0, '总新增竞对数': 0}
                continue
            
            circle_counts = region_df['商圈类型'].value_counts().to_dict()
            result[region] = {
                '强': circle_counts.get('强', 0),
                '中': circle_counts.get('中', 0),
                '弱': circle_counts.get('弱', 0),
                '强占比': round(circle_counts.get('强', 0) / total * 100, 1),
                '中占比': round(circle_counts.get('中', 0) / total * 100, 1),
                '弱占比': round(circle_counts.get('弱', 0) / total * 100, 1),
                '总新增竞对数': total
            }
        
        return result
    
    def get_competitor_by_city_region(self) -> pd.DataFrame:
        """获取5km竞对数按城市和区域类型分析
        
        Returns:
            DataFrame: 城市 | 区域类型 | 门店数 | 竞对总数 | 平均竞对数
        """
        if self.store_df is None or '区域类型' not in self.store_df.columns:
            return pd.DataFrame()
        
        stats = self.store_df.groupby(['城市', '区域类型']).agg({
            '门店名称': 'count',
            '5km内竞对数量': ['sum', 'mean']
        }).reset_index()
        
        stats.columns = ['城市', '区域类型', '门店数', '竞对总数', '平均竞对数']
        stats['平均竞对数'] = stats['平均竞对数'].round(2)
        
        return stats.sort_values(['城市', '区域类型'])
    
    def get_new_competitor_by_city_region(self) -> pd.DataFrame:
        """获取新增竞对数按城市和区域类型分析
        
        Returns:
            DataFrame: 城市 | 区域类型 | 门店数 | 新增竞对总数 | 平均新增竞对数
        """
        if self.store_df is None or '区域类型' not in self.store_df.columns:
            return pd.DataFrame()
        
        stats = self.store_df.groupby(['城市', '区域类型']).agg({
            '门店名称': 'count',
            '近15天5km内新增竞对数量': ['sum', 'mean']
        }).reset_index()
        
        stats.columns = ['城市', '区域类型', '门店数', '新增竞对总数', '平均新增竞对数']
        stats['平均新增竞对数'] = stats['平均新增竞对数'].round(2)
        
        return stats.sort_values('新增竞对总数', ascending=False)
    
    def get_region_competitor_distribution(self) -> pd.DataFrame:
        """获取区域类型的竞对数分布（用于箱线图）
        
        Returns:
            DataFrame: 区域类型 | 5km内竞对数量（每行一个门店）
        """
        if self.store_df is None or '区域类型' not in self.store_df.columns:
            return pd.DataFrame()
        
        return self.store_df[['区域类型', '5km内竞对数量', '近15天5km内新增竞对数量']].copy()

    def get_sku_scale_distribution(self) -> dict:
        """获取竞对SKU规模分布
        
        Returns:
            dict: {'小型(<3000)': count, '中型(3000-6000)': count, '大型(>6000)': count}
        """
        if 'SKU数' not in self.df.columns:
            return {}
        
        sku_data = self.df['SKU数'].dropna()
        
        small = (sku_data < 3000).sum()
        medium = ((sku_data >= 3000) & (sku_data <= 6000)).sum()
        large = (sku_data > 6000).sum()
        
        return {
            '小型(<3000)': int(small),
            '中型(3000-6000)': int(medium),
            '大型(>6000)': int(large)
        }
    
    def get_subsidy_distribution(self) -> dict:
        """获取商补率分布
        
        Returns:
            dict: {'无商补': count, '10%-20%': count, '20%-30%': count, '>30%': count}
        """
        if '商补率' not in self.df.columns:
            return {}
        
        result = {
            '无商补': 0,
            '10%-20%': 0,
            '20%-30%': 0,
            '>30%': 0
        }
        
        for _, row in self.df.iterrows():
            val = row.get('商补率')
            if pd.isna(val):
                result['无商补'] += 1
                continue
            val = str(val).lower().strip()
            if val in ['nan', '', '无', '-']:
                result['无商补'] += 1
            elif '10%' in val or '10-20' in val or '10%-20%' in val:
                result['10%-20%'] += 1
            elif '20%' in val or '20-30' in val or '20%-30%' in val:
                result['20%-30%'] += 1
            elif '30%' in val or '>30' in val:
                result['>30%'] += 1
            else:
                result['无商补'] += 1
        
        return result
    
    def get_subsidy_brand_detail(self) -> pd.DataFrame:
        """获取各商补率档位的品牌详情
        
        Returns:
            DataFrame: 商补率档位 | 品牌 | 数量
        """
        if '商补率' not in self.df.columns:
            return pd.DataFrame()
        
        records = []
        for _, row in self.df.iterrows():
            val = row.get('商补率')
            brand = row.get('竞对名称', '未知')
            
            if pd.isna(val):
                level = '无商补'
            else:
                val = str(val).lower().strip()
                if val in ['nan', '', '无', '-']:
                    level = '无商补'
                elif '10%' in val or '10-20' in val:
                    level = '10%-20%'
                elif '20%' in val or '20-30' in val:
                    level = '20%-30%'
                elif '30%' in val or '>30' in val:
                    level = '>30%'
                else:
                    level = '无商补'
            
            records.append({'商补率档位': level, '品牌': brand})
        
        df = pd.DataFrame(records)
        result = df.groupby(['商补率档位', '品牌']).size().reset_index(name='数量')
        return result.sort_values(['商补率档位', '数量'], ascending=[True, False])
    
    def get_brand_city_heatmap(self) -> pd.DataFrame:
        """获取品牌×城市热力图数据
        
        Returns:
            DataFrame: 品牌 | 城市 | 数量（透视表格式）
        """
        if len(self.df) == 0:
            return pd.DataFrame()
        
        # 统计品牌在各城市的出现次数
        brand_city = self.df.groupby(['竞对名称', '城市']).size().reset_index(name='数量')
        
        # 只取TOP10品牌
        top_brands = self.df['竞对名称'].value_counts().head(10).index.tolist()
        brand_city = brand_city[brand_city['竞对名称'].isin(top_brands)]
        
        # 透视表
        pivot = brand_city.pivot_table(index='竞对名称', columns='城市', values='数量', fill_value=0)
        
        return pivot
    
    def get_new_competitor_by_city(self) -> pd.DataFrame:
        """获取近15天新增竞对按城市分布
        
        Returns:
            DataFrame: 城市 | 门店数 | 有新增的门店数 | 新增竞对总数 | 平均新增数
        """
        if self.store_df is None:
            return pd.DataFrame()
        
        stats = self.store_df.groupby('城市').agg({
            '门店名称': 'count',
            '近15天5km内新增竞对数量': ['sum', 'mean', lambda x: (x > 0).sum()]
        }).reset_index()
        
        stats.columns = ['城市', '门店数', '新增竞对总数', '平均新增数', '有新增的门店数']
        stats['平均新增数'] = stats['平均新增数'].round(2)
        stats['新增占比'] = (stats['有新增的门店数'] / stats['门店数'] * 100).round(1)
        
        return stats.sort_values('新增竞对总数', ascending=False)

    def get_brand_region_expansion(self) -> pd.DataFrame:
        """获取品牌在市区/县城的扩张趋势对比
        
        Returns:
            DataFrame: 品牌名称 | 市区数量 | 县城数量 | 总数 | 市区占比 | 县城占比 | 扩张倾向
        """
        if '区域类型' not in self.df.columns:
            return pd.DataFrame()
        
        # 统计每个品牌在市区和县城的数量
        brand_region = self.df.groupby(['竞对名称', '区域类型']).size().unstack(fill_value=0)
        
        # 确保有市区和县城列
        if '市区' not in brand_region.columns:
            brand_region['市区'] = 0
        if '县城' not in brand_region.columns:
            brand_region['县城'] = 0
        
        brand_region = brand_region.reset_index()
        brand_region.columns = ['品牌名称', '县城数量', '市区数量'] if brand_region.columns[1] == '县城' else ['品牌名称', '市区数量', '县城数量']
        
        # 重新排列列顺序
        if '市区数量' in brand_region.columns and '县城数量' in brand_region.columns:
            brand_region = brand_region[['品牌名称', '市区数量', '县城数量']]
        
        brand_region['总数'] = brand_region['市区数量'] + brand_region['县城数量']
        brand_region['市区占比'] = (brand_region['市区数量'] / brand_region['总数'] * 100).round(1)
        brand_region['县城占比'] = (brand_region['县城数量'] / brand_region['总数'] * 100).round(1)
        
        # 判断扩张倾向
        def get_tendency(row):
            if row['市区占比'] > 60:
                return '市区为主'
            elif row['县城占比'] > 60:
                return '县城为主'
            else:
                return '均衡发展'
        
        brand_region['扩张倾向'] = brand_region.apply(get_tendency, axis=1)
        
        # 按总数排序
        return brand_region.sort_values('总数', ascending=False)

    def generate_insights(self) -> dict:
        """生成竞对分析洞察报告
        
        Returns:
            dict: {
                'summary': 总体概述,
                'key_findings': [关键发现列表],
                'risk_alerts': [风险预警列表],
                'recommendations': [建议列表]
            }
        """
        insights = {
            'summary': '',
            'key_findings': [],
            'risk_alerts': [],
            'recommendations': []
        }
        
        # 获取基础统计数据
        stats = self.get_overview_stats()
        city_summary = self.get_city_summary()
        brand_ranking = self.get_brand_ranking(top_n=10)
        region_stats = self.get_region_analysis()
        
        total_stores = stats.get('总门店数', 0)
        total_new_competitors = stats.get('新增竞对总数', 0)
        stores_with_new = stats.get('有新增竞对的门店数', 0)
        total_brands = stats.get('新增竞对品牌数', 0)
        
        # 1. 总体概述
        if total_stores > 0:
            affected_rate = round(stores_with_new / total_stores * 100, 1)
            
            # 计算受影响门店的平均新增数和最高新增数
            max_new = 0
            avg_affected = 0
            if self.store_df is not None and '近15天5km内新增竞对数量' in self.store_df.columns:
                affected_stores = self.store_df[self.store_df['近15天5km内新增竞对数量'] > 0]
                if len(affected_stores) > 0:
                    max_new = int(affected_stores['近15天5km内新增竞对数量'].max())
                    avg_affected = round(affected_stores['近15天5km内新增竞对数量'].mean(), 1)
            
            insights['summary'] = f"近15天内，{total_stores}家门店中有{stores_with_new}家({affected_rate}%)周边出现新增竞对，共计{total_new_competitors}家新竞对，涉及{total_brands}个品牌。受影响门店平均新增{avg_affected}个竞对，单店最高新增{max_new}个。"
        
        # 2. 关键发现
        # 2.1 城市维度分析
        if not city_summary.empty:
            top_city = city_summary.iloc[0]
            insights['key_findings'].append(
                f"🏙️ 竞争最激烈城市：{top_city['城市']}，新增{int(top_city['新增竞对数'])}家竞对，占总新增的{top_city['占比']}%"
            )
            
            # 找出新增竞对数超过平均值2倍的城市
            if len(city_summary) > 1:
                avg_new = city_summary['新增竞对数'].mean()
                hot_cities = city_summary[city_summary['新增竞对数'] > avg_new * 1.5]
                if len(hot_cities) > 1:
                    hot_city_names = hot_cities['城市'].tolist()[:3]
                    insights['key_findings'].append(
                        f"🔥 竞争热点城市：{', '.join(hot_city_names)}，新增竞对数显著高于平均水平"
                    )
        
        # 2.2 品牌维度分析
        if not brand_ranking.empty:
            top_brand = brand_ranking.iloc[0]
            insights['key_findings'].append(
                f"🏆 扩张最快品牌：{top_brand['品牌名称']}，新增{int(top_brand['出现次数'])}家门店，占比{top_brand['占比']}%"
            )
            
            # 分析品牌集中度
            if len(brand_ranking) >= 3:
                top3_share = brand_ranking.head(3)['占比'].sum()
                if top3_share > 50:
                    insights['key_findings'].append(
                        f"📊 品牌集中度高：TOP3品牌占新增竞对的{round(top3_share, 1)}%，市场竞争格局相对集中"
                    )
        
        # 2.3 区域维度分析
        if not region_stats.empty and '区域类型' in region_stats.columns:
            urban = region_stats[region_stats['区域类型'] == '市区']
            county = region_stats[region_stats['区域类型'] == '县城']
            
            if not urban.empty and not county.empty:
                urban_new = urban['新增竞对数'].values[0] if '新增竞对数' in urban.columns else 0
                county_new = county['新增竞对数'].values[0] if '新增竞对数' in county.columns else 0
                total_new = urban_new + county_new
                
                if total_new > 0:
                    urban_pct = round(urban_new / total_new * 100, 1)
                    county_pct = round(county_new / total_new * 100, 1)
                    
                    if urban_pct > 60:
                        insights['key_findings'].append(
                            f"📍 市区竞争加剧：{urban_pct}%的新增竞对出现在市区，市区门店面临更大竞争压力"
                        )
                    elif county_pct > 60:
                        insights['key_findings'].append(
                            f"📍 县城竞争加剧：{county_pct}%的新增竞对出现在县城，下沉市场竞争升温"
                        )
                    else:
                        insights['key_findings'].append(
                            f"📍 区域竞争均衡：市区{urban_pct}% vs 县城{county_pct}%，竞争压力分布相对均匀"
                        )
        
        # 3. 风险预警
        # 3.1 高竞争门店预警
        if self.store_df is not None and '近15天5km内新增竞对数量' in self.store_df.columns:
            high_risk_stores = self.store_df[self.store_df['近15天5km内新增竞对数量'] >= 3]
            if len(high_risk_stores) > 0:
                insights['risk_alerts'].append(
                    f"⚠️ 高风险门店：{len(high_risk_stores)}家门店周边新增3个及以上竞对，需重点关注"
                )
                
                # 列出TOP3高风险门店
                top_risk = high_risk_stores.nlargest(3, '近15天5km内新增竞对数量')
                risk_names = top_risk['门店名称'].tolist()
                insights['risk_alerts'].append(
                    f"🚨 重点关注门店：{', '.join(risk_names)}"
                )
        
        # 3.2 品牌扩张预警
        if not brand_ranking.empty and len(brand_ranking) >= 1:
            fast_brands = brand_ranking[brand_ranking['出现次数'] >= 5]
            if len(fast_brands) > 0:
                brand_names = fast_brands['品牌名称'].tolist()[:3]
                insights['risk_alerts'].append(
                    f"⚡ 快速扩张品牌：{', '.join(brand_names)}，扩张速度较快，需密切关注其动态"
                )
        
        # 4. 建议
        if total_new_competitors > 0:
            insights['recommendations'].append(
                "💡 建议对高风险门店进行竞品调研，了解新竞对的定价策略和促销活动"
            )
            
            if stores_with_new / total_stores > 0.3 if total_stores > 0 else False:
                insights['recommendations'].append(
                    "💡 超过30%门店受到新竞对影响，建议制定区域性竞争应对策略"
                )
            
            if not brand_ranking.empty:
                top_brand = brand_ranking.iloc[0]['品牌名称']
                insights['recommendations'].append(
                    f"💡 重点研究{top_brand}的商业模式和竞争优势，制定针对性应对方案"
                )
        
        return insights
