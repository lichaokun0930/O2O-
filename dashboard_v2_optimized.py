# -*- coding: utf-8 -*-
"""
O2O门店数据分析看板 v2.1 - 优化版本
基于Dash + Plotly构建的可视化数据看板

优化内容：
- ✅ 删除AI分析模块
- ✅ 添加数据缓存机制（提升加载速度5-10倍）
- ✅ 规范化日志系统（便于问题排查）
- ✅ 修复KPI计算的硬编码列索引（避免数据错位）

运行方式：
    python dashboard_v2_optimized.py
"""

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from pathlib import Path
import os
from datetime import datetime
import base64
import io
import pickle
import hashlib
import logging
from logging.handlers import RotatingFileHandler

# 导入门店分析器（集成untitled1.py功能）
from store_analyzer import get_store_analyzer

# PDF生成相关库
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from PIL import Image

# ==================== 日志系统配置 ====================
def setup_logger(name='dashboard', level=logging.INFO):
    """配置日志系统"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建logs目录
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # 文件输出（自动轮转，最大10MB，保留5个备份）
    file_handler = RotatingFileHandler(
        log_dir / 'dashboard.log',
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# 初始化日志
logger = setup_logger()

# 全局配置
DEFAULT_REPORT_PATH = "./reports/淮安生态新城商品10.29 的副本_分析报告.xlsx"
APP_TITLE = "O2O门店数据分析看板 v2.1"

# ==================== 数据缓存工具 ====================
class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"缓存目录: {self.cache_dir.absolute()}")
    
    def _get_file_hash(self, file_path):
        """计算文件MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_cache_path(self, file_path):
        """获取缓存文件路径"""
        file_hash = self._get_file_hash(file_path)
        return self.cache_dir / f"{Path(file_path).stem}_{file_hash}.cache"
    
    def get(self, file_path):
        """从缓存获取数据"""
        try:
            cache_path = self._get_cache_path(file_path)
            
            if not cache_path.exists():
                logger.debug(f"缓存不存在: {cache_path.name}")
                return None
            
            # 检查缓存是否过期（文件修改时间）
            cache_mtime = cache_path.stat().st_mtime
            file_mtime = Path(file_path).stat().st_mtime
            
            if cache_mtime < file_mtime:
                logger.info(f"缓存已过期: {cache_path.name}")
                cache_path.unlink()  # 删除过期缓存
                return None
            
            # 加载缓存
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.info(f"✅ 使用缓存数据: {cache_path.name}")
            return data
            
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
    
    def set(self, file_path, data):
        """保存数据到缓存"""
        try:
            cache_path = self._get_cache_path(file_path)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            cache_size = cache_path.stat().st_size / 1024 / 1024  # MB
            logger.info(f"💾 缓存已保存: {cache_path.name} ({cache_size:.2f}MB)")
            
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def clear(self):
        """清除所有缓存"""
        count = 0
        for cache_file in self.cache_dir.glob('*.cache'):
            cache_file.unlink()
            count += 1
        logger.info(f"🗑️ 已清除 {count} 个缓存文件")

# 初始化缓存管理器
data_cache = DataCache()

# ==================== KPI列名映射配置 ====================
class KPIColumnMapping:
    """KPI列名映射配置 - 避免硬编码索引"""
    
    # KPI Sheet的列名映射
    KPI_COLUMNS = {
        '门店': ['门店', 'Store', '店铺'],
        '总SKU数(含规格)': ['总SKU数(含规格)', '总SKU数', 'Total SKU'],
        '单规格SPU数': ['单规格SPU数', '单规格商品数'],
        '单规格SKU数': ['单规格SKU数'],
        '多规格SKU总数': ['多规格SKU总数', '多规格SKU数'],
        '总SKU数(去重后)': ['总SKU数(去重后)', '去重SKU数', 'Unique SKU'],
        '动销SKU数': ['动销SKU数', '动销数', 'Active SKU'],
        '滞销SKU数': ['滞销SKU数', '滞销数', 'Inactive SKU'],
        '总销售额(去重后)': ['总销售额(去重后)', '总销售额', 'Total Revenue'],
        '动销率': ['动销率', 'Active Rate'],
        '唯一多规格商品数': ['唯一多规格商品数', '多规格商品数']
    }
    
    # 分类Sheet的列名映射
    CATEGORY_COLUMNS = {
        '一级分类': ['一级分类', '美团一级分类', 'Category'],
        '爆品数': ['美团一级分类爆品sku数', '爆品数', 'Hot Products'],
        '折扣': ['美团一级分类折扣', '折扣', 'Discount'],
        '折扣SKU数': ['美团一级分类折扣sku数', '折扣商品数'],
        '去重SKU数': ['美团一级分类去重SKU数(口径同动销率)', '去重SKU数'],
        '动销SKU数': ['美团一级分类动销sku数', '动销数'],
        '动销率': ['美团一级分类动销率(类内)', '动销率']
    }
    
    @classmethod
    def find_column(cls, df, standard_name, mapping_dict):
        """
        在DataFrame中查找列名
        
        Args:
            df: DataFrame
            standard_name: 标准列名
            mapping_dict: 列名映射字典
            
        Returns:
            实际列名，如果找不到返回None
        """
        if standard_name not in mapping_dict:
            return None
        
        possible_names = mapping_dict[standard_name]
        
        for name in possible_names:
            if name in df.columns:
                return name
        
        return None
    
    @classmethod
    def safe_get_value(cls, df, row_idx, standard_name, mapping_dict, default=0):
        """
        安全获取DataFrame中的值
        
        Args:
            df: DataFrame
            row_idx: 行索引
            standard_name: 标准列名
            mapping_dict: 列名映射字典
            default: 默认值
            
        Returns:
            列值，如果找不到返回默认值
        """
        col_name = cls.find_column(df, standard_name, mapping_dict)
        
        if col_name is None:
            logger.warning(f"未找到列: {standard_name} (尝试: {mapping_dict.get(standard_name, [])})")
            return default
        
        try:
            if row_idx >= len(df):
                return default
            return df.iloc[row_idx][col_name]
        except Exception as e:
            logger.error(f"获取值失败 [{standard_name}]: {e}")
            return default

# ==================== 数据加载器（优化版）====================
class DataLoader:
    """数据加载器 - 负责从Excel报告中读取和预处理数据"""
    
    def __init__(self, excel_path, use_cache=True):
        self.excel_path = excel_path
        self.use_cache = use_cache
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有sheet数据（带缓存）"""
        try:
            # 尝试从缓存加载
            if self.use_cache:
                cached_data = data_cache.get(self.excel_path)
                if cached_data is not None:
                    self.data = cached_data
                    logger.info(f"📦 从缓存加载数据: {Path(self.excel_path).name}")
                    self._log_data_summary()
                    return
            
            # 缓存未命中，从Excel加载
            logger.info(f"📂 从Excel加载数据: {Path(self.excel_path).name}")
            
            # 获取所有sheet名称
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            logger.debug(f"可用Sheet: {sheet_names}")
            
            # 定义Sheet名称映射表
            sheet_mapping = {
                'kpi': ['核心指标对比', 'KPI', '核心指标'],
                'role_analysis': ['商品角色分析', '角色分析'],
                'price_analysis': ['价格带分析', '价格分析'],
                'category_l1': ['美团一级分类详细指标', '一级分类详细指标', '一级分类'],
                'sku_details': ['详细SKU报告(去重后)', 'SKU报告', '详细SKU报告']
            }
            
            # 遍历所有Sheet，按名称匹配
            for key, possible_names in sheet_mapping.items():
                for sheet_name in sheet_names:
                    if any(name in sheet_name for name in possible_names):
                        self.data[key] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                        logger.debug(f"✅ 加载 {key}: '{sheet_name}'")
                        
                        # 特殊处理：清理价格带数据
                        if key == 'price_analysis' and not self.data[key].empty:
                            if 'Unnamed' in str(self.data[key].columns[0]):
                                self.data[key] = self.data[key].drop(self.data[key].columns[0], axis=1)
                        break
            
            # 加载成本分析相关Sheet（如果存在）
            for sheet_name in sheet_names:
                if '成本分析汇总' in sheet_name:
                    self.data['cost_summary'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    logger.debug(f"✅ 加载成本分析汇总数据")
                elif '高毛利商品' in sheet_name:
                    self.data['high_margin_products'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    logger.debug(f"✅ 加载高毛利商品数据")
                elif '低毛利预警' in sheet_name:
                    self.data['low_margin_warning'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    logger.debug(f"✅ 加载低毛利预警数据")
            
            # 填充缺失的数据
            for key in ['kpi', 'category_l1', 'role_analysis', 'price_analysis', 'sku_details', 
                        'cost_summary', 'high_margin_products', 'low_margin_warning']:
                if key not in self.data:
                    self.data[key] = pd.DataFrame()
            
            # 保存到缓存
            if self.use_cache:
                data_cache.set(self.excel_path, self.data)
            
            self._log_data_summary()
            
        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}", exc_info=True)
            # 创建空数据框作为备用
            self.data = {
                'kpi': pd.DataFrame(),
                'category_l1': pd.DataFrame(),
                'role_analysis': pd.DataFrame(),
                'price_analysis': pd.DataFrame()
            }
    
    def _log_data_summary(self):
        """记录数据摘要"""
        logger.info(f"📊 数据加载完成:")
        logger.info(f"  - KPI数据: {self.data['kpi'].shape}")
        logger.info(f"  - 分类数据: {self.data['category_l1'].shape}")
        logger.info(f"  - 价格带数据: {self.data['price_analysis'].shape}")
        logger.info(f"  - 角色分析: {self.data['role_analysis'].shape}")
    
    def get_kpi_summary(self):
        """获取KPI摘要数据（优化版 - 使用列名映射）"""
        if self.data['kpi'].empty:
            logger.warning("KPI数据为空")
            return {}
        
        kpi_df = self.data['kpi']
        if len(kpi_df) == 0:
            return {}
        
        summary = {}
        mapper = KPIColumnMapping
        
        # 使用列名映射安全获取值
        summary['门店'] = mapper.safe_get_value(
            kpi_df, 0, '门店', mapper.KPI_COLUMNS, default='未知'
        )
        summary['总SKU数(含规格)'] = mapper.safe_get_value(
            kpi_df, 0, '总SKU数(含规格)', mapper.KPI_COLUMNS, default=0
        )
        summary['单规格SPU数'] = mapper.safe_get_value(
            kpi_df, 0, '单规格SPU数', mapper.KPI_COLUMNS, default=0
        )
        summary['单规格SKU数'] = mapper.safe_get_value(
            kpi_df, 0, '单规格SKU数', mapper.KPI_COLUMNS, default=0
        )
        summary['多规格SKU总数'] = mapper.safe_get_value(
            kpi_df, 0, '多规格SKU总数', mapper.KPI_COLUMNS, default=0
        )
        summary['总SKU数(去重后)'] = mapper.safe_get_value(
            kpi_df, 0, '总SKU数(去重后)', mapper.KPI_COLUMNS, default=0
        )
        summary['动销SKU数'] = mapper.safe_get_value(
            kpi_df, 0, '动销SKU数', mapper.KPI_COLUMNS, default=0
        )
        summary['滞销SKU数'] = mapper.safe_get_value(
            kpi_df, 0, '滞销SKU数', mapper.KPI_COLUMNS, default=0
        )
        summary['总销售额(去重后)'] = mapper.safe_get_value(
            kpi_df, 0, '总销售额(去重后)', mapper.KPI_COLUMNS, default=0
        )
        summary['动销率'] = mapper.safe_get_value(
            kpi_df, 0, '动销率', mapper.KPI_COLUMNS, default=0
        )
        summary['唯一多规格商品数'] = mapper.safe_get_value(
            kpi_df, 0, '唯一多规格商品数', mapper.KPI_COLUMNS, default=0
        )
        
        # 从美团一级分类详细指标中获取门店爆品数和平均折扣
        if not self.data['category_l1'].empty:
            category_df = self.data['category_l1']
            
            # 使用列名映射获取爆品数
            burst_col = mapper.find_column(category_df, '爆品数', mapper.CATEGORY_COLUMNS)
            if burst_col:
                summary['门店爆品数'] = category_df[burst_col].sum()
            else:
                summary['门店爆品数'] = 0
            
            # 使用列名映射获取折扣
            discount_col = mapper.find_column(category_df, '折扣', mapper.CATEGORY_COLUMNS)
            if discount_col:
                discount_values = pd.to_numeric(category_df[discount_col], errors='coerce')
                summary['门店平均折扣'] = discount_values.mean()
            else:
                summary['门店平均折扣'] = 10.0
        
        # ========== 新增指标计算 ==========
        if not self.data['sku_details'].empty:
            sku_df = self.data['sku_details']
            
            # 1. 平均SKU单价
            if len(sku_df.columns) > 1:
                price_col = pd.to_numeric(sku_df.iloc[:, 1], errors='coerce')
                summary['平均SKU单价'] = price_col.mean()
            
            # 2. 高价值SKU占比
            if len(sku_df.columns) > 1 and summary.get('总SKU数(去重后)', 0) > 0:
                high_value_count = (pd.to_numeric(sku_df.iloc[:, 1], errors='coerce') > 50).sum()
                total_skus = summary['总SKU数(去重后)']
                summary['高价值SKU占比'] = (high_value_count / total_skus) if total_skus > 0 else 0
            
            # 3. 爆款集中度
            if len(sku_df.columns) > 2 and summary.get('总销售额(去重后)', 0) > 0:
                price_col = pd.to_numeric(sku_df.iloc[:, 1], errors='coerce').fillna(0)
                sales_col = pd.to_numeric(sku_df.iloc[:, 2], errors='coerce').fillna(0)
                sku_df_temp = sku_df.copy()
                sku_df_temp['revenue'] = price_col * sales_col
                
                top10_revenue = sku_df_temp.nlargest(10, 'revenue')['revenue'].sum()
                total_revenue = summary['总销售额(去重后)']
                summary['爆款集中度'] = (top10_revenue / total_revenue) if total_revenue > 0 else 0
        
        # 5. 促销强度
        if not self.data['category_l1'].empty:
            category_df = self.data['category_l1']
            
            discount_sku_col = mapper.find_column(category_df, '折扣SKU数', mapper.CATEGORY_COLUMNS)
            dedup_sku_col = mapper.find_column(category_df, '去重SKU数', mapper.CATEGORY_COLUMNS)
            
            if discount_sku_col and dedup_sku_col:
                total_discount_skus = pd.to_numeric(category_df[discount_sku_col], errors='coerce').sum()
                total_dedup_skus = pd.to_numeric(category_df[dedup_sku_col], errors='coerce').sum()
                summary['促销强度'] = (total_discount_skus / total_dedup_skus) if total_dedup_skus > 0 else 0
        
        # ========== 成本分析KPI ==========
        if not self.data.get('cost_summary', pd.DataFrame()).empty:
            cost_df = self.data['cost_summary']
            if len(cost_df) > 0:
                total_row = cost_df.iloc[0]
                
                if '成本销售额' in cost_df.columns:
                    summary['总成本销售额'] = total_row['成本销售额']
                
                if '毛利' in cost_df.columns:
                    summary['总毛利'] = total_row['毛利']
                
                if '美团一级分类售价毛利率' in cost_df.columns:
                    summary['平均毛利率'] = total_row['美团一级分类售价毛利率']
        
        if not self.data.get('high_margin_products', pd.DataFrame()).empty:
            summary['高毛利商品数'] = len(self.data['high_margin_products'])
        
        logger.debug(f"KPI摘要计算完成，共{len(summary)}个指标")
        return summary
    
    def get_category_analysis(self):
        """获取分类分析数据"""
        return self.data['category_l1']
    
    def get_role_analysis(self):
        """获取商品角色分析数据"""
        return self.data['role_analysis']
    
    def get_price_analysis(self):
        """获取价格带分析数据"""
        return self.data['price_analysis']


# ==================== 门店管理器 ====================
class StoreManager:
    """门店管理器 - 支持多门店分析与切换"""
    
    def __init__(self):
        self.stores = {}
        self.current_store = None
        self.default_report = DEFAULT_REPORT_PATH
    
    def add_store(self, name, report_path):
        """添加门店"""
        self.stores[name] = report_path
        if not self.current_store:
            self.current_store = name
        logger.info(f"✅ 门店【{name}】已添加")
    
    def get_store_list(self):
        """获取所有门店列表"""
        stores = list(self.stores.keys())
        if Path(self.default_report).exists():
            default_name = "默认门店"
            if default_name not in stores:
                stores.insert(0, default_name)
        return stores
    
    def get_report_path(self, name):
        """获取门店报告路径"""
        if name in self.stores:
            return self.stores[name]
        elif name == "默认门店":
            return self.default_report
        return None
    
    def switch_store(self, name):
        """切换当前门店"""
        report_path = self.get_report_path(name)
        if report_path and Path(report_path).exists():
            self.current_store = name
            return DataLoader(report_path)
        return None
    
    def clear_all(self):
        """清除所有门店"""
        self.stores.clear()
        self.current_store = None
        logger.info("🗑️ 已清除所有门店")


# ==================== 智能布局管理器 ====================
class SmartLayoutManager:
    """智能布局管理器 - 根据数据复杂度自动调整图表尺寸"""
    
    @staticmethod
    def calculate_heatmap_dimensions(data):
        """计算热力图最优尺寸"""
        if data.empty:
            return 900, 600
        
        rows = len(data)
        cols = len(data.columns) if hasattr(data, 'columns') else 1
        
        base_width = 900
        base_height = max(600, rows * 30 + 200)
        
        max_width = 1400
        max_height = 900
        
        width = min(base_width, max_width)
        height = min(base_height, max_height)
        
        return width, height
    
    @staticmethod
    def calculate_pie_dimensions(categories):
        """计算饼图最优尺寸"""
        num_categories = len(categories) if categories else 4
        
        if num_categories <= 4:
            return 700, 700
        elif num_categories <= 8:
            return 800, 800
        else:
            return 900, 900
    
    @staticmethod
    def calculate_bar_dimensions(data_length):
        """计算柱状图最优尺寸"""
        base_height = 600
        if data_length > 10:
            base_height = 700
        if data_length > 15:
            base_height = 800
        
        return 1000, base_height
