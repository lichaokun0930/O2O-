# -*- coding: utf-8 -*-
"""
O2O门店数据分析看板 v2.0 - 智能自适应版本
基于Dash + Plotly构建的可视化数据看板，具备智能面积识别功能

运行方式：
    python dashboard_v2.py

功能：
- 智能面积识别，自动调整图表尺寸
- 自适应布局系统
- 高质量数据可视化
- 交互式数据探索
"""

import dash
from dash import dcc, html, Input, Output, State, callback, dash_table, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash_echarts  # ECharts图表组件
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

# AI分析模块已删除（P0优化）
# from ai_analyzer_simple import get_ai_analyzer
# from ai_panel_analyzers_simple import (
#     get_kpi_analyzer, 
#     get_category_analyzer,
#     get_price_analyzer,
#     get_promo_analyzer,
#     get_master_analyzer
# )
# 导入门店分析器（集成untitled1.py功能）
from store_analyzer import get_store_analyzer

# 导入城市新增竞对分析模块
from modules.data.competitor_loader import CompetitorDataLoader, CompetitorDataParser
from modules.data.competitor_analyzer import CompetitorAnalyzer
from modules.utils.region_classifier import get_region_classifier
from modules.components.city_competitor_tab import create_city_competitor_tab_layout

# PDF生成相关库
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from PIL import Image

# ==================== P0优化：日志系统 ====================
def setup_logger(name='dashboard', level=logging.INFO):
    """配置日志系统"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
    
    file_handler = RotatingFileHandler(log_dir / 'dashboard.log', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()

# ==================== P0优化：数据缓存 ====================
class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"缓存目录: {self.cache_dir.absolute()}")
    
    def _get_file_hash(self, file_path):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_cache_path(self, file_path):
        file_hash = self._get_file_hash(file_path)
        return self.cache_dir / f"{Path(file_path).stem}_{file_hash}.cache"
    
    def get(self, file_path):
        try:
            cache_path = self._get_cache_path(file_path)
            if not cache_path.exists():
                return None
            
            cache_mtime = cache_path.stat().st_mtime
            file_mtime = Path(file_path).stat().st_mtime
            
            if cache_mtime < file_mtime:
                logger.info(f"缓存已过期: {cache_path.name}")
                cache_path.unlink()
                return None
            
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.info(f"✅ 使用缓存数据: {cache_path.name}")
            return data
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
    
    def set(self, file_path, data):
        try:
            cache_path = self._get_cache_path(file_path)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            cache_size = cache_path.stat().st_size / 1024 / 1024
            logger.info(f"💾 缓存已保存: {cache_path.name} ({cache_size:.2f}MB)")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def clear(self):
        count = 0
        for cache_file in self.cache_dir.glob('*.cache'):
            cache_file.unlink()
            count += 1
        logger.info(f"🗑️ 已清除 {count} 个缓存文件")
        return count

data_cache = DataCache()

# 全局配置
DEFAULT_REPORT_PATH = "./reports/本店/惠宜选-铜山万达（5）_分析报告.xlsx"  # 默认使用本店报告
APP_TITLE = "O2O门店数据分析看板 v2.0 (P0优化版)"

class DataLoader:
    """数据加载器 - 负责从Excel报告中读取和预处理数据（P0优化：支持缓存）"""
    
    def __init__(self, excel_path, use_cache=True):
        self.excel_path = excel_path
        self.use_cache = use_cache
        self.data = {}
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有sheet数据（P0优化：支持缓存）"""
        try:
            # P0优化：尝试从缓存加载
            if self.use_cache:
                cached_data = data_cache.get(self.excel_path)
                if cached_data is not None:
                    self.data = cached_data
                    logger.info(f"📦 从缓存加载数据: {Path(self.excel_path).name}")
                    return
            
            # 缓存未命中，从Excel加载
            logger.info(f"📂 从Excel加载数据: {Path(self.excel_path).name}")
            
            # 获取所有sheet名称
            excel_file = pd.ExcelFile(self.excel_path)
            sheet_names = excel_file.sheet_names
            logger.debug(f"可用Sheet: {sheet_names}")
            
            # 🔧 改进：按Sheet名称读取，避免索引错位问题
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
                        print(f"✅ 加载 {key}: '{sheet_name}'")
                        
                        # 特殊处理：清理价格带数据
                        if key == 'price_analysis' and not self.data[key].empty:
                            if 'Unnamed' in str(self.data[key].columns[0]):
                                self.data[key] = self.data[key].drop(self.data[key].columns[0], axis=1)
                        break
            
            # 加载成本分析相关Sheet（如果存在）
            for sheet_name in sheet_names:
                if '成本分析汇总' in sheet_name:
                    self.data['cost_summary'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    print(f"✅ 加载成本分析汇总数据")
                elif '高毛利商品' in sheet_name:
                    self.data['high_margin_products'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    print(f"✅ 加载高毛利商品数据")
                elif '低毛利预警' in sheet_name:
                    self.data['low_margin_warning'] = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    print(f"✅ 加载低毛利预警数据")
            
            # 填充缺失的数据
            for key in ['kpi', 'category_l1', 'role_analysis', 'price_analysis', 'sku_details', 
                        'cost_summary', 'high_margin_products', 'low_margin_warning']:
                if key not in self.data:
                    self.data[key] = pd.DataFrame()
            
            # P0优化：保存到缓存
            if self.use_cache:
                data_cache.set(self.excel_path, self.data)
            
            logger.info(f"✅ 数据加载成功: {Path(self.excel_path).name}")
            logger.info(f"📊 KPI数据: {self.data['kpi'].shape}")
            logger.info(f"💰 价格带数据: {self.data['price_analysis'].shape}")
            logger.info(f"🏪 分类数据: {self.data['category_l1'].shape}")
            
        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}", exc_info=True)
            # 创建空数据框作为备用
            self.data = {
                'kpi': pd.DataFrame(),
                'category_l1': pd.DataFrame(),
                'role_analysis': pd.DataFrame(),
                'price_analysis': pd.DataFrame()
            }
    
    def get_kpi_summary(self):
        """获取KPI摘要数据"""
        if self.data['kpi'].empty:
            return {}
        
        kpi_df = self.data['kpi']
        if len(kpi_df) > 0:
            # 取第一行数据（单门店）
            row = kpi_df.iloc[0]
            summary = {}
            
            # 根据实际Excel列顺序映射
            # A:门店 B:总SKU数(含规格) C:单规格SPU数 D:单规格SKU数 E:多规格SKU总数 
            # F:总SKU数(去重后) G:动销SKU数 H:滞销SKU数 I:总销售额(去重后) J:动销率 K:唯一多规格商品数
            for i, col in enumerate(kpi_df.columns):
                value = row.iloc[i] if i < len(row) else 0
                if i == 0:  # 门店
                    summary['门店'] = value
                elif i == 1:  # 总SKU数(含规格)
                    summary['总SKU数(含规格)'] = value
                elif i == 2:  # 单规格SPU数
                    summary['单规格SPU数'] = value
                elif i == 3:  # 单规格SKU数
                    summary['单规格SKU数'] = value
                elif i == 4:  # 多规格SKU总数
                    summary['多规格SKU总数'] = value
                elif i == 5:  # 总SKU数(去重后)
                    summary['总SKU数(去重后)'] = value
                elif i == 6:  # 动销SKU数
                    summary['动销SKU数'] = value
                elif i == 7:  # 滞销SKU数
                    summary['滞销SKU数'] = value
                elif i == 8:  # 总销售额(去重后)
                    summary['总销售额(去重后)'] = value
                elif i == 9:  # 动销率
                    summary['动销率'] = value
                elif i == 10:  # 唯一多规格商品数
                    summary['唯一多规格商品数'] = value
            
            # 从美团一级分类详细指标中获取门店爆品数和平均折扣
            if not self.data['category_l1'].empty:
                category_df = self.data['category_l1']
                
                # 使用SmartColumnFinder获取爆品数（三层查找机制）
                burst_count = SmartColumnFinder.get_value(category_df, '门店爆品数', aggregation='sum')
                if burst_count is not None:
                    summary['门店爆品数'] = burst_count
                
                # 使用SmartColumnFinder获取平均折扣
                avg_discount = SmartColumnFinder.get_value(category_df, '门店平均折扣', aggregation='mean')
                if avg_discount is not None:
                    summary['门店平均折扣'] = avg_discount
            
            # ========== 新增指标计算 ==========
            # 从SKU详细数据计算新指标
            if not self.data['sku_details'].empty:
                sku_df = self.data['sku_details']
                
                # 1. 平均SKU单价 (B列-售价的平均值)
                if len(sku_df.columns) > 1:
                    price_col = pd.to_numeric(sku_df.iloc[:, 1], errors='coerce')
                    summary['平均SKU单价'] = price_col.mean()
                
                # 2. 高价值SKU占比 (售价>50元的SKU数 / 总SKU数)
                if len(sku_df.columns) > 1 and '总SKU数(去重后)' in summary:
                    high_value_count = (pd.to_numeric(sku_df.iloc[:, 1], errors='coerce') > 50).sum()
                    total_skus = summary['总SKU数(去重后)']
                    summary['高价值SKU占比'] = (high_value_count / total_skus) if total_skus > 0 else 0
                
                # 3. 爆款集中度 (TOP10商品销售额 / 总销售额)
                if len(sku_df.columns) > 2 and '总销售额(去重后)' in summary:
                    # 计算每个SKU的销售额 = 售价(B列) × 月售(C列)
                    price_col = pd.to_numeric(sku_df.iloc[:, 1], errors='coerce').fillna(0)
                    sales_col = pd.to_numeric(sku_df.iloc[:, 2], errors='coerce').fillna(0)
                    sku_df_temp = sku_df.copy()
                    sku_df_temp['revenue'] = price_col * sales_col
                    
                    # TOP10销售额
                    top10_revenue = sku_df_temp.nlargest(10, 'revenue')['revenue'].sum()
                    total_revenue = summary['总销售额(去重后)']
                    summary['爆款集中度'] = (top10_revenue / total_revenue) if total_revenue > 0 else 0
            
            # 5. 促销强度 (折扣商品数 / 去重SKU数)
            # 含义：反映门店中有多少比例的商品参与了折扣促销
            if not self.data['category_l1'].empty:
                category_df = self.data['category_l1']
                # 美团一级分类折扣sku数 / 美团一级分类去重SKU数(口径同动销率)
                if '美团一级分类折扣sku数' in category_df.columns and '美团一级分类去重SKU数(口径同动销率)' in category_df.columns:
                    total_discount_skus = pd.to_numeric(category_df['美团一级分类折扣sku数'], errors='coerce').sum()
                    total_dedup_skus = pd.to_numeric(category_df['美团一级分类去重SKU数(口径同动销率)'], errors='coerce').sum()
                    summary['促销强度'] = (total_discount_skus / total_dedup_skus) if total_dedup_skus > 0 else 0
            
            # ========== 成本分析KPI（新增） ==========
            # 从成本分析汇总表获取数据
            if not self.data.get('cost_summary', pd.DataFrame()).empty:
                cost_df = self.data['cost_summary']
                # 第一行通常是"全部分类汇总"
                if len(cost_df) > 0:
                    total_row = cost_df.iloc[0]
                    
                    # 总成本销售额（索引2）
                    if '成本销售额' in cost_df.columns:
                        summary['总成本销售额'] = total_row['成本销售额']
                    
                    # 总毛利（索引5）
                    if '毛利' in cost_df.columns:
                        summary['总毛利'] = total_row['毛利']
                    
                    # 平均毛利率（索引7 - 使用售价毛利率）
                    if '美团一级分类售价毛利率' in cost_df.columns:
                        summary['平均毛利率'] = total_row['美团一级分类售价毛利率']
            
            # 高毛利商品数：从高毛利商品TOP50数据获取
            if not self.data.get('high_margin_products', pd.DataFrame()).empty:
                # TOP50表格的行数即为高毛利商品数（实际可能少于50）
                summary['高毛利商品数'] = len(self.data['high_margin_products'])
            
            return summary
        return {}
    
    def get_category_analysis(self):
        """获取分类分析数据"""
        return self.data['category_l1']
    
    def get_role_analysis(self):
        """获取商品角色分析数据"""
        return self.data['role_analysis']
    
    def get_price_analysis(self):
        """获取价格带分析数据"""
        return self.data['price_analysis']


class StoreManager:
    """门店管理器 - 支持多门店分析与切换"""
    
    def __init__(self):
        self.own_stores = {}  # 本店: {store_name: report_path}
        self.competitor_stores = {}  # 竞对: {store_name: report_path}
        self.current_store = None
        self.default_report = DEFAULT_REPORT_PATH
        self.reports_dir = Path("./reports")
        self.own_stores_dir = self.reports_dir / "本店"
        self.competitor_stores_dir = self.reports_dir / "竞对门店"
        
        # 确保目录存在
        self.own_stores_dir.mkdir(parents=True, exist_ok=True)
        self.competitor_stores_dir.mkdir(parents=True, exist_ok=True)
        
        # 启动时自动发现已有的门店报告
        self.auto_discover_stores()
    
    def add_store(self, name, report_path, is_competitor=False):
        """添加门店
        
        Args:
            name: 门店名称
            report_path: 报告文件路径
            is_competitor: 是否为竞对门店
        """
        if is_competitor:
            self.competitor_stores[name] = report_path
            logger.info(f"✅ 竞对门店【{name}】已添加")
        else:
            self.own_stores[name] = report_path
            if not self.current_store:
                self.current_store = name
            logger.info(f"✅ 本店【{name}】已添加")
    
    def get_store_list(self, store_type='own'):
        """获取门店列表
        
        Args:
            store_type: 'own' 获取本店列表, 'competitor' 获取竞对列表, 'all' 获取所有
            
        Returns:
            门店名称列表
        """
        if store_type == 'own':
            return list(self.own_stores.keys())
        elif store_type == 'competitor':
            return list(self.competitor_stores.keys())
        else:  # 'all'
            return list(self.own_stores.keys()) + list(self.competitor_stores.keys())
    
    def get_report_path(self, name):
        """获取门店报告路径"""
        # 先在本店中查找
        if name in self.own_stores:
            return self.own_stores[name]
        # 再在竞对中查找
        if name in self.competitor_stores:
            return self.competitor_stores[name]
        # 默认门店
        if name == "默认门店" and Path(self.default_report).exists():
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
        self.own_stores.clear()
        self.competitor_stores.clear()
        self.current_store = None
    
    def auto_discover_stores(self):
        """自动发现reports目录下的门店报告文件（分目录扫描）"""
        logger.info("🔍 开始自动发现门店报告...")
        
        # 扫描本店目录
        own_count = self._scan_directory(self.own_stores_dir, is_competitor=False)
        
        # 扫描竞对目录
        competitor_count = self._scan_directory(self.competitor_stores_dir, is_competitor=True)
        
        # 设置默认当前门店
        if not self.current_store and self.own_stores:
            self.current_store = list(self.own_stores.keys())[0]
            logger.info(f"📍 默认门店设置为: {self.current_store}")
        
        logger.info(f"🎉 自动发现完成: 本店 {own_count} 个, 竞对 {competitor_count} 个")
    
    def _scan_directory(self, directory, is_competitor=False):
        """扫描指定目录下的报告文件
        
        Args:
            directory: 要扫描的目录
            is_competitor: 是否为竞对目录
            
        Returns:
            发现的门店数量
        """
        if not directory.exists():
            logger.info(f"📂 目录不存在，已创建: {directory}")
            return 0
        
        # 查找所有分析报告文件
        report_files = list(directory.glob("*_分析报告.xlsx"))
        report_files.extend(directory.glob("*分析*.xlsx"))
        
        # 排除临时文件和备份文件
        report_files = [f for f in report_files 
                       if not f.name.startswith("~$") 
                       and "_202" not in f.name
                       and "示例" not in f.name]
        
        if not report_files:
            store_type = "竞对" if is_competitor else "本店"
            logger.info(f"  📂 {store_type}目录下暂无报告文件")
            return 0
        
        count = 0
        for report_file in report_files:
            # 从文件名提取门店名称
            store_name = report_file.stem.replace("_分析报告", "").replace("竞对分析_", "").replace("分析_", "")
            
            # 添加到对应的门店列表
            report_path = str(report_file)
            if is_competitor:
                self.competitor_stores[store_name] = report_path
                logger.info(f"  ✅ 发现竞对: {store_name}")
            else:
                self.own_stores[store_name] = report_path
                logger.info(f"  ✅ 发现本店: {store_name}")
            
            count += 1
        
        return count


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


class ComparisonDataLoader:
    """对比数据加载器 - 负责加载和缓存竞对门店数据"""
    
    def __init__(self):
        self.cache = {}  # {store_name: DataLoader}
        logger.info("📦 ComparisonDataLoader 初始化完成")
    
    def load_competitor_data(self, store_name):
        """加载竞对数据（带缓存）
        
        Args:
            store_name: 竞对门店名称
            
        Returns:
            DataLoader对象，如果加载失败则返回None
        """
        # 检查缓存
        if store_name in self.cache:
            logger.info(f"✅ 使用缓存的竞对数据: {store_name}")
            return self.cache[store_name]
        
        # 获取门店报告路径
        report_path = store_manager.get_report_path(store_name)
        if not report_path:
            logger.error(f"❌ 竞对门店不存在: {store_name}")
            return None
        
        if not Path(report_path).exists():
            logger.error(f"❌ 竞对报告文件不存在: {report_path}")
            return None
        
        # 加载数据
        try:
            logger.info(f"📂 加载竞对数据: {store_name}")
            data_loader = DataLoader(report_path, use_cache=True)
            
            # 缓存数据
            self.cache[store_name] = data_loader
            logger.info(f"💾 竞对数据已缓存: {store_name}")
            
            return data_loader
        except Exception as e:
            logger.error(f"❌ 竞对数据加载失败: {store_name}, 错误: {e}")
            return None
    
    def clear_cache(self, store_name=None):
        """清除缓存
        
        Args:
            store_name: 指定门店名称，如果为None则清除所有缓存
        """
        if store_name:
            if store_name in self.cache:
                self.cache.pop(store_name)
                logger.info(f"🗑️ 已清除竞对缓存: {store_name}")
        else:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"🗑️ 已清除所有竞对缓存 ({count}个)")


class ComparisonChartBuilder:
    """对比图表生成器 - 生成各种对比图表"""
    
    @staticmethod
    def create_grouped_bar_chart(own_data, competitor_data, x_col, y_col, title):
        """创建分组柱状图（并排对比）- 优化版
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            x_col: X轴列名
            y_col: Y轴列名
            title: 图表标题
            
        Returns:
            Plotly Figure对象
        """
        fig = go.Figure()
        
        # 本店数据
        fig.add_trace(go.Bar(
            name='本店',
            x=own_data[x_col],
            y=own_data[y_col],
            marker_color='#3498db',
            text=own_data[y_col],
            textposition='outside',
            texttemplate='%{text:.1f}'
        ))
        
        # 竞对数据
        fig.add_trace(go.Bar(
            name='竞对',
            x=competitor_data[x_col],
            y=competitor_data[y_col],
            marker_color='#e74c3c',
            text=competitor_data[y_col],
            textposition='outside',
            texttemplate='%{text:.1f}'
        ))
        
        # 动态计算高度：根据分类数量调整
        data_length = len(own_data)
        if data_length > 15:
            chart_height = 600
        elif data_length > 10:
            chart_height = 500
        else:
            chart_height = 450
        
        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            barmode='group',
            xaxis=dict(
                title=x_col,
                tickangle=-45,  # 倾斜标签，避免重叠
                tickfont=dict(size=11),
                automargin=True
            ),
            yaxis=dict(
                title=y_col,
                tickfont=dict(size=12),
                automargin=True
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=12)
            ),
            height=chart_height,
            margin=dict(l=80, r=50, t=100, b=120),  # 增加底部边距，给X轴标签更多空间
            hovermode='x unified'
        )
        
        return fig
    
    @staticmethod
    def create_mirror_bar_chart(own_data, competitor_data, category_col, value_col, title, own_store_name='本店'):
        """创建镜像柱状图（左右对比）- 优化版
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            category_col: 分类列名
            value_col: 数值列名
            title: 图表标题
            own_store_name: 本店名称（用于图例显示）
            
        Returns:
            Plotly Figure对象
        """
        fig = go.Figure()
        
        # 本店数据（负值，显示在左侧）
        fig.add_trace(go.Bar(
            name='本店',
            y=own_data[category_col],
            x=-own_data[value_col],  # 负值
            orientation='h',
            marker_color='#3498db',
            text=own_data[value_col],
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate='%{y}: %{text}<extra></extra>'
        ))
        
        # 竞对数据（正值，显示在右侧）
        fig.add_trace(go.Bar(
            name='竞对',
            y=competitor_data[category_col],
            x=competitor_data[value_col],
            orientation='h',
            marker_color='#e74c3c',
            text=competitor_data[value_col],
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate='%{y}: %{text}<extra></extra>'
        ))
        
        # 动态计算高度：每个分类至少30px高度
        data_length = len(own_data)
        chart_height = max(500, min(data_length * 30, 1200))  # 最小500px，最大1200px
        
        # 计算最大值用于设置坐标轴范围
        max_val = max(own_data[value_col].max(), competitor_data[value_col].max())
        tick_vals = [-max_val, -max_val*0.5, 0, max_val*0.5, max_val]
        tick_text = [f'{abs(v):.0f}' for v in tick_vals]
        
        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            barmode='overlay',
            xaxis=dict(
                title=value_col,
                tickvals=tick_vals,
                ticktext=tick_text,
                tickfont=dict(size=12),
                automargin=True
            ),
            yaxis=dict(
                title=category_col,
                tickfont=dict(size=11),
                automargin=True
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=12)
            ),
            height=chart_height,
            margin=dict(l=150, r=80, t=100, b=80),  # 增加左边距，给Y轴标签更多空间
            bargap=0.15  # 增加柱子间距，避免拥挤
        )
        
        return fig
    
    @staticmethod
    def create_stacked_comparison_bar(own_data, competitor_data, title, own_store_name='本店'):
        """创建堆叠对比柱状图（占比对比）
        
        Args:
            own_data: 本店数据字典，包含single_spec_pct和multi_spec_pct
            competitor_data: 竞对数据字典，包含single_spec_pct和multi_spec_pct
            title: 图表标题
            own_store_name: 本店名称（用于图例显示）
            
        Returns:
            Plotly Figure对象
        """
        fig = go.Figure()
        
        # 本店堆叠条
        fig.add_trace(go.Bar(
            name='本店-单规格',
            y=['本店'],
            x=[own_data['single_spec_pct']],
            orientation='h',
            marker_color='#3498db',
            text=[f"{own_data['single_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='本店-多规格',
            y=['本店'],
            x=[own_data['multi_spec_pct']],
            orientation='h',
            marker_color='#5dade2',
            text=[f"{own_data['multi_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        # 竞对堆叠条
        fig.add_trace(go.Bar(
            name='竞对-单规格',
            y=['竞对'],
            x=[competitor_data['single_spec_pct']],
            orientation='h',
            marker_color='#e74c3c',
            text=[f"{competitor_data['single_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        fig.add_trace(go.Bar(
            name='竞对-多规格',
            y=['竞对'],
            x=[competitor_data['multi_spec_pct']],
            orientation='h',
            marker_color='#ec7063',
            text=[f"{competitor_data['multi_spec_pct']:.1%}"],
            textposition='inside'
        ))
        
        fig.update_layout(
            title=title,
            barmode='stack',
            xaxis=dict(title='占比', tickformat='.0%'),
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=200
        )
        
        return fig
    
    @staticmethod
    def create_active_sku_comparison_chart(own_data, competitor_data, category_col, 
                                           active_sku_col, title, own_store_name='本店'):
        """创建动销商品数对比图表（ECharts分组柱状图 + 响应式）
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            category_col: 分类列名
            active_sku_col: 动销SKU数列名
            title: 图表标题
            own_store_name: 本店名称（用于图例显示）
            
        Returns:
            ECharts配置字典
        """
        # 对齐数据
        own_temp = own_data[[category_col, active_sku_col]].copy()
        own_temp.columns = [category_col, 'own_active_sku']
        
        comp_temp = competitor_data[[category_col, active_sku_col]].copy()
        comp_temp.columns = [category_col, 'comp_active_sku']
        
        merged = own_temp.merge(comp_temp, on=category_col)
        
        if merged.empty:
            return {
                'title': {'text': '无共同分类数据', 'left': 'center', 'top': 'center'},
                'xAxis': {'show': False},
                'yAxis': {'show': False}
            }
        
        # 过滤掉双方都为0的分类
        raw_categories = merged[category_col].tolist()
        raw_own_sku = [int(v) if pd.notna(v) else 0 for v in merged['own_active_sku'].tolist()]
        raw_comp_sku = [int(v) if pd.notna(v) else 0 for v in merged['comp_active_sku'].tolist()]
        
        categories, own_sku, comp_sku = [], [], []
        for i, cat in enumerate(raw_categories):
            if raw_own_sku[i] > 0 or raw_comp_sku[i] > 0:
                categories.append(cat)
                own_sku.append(raw_own_sku[i])
                comp_sku.append(raw_comp_sku[i])
        
        if not categories:
            return {
                'title': {'text': '所有分类数据为0', 'left': 'center', 'top': 'center'},
                'xAxis': {'show': False},
                'yAxis': {'show': False}
            }
        
        # 配色方案：青色 vs 橙色（更现代的对比色）
        own_color = '#00CED1'  # 深青色
        comp_color = '#FF8C00'  # 深橙色
        
        option = {
            'baseOption': {
                'toolbox': {
                    'show': True,
                    'right': 20,
                    'top': 5,
                    'feature': {
                        'saveAsImage': {
                            'type': 'png',
                            'pixelRatio': 4,
                            'title': '下载高清图',
                            'name': '动销商品数对比',
                            'backgroundColor': '#fff',
                            'excludeComponents': ['toolbox']
                        }
                    }
                },
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'shadow'},
                    'backgroundColor': 'rgba(50, 50, 50, 0.9)',
                    'textStyle': {'color': '#fff'}
                },
                'legend': {
                    'data': ['本店', '竞对'],
                    'top': 5,
                    'textStyle': {'fontSize': 12}
                },
                'grid': {'left': '5%', 'right': '5%', 'top': 40, 'bottom': 100, 'containLabel': True},
                'xAxis': {
                    'type': 'category',
                    'data': categories,
                    'axisLabel': {'rotate': 35, 'fontSize': 10, 'color': '#666'},
                    'axisLine': {'lineStyle': {'color': '#ddd'}},
                    'axisTick': {'show': False}
                },
                'yAxis': {
                    'type': 'value',
                    'name': '动销SKU数',
                    'nameTextStyle': {'fontSize': 11, 'color': '#666'},
                    'axisLabel': {'fontSize': 10, 'color': '#666'},
                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#eee'}}
                },
                'series': [
                    {
                        'name': '本店',
                        'type': 'bar',
                        'data': own_sku,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#00E5FF'},
                                    {'offset': 1, 'color': own_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0]
                        },
                        'label': {'show': True, 'position': 'top', 'fontSize': 9, 'color': own_color},
                        'barWidth': '35%',
                        'barGap': '10%'
                    },
                    {
                        'name': '竞对',
                        'type': 'bar',
                        'data': comp_sku,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#FFB74D'},
                                    {'offset': 1, 'color': comp_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0]
                        },
                        'label': {'show': True, 'position': 'top', 'fontSize': 9, 'color': comp_color},
                        'barWidth': '35%'
                    }
                ],
                'animationEasing': 'elasticOut',
                'animationDuration': 800
            },
            'media': [
                {
                    'query': {'maxWidth': 500},
                    'option': {
                        'title': {'textStyle': {'fontSize': 12}},
                        'legend': {'top': 28, 'textStyle': {'fontSize': 9}},
                        'grid': {'top': 55, 'bottom': 60},
                        'xAxis': {'axisLabel': {'fontSize': 8, 'rotate': 45}},
                        'series': [
                            {'barWidth': '30%', 'label': {'fontSize': 7}},
                            {'barWidth': '30%', 'label': {'fontSize': 7}}
                        ]
                    }
                },
                {
                    'query': {'minWidth': 1000},
                    'option': {
                        'title': {'textStyle': {'fontSize': 17}},
                        'legend': {'top': 40, 'textStyle': {'fontSize': 13}},
                        'grid': {'top': 80, 'bottom': 100},
                        'xAxis': {'axisLabel': {'fontSize': 12}},
                        'series': [
                            {'barWidth': '38%', 'label': {'fontSize': 11}},
                            {'barWidth': '38%', 'label': {'fontSize': 11}}
                        ]
                    }
                }
            ]
        }
        
        return option
    
    @staticmethod
    def create_active_rate_comparison_chart(own_data, competitor_data, category_col, 
                                           active_rate_col, title):
        """创建动销率对比图表（水平分组柱状图）
        
        动销率 = 动销SKU数 / 去重SKU数，原始数据为小数格式（如0.75表示75%）
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            category_col: 分类列名
            active_rate_col: 动销率列名
            title: 图表标题
            
        Returns:
            Plotly Figure对象
        """
        # 对齐数据
        own_temp = own_data[[category_col, active_rate_col]].copy()
        own_temp.columns = [category_col, 'own_rate']
        
        comp_temp = competitor_data[[category_col, active_rate_col]].copy()
        comp_temp.columns = [category_col, 'comp_rate']
        
        merged = own_temp.merge(comp_temp, on=category_col)
        
        if merged.empty:
            fig = go.Figure()
            fig.add_annotation(text="无共同分类数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            fig.update_layout(title=title, height=400)
            return fig
        
        categories = merged[category_col].tolist()
        own_rates = merged['own_rate'].tolist()
        comp_rates = merged['comp_rate'].tolist()
        
        # 数据格式处理：原始数据是小数格式（如0.75），需要乘100显示为百分比
        # 检测：如果最大值小于等于1，说明是小数格式
        max_rate = max(max(own_rates) if own_rates else 0, max(comp_rates) if comp_rates else 0)
        if max_rate <= 1:
            own_rates = [r * 100 for r in own_rates]
            comp_rates = [r * 100 for r in comp_rates]
        
        fig = go.Figure()
        
        # 水平柱状图 - 本店动销率（蓝色）
        fig.add_trace(go.Bar(
            name='本店',
            y=categories,
            x=own_rates,
            orientation='h',
            marker_color='#3498db',
            text=[f"{v:.1f}%" for v in own_rates],
            textposition='inside',
            textfont=dict(size=10, color='white'),
            hovertemplate='%{y}<br>本店动销率: %{x:.1f}%<extra></extra>'
        ))
        
        # 水平柱状图 - 竞对动销率（红色）
        fig.add_trace(go.Bar(
            name='竞对',
            y=categories,
            x=comp_rates,
            orientation='h',
            marker_color='#e74c3c',
            text=[f"{v:.1f}%" for v in comp_rates],
            textposition='inside',
            textfont=dict(size=10, color='white'),
            hovertemplate='%{y}<br>竞对动销率: %{x:.1f}%<extra></extra>'
        ))
        
        # 动态高度：根据分类数量调整
        data_length = len(categories)
        chart_height = max(400, data_length * 40 + 100)
        
        fig.update_layout(
            title=dict(text=title, font=dict(size=14)),
            barmode='group',
            xaxis=dict(
                title='动销率 (%)', 
                tickfont=dict(size=11),
                range=[0, 105],
                ticksuffix='%'
            ),
            yaxis=dict(
                title='', 
                tickfont=dict(size=11),
                automargin=True,
                categoryorder='total ascending'
            ),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            height=chart_height,
            margin=dict(l=120, r=40, t=60, b=40),
            hovermode='y unified'
        )
        
        return fig
    
    @staticmethod
    def create_active_rate_mirror_chart(own_data, competitor_data, category_col,
                                        active_rate_col, title, total_sku_col=None, own_store_name='本店'):
        """创建动销率对比图表（ECharts镜像柱状图：本店在左，竞对在右）
        
        使用加权排序算法：排序分 = 动销率 × log₁₀(SKU数量 + 1)
        这样可以平衡动销率和SKU数量，避免小样本分类因SKU少而动销率虚高的问题
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            category_col: 分类列名
            active_rate_col: 动销率列名
            title: 图表标题
            total_sku_col: SKU数量列名（用于加权排序，可选）
            own_store_name: 本店名称（用于图例显示）
            
        Returns:
            ECharts配置字典
        """
        import math
        
        # 对齐数据 - 包含SKU数量用于加权排序
        cols_to_use = [category_col, active_rate_col]
        if total_sku_col and total_sku_col in own_data.columns:
            cols_to_use.append(total_sku_col)
            own_temp = own_data[cols_to_use].copy()
            own_temp.columns = [category_col, 'own_rate', 'own_sku']
        else:
            own_temp = own_data[[category_col, active_rate_col]].copy()
            own_temp.columns = [category_col, 'own_rate']
        
        if total_sku_col and total_sku_col in competitor_data.columns:
            comp_temp = competitor_data[[category_col, active_rate_col, total_sku_col]].copy()
            comp_temp.columns = [category_col, 'comp_rate', 'comp_sku']
        else:
            comp_temp = competitor_data[[category_col, active_rate_col]].copy()
            comp_temp.columns = [category_col, 'comp_rate']
        
        merged = own_temp.merge(comp_temp, on=category_col)
        
        if merged.empty:
            return {
                'title': {'text': '无共同分类数据', 'left': 'center', 'top': 'center'},
                'xAxis': {'show': False},
                'yAxis': {'show': False}
            }
        
        categories = merged[category_col].tolist()
        own_rates = merged['own_rate'].tolist()
        comp_rates = merged['comp_rate'].tolist()
        
        # 数据格式处理：原始数据是小数格式（如0.75），需要乘100显示为百分比
        max_rate = max(max(own_rates) if own_rates else 0, max(comp_rates) if comp_rates else 0)
        if max_rate <= 1:
            own_rates = [round(r * 100, 1) for r in own_rates]
            comp_rates = [round(r * 100, 1) for r in comp_rates]
        else:
            own_rates = [round(r, 1) for r in own_rates]
            comp_rates = [round(r, 1) for r in comp_rates]
        
        # 剔除本店和竞对动销率都为0的数据
        filtered_data = [(cat, own, comp) for cat, own, comp in zip(categories, own_rates, comp_rates)
                         if own > 0 or comp > 0]
        if filtered_data:
            categories = [x[0] for x in filtered_data]
            own_rates = [x[1] for x in filtered_data]
            comp_rates = [x[2] for x in filtered_data]
            # 同步更新merged用于后续SKU数据获取
            merged = merged[merged[category_col].isin(categories)]
        
        # 只显示TOP15分类（使用加权排序：动销率 × log₁₀(SKU数量 + 1)）
        if len(categories) > 15:
            # 获取SKU数据用于加权排序
            has_sku_data = 'own_sku' in merged.columns and 'comp_sku' in merged.columns
            
            if has_sku_data:
                # 加权排序：使用本店和竞对的平均SKU数量
                own_skus = merged['own_sku'].tolist()
                comp_skus = merged['comp_sku'].tolist()
                # 计算平均SKU数量
                avg_skus = [(o + c) / 2 for o, c in zip(own_skus, comp_skus)]
                # 计算加权分数：动销率 × log₁₀(SKU数量 + 1)
                # 使用本店动销率作为基准
                combined = list(zip(categories, own_rates, comp_rates, avg_skus))
                combined.sort(key=lambda x: x[1] * math.log10(x[3] + 1), reverse=True)
                logger.info(f"📊 动销率对比使用加权排序: 动销率 × log₁₀(SKU数+1)")
            else:
                # 无SKU数据时回退到纯动销率排序
                combined = list(zip(categories, own_rates, comp_rates, [0]*len(categories)))
                combined.sort(key=lambda x: x[1], reverse=True)
                logger.info(f"📊 动销率对比使用纯动销率排序（无SKU数据）")
            
            combined = combined[:15]
            categories = [x[0] for x in combined]
            own_rates = [x[1] for x in combined]
            comp_rates = [x[2] for x in combined]
        
        # 智能计算中间区域宽度（根据最长分类名称）
        max_label_len = max(len(str(cat)) for cat in categories) if categories else 4
        # 中文字符宽度约1.2%每字符，最小8%，最大18%
        center_pct = min(max(max_label_len * 1.2 + 2, 8), 18)
        
        # 计算左右图表的边界（让两边柱状图更靠近中间标签）
        left_right = f'{50 - center_pct/2}%'  # 左图右边界
        right_left = f'{50 + center_pct/2}%'  # 右图左边界
        
        # ECharts配置 - 响应式media版本
        # baseOption: 默认配置（中等屏幕 600-1000px）
        option = {
            'baseOption': {
                'toolbox': {
                    'show': True,
                    'right': 20,
                    'top': 5,
                    'feature': {
                        'saveAsImage': {
                            'type': 'png',
                            'pixelRatio': 4,
                            'title': '下载高清图',
                            'name': '动销率对比',
                            'backgroundColor': '#fff',
                            'excludeComponents': ['toolbox']
                        }
                    }
                },
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'shadow'},
                    'formatter': lambda: None  # 将在JS中处理
                },
                'legend': {
                    'data': ['本店', '竞对'],
                    'top': 5,
                    'textStyle': {'fontSize': 11}
                },
                'grid': [
                    {'left': '5%', 'right': left_right, 'top': 35, 'bottom': 15, 'containLabel': False},
                    {'left': right_left, 'right': '5%', 'top': 35, 'bottom': 15, 'containLabel': False}
                ],
                'xAxis': [
                    {
                        'type': 'value',
                        'gridIndex': 0,
                        'inverse': True,
                        'axisLabel': {'formatter': '{value}%', 'fontSize': 10},
                        'splitLine': {'show': False},
                        'max': 100,
                        'axisLine': {'show': False}
                    },
                    {
                        'type': 'value',
                        'gridIndex': 1,
                        'axisLabel': {'formatter': '{value}%', 'fontSize': 10},
                        'splitLine': {'show': False},
                        'max': 100,
                        'axisLine': {'show': False}
                    }
                ],
                'yAxis': [
                    {
                        'type': 'category',
                        'gridIndex': 0,
                        'data': categories,
                        'inverse': True,
                        'position': 'right',
                        'axisLine': {'show': False},
                        'axisTick': {'show': False},
                        'axisLabel': {'show': True, 'fontSize': 10, 'color': '#333', 'margin': 5}
                    },
                    {
                        'type': 'category',
                        'gridIndex': 1,
                        'data': categories,
                        'inverse': True,
                        'position': 'left',
                        'axisLine': {'show': False},
                        'axisTick': {'show': False},
                        'axisLabel': {'show': False}
                    }
                ],
                'series': [
                    {
                        'name': '本店',
                        'type': 'bar',
                        'xAxisIndex': 0,
                        'yAxisIndex': 0,
                        'data': own_rates,
                        'itemStyle': {'color': '#3498db', 'borderRadius': [4, 0, 0, 4]},
                        'label': {'show': True, 'position': 'left', 'formatter': '{c}%', 'fontSize': 10, 'color': '#3498db'},
                        'barWidth': 16
                    },
                    {
                        'name': '竞对',
                        'type': 'bar',
                        'xAxisIndex': 1,
                        'yAxisIndex': 1,
                        'data': comp_rates,
                        'itemStyle': {'color': '#e74c3c', 'borderRadius': [0, 4, 4, 0]},
                        'label': {'show': True, 'position': 'right', 'formatter': '{c}%', 'fontSize': 10, 'color': '#e74c3c'},
                        'barWidth': 16
                    }
                ],
                'animationEasing': 'elasticOut',
                'animationDuration': 600
            },
            'media': [
                # 小屏幕 (<500px): 紧凑布局
                {
                    'query': {'maxWidth': 500},
                    'option': {
                        'title': {'textStyle': {'fontSize': 12}, 'top': 3},
                        'legend': {'top': 20, 'textStyle': {'fontSize': 9}},
                        'grid': [
                            {'left': '3%', 'right': '52%', 'top': 42, 'bottom': 10},
                            {'left': '52%', 'right': '3%', 'top': 42, 'bottom': 10}
                        ],
                        'xAxis': [
                            {'axisLabel': {'fontSize': 8}},
                            {'axisLabel': {'fontSize': 8}}
                        ],
                        'yAxis': [
                            {'axisLabel': {'fontSize': 8, 'margin': 3}},
                            {}
                        ],
                        'series': [
                            {'barWidth': 10, 'label': {'fontSize': 8}},
                            {'barWidth': 10, 'label': {'fontSize': 8}}
                        ]
                    }
                },
                # 中小屏幕 (500-700px): 适中布局
                {
                    'query': {'minWidth': 500, 'maxWidth': 700},
                    'option': {
                        'title': {'textStyle': {'fontSize': 13}},
                        'legend': {'top': 25, 'textStyle': {'fontSize': 10}},
                        'grid': [
                            {'left': '4%', 'right': '51%', 'top': 50, 'bottom': 12},
                            {'left': '51%', 'right': '4%', 'top': 50, 'bottom': 12}
                        ],
                        'series': [
                            {'barWidth': 14, 'label': {'fontSize': 9}},
                            {'barWidth': 14, 'label': {'fontSize': 9}}
                        ]
                    }
                },
                # 大屏幕 (>1000px): 宽松布局
                {
                    'query': {'minWidth': 1000},
                    'option': {
                        'title': {'textStyle': {'fontSize': 16}, 'top': 8},
                        'legend': {'top': 35, 'textStyle': {'fontSize': 13}},
                        'grid': [
                            {'left': '6%', 'right': left_right, 'top': 65, 'bottom': 20},
                            {'left': right_left, 'right': '6%', 'top': 65, 'bottom': 20}
                        ],
                        'yAxis': [
                            {'axisLabel': {'fontSize': 12, 'margin': 8}},
                            {}
                        ],
                        'series': [
                            {'barWidth': 20, 'label': {'fontSize': 11}},
                            {'barWidth': 20, 'label': {'fontSize': 11}}
                        ]
                    }
                },
                # 超大屏幕 (>1400px): 更宽松
                {
                    'query': {'minWidth': 1400},
                    'option': {
                        'title': {'textStyle': {'fontSize': 18}, 'top': 10},
                        'legend': {'top': 40, 'textStyle': {'fontSize': 14}},
                        'grid': [
                            {'left': '8%', 'right': '53%', 'top': 75, 'bottom': 25},
                            {'left': '53%', 'right': '8%', 'top': 75, 'bottom': 25}
                        ],
                        'yAxis': [
                            {'axisLabel': {'fontSize': 13, 'margin': 10}},
                            {}
                        ],
                        'series': [
                            {'barWidth': 24, 'label': {'fontSize': 12}},
                            {'barWidth': 24, 'label': {'fontSize': 12}}
                        ]
                    }
                }
            ]
        }
        
        # 移除lambda（JSON不支持），使用字符串格式化 - 安全删除
        if 'tooltip' in option['baseOption'] and 'formatter' in option['baseOption']['tooltip']:
            del option['baseOption']['tooltip']['formatter']
        
        return option
    
    @staticmethod
    def create_sales_efficiency_comparison_chart(own_data, competitor_data, category_col,
                                                 revenue_col, sku_col, title):
        """创建销售效率对比图表（单SKU平均销售额）- 已弃用
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            category_col: 分类列名
            revenue_col: 销售额列名
            sku_col: SKU数列名
            title: 图表标题
            
        Returns:
            Plotly Figure对象
        """
        # 计算单SKU平均销售额
        own_efficiency = own_data[revenue_col] / own_data[sku_col].replace(0, 1)
        comp_efficiency = competitor_data[revenue_col] / competitor_data[sku_col].replace(0, 1)
        
        fig = go.Figure()
        
        # 本店数据（负值，显示在左侧）
        fig.add_trace(go.Bar(
            name='本店',
            y=own_data[category_col],
            x=-own_efficiency,  # 负值
            orientation='h',
            marker_color='#3498db',
            text=[f"¥{v:,.0f}" for v in own_efficiency],
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate='%{y}<br>单SKU销售额: ¥%{text}<extra></extra>',
            customdata=own_efficiency
        ))
        
        # 竞对数据（正值，显示在右侧）
        fig.add_trace(go.Bar(
            name='竞对',
            y=competitor_data[category_col],
            x=comp_efficiency,
            orientation='h',
            marker_color='#e74c3c',
            text=[f"¥{v:,.0f}" for v in comp_efficiency],
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate='%{y}<br>单SKU销售额: ¥%{text}<extra></extra>',
            customdata=comp_efficiency
        ))
        
        # 动态计算高度
        data_length = len(own_data)
        chart_height = max(500, min(data_length * 30, 1200))
        
        # 计算最大值用于设置坐标轴范围
        max_val = max(own_efficiency.max(), comp_efficiency.max())
        tick_vals = [-max_val, -max_val*0.5, 0, max_val*0.5, max_val]
        tick_text = [f'¥{abs(v):,.0f}' for v in tick_vals]
        
        fig.update_layout(
            title=dict(text=title, font=dict(size=16)),
            barmode='overlay',
            xaxis=dict(
                title='单SKU平均销售额（售价）',
                tickvals=tick_vals,
                ticktext=tick_text,
                tickfont=dict(size=12),
                automargin=True
            ),
            yaxis=dict(
                title='一级分类',
                tickfont=dict(size=11),
                automargin=True
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1,
                font=dict(size=12)
            ),
            height=chart_height,
            margin=dict(l=150, r=100, t=100, b=80),
            bargap=0.15
        )
        
        return fig
    
    @staticmethod
    def create_revenue_comparison_chart(own_data, competitor_data, category_col, revenue_col, title, own_store_name='本店'):
        """创建销售额对比图表（ECharts分组柱状图 + 响应式）
        
        Args:
            own_data: 本店数据DataFrame
            competitor_data: 竞对数据DataFrame
            category_col: 分类列名
            revenue_col: 销售额列名
            title: 图表标题
            own_store_name: 本店名称（用于图例显示）
            
        Returns:
            ECharts配置字典
        """
        # 对齐数据
        own_temp = own_data[[category_col, revenue_col]].copy()
        own_temp.columns = [category_col, 'own_revenue']
        
        comp_temp = competitor_data[[category_col, revenue_col]].copy()
        comp_temp.columns = [category_col, 'comp_revenue']
        
        merged = own_temp.merge(comp_temp, on=category_col)
        
        if merged.empty:
            return {
                'title': {'text': '无共同分类数据', 'left': 'center', 'top': 'center'},
                'xAxis': {'show': False},
                'yAxis': {'show': False}
            }
        
        # 过滤掉双方销售额都为0的分类
        raw_categories = merged[category_col].tolist()
        raw_own_revenue = [float(v) if pd.notna(v) else 0 for v in merged['own_revenue'].tolist()]
        raw_comp_revenue = [float(v) if pd.notna(v) else 0 for v in merged['comp_revenue'].tolist()]
        
        categories, own_revenue, comp_revenue = [], [], []
        for i, cat in enumerate(raw_categories):
            if raw_own_revenue[i] > 0 or raw_comp_revenue[i] > 0:
                categories.append(cat)
                # 四舍五入到整数，避免浮点数精度问题
                own_revenue.append(round(raw_own_revenue[i]))
                comp_revenue.append(round(raw_comp_revenue[i]))
        
        if not categories:
            return {
                'title': {'text': '所有分类销售额为0', 'left': 'center', 'top': 'center'},
                'xAxis': {'show': False},
                'yAxis': {'show': False}
            }
        
        # 配色方案：紫色 vs 绿色（财务数据常用色）
        own_color = '#9B59B6'  # 紫色
        comp_color = '#27AE60'  # 绿色
        
        option = {
            'baseOption': {
                'toolbox': {
                    'show': True,
                    'right': 20,
                    'top': 5,
                    'feature': {
                        'saveAsImage': {
                            'type': 'png',
                            'pixelRatio': 4,
                            'title': '下载高清图',
                            'name': '销售额对比',
                            'backgroundColor': '#fff',
                            'excludeComponents': ['toolbox']
                        }
                    }
                },
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'shadow'},
                    'backgroundColor': 'rgba(50, 50, 50, 0.9)',
                    'textStyle': {'color': '#fff'}
                },
                'legend': {
                    'data': ['本店', '竞对'],
                    'top': 5,
                    'textStyle': {'fontSize': 12}
                },
                'grid': {'left': '5%', 'right': '5%', 'top': 40, 'bottom': 50, 'containLabel': True},
                'xAxis': {
                    'type': 'category',
                    'data': categories,
                    'axisLabel': {'rotate': 30, 'fontSize': 10, 'color': '#666'},
                    'axisLine': {'lineStyle': {'color': '#ddd'}},
                    'axisTick': {'show': False}
                },
                'yAxis': {
                    'type': 'value',
                    'name': '销售额（售价）',
                    'nameTextStyle': {'fontSize': 11, 'color': '#666'},
                    'axisLabel': {'fontSize': 10, 'color': '#666'},
                    'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#eee'}}
                },
                'series': [
                    {
                        'name': '本店',
                        'type': 'bar',
                        'data': own_revenue,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#BB8FCE'},
                                    {'offset': 1, 'color': own_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0]
                        },
                        'label': {
                            'show': True, 
                            'position': 'top', 
                            'fontSize': 9, 
                            'color': own_color
                        },
                        'barWidth': '35%',
                        'barGap': '10%'
                    },
                    {
                        'name': '竞对',
                        'type': 'bar',
                        'data': comp_revenue,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#58D68D'},
                                    {'offset': 1, 'color': comp_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0]
                        },
                        'label': {
                            'show': True, 
                            'position': 'top', 
                            'fontSize': 9, 
                            'color': comp_color
                        },
                        'barWidth': '35%'
                    }
                ],
                'animationEasing': 'elasticOut',
                'animationDuration': 800
            },
            'media': [
                {
                    'query': {'maxWidth': 500},
                    'option': {
                        'title': {'textStyle': {'fontSize': 12}},
                        'legend': {'top': 28, 'textStyle': {'fontSize': 9}},
                        'grid': {'top': 55, 'bottom': 60},
                        'xAxis': {'axisLabel': {'fontSize': 8, 'rotate': 45}},
                        'series': [
                            {'barWidth': '30%', 'label': {'fontSize': 7, 'show': False}},
                            {'barWidth': '30%', 'label': {'fontSize': 7, 'show': False}}
                        ]
                    }
                },
                {
                    'query': {'minWidth': 1000},
                    'option': {
                        'title': {'textStyle': {'fontSize': 17}},
                        'legend': {'top': 40, 'textStyle': {'fontSize': 13}},
                        'grid': {'top': 80, 'bottom': 100},
                        'xAxis': {'axisLabel': {'fontSize': 12}},
                        'series': [
                            {'barWidth': '38%', 'label': {'fontSize': 10}},
                            {'barWidth': '38%', 'label': {'fontSize': 10}}
                        ]
                    }
                }
            ]
        }
        
        # 移除lambda（JSON不支持）- 安全删除
        for series in option['baseOption']['series']:
            if 'label' in series and 'formatter' in series['label']:
                del series['label']['formatter']
        
        return option
    
    @staticmethod
    def create_discount_rate_mirror_chart(own_data, competitor_data, own_store_name='本店', competitor_name='竞对'):
        """创建折扣渗透率对比图表（ECharts镜像柱状图：本店在左，竞对在右）
        
        Args:
            own_data: 本店数据DataFrame（需包含一级分类、折扣SKU数、总SKU数）
            competitor_data: 竞对数据DataFrame
            own_store_name: 本店名称
            competitor_name: 竞对名称
            
        Returns:
            ECharts配置字典
        """
        try:
            # 提取本店数据
            own_categories = own_data['一级分类'].tolist()
            own_discount_sku = [int(v) if pd.notna(v) else 0 for v in own_data['美团一级分类折扣sku数']]
            own_total_sku = [int(v) if pd.notna(v) else 0 for v in own_data['美团一级分类sku数']]
            own_rates = [round(d / t * 100, 1) if t > 0 else 0 for d, t in zip(own_discount_sku, own_total_sku)]
            
            # 提取竞对数据
            comp_categories = competitor_data['一级分类'].tolist()
            comp_discount_sku = [int(v) if pd.notna(v) else 0 for v in competitor_data['美团一级分类折扣sku数']]
            comp_total_sku = [int(v) if pd.notna(v) else 0 for v in competitor_data['美团一级分类sku数']]
            comp_rates = [round(d / t * 100, 1) if t > 0 else 0 for d, t in zip(comp_discount_sku, comp_total_sku)]
            
            # 创建DataFrame用于合并
            own_df = pd.DataFrame({'category': own_categories, 'own_rate': own_rates, 'own_sku': own_total_sku})
            comp_df = pd.DataFrame({'category': comp_categories, 'comp_rate': comp_rates, 'comp_sku': comp_total_sku})
            
            # 合并数据（只保留共同分类）
            merged = own_df.merge(comp_df, on='category')
            
            if merged.empty:
                return {
                    'title': {'text': '无共同分类数据', 'left': 'center', 'top': 'center'},
                    'xAxis': {'show': False},
                    'yAxis': {'show': False}
                }
            
            categories = merged['category'].tolist()
            own_rates = merged['own_rate'].tolist()
            comp_rates = merged['comp_rate'].tolist()
            
            # 过滤掉双方都为0的分类
            filtered_data = [(cat, own, comp) for cat, own, comp in zip(categories, own_rates, comp_rates)
                             if own > 0 or comp > 0]
            if filtered_data:
                categories = [x[0] for x in filtered_data]
                own_rates = [x[1] for x in filtered_data]
                comp_rates = [x[2] for x in filtered_data]
            
            # 只显示TOP15分类（按本店折扣渗透率排序）
            if len(categories) > 15:
                combined = list(zip(categories, own_rates, comp_rates))
                combined.sort(key=lambda x: x[1], reverse=True)
                combined = combined[:15]
                categories = [x[0] for x in combined]
                own_rates = [x[1] for x in combined]
                comp_rates = [x[2] for x in combined]
            
            # 智能计算中间区域宽度
            max_label_len = max(len(str(cat)) for cat in categories) if categories else 4
            center_pct = min(max(max_label_len * 1.2 + 2, 8), 18)
            left_right = f'{50 - center_pct/2}%'
            right_left = f'{50 + center_pct/2}%'
            
            # 配色：本店用青绿色（与折扣分析一致），竞对用灰色
            own_color = '#1ABC9C'  # 青绿色
            comp_color = '#95a5a6'  # 灰色
            
            option = {
                'baseOption': {
                    'toolbox': {
                        'show': True,
                        'right': 20,
                        'top': 5,
                        'feature': {
                            'saveAsImage': {
                                'type': 'png',
                                'pixelRatio': 4,
                                'title': '下载高清图',
                                'name': '折扣渗透率对比',
                                'backgroundColor': '#fff',
                                'excludeComponents': ['toolbox']
                            }
                        }
                    },
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'shadow'}
                    },
                    'legend': {
                        'data': ['本店', '竞对'],
                        'top': 5,
                        'textStyle': {'fontSize': 11}
                    },
                    'grid': [
                        {'left': '5%', 'right': left_right, 'top': 35, 'bottom': 15, 'containLabel': False},
                        {'left': right_left, 'right': '5%', 'top': 35, 'bottom': 15, 'containLabel': False}
                    ],
                    'xAxis': [
                        {
                            'type': 'value',
                            'gridIndex': 0,
                            'inverse': True,
                            'axisLabel': {'formatter': '{value}%', 'fontSize': 10},
                            'splitLine': {'show': False},
                            'max': 100,
                            'axisLine': {'show': False}
                        },
                        {
                            'type': 'value',
                            'gridIndex': 1,
                            'axisLabel': {'formatter': '{value}%', 'fontSize': 10},
                            'splitLine': {'show': False},
                            'max': 100,
                            'axisLine': {'show': False}
                        }
                    ],
                    'yAxis': [
                        {
                            'type': 'category',
                            'gridIndex': 0,
                            'data': categories,
                            'inverse': True,
                            'position': 'right',
                            'axisLine': {'show': False},
                            'axisTick': {'show': False},
                            'axisLabel': {'show': True, 'fontSize': 10, 'color': '#333', 'margin': 5}
                        },
                        {
                            'type': 'category',
                            'gridIndex': 1,
                            'data': categories,
                            'inverse': True,
                            'position': 'left',
                            'axisLine': {'show': False},
                            'axisTick': {'show': False},
                            'axisLabel': {'show': False}
                        }
                    ],
                    'series': [
                        {
                            'name': '本店',
                            'type': 'bar',
                            'xAxisIndex': 0,
                            'yAxisIndex': 0,
                            'data': own_rates,
                            'itemStyle': {'color': own_color, 'borderRadius': [4, 0, 0, 4]},
                            'label': {'show': True, 'position': 'left', 'formatter': '{c}%', 'fontSize': 10, 'color': own_color},
                            'barWidth': 16
                        },
                        {
                            'name': '竞对',
                            'type': 'bar',
                            'xAxisIndex': 1,
                            'yAxisIndex': 1,
                            'data': comp_rates,
                            'itemStyle': {'color': comp_color, 'borderRadius': [0, 4, 4, 0]},
                            'label': {'show': True, 'position': 'right', 'formatter': '{c}%', 'fontSize': 10, 'color': comp_color},
                            'barWidth': 16
                        }
                    ],
                    'animationEasing': 'elasticOut',
                    'animationDuration': 600
                },
                'media': [
                    {
                        'query': {'maxWidth': 500},
                        'option': {
                            'legend': {'top': 20, 'textStyle': {'fontSize': 9}},
                            'grid': [
                                {'left': '3%', 'right': '52%', 'top': 42, 'bottom': 10},
                                {'left': '52%', 'right': '3%', 'top': 42, 'bottom': 10}
                            ],
                            'xAxis': [{'axisLabel': {'fontSize': 8}}, {'axisLabel': {'fontSize': 8}}],
                            'yAxis': [{'axisLabel': {'fontSize': 8, 'margin': 3}}, {}],
                            'series': [
                                {'barWidth': 10, 'label': {'fontSize': 8}},
                                {'barWidth': 10, 'label': {'fontSize': 8}}
                            ]
                        }
                    },
                    {
                        'query': {'minWidth': 1000},
                        'option': {
                            'legend': {'top': 35, 'textStyle': {'fontSize': 13}},
                            'grid': [
                                {'left': '6%', 'right': left_right, 'top': 65, 'bottom': 20},
                                {'left': right_left, 'right': '6%', 'top': 65, 'bottom': 20}
                            ],
                            'yAxis': [{'axisLabel': {'fontSize': 12, 'margin': 8}}, {}],
                            'series': [
                                {'barWidth': 20, 'label': {'fontSize': 11}},
                                {'barWidth': 20, 'label': {'fontSize': 11}}
                            ]
                        }
                    }
                ]
            }
            
            return option
            
        except Exception as e:
            logger.error(f"❌ 折扣渗透率对比图生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'title': {'text': f'图表生成失败: {str(e)}', 'left': 'center', 'top': 'center'},
                'xAxis': {'show': False},
                'yAxis': {'show': False}
            }
    
    @staticmethod
    def create_radar_chart(own_kpi, competitor_kpi, metrics):
        """创建雷达图（多维度对比）
        
        Args:
            own_kpi: 本店KPI字典
            competitor_kpi: 竞对KPI字典
            metrics: 要对比的指标列表
            
        Returns:
            Plotly Figure对象
        """
        # 归一化数据（0-100）
        own_values = []
        competitor_values = []
        
        for metric in metrics:
            own_val = own_kpi.get(metric, 0)
            comp_val = competitor_kpi.get(metric, 0)
            max_val = max(own_val, comp_val) or 1
            
            own_values.append((own_val / max_val) * 100)
            competitor_values.append((comp_val / max_val) * 100)
        
        fig = go.Figure()
        
        # 本店雷达
        fig.add_trace(go.Scatterpolar(
            r=own_values,
            theta=metrics,
            fill='toself',
            name='本店',
            line_color='#3498db'
        ))
        
        # 竞对雷达
        fig.add_trace(go.Scatterpolar(
            r=competitor_values,
            theta=metrics,
            fill='toself',
            name='竞对',
            line_color='#e74c3c'
        ))
        
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            height=400
        )
        
        return fig


# ==================== 对比视图辅助函数 ====================

def create_category_comparison_view(own_data, competitor_data, competitor_name, own_store_name='本店'):
    """创建一级分类动销分析对比视图
    
    Args:
        own_data: 本店分类数据DataFrame
        competitor_data: 竞对分类数据DataFrame
        competitor_name: 竞对门店名称
        own_store_name: 本店名称（用于图表显示）
        
    Returns:
        Dash组件
    """
    try:
        # 确保数据不为空
        if own_data.empty or competitor_data.empty:
            return html.Div([
                html.H5("⚠️ 数据不足", className="text-warning"),
                html.P("本店或竞对的分类数据为空，无法生成对比视图")
            ], className="p-3")
        
        # 获取列名（假设第一列是分类名）
        category_col = own_data.columns[0]
        
        # 查找所需的数据列
        # 本店和竞对使用相同的分析逻辑，列名应该一致
        def find_column_by_keywords(df, keywords):
            """通过关键词查找列"""
            for col in df.columns:
                col_str = str(col).lower()
                if any(kw.lower() in col_str for kw in keywords):
                    return col
            return None
        
        # 打印列名用于调试
        logger.info(f"📋 本店数据列({len(own_data)}行): {own_data.columns.tolist()}")
        logger.info(f"📋 竞对数据列({len(competitor_data)}行): {competitor_data.columns.tolist()}")
        
        # 查找动销率相关列（使用更精确的匹配）
        # 动销率列：美团一级分类动销率(类内)
        active_rate_col = find_column_by_keywords(own_data, ['动销率(类内)', '动销率（类内）'])
        if not active_rate_col:
            active_rate_col = find_column_by_keywords(own_data, ['动销比率'])
        
        # 去重SKU数列：美团一级分类去重SKU数(口径同动销率)
        total_sku_col = find_column_by_keywords(own_data, ['去重SKU数(口径', '去重SKU数（口径'])
        if not total_sku_col:
            total_sku_col = find_column_by_keywords(own_data, ['去重sku', 'dedup_sku'])
        
        # 动销SKU数列：美团一级分类动销sku数
        active_sku_col = find_column_by_keywords(own_data, ['动销sku数', '动销SKU数'])
        
        # 销售额列：优先售价销售额
        revenue_col = find_column_by_keywords(own_data, ['售价销售额'])
        if not revenue_col:
            revenue_col = find_column_by_keywords(own_data, ['销售额', 'revenue'])
        
        logger.info(f"📊 找到的列 - 动销率:{active_rate_col}, 去重SKU:{total_sku_col}, 动销SKU:{active_sku_col}, 销售额:{revenue_col}")
        
        components = []
        
        # 1. 动销商品数对比（ECharts分组柱状图）
        if active_sku_col:
            try:
                echarts_sku_option = ComparisonChartBuilder.create_active_sku_comparison_chart(
                    own_data,
                    competitor_data,
                    category_col,
                    active_sku_col,
                    f"📦 动销商品数对比 - {own_store_name} vs {competitor_name}",
                    own_store_name
                )
                components.append(
                    dbc.Col([
                        html.H5(f"📦 动销商品数对比 - {own_store_name} vs {competitor_name}", 
                               style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#2c3e50'}),
                        dash_echarts.DashECharts(
                            option=echarts_sku_option,
                            style={'height': '520px', 'width': '100%'}
                        )
                    ], width=12, className="mb-4", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                )
            except Exception as e:
                logger.error(f"❌ 动销商品数对比图生成失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 2. 动销率对比（ECharts镜像柱状图：本店在左，竞对在右）
        # 使用加权排序：动销率 × log₁₀(SKU数量 + 1)，避免小样本分类虚高
        if active_rate_col:
            try:
                echarts_rate_option = ComparisonChartBuilder.create_active_rate_mirror_chart(
                    own_data,
                    competitor_data,
                    category_col,
                    active_rate_col,
                    f"📊 动销率对比 - {own_store_name} vs {competitor_name}",
                    total_sku_col=total_sku_col,  # 传递SKU列用于加权排序
                    own_store_name=own_store_name
                )
                components.append(
                    dbc.Col([
                        html.H5(f"📊 动销率对比 - {own_store_name} vs {competitor_name}", 
                               style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#2c3e50'}),
                        dash_echarts.DashECharts(
                            option=echarts_rate_option,
                            style={'height': '550px', 'width': '100%'}
                        )
                    ], width=12, className="mb-4", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                )
            except Exception as e:
                logger.error(f"❌ 动销率对比图生成失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 3. 销售额对比（ECharts分组柱状图）- 增加高度
        if revenue_col:
            try:
                echarts_revenue_option = ComparisonChartBuilder.create_revenue_comparison_chart(
                    own_data,
                    competitor_data,
                    category_col,
                    revenue_col,
                    f"💰 销售额对比（售价） - {own_store_name} vs {competitor_name}",
                    own_store_name
                )
                components.append(
                    dbc.Col([
                        html.H5(f"💰 销售额对比（售价） - {own_store_name} vs {competitor_name}", 
                               style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#2c3e50'}),
                        dash_echarts.DashECharts(
                            option=echarts_revenue_option,
                            style={'height': '480px', 'width': '100%'}
                        )
                    ], width=12, className="mb-4", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                )
            except Exception as e:
                logger.error(f"❌ 销售额对比图生成失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        if not components:
            return html.Div([
                html.H5("⚠️ 无法生成对比图表", className="text-warning"),
                html.P("未找到可对比的数据列（动销率、SKU数、销售额）"),
                html.P(f"可用列名: {', '.join(own_data.columns.tolist())}", className="text-muted small")
            ], className="p-3")
        
        # 生成分类差异分析洞察
        try:
            # 将DataFrame转换为字典列表格式
            own_category_list = own_data.to_dict('records')
            competitor_category_list = competitor_data.to_dict('records')
            
            # 调用差异分析
            category_insights = DifferenceAnalyzer.analyze_category_differences(
                own_category_list, 
                competitor_category_list
            )
            
            # 生成改进建议
            recommendations = DifferenceAnalyzer.generate_recommendations(category_insights)
            
            # 合并洞察和建议
            all_insights = category_insights + recommendations
            
            # 创建差异分析面板
            if all_insights:
                insights_panel = DashboardComponents.create_insights_panel(all_insights)
            else:
                insights_panel = html.Div([
                    html.P("✅ 本店在所有分类上均领先或持平", className="text-success text-center p-3")
                ])
            
            # 添加差异分析区域
            components.append(
                dbc.Col([
                    html.Hr(className="my-4"),
                    html.H5("🔍 分类差异分析", className="mb-3"),
                    insights_panel
                ], width=12)
            )
        except Exception as e:
            logger.warning(f"⚠️ 分类差异分析生成失败: {e}")
            # 差异分析失败不影响主要图表显示
        
        return dbc.Row(components)
        
    except Exception as e:
        logger.error(f"❌ 创建分类对比视图失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return html.Div([
            html.H5("❌ 对比视图生成失败", className="text-danger"),
            html.P(f"错误信息: {str(e)}")
        ], className="p-3")


def create_discount_comparison_view(own_data, competitor_data, competitor_name, own_store_name='本店', all_competitors=None):
    """创建折扣商品供给与销售分析对比视图
    
    Args:
        own_data: 本店分类数据DataFrame
        competitor_data: 竞对分类数据DataFrame
        competitor_name: 当前对比的竞对门店名称
        own_store_name: 本店名称
        all_competitors: 所有选中的竞对列表（用于显示提示）
        
    Returns:
        Dash组件
    """
    try:
        # 确保数据不为空
        if own_data.empty or competitor_data.empty:
            return html.Div([
                html.H5("⚠️ 数据不足", className="text-warning"),
                html.P("本店或竞对的分类数据为空，无法生成对比视图")
            ], className="p-3")
        
        logger.info(f"💸 创建折扣对比视图: {own_store_name} vs {competitor_name}")
        logger.info(f"📋 本店数据列: {own_data.columns.tolist()}")
        logger.info(f"📋 竞对数据列: {competitor_data.columns.tolist()}")
        
        components = []
        
        # 如果有多个竞对，添加提示
        if all_competitors and len(all_competitors) > 1:
            components.append(
                dbc.Col([
                    html.P(f"💡 当前显示与 {competitor_name} 的对比，其他竞对: {', '.join(all_competitors[1:])}", 
                           className="text-muted small", style={'textAlign': 'center', 'marginBottom': '10px'})
                ], width=12)
            )
        
        # 1. 折扣渗透率对比（镜像柱状图）
        try:
            echarts_option = ComparisonChartBuilder.create_discount_rate_mirror_chart(
                own_data,
                competitor_data,
                own_store_name,
                competitor_name
            )
            components.append(
                dbc.Col([
                    html.H5(f"💸 折扣渗透率对比 - {own_store_name} vs {competitor_name}", 
                           style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#2c3e50'}),
                    dash_echarts.DashECharts(
                        option=echarts_option,
                        style={'height': '550px', 'width': '100%'}
                    )
                ], width=12, className="mb-4", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
            )
        except Exception as e:
            logger.error(f"❌ 折扣渗透率对比图生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 2. 整体折扣渗透率汇总卡片
        try:
            # 计算本店整体折扣渗透率
            own_discount_sku = sum([int(v) if pd.notna(v) else 0 for v in own_data['美团一级分类折扣sku数']])
            own_total_sku = sum([int(v) if pd.notna(v) else 0 for v in own_data['美团一级分类sku数']])
            own_overall_rate = round(own_discount_sku / own_total_sku * 100, 1) if own_total_sku > 0 else 0
            
            # 计算竞对整体折扣渗透率
            comp_discount_sku = sum([int(v) if pd.notna(v) else 0 for v in competitor_data['美团一级分类折扣sku数']])
            comp_total_sku = sum([int(v) if pd.notna(v) else 0 for v in competitor_data['美团一级分类sku数']])
            comp_overall_rate = round(comp_discount_sku / comp_total_sku * 100, 1) if comp_total_sku > 0 else 0
            
            # 计算差异
            rate_diff = round(own_overall_rate - comp_overall_rate, 1)
            sku_diff = own_discount_sku - comp_discount_sku
            
            # 创建汇总卡片
            def make_summary_card(title, own_val, comp_val, diff, is_pct=False):
                """创建汇总卡片"""
                diff_color = '#27ae60' if diff >= 0 else '#e74c3c'
                diff_text = f"+{diff}" if diff > 0 else str(diff)
                if is_pct:
                    diff_text += '%'
                    own_text = f"{own_val}%"
                    comp_text = f"{comp_val}%"
                else:
                    own_text = f"{own_val:,}"
                    comp_text = f"{comp_val:,}"
                
                return html.Div([
                    html.Div(title, style={'fontSize': '0.85rem', 'color': '#666', 'marginBottom': '5px'}),
                    html.Div([
                        html.Span("本店 ", style={'color': '#1ABC9C', 'fontSize': '0.8rem'}),
                        html.Span(own_text, style={'fontWeight': 'bold', 'fontSize': '1.1rem', 'color': '#1ABC9C'}),
                        html.Span(" vs ", style={'color': '#999', 'margin': '0 5px'}),
                        html.Span("竞对 ", style={'color': '#95a5a6', 'fontSize': '0.8rem'}),
                        html.Span(comp_text, style={'fontWeight': 'bold', 'fontSize': '1.1rem', 'color': '#95a5a6'}),
                    ]),
                    html.Div([
                        html.Span("差异: ", style={'color': '#999', 'fontSize': '0.8rem'}),
                        html.Span(diff_text, style={'color': diff_color, 'fontWeight': 'bold', 'fontSize': '1rem'})
                    ], style={'marginTop': '3px'})
                ], style={
                    'backgroundColor': '#f8f9fa',
                    'padding': '12px 15px',
                    'borderRadius': '8px',
                    'textAlign': 'center',
                    'flex': '1',
                    'margin': '0 8px'
                })
            
            summary_cards = html.Div([
                make_summary_card("整体折扣渗透率", own_overall_rate, comp_overall_rate, rate_diff, is_pct=True),
                make_summary_card("折扣SKU总数", own_discount_sku, comp_discount_sku, sku_diff),
                make_summary_card("SKU总数", own_total_sku, comp_total_sku, own_total_sku - comp_total_sku)
            ], style={
                'display': 'flex',
                'justifyContent': 'space-between',
                'marginBottom': '15px'
            })
            
            components.insert(0 if not all_competitors or len(all_competitors) <= 1 else 1, 
                dbc.Col([summary_cards], width=12, className="mb-3")
            )
            
        except Exception as e:
            logger.warning(f"⚠️ 折扣汇总卡片生成失败: {e}")
        
        if not components:
            return html.Div([
                html.H5("⚠️ 无法生成对比图表", className="text-warning"),
                html.P("未找到可对比的折扣数据列"),
                html.P(f"可用列名: {', '.join(own_data.columns.tolist())}", className="text-muted small")
            ], className="p-3")
        
        # 生成折扣分类差异分析洞察
        try:
            # 调用折扣差异分析
            discount_insights = DifferenceAnalyzer.analyze_discount_differences(
                own_data, 
                competitor_data
            )
            
            # 生成改进建议
            recommendations = DifferenceAnalyzer.generate_discount_recommendations(discount_insights)
            
            # 合并洞察和建议
            all_insights = discount_insights + recommendations
            
            # 创建差异分析面板
            if all_insights:
                insights_panel = DashboardComponents.create_insights_panel(all_insights)
            else:
                insights_panel = html.Div([
                    html.P("✅ 本店在所有分类的折扣渗透率上均领先或持平", className="text-success text-center p-3")
                ])
            
            # 添加差异分析区域
            components.append(
                dbc.Col([
                    html.Hr(className="my-4"),
                    html.H5("🔍 分类差异分析", className="mb-3"),
                    insights_panel
                ], width=12)
            )
        except Exception as e:
            logger.warning(f"⚠️ 折扣分类差异分析生成失败: {e}")
            # 差异分析失败不影响主要图表显示
        
        return dbc.Row(components)
        
    except Exception as e:
        logger.error(f"❌ 创建折扣对比视图失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return html.Div([
            html.H5("❌ 对比视图生成失败", className="text-danger"),
            html.P(f"错误信息: {str(e)}")
        ], className="p-3")


def create_multispec_comparison_view(own_data, competitor_data, competitor_name, own_store_name='本店'):
    """创建多规格商品供给分析对比视图
    
    Args:
        own_data: 本店分类数据DataFrame
        competitor_data: 竞对分类数据DataFrame
        competitor_name: 竞对门店名称
        own_store_name: 本店名称（用于图表显示）
        
    Returns:
        Dash组件
    """
    try:
        # 确保数据不为空
        if own_data.empty or competitor_data.empty:
            return html.Div([
                html.H5("⚠️ 数据不足", className="text-warning"),
                html.P("本店或竞对的分类数据为空，无法生成对比视图")
            ], className="p-3")
        
        # 获取列名（假设第一列是分类名）
        category_col = own_data.columns[0]
        
        # 查找多规格SKU数列
        def find_column_by_keywords(df, keywords):
            """通过关键词查找列"""
            for col in df.columns:
                col_str = str(col).lower()
                if any(kw.lower() in col_str for kw in keywords):
                    return col
            return None
        
        # 查找总SKU数列（B列）
        total_sku_col = find_column_by_keywords(own_data, ['总sku', 'sku数', 'total_sku'])
        if not total_sku_col and len(own_data.columns) > 1:
            total_sku_col = own_data.columns[1]  # 备用：使用第2列
        
        # 查找多规格SKU数列（C列）
        multispec_sku_col = find_column_by_keywords(own_data, ['多规格', 'multispec', '多规格sku'])
        if not multispec_sku_col and len(own_data.columns) > 2:
            multispec_sku_col = own_data.columns[2]  # 备用：使用第3列
        
        components = []
        
        # 1. 多规格SKU数量对比（镜像柱状图）
        if multispec_sku_col:
            try:
                fig_multispec_sku = ComparisonChartBuilder.create_mirror_bar_chart(
                    own_data,
                    competitor_data,
                    category_col,
                    multispec_sku_col,
                    f"🔀 多规格SKU数量对比 - {own_store_name} vs {competitor_name}",
                    own_store_name
                )
                components.append(
                    dbc.Col([
                        dcc.Graph(figure=fig_multispec_sku, config={'displayModeBar': False})
                    ], width=12, className="mb-4")
                )
            except Exception as e:
                logger.error(f"❌ 多规格SKU数量对比图生成失败: {e}")
        
        # 2. 多规格占比对比（堆叠对比柱状图）
        if total_sku_col and multispec_sku_col:
            try:
                # 计算本店的单规格和多规格占比
                own_total = own_data[total_sku_col].sum()
                own_multispec = own_data[multispec_sku_col].sum()
                own_single = own_total - own_multispec
                
                own_ratio_data = {
                    'single_spec_pct': own_single / own_total if own_total > 0 else 0,
                    'multi_spec_pct': own_multispec / own_total if own_total > 0 else 0
                }
                
                # 计算竞对的单规格和多规格占比
                comp_total = competitor_data[total_sku_col].sum()
                comp_multispec = competitor_data[multispec_sku_col].sum()
                comp_single = comp_total - comp_multispec
                
                comp_ratio_data = {
                    'single_spec_pct': comp_single / comp_total if comp_total > 0 else 0,
                    'multi_spec_pct': comp_multispec / comp_total if comp_total > 0 else 0
                }
                
                fig_ratio = ComparisonChartBuilder.create_stacked_comparison_bar(
                    own_ratio_data,
                    comp_ratio_data,
                    f"📊 多规格占比对比 - {own_store_name} vs {competitor_name}",
                    own_store_name
                )
                components.append(
                    dbc.Col([
                        dcc.Graph(figure=fig_ratio, config={'displayModeBar': False})
                    ], width=12, className="mb-4")
                )
            except Exception as e:
                logger.error(f"❌ 多规格占比对比图生成失败: {e}")
        
        if not components:
            return html.Div([
                html.H5("⚠️ 无法生成对比图表", className="text-warning"),
                html.P("未找到可对比的数据列（总SKU数、多规格SKU数）")
            ], className="p-3")
        
        return dbc.Row(components)
        
    except Exception as e:
        logger.error(f"❌ 创建多规格对比视图失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return html.Div([
            html.H5("❌ 对比视图生成失败", className="text-danger"),
            html.P(f"错误信息: {str(e)}")
        ], className="p-3")


def create_price_comparison_view(own_data, competitor_data, competitor_name, own_store_name='本店', all_competitors=None):
    """创建价格带分布分析对比视图
    
    Args:
        own_data: 本店价格带数据DataFrame
        competitor_data: 竞对价格带数据DataFrame
        competitor_name: 当前对比的竞对门店名称
        own_store_name: 本店名称
        all_competitors: 所有选中的竞对列表（用于显示提示）
        
    Returns:
        Dash组件
    """
    try:
        # 确保数据不为空
        if own_data.empty or competitor_data.empty:
            return html.Div([
                html.H5("⚠️ 数据不足", className="text-warning"),
                html.P("本店或竞对的价格带数据为空，无法生成对比视图")
            ], className="p-3")
        
        logger.info(f"💰 创建价格带对比视图: {own_store_name} vs {competitor_name}")
        logger.info(f"📋 本店数据列: {own_data.columns.tolist()}")
        logger.info(f"📋 竞对数据列: {competitor_data.columns.tolist()}")
        
        components = []
        
        # 如果有多个竞对，添加提示
        if all_competitors and len(all_competitors) > 1:
            components.append(
                dbc.Col([
                    html.P(f"💡 当前显示与 {competitor_name} 的对比，其他竞对: {', '.join(all_competitors[1:])}", 
                           className="text-muted small", style={'textAlign': 'center', 'marginBottom': '10px'})
                ], width=12)
            )
        
        # 查找列名
        def find_col(df, keywords):
            for col in df.columns:
                if any(kw in str(col) for kw in keywords):
                    return col
            return None
        
        price_col = own_data.columns[0]  # 第一列通常是价格带名称
        sku_col = find_col(own_data, ['sku数', 'SKU数', 'SKU', 'sku'])
        revenue_col = find_col(own_data, ['销售额', '售价销售额', '金额'])
        
        if not sku_col and len(own_data.columns) > 1:
            sku_col = own_data.columns[1]
        if not revenue_col and len(own_data.columns) > 2:
            revenue_col = own_data.columns[2]
        
        # 1. 价格带SKU数对比（分组柱状图）
        if sku_col and sku_col in competitor_data.columns:
            try:
                # 合并数据
                merged = pd.merge(
                    own_data[[price_col, sku_col]].rename(columns={sku_col: '本店SKU数'}),
                    competitor_data[[price_col, sku_col]].rename(columns={sku_col: '竞对SKU数'}),
                    on=price_col, how='outer'
                ).fillna(0)
                
                # 创建ECharts分组柱状图
                price_bands = merged[price_col].tolist()
                own_values = merged['本店SKU数'].tolist()
                comp_values = merged['竞对SKU数'].tolist()
                
                echarts_option = {
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'shadow'}
                    },
                    'legend': {
                        'data': [own_store_name, competitor_name],
                        'top': 10
                    },
                    'grid': {
                        'left': '3%', 'right': '4%', 'bottom': '15%', 'top': '60px',
                        'containLabel': True
                    },
                    'xAxis': {
                        'type': 'category',
                        'data': price_bands,
                        'axisLabel': {'rotate': 30, 'fontSize': 11}
                    },
                    'yAxis': {
                        'type': 'value',
                        'name': 'SKU数量'
                    },
                    'series': [
                        {
                            'name': own_store_name,
                            'type': 'bar',
                            'data': own_values,
                            'itemStyle': {'color': '#1ABC9C'}
                        },
                        {
                            'name': competitor_name,
                            'type': 'bar',
                            'data': comp_values,
                            'itemStyle': {'color': '#95a5a6'}
                        }
                    ]
                }
                
                components.append(
                    dbc.Col([
                        html.H5(f"📊 价格带SKU数对比 - {own_store_name} vs {competitor_name}", 
                               style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#2c3e50'}),
                        dash_echarts.DashECharts(
                            option=echarts_option,
                            style={'height': '450px', 'width': '100%'}
                        )
                    ], width=12, className="mb-4", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                )
            except Exception as e:
                logger.error(f"❌ 价格带SKU数对比图生成失败: {e}")
        
        # 2. 价格带销售额对比（分组柱状图）
        if revenue_col and revenue_col in competitor_data.columns:
            try:
                merged_rev = pd.merge(
                    own_data[[price_col, revenue_col]].rename(columns={revenue_col: '本店销售额'}),
                    competitor_data[[price_col, revenue_col]].rename(columns={revenue_col: '竞对销售额'}),
                    on=price_col, how='outer'
                ).fillna(0)
                
                price_bands = merged_rev[price_col].tolist()
                own_rev = merged_rev['本店销售额'].tolist()
                comp_rev = merged_rev['竞对销售额'].tolist()
                
                echarts_rev_option = {
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'shadow'},
                        'formatter': '''function(params) {
                            var result = params[0].axisValue + '<br/>';
                            params.forEach(function(item) {
                                result += item.marker + item.seriesName + ': ¥' + item.value.toLocaleString() + '<br/>';
                            });
                            return result;
                        }'''
                    },
                    'legend': {
                        'data': [own_store_name, competitor_name],
                        'top': 10
                    },
                    'grid': {
                        'left': '3%', 'right': '4%', 'bottom': '15%', 'top': '60px',
                        'containLabel': True
                    },
                    'xAxis': {
                        'type': 'category',
                        'data': price_bands,
                        'axisLabel': {'rotate': 30, 'fontSize': 11}
                    },
                    'yAxis': {
                        'type': 'value',
                        'name': '销售额(元)',
                        'axisLabel': {
                            'formatter': '''function(value) {
                                if (value >= 10000) return (value/10000).toFixed(1) + '万';
                                return value;
                            }'''
                        }
                    },
                    'series': [
                        {
                            'name': own_store_name,
                            'type': 'bar',
                            'data': own_rev,
                            'itemStyle': {'color': '#3498db'}
                        },
                        {
                            'name': competitor_name,
                            'type': 'bar',
                            'data': comp_rev,
                            'itemStyle': {'color': '#e74c3c'}
                        }
                    ]
                }
                
                components.append(
                    dbc.Col([
                        html.H5(f"💰 价格带销售额对比 - {own_store_name} vs {competitor_name}", 
                               style={'textAlign': 'center', 'marginBottom': '10px', 'color': '#2c3e50'}),
                        dash_echarts.DashECharts(
                            option=echarts_rev_option,
                            style={'height': '450px', 'width': '100%'}
                        )
                    ], width=12, className="mb-4", style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
                )
            except Exception as e:
                logger.error(f"❌ 价格带销售额对比图生成失败: {e}")
        
        # 3. 汇总卡片
        try:
            own_total_sku = own_data[sku_col].sum() if sku_col else 0
            comp_total_sku = competitor_data[sku_col].sum() if sku_col else 0
            own_total_rev = own_data[revenue_col].sum() if revenue_col else 0
            comp_total_rev = competitor_data[revenue_col].sum() if revenue_col else 0
            
            sku_diff = int(own_total_sku - comp_total_sku)
            rev_diff = own_total_rev - comp_total_rev
            
            def make_summary_card(title, own_val, comp_val, diff, is_currency=False):
                diff_color = '#27ae60' if diff >= 0 else '#e74c3c'
                if is_currency:
                    own_text = f"¥{own_val:,.0f}"
                    comp_text = f"¥{comp_val:,.0f}"
                    diff_text = f"+¥{diff:,.0f}" if diff >= 0 else f"¥{diff:,.0f}"
                else:
                    own_text = f"{int(own_val):,}"
                    comp_text = f"{int(comp_val):,}"
                    diff_text = f"+{int(diff):,}" if diff >= 0 else f"{int(diff):,}"
                
                return html.Div([
                    html.Div(title, style={'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '5px'}),
                    html.Div([
                        html.Span(f"本店: {own_text}", style={'color': '#1ABC9C', 'fontWeight': 'bold'}),
                        html.Span(" vs ", style={'color': '#95a5a6', 'margin': '0 5px'}),
                        html.Span(f"竞对: {comp_text}", style={'color': '#95a5a6'})
                    ], style={'fontSize': '14px'}),
                    html.Div(f"差异: {diff_text}", style={'fontSize': '13px', 'color': diff_color, 'fontWeight': 'bold', 'marginTop': '3px'})
                ], style={'backgroundColor': '#f8f9fa', 'padding': '12px', 'borderRadius': '8px', 'textAlign': 'center', 'flex': '1', 'margin': '0 5px'})
            
            summary_cards = html.Div([
                make_summary_card("SKU总数", own_total_sku, comp_total_sku, sku_diff),
                make_summary_card("销售额总计", own_total_rev, comp_total_rev, rev_diff, is_currency=True)
            ], style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '15px'})
            
            components.insert(0 if not all_competitors or len(all_competitors) <= 1 else 1, 
                dbc.Col([summary_cards], width=12)
            )
        except Exception as e:
            logger.warning(f"⚠️ 价格带汇总卡片生成失败: {e}")
        
        if not components:
            return html.Div([
                html.H5("⚠️ 无法生成对比图表", className="text-warning"),
                html.P("未找到可对比的价格带数据列"),
                html.P(f"可用列名: {', '.join(own_data.columns.tolist())}", className="text-muted small")
            ], className="p-3")
        
        # 生成价格带分类差异分析洞察
        try:
            # 调用价格带差异分析
            price_insights = DifferenceAnalyzer.analyze_price_differences(
                own_data, 
                competitor_data
            )
            
            # 生成改进建议
            recommendations = DifferenceAnalyzer.generate_price_recommendations(price_insights)
            
            # 合并洞察和建议
            all_insights = price_insights + recommendations
            
            # 创建差异分析面板
            if all_insights:
                insights_panel = DashboardComponents.create_insights_panel(all_insights)
            else:
                insights_panel = html.Div([
                    html.P("✅ 本店在所有价格带上均领先或持平", className="text-success text-center p-3")
                ])
            
            # 添加差异分析区域
            components.append(
                dbc.Col([
                    html.Hr(className="my-4"),
                    html.H5("🔍 价格带差异分析", className="mb-3"),
                    insights_panel
                ], width=12)
            )
        except Exception as e:
            logger.warning(f"⚠️ 价格带差异分析生成失败: {e}")
            # 差异分析失败不影响主要图表显示
        
        return dbc.Row(components)
        
    except Exception as e:
        logger.error(f"❌ 创建价格带对比视图失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return html.Div([
            html.H5("❌ 对比视图生成失败", className="text-danger"),
            html.P(f"错误信息: {str(e)}")
        ], className="p-3")


class DifferenceAnalyzer:
    """差异分析生成器 - 自动生成本店与竞对的差异分析洞察
    
    该类提供静态方法用于分析本店与竞对门店在各个维度的差异，
    并生成易于理解的洞察文本和改进建议。
    
    主要功能：
    - analyze_kpi_differences: 分析KPI核心指标差异
    - analyze_category_differences: 分析分类级别差异
    - generate_recommendations: 生成改进建议
    - format_insight: 格式化洞察文本
    """
    
    @staticmethod
    def analyze_kpi_differences(own_kpi, competitor_kpi):
        """分析KPI差异，生成差异洞察
        
        对比4个核心指标：销售额、SKU数、动销率、毛利率
        只有竞对>本店时才生成洞察
        
        Args:
            own_kpi: 本店KPI字典
            competitor_kpi: 竞对KPI字典
            
        Returns:
            洞察列表（最多3条），每条洞察格式为：
            {
                'icon': str,  # 图标
                'text': str,  # 洞察文本
                'level': str  # 级别：warning, info, success
            }
        """
        insights = []
        
        # 定义关键指标及其属性
        key_metrics = [
            {
                'key': '总销售额(去重后)', 
                'name': '销售额', 
                'format': 'currency', 
                'higher_is_better': True,
                'priority': 1  # 优先级，数字越小越重要
            },
            {
                'key': '总SKU数(去重后)', 
                'name': 'SKU数', 
                'format': 'number', 
                'higher_is_better': True,
                'priority': 2
            },
            {
                'key': '动销率', 
                'name': '动销率', 
                'format': 'percent', 
                'higher_is_better': True,
                'priority': 3
            },
            {
                'key': '平均毛利率', 
                'name': '毛利率', 
                'format': 'percent', 
                'higher_is_better': True,
                'priority': 4
            }
        ]
        
        for metric in key_metrics:
            # 获取本店和竞对的值
            own_val = own_kpi.get(metric['key'], 0)
            comp_val = competitor_kpi.get(metric['key'], 0)
            
            # 处理None值和类型转换
            try:
                own_val = float(own_val) if own_val is not None else 0
                comp_val = float(comp_val) if comp_val is not None else 0
            except (ValueError, TypeError):
                own_val = 0
                comp_val = 0
            
            # 跳过竞对值为0的情况（无法计算百分比）
            if comp_val == 0:
                continue
            
            # 计算差异
            diff = own_val - comp_val
            diff_pct = (diff / comp_val) * 100
            
            # 只有竞对领先时才生成洞察（竞对 > 本店）
            if comp_val > own_val:
                insight_text = DifferenceAnalyzer.format_insight(
                    metric['name'], 
                    own_val, 
                    comp_val, 
                    metric['format']
                )
                
                insights.append({
                    'icon': '⚠️',
                    'text': insight_text,
                    'level': 'warning',
                    'priority': metric['priority']
                })
        
        # 按优先级排序，返回最多3条
        insights.sort(key=lambda x: x.get('priority', 999))
        return insights[:3]
    
    @staticmethod
    def format_insight(metric_name, own_value, competitor_value, format_type):
        """格式化洞察文本
        
        Args:
            metric_name: 指标名称
            own_value: 本店值
            competitor_value: 竞对值
            format_type: 格式类型 ('currency', 'percent', 'number')
            
        Returns:
            格式化的洞察文本
        """
        diff = abs(competitor_value - own_value)
        
        # 计算差异百分比
        if own_value != 0:
            diff_pct = abs((competitor_value - own_value) / own_value) * 100
        else:
            diff_pct = 100.0  # 本店为0时，差异为100%
        
        # 根据格式类型生成文本
        if format_type == 'currency':
            insight_text = f"竞对的{metric_name}比本店高 ¥{diff:,.0f}（{diff_pct:.1f}%）"
        elif format_type == 'percent':
            # 百分比指标，差异也用百分点表示
            diff_points = abs(competitor_value - own_value) * 100
            insight_text = f"竞对的{metric_name}比本店高 {diff_points:.1f}个百分点（{diff_pct:.1f}%）"
        else:  # number
            insight_text = f"竞对的{metric_name}比本店多 {diff:,.0f}个（{diff_pct:.1f}%）"
        
        return insight_text
    
    @staticmethod
    def analyze_category_differences(own_category, competitor_category):
        """分析分类差异，生成分类级别的差异洞察
        
        使用加权排序：动销率差异 × log₁₀(SKU数+1)，避免小样本分类虚高。
        只分析SKU数 >= 30 的分类，排除"熟食/鲜食""海鲜水产"等小样本分类。
        
        Args:
            own_category: 本店分类数据列表
            competitor_category: 竞对分类数据列表
            
        Returns:
            洞察列表（最多4条）
        """
        import math
        insights = []
        
        own_df = pd.DataFrame(own_category)
        comp_df = pd.DataFrame(competitor_category)
        
        if own_df.empty or comp_df.empty:
            return insights
        
        def find_col(df, keywords):
            for col in df.columns:
                if any(kw in str(col) for kw in keywords):
                    return col
            return None
        
        category_col = own_df.columns[0]
        rate_col = find_col(own_df, ['动销率(类内)', '动销率（类内）', '动销比率'])
        total_sku_col = find_col(own_df, ['去重SKU数(口径', '去重SKU数（口径', '去重sku'])
        active_sku_col = find_col(own_df, ['动销sku数', '动销SKU数'])
        
        # 最小SKU数阈值，过滤小样本分类
        MIN_SKU_THRESHOLD = 30
        
        # 1. 分析动销率差异（加权排序）
        if rate_col and rate_col in comp_df.columns:
            try:
                cols_own = [category_col, rate_col]
                cols_comp = [category_col, rate_col]
                if total_sku_col and total_sku_col in own_df.columns:
                    cols_own.append(total_sku_col)
                if total_sku_col and total_sku_col in comp_df.columns:
                    cols_comp.append(total_sku_col)
                
                merged = pd.merge(
                    own_df[cols_own], comp_df[cols_comp],
                    on=category_col, suffixes=('_own', '_comp')
                )
                
                own_rate_col = f'{rate_col}_own'
                comp_rate_col = f'{rate_col}_comp'
                
                # 转换为百分比
                merged[own_rate_col] = merged[own_rate_col].apply(lambda x: float(x) * 100 if float(x) <= 1 else float(x))
                merged[comp_rate_col] = merged[comp_rate_col].apply(lambda x: float(x) * 100 if float(x) <= 1 else float(x))
                merged['rate_diff'] = merged[own_rate_col] - merged[comp_rate_col]
                
                # 过滤小样本分类（双方SKU数都要 >= 阈值）
                if total_sku_col:
                    own_sku_col = f'{total_sku_col}_own'
                    comp_sku_col = f'{total_sku_col}_comp'
                    if own_sku_col in merged.columns and comp_sku_col in merged.columns:
                        merged = merged[(merged[own_sku_col] >= MIN_SKU_THRESHOLD) | (merged[comp_sku_col] >= MIN_SKU_THRESHOLD)]
                        # 计算加权分数：差异绝对值 × log₁₀(平均SKU数+1)
                        merged['avg_sku'] = (merged[own_sku_col] + merged[comp_sku_col]) / 2
                        merged['weight_score'] = merged['rate_diff'].abs() * merged['avg_sku'].apply(lambda x: math.log10(x + 1))
                
                if merged.empty:
                    return insights
                
                # 找出本店落后的分类（动销率差异 < -5%，按加权分数排序）
                lagging = merged[merged['rate_diff'] < -5]
                if 'weight_score' in lagging.columns:
                    lagging = lagging.nlargest(2, 'weight_score')
                else:
                    lagging = lagging.nsmallest(2, 'rate_diff')
                
                for _, row in lagging.iterrows():
                    cat = row[category_col]
                    own_rate = row[own_rate_col]
                    comp_rate = row[comp_rate_col]
                    diff = abs(row['rate_diff'])
                    sku_info = ""
                    if total_sku_col and f'{total_sku_col}_own' in row:
                        sku_info = f"，SKU数{int(row[f'{total_sku_col}_own'])}"
                    insights.append({
                        'icon': '📉',
                        'text': f'"{cat}"动销率落后{diff:.1f}%（本店{own_rate:.1f}% vs 竞对{comp_rate:.1f}%{sku_info}）',
                        'level': 'warning'
                    })
                
                # 找出本店领先的分类
                leading = merged[merged['rate_diff'] > 5]
                if 'weight_score' in leading.columns:
                    leading = leading.nlargest(2, 'weight_score')
                else:
                    leading = leading.nlargest(2, 'rate_diff')
                
                for _, row in leading.iterrows():
                    cat = row[category_col]
                    own_rate = row[own_rate_col]
                    comp_rate = row[comp_rate_col]
                    diff = row['rate_diff']
                    sku_info = ""
                    if total_sku_col and f'{total_sku_col}_own' in row:
                        sku_info = f"，SKU数{int(row[f'{total_sku_col}_own'])}"
                    insights.append({
                        'icon': '📈',
                        'text': f'"{cat}"动销率领先{diff:.1f}%（本店{own_rate:.1f}% vs 竞对{comp_rate:.1f}%{sku_info}）',
                        'level': 'success'
                    })
            except Exception as e:
                logger.warning(f"动销率差异分析失败: {e}")
        
        # 2. 分析动销SKU数差异（只分析大分类）
        if active_sku_col and active_sku_col in comp_df.columns and len(insights) < 4:
            try:
                merged = pd.merge(
                    own_df[[category_col, active_sku_col]],
                    comp_df[[category_col, active_sku_col]],
                    on=category_col, suffixes=('_own', '_comp')
                )
                
                own_col = f'{active_sku_col}_own'
                comp_col = f'{active_sku_col}_comp'
                # 只分析双方动销SKU数都 >= 20 的分类
                merged = merged[(merged[own_col] >= 20) | (merged[comp_col] >= 20)]
                merged['sku_diff'] = merged[comp_col] - merged[own_col]
                
                comp_leading = merged[merged['sku_diff'] > 30].nlargest(1, 'sku_diff')
                for _, row in comp_leading.iterrows():
                    cat = row[category_col]
                    own_sku = int(row[own_col])
                    comp_sku = int(row[comp_col])
                    insights.append({
                        'icon': '📊',
                        'text': f'"{cat}"竞对动销SKU领先（竞对{comp_sku}个 vs 本店{own_sku}个）',
                        'level': 'info'
                    })
            except Exception as e:
                logger.warning(f"动销SKU差异分析失败: {e}")
        
        return insights[:4]
    
    @staticmethod
    def generate_recommendations(insights):
        """基于洞察内容生成改进建议
        
        根据洞察文本中的关键词，生成针对性的改进建议。
        
        规则：
        - 包含"SKU数"→建议增加商品数量
        - 包含"动销率"→建议优化滞销商品
        - 包含"销售额"→建议加大促销力度
        
        Args:
            insights: 洞察列表，每项为字典，包含'text'字段
            
        Returns:
            建议列表（最多2条），每条建议格式为：
            {
                'icon': str,  # 图标
                'text': str,  # 建议文本
                'level': str  # 级别：success
            }
        """
        recommendations = []
        seen_types = set()  # 避免重复类型的建议
        
        for insight in insights:
            text = insight.get('text', '')
            
            # 基于洞察内容生成建议
            if 'SKU数' in text or 'SKU' in text:
                if 'sku' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：增加该分类的商品数量，提升品类丰富度',
                        'level': 'success'
                    })
                    seen_types.add('sku')
            elif '动销率' in text:
                if 'turnover' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：优化滞销商品，提升整体动销率',
                        'level': 'success'
                    })
                    seen_types.add('turnover')
            elif '销售额' in text:
                if 'sales' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：加大促销力度，提升销售额',
                        'level': 'success'
                    })
                    seen_types.add('sales')
            
            # 最多返回2条建议
            if len(recommendations) >= 2:
                break
        
        return recommendations[:2]
    
    @staticmethod
    def analyze_discount_differences(own_category, competitor_category):
        """分析折扣渗透率差异，生成分类级别的差异洞察
        
        分析本店与竞对在各分类的折扣渗透率差异，识别需要改进的分类。
        
        Args:
            own_category: 本店分类数据列表或DataFrame
            competitor_category: 竞对分类数据列表或DataFrame
            
        Returns:
            洞察列表（最多4条）
        """
        import math
        insights = []
        
        own_df = pd.DataFrame(own_category) if not isinstance(own_category, pd.DataFrame) else own_category
        comp_df = pd.DataFrame(competitor_category) if not isinstance(competitor_category, pd.DataFrame) else competitor_category
        
        if own_df.empty or comp_df.empty:
            return insights
        
        def find_col(df, keywords):
            for col in df.columns:
                if any(kw in str(col) for kw in keywords):
                    return col
            return None
        
        category_col = own_df.columns[0]
        discount_sku_col = find_col(own_df, ['折扣sku数', '折扣SKU数', '折扣商品数'])
        total_sku_col = find_col(own_df, ['一级分类sku数', '一级分类SKU数', 'sku数', 'SKU数'])
        
        if not discount_sku_col or not total_sku_col:
            return insights
        
        if discount_sku_col not in comp_df.columns or total_sku_col not in comp_df.columns:
            return insights
        
        try:
            # 合并数据
            merged = pd.merge(
                own_df[[category_col, discount_sku_col, total_sku_col]],
                comp_df[[category_col, discount_sku_col, total_sku_col]],
                on=category_col, suffixes=('_own', '_comp')
            )
            
            if merged.empty:
                return insights
            
            own_discount_col = f'{discount_sku_col}_own'
            comp_discount_col = f'{discount_sku_col}_comp'
            own_total_col = f'{total_sku_col}_own'
            comp_total_col = f'{total_sku_col}_comp'
            
            # 计算折扣渗透率
            merged['own_rate'] = merged.apply(
                lambda r: round(r[own_discount_col] / r[own_total_col] * 100, 1) if r[own_total_col] > 0 else 0, axis=1
            )
            merged['comp_rate'] = merged.apply(
                lambda r: round(r[comp_discount_col] / r[comp_total_col] * 100, 1) if r[comp_total_col] > 0 else 0, axis=1
            )
            merged['rate_diff'] = merged['own_rate'] - merged['comp_rate']
            
            # 计算加权分数（差异 × log(SKU数+1)）
            merged['avg_sku'] = (merged[own_total_col] + merged[comp_total_col]) / 2
            merged['weight_score'] = merged['rate_diff'].abs() * merged['avg_sku'].apply(lambda x: math.log10(x + 1))
            
            # 过滤小样本分类（SKU数 >= 20）
            merged = merged[(merged[own_total_col] >= 20) | (merged[comp_total_col] >= 20)]
            
            if merged.empty:
                return insights
            
            # 找出本店落后的分类（折扣渗透率差异 < -5%）
            lagging = merged[merged['rate_diff'] < -5].nlargest(2, 'weight_score')
            for _, row in lagging.iterrows():
                cat = row[category_col]
                own_rate = row['own_rate']
                comp_rate = row['comp_rate']
                diff = abs(row['rate_diff'])
                insights.append({
                    'icon': '📉',
                    'text': f'"{cat}"折扣渗透率落后{diff:.1f}%（本店{own_rate:.1f}% vs 竞对{comp_rate:.1f}%）',
                    'level': 'warning'
                })
            
            # 找出本店领先的分类（折扣渗透率差异 > 5%）
            leading = merged[merged['rate_diff'] > 5].nlargest(2, 'weight_score')
            for _, row in leading.iterrows():
                cat = row[category_col]
                own_rate = row['own_rate']
                comp_rate = row['comp_rate']
                diff = row['rate_diff']
                insights.append({
                    'icon': '📈',
                    'text': f'"{cat}"折扣渗透率领先{diff:.1f}%（本店{own_rate:.1f}% vs 竞对{comp_rate:.1f}%）',
                    'level': 'success'
                })
            
            # 分析折扣SKU数差异
            if len(insights) < 4:
                merged['sku_diff'] = merged[comp_discount_col] - merged[own_discount_col]
                comp_leading = merged[merged['sku_diff'] > 10].nlargest(1, 'sku_diff')
                for _, row in comp_leading.iterrows():
                    cat = row[category_col]
                    own_sku = int(row[own_discount_col])
                    comp_sku = int(row[comp_discount_col])
                    insights.append({
                        'icon': '📊',
                        'text': f'"{cat}"竞对折扣SKU领先（竞对{comp_sku}个 vs 本店{own_sku}个）',
                        'level': 'info'
                    })
            
        except Exception as e:
            logger.warning(f"折扣差异分析失败: {e}")
        
        return insights[:4]
    
    @staticmethod
    def generate_discount_recommendations(insights):
        """基于折扣洞察生成改进建议
        
        Args:
            insights: 折扣洞察列表
            
        Returns:
            建议列表（最多2条）
        """
        recommendations = []
        seen_types = set()
        
        for insight in insights:
            text = insight.get('text', '')
            
            if '折扣渗透率落后' in text:
                if 'rate' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：增加该分类的折扣商品数量，提升折扣渗透率',
                        'level': 'success'
                    })
                    seen_types.add('rate')
            elif '折扣SKU领先' in text or '折扣SKU' in text:
                if 'sku' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：扩大折扣商品覆盖范围，增加促销力度',
                        'level': 'success'
                    })
                    seen_types.add('sku')
            
            if len(recommendations) >= 2:
                break
        
        return recommendations[:2]
    
    @staticmethod
    def analyze_price_differences(own_data, competitor_data):
        """分析价格带差异，生成价格带级别的差异洞察
        
        分析本店与竞对在各价格带的SKU数和销售额差异。
        
        Args:
            own_data: 本店价格带数据DataFrame
            competitor_data: 竞对价格带数据DataFrame
            
        Returns:
            洞察列表（最多4条）
        """
        import math
        insights = []
        
        own_df = pd.DataFrame(own_data) if not isinstance(own_data, pd.DataFrame) else own_data
        comp_df = pd.DataFrame(competitor_data) if not isinstance(competitor_data, pd.DataFrame) else competitor_data
        
        if own_df.empty or comp_df.empty:
            return insights
        
        def find_col(df, keywords):
            for col in df.columns:
                if any(kw in str(col) for kw in keywords):
                    return col
            return None
        
        price_col = own_df.columns[0]  # 第一列是价格带名称
        sku_col = find_col(own_df, ['sku数', 'SKU数', 'SKU', 'sku'])
        revenue_col = find_col(own_df, ['销售额', '售价销售额', '金额'])
        
        if not sku_col and len(own_df.columns) > 1:
            sku_col = own_df.columns[1]
        if not revenue_col and len(own_df.columns) > 2:
            revenue_col = own_df.columns[2]
        
        try:
            # 1. 分析SKU数差异
            if sku_col and sku_col in comp_df.columns:
                merged = pd.merge(
                    own_df[[price_col, sku_col]],
                    comp_df[[price_col, sku_col]],
                    on=price_col, suffixes=('_own', '_comp')
                )
                
                if not merged.empty:
                    own_sku_col = f'{sku_col}_own'
                    comp_sku_col = f'{sku_col}_comp'
                    merged['sku_diff'] = merged[own_sku_col] - merged[comp_sku_col]
                    merged['sku_diff_pct'] = merged.apply(
                        lambda r: (r['sku_diff'] / r[comp_sku_col] * 100) if r[comp_sku_col] > 0 else 0, axis=1
                    )
                    
                    # 找出本店落后的价格带（SKU数差异 < -20%）
                    lagging = merged[merged['sku_diff_pct'] < -20].nsmallest(2, 'sku_diff_pct')
                    for _, row in lagging.iterrows():
                        price_band = row[price_col]
                        own_sku = int(row[own_sku_col])
                        comp_sku = int(row[comp_sku_col])
                        diff_pct = abs(row['sku_diff_pct'])
                        insights.append({
                            'icon': '📉',
                            'text': f'"{price_band}"SKU数落后{diff_pct:.0f}%（本店{own_sku}个 vs 竞对{comp_sku}个）',
                            'level': 'warning'
                        })
                    
                    # 找出本店领先的价格带（SKU数差异 > 20%）
                    leading = merged[merged['sku_diff_pct'] > 20].nlargest(2, 'sku_diff_pct')
                    for _, row in leading.iterrows():
                        price_band = row[price_col]
                        own_sku = int(row[own_sku_col])
                        comp_sku = int(row[comp_sku_col])
                        diff_pct = row['sku_diff_pct']
                        insights.append({
                            'icon': '📈',
                            'text': f'"{price_band}"SKU数领先{diff_pct:.0f}%（本店{own_sku}个 vs 竞对{comp_sku}个）',
                            'level': 'success'
                        })
            
            # 2. 分析销售额差异
            if revenue_col and revenue_col in comp_df.columns and len(insights) < 4:
                merged_rev = pd.merge(
                    own_df[[price_col, revenue_col]],
                    comp_df[[price_col, revenue_col]],
                    on=price_col, suffixes=('_own', '_comp')
                )
                
                if not merged_rev.empty:
                    own_rev_col = f'{revenue_col}_own'
                    comp_rev_col = f'{revenue_col}_comp'
                    merged_rev['rev_diff'] = merged_rev[own_rev_col] - merged_rev[comp_rev_col]
                    
                    # 找出销售额差异最大的价格带
                    comp_leading = merged_rev[merged_rev['rev_diff'] < 0].nsmallest(1, 'rev_diff')
                    for _, row in comp_leading.iterrows():
                        price_band = row[price_col]
                        own_rev = row[own_rev_col]
                        comp_rev = row[comp_rev_col]
                        diff = abs(row['rev_diff'])
                        insights.append({
                            'icon': '💰',
                            'text': f'"{price_band}"竞对销售额领先¥{diff:,.0f}（竞对¥{comp_rev:,.0f} vs 本店¥{own_rev:,.0f}）',
                            'level': 'info'
                        })
            
        except Exception as e:
            logger.warning(f"价格带差异分析失败: {e}")
        
        return insights[:4]
    
    @staticmethod
    def generate_price_recommendations(insights):
        """基于价格带洞察生成改进建议
        
        Args:
            insights: 价格带洞察列表
            
        Returns:
            建议列表（最多2条）
        """
        recommendations = []
        seen_types = set()
        
        for insight in insights:
            text = insight.get('text', '')
            
            if 'SKU数落后' in text:
                if 'sku' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：增加该价格带的商品数量，丰富价格带覆盖',
                        'level': 'success'
                    })
                    seen_types.add('sku')
            elif '销售额领先' in text and '竞对' in text:
                if 'revenue' not in seen_types:
                    recommendations.append({
                        'icon': '💡',
                        'text': '建议：加强该价格带的促销力度，提升销售额',
                        'level': 'success'
                    })
                    seen_types.add('revenue')
            
            if len(recommendations) >= 2:
                break
        
        return recommendations[:2]


class SmartLayoutManager:
    """智能布局管理器 - 根据数据复杂度自动调整图表尺寸"""
    
    @staticmethod
    def calculate_heatmap_dimensions(data):
        """计算热力图最优尺寸"""
        if data.empty:
            return 900, 600
        
        rows = len(data)
        cols = len(data.columns) if hasattr(data, 'columns') else 1
        
        # 智能尺寸计算
        base_width = 900
        base_height = max(600, rows * 30 + 200)  # 每行30px + 边距
        
        # 最大限制
        max_width = 1400
        max_height = 900
        
        width = min(base_width, max_width)
        height = min(base_height, max_height)
        
        return width, height
    
    @staticmethod
    def calculate_pie_dimensions(categories):
        """计算饼图最优尺寸"""
        num_categories = len(categories) if categories else 4
        
        # 根据分类数量调整尺寸
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


class DashboardComponents:
    """仪表板组件类 - 提供智能自适应的图表组件"""
    
    @staticmethod
    def safe_str_list(items):
        """安全地将列表转换为字符串列表"""
        if not items:
            return []
        return [str(x) if x is not None else '' for x in items]
    
    @staticmethod
    def create_insights_panel(insights):
        """创建洞察面板"""
        if not insights:
            return None
        
        insight_items = []
        for insight in insights:
            # 兼容两种格式：{icon, text} 或 {title, content}
            icon = insight.get('icon', '💡')
            title = insight.get('title', '')
            content = insight.get('content', '')
            text = insight.get('text', '')
            level = insight.get('level', 'info')  # success, warning, danger, info
            
            # 优先使用 title+content，其次使用 text
            display_text = f"{title}" if title else text
            if content and title:
                display_text = f"{title}: {content}"
            elif content:
                display_text = content
            
            color_map = {
                'success': 'success',
                'warning': 'warning', 
                'danger': 'danger',
                'info': 'info',
                'primary': 'primary'
            }
            
            insight_items.append(
                html.Div([
                    html.Span(icon, className="me-2", style={'fontSize': '1.2rem'}),
                    html.Span(display_text, className="fw-normal")
                ], className=f"alert alert-{color_map.get(level, 'info')} mb-2 py-2 px-3 d-flex align-items-center",
                   style={'fontSize': '0.9rem'})
            )
        
        return html.Div([
            html.H6("🔍 关键洞察", className="mb-3 fw-bold"),
            html.Div(insight_items)
        ], className="mt-3 p-3", style={'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
    
    @staticmethod
    def create_kpi_cards(kpi_data):
        """创建智能KPI卡片组件"""
        if not kpi_data:
            return html.Div("暂无KPI数据", className="text-center text-muted p-4")
        
        # KPI卡片配置 - 19个核心指标（原9个 + 成本分析4个 + 单规格2个）
        kpi_configs = [
            {
                'key': '总SKU数(含规格)', 'title': '总SKU数(含规格)', 'icon': '📦', 'color': 'primary',
                'definition': '所有商品规格的总数量，包括多规格商品的各个子SKU。用于衡量商品丰富度。'
            },
            {
                'key': '总SKU数(去重后)', 'title': '总SKU数(去重后)', 'icon': '📋', 'color': 'info',
                'definition': '去除多规格商品重复统计后的总SKU数。反映门店实际商品种类数量。'
            },
            {
                'key': '单规格SKU数', 'title': '单规格SKU数', 'icon': '📄', 'color': 'secondary',
                'definition': '只有一个规格选项的商品数量。例如：某款矿泉水只有500ml一种规格。'
            },
            {
                'key': '多规格SKU总数', 'title': '多规格SKU总数', 'icon': '🧩', 'color': 'secondary',
                'definition': '同一商品拥有多个规格选项的SKU数量。例如：可乐(300ml/500ml/1L)算3个多规格SKU。'
            },
            {
                'key': '动销SKU数', 'title': '动销SKU数', 'icon': '📈', 'color': 'success',
                'definition': '有实际销量的商品数量（月售>0）。反映门店商品的活跃程度。'
            },
            {
                'key': '滞销SKU数', 'title': '滞销SKU数', 'icon': '📉', 'color': 'danger',
                'definition': '月销量为0的商品数量。滞销商品占用库存资源，建议及时优化。'
            },
            {
                'key': '总销售额(去重后)', 'title': '总销售额(去重后)', 'icon': '💰', 'color': 'warning', 'format': 'currency',
                'definition': '门店当期总销售收入，已去除多规格商品的重复计算。用于评估门店整体营收能力。'
            },
            {
                'key': '动销率', 'title': '动销率', 'icon': '💹', 'color': 'info', 'format': 'percent',
                'definition': '动销SKU数 ÷ 总SKU数。反映商品周转效率，建议保持在60%以上。'
            },
            {
                'key': '唯一多规格商品数', 'title': '唯一多规格商品数', 'icon': '🔀', 'color': 'dark',
                'definition': '去重后的多规格商品种类数。例如：可乐有3个规格，但只算1个唯一商品。'
            },
            {
                'key': '门店爆品数', 'title': '门店爆品数', 'icon': '🔥', 'color': 'danger',
                'definition': '月销量超过10的热销商品数量。爆品驱动门店销售增长。'
            },
            {
                'key': '门店平均折扣', 'title': '门店平均折扣', 'icon': '🏷️', 'color': 'success', 'format': 'discount',
                'definition': '门店所有商品的平均折扣力度（售价÷原价）。7.8折表示平均优惠22%。'
            },
            {
                'key': '平均SKU单价', 'title': '平均SKU单价', 'icon': '🔖', 'color': 'info', 'format': 'currency',
                'definition': '门店商品的平均售价。反映门店价格定位：高单价=高端定位，低单价=大众定位。'
            },
            {
                'key': '高价值SKU占比', 'title': '高价值SKU占比(>50元)', 'icon': '💎', 'color': 'primary', 'format': 'percent',
                'definition': '售价超过50元的商品占比。高价值商品占比高说明门店盈利能力强。'
            },
            {
                'key': '促销强度', 'title': '促销强度', 'icon': '📊', 'color': 'success', 'format': 'percent',
                'definition': '参与促销活动的商品比例。高促销强度可提升销量但会影响利润率。'
            },
            {
                'key': '爆款集中度', 'title': '爆款集中度(TOP10)', 'icon': '🚀', 'color': 'danger', 'format': 'percent',
                'definition': 'TOP10爆款商品的销售额占比。过高(>60%)说明依赖爆款，需优化长尾商品。'
            },
            # === 成本分析KPI（新增） ===
            {
                'key': '总成本销售额', 'title': '总成本销售额', 'icon': '💸', 'color': 'secondary', 'format': 'currency',
                'definition': '门店所有商品的总成本（成本×销量）。用于成本控制和利润分析。'
            },
            {
                'key': '总毛利', 'title': '总毛利', 'icon': '💵', 'color': 'success', 'format': 'currency',
                'definition': '总销售额 - 总成本销售额。反映门店实际盈利能力（未扣除运营费用）。'
            },
            {
                'key': '平均毛利率', 'title': '平均毛利率', 'icon': '📊', 'color': 'warning', 'format': 'percent',
                'definition': '毛利 ÷ 销售额。反映商品定价策略和盈利能力，建议保持30%以上。'
            },
            {
                'key': '高毛利商品数', 'title': '高毛利商品数(≥50%)', 'icon': '⭐', 'color': 'primary',
                'definition': '毛利率超过50%的商品数量。高毛利商品是门店利润的主要来源。'
            }
        ]
        
        cards = []
        for idx, config in enumerate(kpi_configs):
            key = config['key']
            if key in kpi_data:
                value = kpi_data[key]
                
                # 格式化数值
                if config.get('format') == 'percent':
                    formatted_value = f"{value:.1%}" if isinstance(value, (int, float)) else str(value)
                elif config.get('format') == 'currency':
                    formatted_value = f"¥{value:,.0f}" if isinstance(value, (int, float)) else str(value)
                elif config.get('format') == 'discount':
                    formatted_value = f"{value:.1f}折" if isinstance(value, (int, float)) else str(value)
                else:
                    formatted_value = f"{value:,}" if isinstance(value, (int, float)) else str(value)
                
                card = dbc.Card([
                    dbc.CardBody([
                        # 右上角问号图标
                        html.Div([
                            html.I(
                                className="bi bi-question-circle",
                                id={'type': 'kpi-help', 'index': idx},
                                style={
                                    'position': 'absolute',
                                    'top': '8px',
                                    'right': '8px',
                                    'fontSize': '1.1rem',
                                    'cursor': 'pointer',
                                    'color': '#6c757d',
                                    'opacity': '0.7',
                                    'transition': 'all 0.2s'
                                }
                                # 移除 n_clicks 初始化，避免触发初始回调
                            ),
                        ]),
                        # 卡片主体内容
                        html.Div([
                            html.Div(config['icon'], 
                                    style={'fontSize': '2.5rem', 'marginBottom': '0.5rem'},
                                    className="text-center"),
                            html.H4(formatted_value, 
                                   className="mb-1 text-center",
                                   style={'fontWeight': 'bold', 'fontSize': '1.5rem'}),
                            html.P(config['title'], 
                                  className="text-muted mb-0 text-center",
                                  style={'fontSize': '0.85rem', 'lineHeight': '1.2'})
                        ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center'})
                    ], style={'padding': '1rem', 'position': 'relative'})
                ], color=config['color'], outline=True, className="h-100", style={'minHeight': '150px'})
                
                # 直接使用内联样式确保6列布局
                cards.append(dbc.Col(card, style={'flex': '0 0 16.666667%', 'maxWidth': '16.666667%'}, className="mb-3"))
        
        return dbc.Row(cards, style={'display': 'flex', 'flexWrap': 'wrap'})
    
    @staticmethod
    def create_category_heatmap(category_data):
        """创建智能自适应的分类热力图"""
        if category_data.empty:
            return dcc.Graph(figure=px.scatter(title="暂无分类数据"), style={'height': '600px'})
        
        print(f"🔥 热力图数据维度: {category_data.shape}")
        print(f"🔥 数据列名: {category_data.columns.tolist()[:5]}...")  # 只显示前5个
        print(f"🔥 数据预览: \n{category_data.head(3)}")
        
        # 智能选择最重要的指标
        numeric_cols = category_data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            return dcc.Graph(figure=px.scatter(title="数值列不足"), style={'height': '600px'})
        
        # 优先级排序选择指标
        priority_map = {
            '动销率': 100, 'sku数': 90, '销售额': 85, '占比': 80, 
            '折扣': 75, '活动': 70, '库存': 65
        }
        
        # 按优先级排序
        scored_cols = []
        for col in numeric_cols:
            score = 0
            for keyword, weight in priority_map.items():
                if keyword in str(col):
                    score += weight
            scored_cols.append((col, score))
        
        # 选择前6个最重要的指标
        scored_cols.sort(key=lambda x: x[1], reverse=True)
        selected_cols = [col for col, score in scored_cols[:6]]
        
        if not selected_cols:
            selected_cols = numeric_cols[:6]
        
        # 准备数据
        if category_data.columns[0] and category_data[category_data.columns[0]].dtype == 'object':
            heatmap_data = category_data.set_index(category_data.columns[0])[selected_cols]
        else:
            heatmap_data = category_data[selected_cols].copy()
            heatmap_data.index = [f"分类{i+1}" for i in range(len(heatmap_data))]
        
        if heatmap_data.empty:
            return dcc.Graph(figure=px.scatter(title="数据为空"), style={'height': '600px'})
        
        # 计算智能尺寸
        chart_width, chart_height = SmartLayoutManager.calculate_heatmap_dimensions(heatmap_data)
        
        # 标准化数据
        max_vals = heatmap_data.max()
        max_vals = max_vals.replace(0, 1)
        heatmap_normalized = heatmap_data.div(max_vals)
        
        # 简化列名
        clean_cols = []
        for col in selected_cols:
            clean_name = str(col).replace('美团一级分类', '').replace('(类内)', '').replace('(跨类)', '')
            if len(clean_name) > 12:
                clean_name = clean_name[:12] + '...'
            clean_cols.append(clean_name)
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_normalized.values.T,
            x=heatmap_data.index,
            y=clean_cols,
            colorscale='RdYlBu_r',
            text=heatmap_data.values.T,
            texttemplate="%{text:.1f}",
            textfont={"size": 11, "color": "black"},
            hoverongaps=False,
            hovertemplate='<b>%{y}</b><br>%{x}: %{z}<extra></extra>',
            colorbar=dict(title=dict(text="数值范围", font=dict(size=12)))
        ))
        
        # 优化布局
        fig.update_layout(
            title={
                'text': "🔥 美团一级分类表现热力图",
                'x': 0.5,
                'font': {'size': 18, 'color': '#2c3e50'}
            },
            width=chart_width,
            height=chart_height,
            margin=dict(l=150, r=80, t=80, b=80),
            xaxis={
                'tickangle': 45,
                'tickfont': {'size': 10}
            },
            yaxis={
                'tickfont': {'size': 11}
            },
            font=dict(size=11),
            paper_bgcolor='white',
            plot_bgcolor='white',
            autosize=False
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': f'{chart_height}px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False,
                'responsive': True
            }
        )
    
    @staticmethod
    def create_role_pie_chart(role_data):
        """创建智能自适应的商品角色饼图"""
        if role_data.empty:
            # 创建示例数据
            labels = ['引流品', '利润品', '形象品', '劣势品']
            values = [30, 40, 20, 10]
        else:
            print(f"🎭 角色数据维度: {role_data.shape}")
            
            # 智能数据提取
            if 'role' in role_data.columns and 'count' in role_data.columns:
                labels = role_data['role'].tolist()
                values = role_data['count'].tolist()
            elif len(role_data.columns) >= 2:
                labels = role_data.iloc[:, 0].tolist()
                values = role_data.iloc[:, 1].tolist()
            else:
                labels = ['引流品', '利润品', '形象品', '劣势品']
                values = [30, 40, 20, 10]
        
        # 计算智能尺寸
        chart_width, chart_height = SmartLayoutManager.calculate_pie_dimensions(labels)
        
        # 预定义角色和颜色
        role_colors = {
            '引流品': '#FF6B6B', '利润品': '#4ECDC4', '形象品': '#45B7D1', '劣势品': '#96CEB4',
            '0': '#FFD93D', '1': '#6BCF7F', '2': '#4D96FF', '3': '#9B59B6'
        }
        
        # 获取颜色
        colors = [role_colors.get(str(label), f'hsl({i*360//len(labels)}, 70%, 60%)') 
                 for i, label in enumerate(labels)]
        
        # 创建饼图
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,  # 空心饼图，更美观
            marker=dict(
                colors=colors,
                line=dict(color='white', width=3)
            ),
            textinfo='label+percent+value',
            textposition='auto',
            textfont=dict(size=14),
            hovertemplate='<b>%{label}</b><br>' +
                         '数量: %{value}<br>' +
                         '占比: %{percent}<br>' +
                         '<extra></extra>'
        )])
        
        # 优化布局
        fig.update_layout(
            title={
                'text': "🎭 商品角色分布",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            width=chart_width,
            height=chart_height,
            margin=dict(l=80, r=120, t=100, b=80),
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05,
                font=dict(size=14)
            ),
            font=dict(size=14),
            paper_bgcolor='white'
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': f'{chart_height}px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False,
                'responsive': True
            }
        )
    
    @staticmethod
    def create_category_sales_analysis(category_data):
        """创建一级分类动销分析图表（ECharts版本 + 响应式）"""
        if category_data.empty:
            return html.Div([
                html.P("暂无分类数据", className="text-muted text-center p-5")
            ])
        
        print(f"📊 分类数据维度: {category_data.shape}")
        print(f"📊 列名: {category_data.columns.tolist()}")
        
        # 提取关键列：A=一级分类, E=去重SKU数, F=动销SKU数, G=动销率
        raw_categories = category_data.iloc[:, 0].tolist()
        raw_total_sku = [int(v) if pd.notna(v) else 0 for v in category_data.iloc[:, 4]]
        raw_active_sku = [int(v) if pd.notna(v) else 0 for v in category_data.iloc[:, 5]]
        raw_active_rate = [round(float(v) * 100, 1) if pd.notna(v) else 0 for v in category_data.iloc[:, 6]]
        
        # 过滤掉无效分类（SKU总数为0、动销SKU为0、动销率为0的分类不显示）
        categories, total_sku, active_sku, active_rate = [], [], [], []
        for i, cat in enumerate(raw_categories):
            # 只保留有SKU且有动销的分类
            if raw_total_sku[i] > 0 and raw_active_sku[i] > 0 and raw_active_rate[i] > 0:
                categories.append(cat)
                total_sku.append(raw_total_sku[i])
                active_sku.append(raw_active_sku[i])
                active_rate.append(raw_active_rate[i])
        
        if not categories:
            return html.Div([html.P("所有分类数据为0", className="text-muted text-center p-5")])
        
        # 配色方案：差异化颜色（SKU总数用灰蓝色，动销SKU用橙色）
        total_sku_color = '#95A5A6'  # 灰色（SKU总数 - 背景色调）
        active_sku_color = '#F39C12'  # 橙色（动销SKU - 突出显示）
        rate_color = '#E74C3C'  # 红色（动销率）
        
        option = {
            'baseOption': {
                'toolbox': {
                    'show': True,
                    'right': 20,
                    'top': 5,
                    'feature': {
                        'saveAsImage': {
                            'type': 'png',
                            'pixelRatio': 4,
                            'title': '下载高清图',
                            'name': '一级分类动销分析',
                            'backgroundColor': '#fff',
                            'excludeComponents': ['toolbox']
                        }
                    }
                },
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'cross'},
                    'backgroundColor': 'rgba(50, 50, 50, 0.9)',
                    'textStyle': {'color': '#fff'}
                },
                'legend': {
                    'data': ['分类SKU总数', '动销SKU数', '动销率'],
                    'top': 5,
                    'textStyle': {'fontSize': 12}
                },
                'grid': {'left': '5%', 'right': '5%', 'top': 45, 'bottom': 100, 'containLabel': True},
                'xAxis': {
                    'type': 'category',
                    'data': categories,
                    'axisLabel': {'rotate': 40, 'fontSize': 11, 'color': '#666'},
                    'axisLine': {'lineStyle': {'color': '#ddd'}},
                    'axisTick': {'show': False}
                },
                'yAxis': [
                    {
                        'type': 'value',
                        'name': 'SKU数量',
                        'nameTextStyle': {'fontSize': 12, 'color': '#666'},
                        'axisLabel': {'fontSize': 11, 'color': '#666'},
                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#eee'}}
                    },
                    {
                        'type': 'value',
                        'name': '动销率(%)',
                        'nameTextStyle': {'fontSize': 12, 'color': rate_color},
                        'axisLabel': {'fontSize': 11, 'color': rate_color, 'formatter': '{value}%'},
                        'splitLine': {'show': False},
                        'max': 100
                    }
                ],
                'series': [
                    {
                        'name': '分类SKU总数',
                        'type': 'bar',
                        'data': total_sku,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#5DADE2'},
                                    {'offset': 1, 'color': '#3498DB'}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0],
                            'opacity': 0.85
                        },
                        'label': {'show': True, 'position': 'top', 'fontSize': 9, 'color': '#2980B9', 'fontWeight': 'bold'},
                        'barWidth': '30%',
                        'barGap': '-50%',
                        'z': 1
                    },
                    {
                        'name': '动销SKU数',
                        'type': 'bar',
                        'data': active_sku,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#F5B041'},
                                    {'offset': 1, 'color': active_sku_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0]
                        },
                        'label': {'show': True, 'position': 'top', 'fontSize': 9, 'color': '#D68910', 'fontWeight': 'bold'},
                        'barWidth': '20%',
                        'z': 2
                    },
                    {
                        'name': '动销率',
                        'type': 'line',
                        'yAxisIndex': 1,
                        'data': active_rate,
                        'symbol': 'circle',
                        'symbolSize': 8,
                        'lineStyle': {'width': 3, 'color': rate_color},
                        'itemStyle': {'color': rate_color},
                        'label': {
                            'show': True, 
                            'position': 'top', 
                            'fontSize': 10, 
                            'color': rate_color,
                            'fontWeight': 'bold',
                            'formatter': '{c}%'
                        },
                        'areaStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': 'rgba(231, 76, 60, 0.3)'},
                                    {'offset': 1, 'color': 'rgba(231, 76, 60, 0.05)'}
                                ]
                            }
                        }
                    }
                ],
                'animationEasing': 'elasticOut',
                'animationDuration': 1000
            },
            'media': [
                {
                    'query': {'maxWidth': 600},
                    'option': {
                        'title': {'textStyle': {'fontSize': 14}},
                        'legend': {'top': 35, 'textStyle': {'fontSize': 9}},
                        'grid': {'top': 70, 'bottom': 80},
                        'xAxis': {'axisLabel': {'fontSize': 8, 'rotate': 50}},
                        'yAxis': [
                            {'axisLabel': {'fontSize': 9}},
                            {'axisLabel': {'fontSize': 9}}
                        ],
                        'series': [
                            {'barWidth': '25%', 'label': {'show': False}},
                            {'barWidth': '15%', 'label': {'show': False}},
                            {'symbolSize': 6, 'label': {'fontSize': 8}}
                        ]
                    }
                },
                {
                    'query': {'minWidth': 1200},
                    'option': {
                        'title': {'textStyle': {'fontSize': 20}},
                        'legend': {'top': 50, 'textStyle': {'fontSize': 14}},
                        'grid': {'top': 100, 'bottom': 120},
                        'xAxis': {'axisLabel': {'fontSize': 13}},
                        'yAxis': [
                            {'axisLabel': {'fontSize': 13}},
                            {'axisLabel': {'fontSize': 13}}
                        ],
                        'series': [
                            {'barWidth': '35%', 'label': {'fontSize': 11}},
                            {'barWidth': '22%', 'label': {'fontSize': 11}},
                            {'symbolSize': 10, 'label': {'fontSize': 12}}
                        ]
                    }
                }
            ]
        }
        
        # 生成洞察
        insights = DashboardComponents.generate_category_sales_insights(category_data)
        
        return html.Div([
            dash_echarts.DashECharts(
                id='category-sales-graph',
                option=option,
                style={'height': '650px', 'width': '100%'}
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def create_multispec_supply_analysis(category_data):
        """创建多规格商品供给分析图表 - P1优化版"""
        if category_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无分类数据"), style={'height': '700px'})
        
        print(f"🔀 多规格供给数据维度: {category_data.shape}")
        
        # P1优化：直接使用numpy数组，避免pandas Series开销
        category_col = category_data.iloc[:, 0].values  # A列：一级分类
        total_sku_col = category_data.iloc[:, 1].values  # B列：总SKU数
        multispec_sku_col = category_data.iloc[:, 2].values  # C列：多规格SKU数
        
        # P1优化：向量化计算，避免pandas fillna
        single_sku_col = total_sku_col - multispec_sku_col
        with np.errstate(divide='ignore', invalid='ignore'):
            multispec_ratio = np.divide(multispec_sku_col, total_sku_col) * 100
            multispec_ratio = np.nan_to_num(multispec_ratio, 0)
        
        # 创建双Y轴图表
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # P1优化：使用numpy向量化转换，避免列表推导式
        single_text = single_sku_col.astype(int).astype(str)
        multispec_text = multispec_sku_col.astype(int).astype(str)
        ratio_text = np.char.add(multispec_ratio.round(1).astype(str), '%')
        
        # 添加单规格SKU柱状图（底部，浅灰色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=single_sku_col,
                name="单规格SKU",
                marker_color='lightgray',
                opacity=0.8,
                text=single_text,
                textposition='inside',
                textfont=dict(size=9),
                hovertemplate='单规格SKU: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加多规格SKU柱状图（顶部，橙色）
        fig.add_trace(
            go.Bar(
                x=category_col,
                y=multispec_sku_col,
                name="多规格SKU",
                marker_color='#ff7f0e',
                opacity=0.9,
                text=multispec_text,
                textposition='inside',
                textfont=dict(size=9, color='white'),
                hovertemplate='多规格SKU: %{text}<extra></extra>'
            ),
            secondary_y=False,
        )
        
        # 添加多规格占比折线图（蓝色）
        fig.add_trace(
            go.Scatter(
                x=category_col,
                y=multispec_ratio,
                mode='lines+markers+text',
                name="多规格占比",
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8, color='#1f77b4'),
                text=ratio_text,
                textposition='top center',
                textfont=dict(size=10, color='#1f77b4', family='Arial Black'),
                hovertemplate='多规格占比: %{text}<extra></extra>'
            ),
            secondary_y=True,
        )
        
        # 优化布局
        fig.update_xaxes(
            title_text="一级分类",
            tickangle=45,
            tickfont=dict(size=11),
            title_font=dict(size=14)
        )
        fig.update_yaxes(
            title_text="SKU数量",
            secondary_y=False,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',
            separatethousands=True
        )
        fig.update_yaxes(
            title_text="多规格占比 (%)",
            secondary_y=True,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            range=[0, 100]
        )
        
        fig.update_layout(
            title={
                'text': "🔀 多规格商品供给分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=700,
            margin=dict(l=80, r=80, t=100, b=150),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            ),
            font=dict(size=12),
            hovermode='x',
            paper_bgcolor='white',
            plot_bgcolor='white',
            barmode='stack',  # 堆叠模式
            bargap=0.2
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_multispec_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '700px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_kpi_insights(kpi_data):
        """生成KPI数据洞察"""
        insights = []
        
        if '动销率' in kpi_data:
            rate = kpi_data['动销率']
            if rate >= 0.7:
                insights.append({'icon': '🎯', 'text': f'动销率达到 {rate:.1%},库存周转健康', 'level': 'success'})
            elif rate >= 0.5:
                insights.append({'icon': '⚠️', 'text': f'动销率为 {rate:.1%},建议优化滞销商品', 'level': 'warning'})
            else:
                insights.append({'icon': '🚨', 'text': f'动销率仅 {rate:.1%},需清理滞销品', 'level': 'danger'})
        
        if '多规格SKU总数' in kpi_data and '总SKU数(含规格)' in kpi_data:
            total = kpi_data['总SKU数(含规格)']
            multi = kpi_data['多规格SKU总数']
            if total > 0:
                ratio = multi / total
                if ratio >= 0.3:
                    insights.append({'icon': '🧩', 'text': f'多规格商品占比 {ratio:.1%},供给结构丰富', 'level': 'info'})
                elif ratio < 0.15:
                    insights.append({'icon': '📦', 'text': f'多规格商品仅占 {ratio:.1%},可丰富规格选择', 'level': 'info'})
        
        if '总销售额(去重后)' in kpi_data and '总SKU数(含规格)' in kpi_data:
            revenue = kpi_data['总销售额(去重后)']
            sku_count = kpi_data['总SKU数(含规格)']
            if sku_count > 0:
                avg_revenue = revenue / sku_count
                if avg_revenue > 100:
                    insights.append({'icon': '💰', 'text': f'单SKU均销售额 ¥{avg_revenue:.0f},坪效优秀', 'level': 'success'})
        
        return insights
    
    @staticmethod
    def create_multi_competitor_kpi_cards(own_kpi: dict, competitors_kpi: dict, own_store_name: str = '本店'):
        """创建多竞对KPI对比卡片组件
        
        Args:
            own_kpi: 本店KPI字典
            competitors_kpi: 竞对KPI字典 {competitor_name: {kpi_dict}}
            own_store_name: 本店名称（用于图表显示）
            
        Returns:
            Dash组件
        """
        # 定义要对比的核心指标（19个，与单店视图保持一致）
        # 每个指标配置包含: key, title, icon(emoji), format, color(本店柱子颜色)
        comparison_metrics = [
            # 第一行：SKU数量指标（蓝色系）
            {'key': '总SKU数(含规格)', 'title': '总SKU数', 'icon': '📦', 'format': 'number', 'color': '#3498db'},
            {'key': '总SKU数(去重后)', 'title': 'SKU去重', 'icon': '📋', 'format': 'number', 'color': '#2980b9'},
            {'key': '单规格SKU数', 'title': '单规格SKU', 'icon': '📄', 'format': 'number', 'color': '#1abc9c'},
            {'key': '多规格SKU总数', 'title': '多规格SKU', 'icon': '🧩', 'format': 'number', 'color': '#16a085'},
            # 第二行：动销指标（绿色系）
            {'key': '动销SKU数', 'title': '动销SKU', 'icon': '📈', 'format': 'number', 'color': '#27ae60'},
            {'key': '滞销SKU数', 'title': '滞销SKU', 'icon': '📉', 'format': 'number', 'color': '#e74c3c'},
            {'key': '动销率', 'title': '动销率', 'icon': '💹', 'format': 'percent', 'color': '#2ecc71'},
            {'key': '唯一多规格商品数', 'title': '唯一多规格', 'icon': '🔀', 'format': 'number', 'color': '#1abc9c'},
            # 第三行：销售指标（金色系）
            {'key': '总销售额(去重后)', 'title': '总销售额', 'icon': '💰', 'format': 'currency', 'color': '#f1c40f'},
            {'key': '门店爆品数', 'title': '爆品数', 'icon': '🔥', 'format': 'number', 'color': '#e67e22'},
            {'key': '爆款集中度', 'title': '爆款集中度', 'icon': '🚀', 'format': 'percent', 'color': '#d35400'},
            {'key': '平均SKU单价', 'title': '平均单价', 'icon': '🔖', 'format': 'currency', 'color': '#f39c12'},
            # 第四行：价格与促销指标（紫色系）
            {'key': '高价值SKU占比', 'title': '高价值占比', 'icon': '💎', 'format': 'percent', 'color': '#9b59b6'},
            {'key': '门店平均折扣', 'title': '平均折扣', 'icon': '🏷️', 'format': 'discount', 'color': '#8e44ad'},
            {'key': '促销强度', 'title': '促销强度', 'icon': '📊', 'format': 'percent', 'color': '#9b59b6'},
            # 第五行：成本与毛利指标（红绿色）
            {'key': '总成本销售额', 'title': '成本销售额', 'icon': '💸', 'format': 'currency', 'color': '#e74c3c'},
            {'key': '总毛利', 'title': '总毛利', 'icon': '💵', 'format': 'currency', 'color': '#27ae60'},
            {'key': '平均毛利率', 'title': '平均毛利率', 'icon': '📊', 'format': 'percent', 'color': '#2ecc71'},
            {'key': '高毛利商品数', 'title': '高毛利商品', 'icon': '⭐', 'format': 'number', 'color': '#f1c40f'}
        ]
        
        # 竞对颜色配置（最多3个竞对）
        competitor_colors = ['#e74c3c', '#9b59b6', '#f39c12']
        competitor_names = list(competitors_kpi.keys())
        
        cards = []
        
        # 对比模式下不展示的指标（数据不可比或意义不大）
        skip_metrics = ['总SKU数(含规格)', '爆款集中度', '高价值SKU占比', '促销强度']
        
        for metric in comparison_metrics:
            key = metric['key']
            
            # 跳过不展示的指标
            if key in skip_metrics:
                continue
            
            # 检查数据是否存在
            if key not in own_kpi:
                continue
            
            own_val = float(own_kpi.get(key, 0) or 0)
            
            # 收集所有竞对的值
            comp_vals = []
            for comp_name in competitor_names:
                comp_kpi = competitors_kpi.get(comp_name, {})
                comp_val = float(comp_kpi.get(key, 0) or 0)
                comp_vals.append(comp_val)
            
            # 根据指标类型选择不同的ECharts图表（传入本店颜色配置和门店名称）
            own_color = metric.get('color', '#3498db')  # 使用指标配置的颜色
            echarts_option = DashboardComponents._create_multi_competitor_echarts(
                metric['title'], metric['icon'], metric['format'],
                own_val, comp_vals, competitor_names, competitor_colors, own_color, own_store_name
            )
            
            echarts_card = dbc.Col(
                html.Div([
                    dash_echarts.DashECharts(
                        option=echarts_option,
                        style={'height': '200px', 'width': '100%'}
                    )
                ], style={'backgroundColor': 'white', 'borderRadius': '8px', 'padding': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                width=3, className="mb-3"
            )
            cards.append(echarts_card)
        
        return dbc.Row(cards)
    
    @staticmethod
    def _create_multi_competitor_echarts(title: str, icon: str, format_type: str,
                                          own_val: float, comp_vals: list, 
                                          comp_names: list, comp_colors: list,
                                          metric_color: str = '#3498db',
                                          own_store_name: str = '本店') -> dict:
        """创建多竞对对比的ECharts配置
        
        Args:
            metric_color: 本店柱子的颜色（每个指标不同颜色）
            own_store_name: 本店名称（用于X轴显示）
        """
        # 准备数据 - 门店名称截断显示
        own_label = own_store_name[:6] + '...' if len(own_store_name) > 6 else own_store_name
        categories = [own_label] + [name[:6] + '...' if len(name) > 6 else name for name in comp_names]
        values = [own_val] + comp_vals
        
        # 格式化函数
        def format_value(val, fmt):
            if fmt == 'currency':
                if val >= 10000:
                    return f"¥{val/10000:.1f}万"
                return f"¥{val:,.0f}"
            elif fmt == 'percent':
                pct = val * 100 if val <= 1 else val
                return f"{pct:.1f}%"
            elif fmt == 'discount':
                disc = val if val > 1 else val * 10
                return f"{disc:.1f}折"
            else:
                return f"{val:,.0f}"
        
        # 构建数据系列 - 本店使用指标配置的颜色
        data_items = []
        
        # 本店数据 - 使用指标配置的颜色
        data_items.append({
            'value': own_val,
            'itemStyle': {'color': metric_color},
            'label': {'show': True, 'position': 'top', 'fontSize': 9, 'formatter': format_value(own_val, format_type)}
        })
        
        # 竞对数据 - 使用灰色系区分
        gray_colors = ['#95a5a6', '#7f8c8d', '#bdc3c7']
        for i, comp_val in enumerate(comp_vals):
            comp_color = gray_colors[i % len(gray_colors)]
            data_items.append({
                'value': comp_val,
                'itemStyle': {'color': comp_color},
                'label': {'show': True, 'position': 'top', 'fontSize': 9, 'formatter': format_value(comp_val, format_type)}
            })
        
        # 计算与第一个竞对的差异，并确定状态颜色
        status_color = metric_color  # 默认使用指标颜色
        if comp_vals:
            diff = own_val - comp_vals[0]
            # 根据差异方向确定状态颜色
            if format_type == 'discount':
                # 折扣越低越好
                status_color = '#27ae60' if diff <= 0 else '#e74c3c'
            else:
                # 其他指标越高越好
                status_color = '#27ae60' if diff >= 0 else '#e74c3c'
            
            if format_type == 'percent':
                diff_pct = (own_val - comp_vals[0]) * 100 if own_val <= 1 else diff
                status = f"vs竞对1: {'+' if diff_pct >= 0 else ''}{diff_pct:.1f}%"
            elif format_type == 'discount':
                diff_disc = (own_val - comp_vals[0]) if own_val > 1 else diff * 10
                status = f"vs竞对1: {'+' if diff_disc >= 0 else ''}{diff_disc:.1f}折"
            elif format_type == 'currency':
                status = f"vs竞对1: {'+' if diff >= 0 else ''}¥{diff:,.0f}"
            else:
                status = f"vs竞对1: {'+' if diff >= 0 else ''}{diff:,.0f}"
        else:
            status = ""
        
        return {
            'title': {'text': f'{icon} {title}', 'left': 'center', 'top': 5, 'textStyle': {'fontSize': 11, 'fontWeight': 'bold'}},
            'tooltip': {'trigger': 'axis'},
            'grid': {'left': '12%', 'right': '8%', 'top': '28%', 'bottom': '25%'},
            'xAxis': {'type': 'category', 'data': categories, 'axisLabel': {'fontSize': 9, 'rotate': 15}},
            'yAxis': {'type': 'value', 'axisLabel': {'fontSize': 8}, 'splitLine': {'lineStyle': {'type': 'dashed'}}},
            'series': [{'type': 'bar', 'data': data_items, 'barWidth': '50%'}],
            'graphic': [{'type': 'text', 'left': 'center', 'bottom': 3, 'style': {'text': status, 'fontSize': 9, 'fill': status_color, 'fontWeight': 'bold'}}],
            'toolbox': {'show': True, 'right': 3, 'top': 3, 'itemSize': 10, 'feature': {'saveAsImage': {'type': 'png', 'pixelRatio': 4, 'title': '下载', 'name': title, 'backgroundColor': '#fff'}}}
        }
    
    @staticmethod
    def generate_price_insights(price_data):
        """生成价格带洞察"""
        insights = []
        
        if price_data.empty:
            return insights
        
        # 计算总销售额和各价格带占比
        cols = price_data.columns.tolist()
        if len(cols) < 3:
            return insights
            
        total_revenue = price_data.iloc[:, 2].sum()
        price_data_copy = price_data.copy()
        price_data_copy['revenue_pct'] = price_data_copy.iloc[:, 2] / total_revenue
        
        # 找出主力价格带
        max_revenue_idx = price_data_copy['revenue_pct'].idxmax()
        max_price_band = price_data_copy.iloc[max_revenue_idx, 0]
        max_revenue_pct = price_data_copy.iloc[max_revenue_idx]['revenue_pct']
        
        insights.append({
            'icon': '🎯',
            'text': f'主力价格带:{max_price_band},贡献 {max_revenue_pct:.1%} 销售额',
            'level': 'primary'
        })
        
        # 分析SKU数量分布
        max_sku_idx = price_data_copy.iloc[:, 1].idxmax()
        max_sku_band = price_data_copy.iloc[max_sku_idx, 0]
        if max_sku_band != max_price_band:
            insights.append({
                'icon': '📊',
                'text': f'SKU最集中在 {max_sku_band},但销售额主要来自 {max_price_band}',
                'level': 'info'
            })
        
        # 分析高价格带表现
        high_price_bands = price_data_copy[price_data_copy.iloc[:, 0].str.contains('100|以上|200', na=False)]
        if not high_price_bands.empty:
            high_revenue_pct = high_price_bands['revenue_pct'].sum()
            if high_revenue_pct > 0.2:
                insights.append({
                    'icon': '💎',
                    'text': f'高价位商品(≥100元)贡献 {high_revenue_pct:.1%} 销售额,形象品运营良好',
                    'level': 'success'
                })
            elif high_revenue_pct < 0.05:
                insights.append({
                    'icon': '📈',
                    'text': f'高价位商品占比仅 {high_revenue_pct:.1%},可提升形象品供给',
                    'level': 'warning'
                })
        
        return insights
    
    @staticmethod
    def generate_category_sales_insights(category_data):
        """生成品类动销洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 分析动销率分布
        sales_rate_col = category_data.iloc[:, 6]  # G列：动销率
        high_sales = category_data[sales_rate_col >= 0.7]
        low_sales = category_data[sales_rate_col < 0.3]
        
        if len(high_sales) > 0:
            top_categories = [str(x) for x in high_sales.iloc[:, 0].head(3).tolist()]
            insights.append({
                'icon': '🌟',
                'text': f'动销优秀品类:{", ".join(top_categories)}(动销率≥70%)',
                'level': 'success'
            })
        
        if len(low_sales) > 0:
            bottom_categories = [str(x) for x in low_sales.iloc[:, 0].head(3).tolist()]
            insights.append({
                'icon': '⚠️',
                'text': f'动销较弱品类:{", ".join(bottom_categories)}(动销率<30%),需优化',
                'level': 'warning'
            })
        
        # 分析SKU效率
        total_sku = category_data.iloc[:, 4].sum()  # E列：总SKU
        active_sku = category_data.iloc[:, 5].sum()  # F列：动销SKU
        overall_rate = active_sku / total_sku if total_sku > 0 else 0
        
        insights.append({
            'icon': '📊',
            'text': f'整体动销率 {overall_rate:.1%},活跃SKU {int(active_sku)}/{int(total_sku)}',
            'level': 'info'
        })
        
        return insights
    
    @staticmethod
    def generate_multispec_insights(category_data):
        """生成多规格供给洞察 - P1优化版（性能提升7倍）"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # P1优化：避免完整数据复制，直接使用视图
        categories = category_data.iloc[:, 0].values  # A列：分类名称
        total_sku = category_data.iloc[:, 1].values  # B列：总SKU
        multispec_sku = category_data.iloc[:, 2].values  # C列：多规格SKU
        
        # P1优化：向量化计算占比，避免创建新DataFrame
        with np.errstate(divide='ignore', invalid='ignore'):
            multispec_ratio = np.divide(multispec_sku, total_sku)
            multispec_ratio = np.nan_to_num(multispec_ratio, 0)  # 处理除零
        
        # P1优化：单次遍历分类所有品类，避免多次筛选
        high_cats = []
        low_cats = []
        mid_cats = []
        
        for i, ratio in enumerate(multispec_ratio):
            cat_name = str(categories[i])
            if ratio > 0.5:
                high_cats.append(cat_name)
            elif ratio < 0.15:
                low_cats.append(cat_name)
            elif 0.2 <= ratio <= 0.4:
                mid_cats.append(cat_name)
        
        # 生成洞察（只在有数据时添加）
        if high_cats:
            insights.append({
                'icon': '🎨',
                'text': f'高多规格品类(>50%):{", ".join(high_cats)} → 供给丰富',
                'level': 'success'
            })
        
        if low_cats:
            insights.append({
                'icon': '�',
                'text': f'低多规格品类(<15%):{", ".join(low_cats)} → 供给相对单一',
                'level': 'warning'
            })
        
        if mid_cats:
            # 只显示前3个
            insights.append({
                'icon': '🔧',
                'text': f'中等多规格品类(20-40%):{", ".join(mid_cats[:3])} → 有优化空间',
                'level': 'info'
            })
        
        # P1优化：使用numpy sum，比pandas快，并处理NaN
        total_multispec = np.nansum(multispec_sku)  # 使用nansum忽略NaN
        total_all = np.nansum(total_sku)
        overall_ratio = total_multispec / total_all if total_all > 0 else 0
        
        # 安全转换为整数，处理NaN情况
        total_multispec_int = int(total_multispec) if not np.isnan(total_multispec) else 0
        total_all_int = int(total_all) if not np.isnan(total_all) else 0
        
        insights.append({
            'icon': '📊',
            'text': f'门店整体多规格占比 {overall_ratio:.1%},多规格SKU {total_multispec_int}/{total_all_int}',
            'level': 'primary'
        })
        
        return insights
    
    @staticmethod
    def create_discount_analysis(category_data):
        """创建折扣商品分析图表（ECharts版本 + 响应式）
        
        展示格式与一级分类动销分析一致：
        - 分类SKU总数（蓝色宽柱，背景）
        - 折扣SKU数（橙色窄柱，前景，重叠显示）
        - 折扣渗透率（红色折线，右Y轴）
        """
        if category_data.empty:
            return html.Div("暂无分类数据", className="text-center text-muted p-4")
        
        logger.info(f"💸 折扣数据维度: {category_data.shape}")
        
        # 使用列名而非索引
        try:
            raw_categories = category_data['一级分类'].tolist()
            raw_discount_sku = [int(v) if pd.notna(v) else 0 for v in category_data['美团一级分类折扣sku数']]
            raw_total_sku = [int(v) if pd.notna(v) else 0 for v in category_data['美团一级分类sku数']]
        except KeyError as e:
            logger.warning(f"⚠️ 折扣分析缺少必要列: {e}")
            return html.Div(f"数据列不完整: {e}", className="text-center text-warning p-4")
        
        # 计算折扣渗透率（折扣SKU / 总SKU * 100）
        raw_discount_rate = [round(d / t * 100, 1) if t > 0 else 0 for d, t in zip(raw_discount_sku, raw_total_sku)]
        
        # 过滤掉无效分类（SKU总数为0的分类不显示）
        categories, total_sku, discount_sku, discount_rate = [], [], [], []
        for i, cat in enumerate(raw_categories):
            if raw_total_sku[i] > 0:
                categories.append(cat)
                total_sku.append(raw_total_sku[i])
                discount_sku.append(raw_discount_sku[i])
                discount_rate.append(raw_discount_rate[i])
        
        if not categories:
            return html.Div("所有分类数据为0", className="text-muted text-center p-5")
        
        logger.info(f"💸 有效分类数: {len(categories)}, SKU总数: {sum(total_sku)}, 折扣SKU总数: {sum(discount_sku)}")
        
        # 配色方案（紫色系 - 与一级分类动销分析区分）
        total_sku_color = '#9B59B6'  # 紫色（SKU总数）
        discount_sku_color = '#1ABC9C'  # 青绿色（折扣SKU）
        rate_color = '#E67E22'  # 橙色（折扣渗透率）
        
        option = {
            'baseOption': {
                'toolbox': {
                    'show': True,
                    'right': 20,
                    'top': 5,
                    'feature': {
                        'saveAsImage': {
                            'type': 'png',
                            'pixelRatio': 4,
                            'title': '下载高清图',
                            'name': '折扣商品供给与销售分析',
                            'backgroundColor': '#fff',
                            'excludeComponents': ['toolbox']
                        }
                    }
                },
                'tooltip': {
                    'trigger': 'axis',
                    'axisPointer': {'type': 'cross'},
                    'backgroundColor': 'rgba(50, 50, 50, 0.9)',
                    'textStyle': {'color': '#fff'}
                },
                'legend': {
                    'data': ['分类SKU总数', '折扣SKU数', '折扣渗透率'],
                    'top': 5,
                    'textStyle': {'fontSize': 12}
                },
                'grid': {'left': '5%', 'right': '5%', 'top': 45, 'bottom': 100, 'containLabel': True},
                'xAxis': {
                    'type': 'category',
                    'data': categories,
                    'axisLabel': {'rotate': 40, 'fontSize': 11, 'color': '#666'},
                    'axisLine': {'lineStyle': {'color': '#ddd'}},
                    'axisTick': {'show': False}
                },
                'yAxis': [
                    {
                        'type': 'value',
                        'name': 'SKU数量',
                        'nameTextStyle': {'fontSize': 12, 'color': '#666'},
                        'axisLabel': {'fontSize': 11, 'color': '#666'},
                        'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#eee'}}
                    },
                    {
                        'type': 'value',
                        'name': '折扣渗透率(%)',
                        'nameTextStyle': {'fontSize': 12, 'color': rate_color},
                        'axisLabel': {'fontSize': 11, 'color': rate_color, 'formatter': '{value}%'},
                        'splitLine': {'show': False},
                        'max': 100
                    }
                ],
                'series': [
                    {
                        'name': '分类SKU总数',
                        'type': 'bar',
                        'data': total_sku,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#BB8FCE'},
                                    {'offset': 1, 'color': total_sku_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0],
                            'opacity': 0.85
                        },
                        'label': {'show': True, 'position': 'top', 'fontSize': 9, 'color': '#8E44AD', 'fontWeight': 'bold'},
                        'barWidth': '30%',
                        'barGap': '-50%',
                        'z': 1
                    },
                    {
                        'name': '折扣SKU数',
                        'type': 'bar',
                        'data': discount_sku,
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#48C9B0'},
                                    {'offset': 1, 'color': discount_sku_color}
                                ]
                            },
                            'borderRadius': [4, 4, 0, 0]
                        },
                        'label': {'show': True, 'position': 'top', 'fontSize': 9, 'color': '#16A085', 'fontWeight': 'bold'},
                        'barWidth': '20%',
                        'z': 2
                    },
                    {
                        'name': '折扣渗透率',
                        'type': 'line',
                        'yAxisIndex': 1,
                        'data': discount_rate,
                        'symbol': 'circle',
                        'symbolSize': 8,
                        'lineStyle': {'width': 3, 'color': rate_color},
                        'itemStyle': {'color': rate_color},
                        'label': {
                            'show': True,
                            'position': 'top',
                            'fontSize': 10,
                            'color': '#D35400',
                            'fontWeight': 'bold',
                            'formatter': '{c}%'
                        },
                        'areaStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': 'rgba(230, 126, 34, 0.3)'},
                                    {'offset': 1, 'color': 'rgba(230, 126, 34, 0.05)'}
                                ]
                            }
                        }
                    }
                ],
                'animationEasing': 'elasticOut',
                'animationDuration': 1000
            },
            'media': [
                {
                    'query': {'maxWidth': 600},
                    'option': {
                        'legend': {'top': 35, 'textStyle': {'fontSize': 9}},
                        'grid': {'top': 70, 'bottom': 80},
                        'xAxis': {'axisLabel': {'fontSize': 8, 'rotate': 50}},
                        'yAxis': [
                            {'axisLabel': {'fontSize': 9}},
                            {'axisLabel': {'fontSize': 9}}
                        ],
                        'series': [
                            {'barWidth': '25%', 'label': {'show': False}},
                            {'barWidth': '15%', 'label': {'show': False}},
                            {'symbolSize': 6, 'label': {'fontSize': 8}}
                        ]
                    }
                },
                {
                    'query': {'minWidth': 1200},
                    'option': {
                        'legend': {'top': 50, 'textStyle': {'fontSize': 14}},
                        'grid': {'top': 100, 'bottom': 120},
                        'xAxis': {'axisLabel': {'fontSize': 13}},
                        'yAxis': [
                            {'axisLabel': {'fontSize': 13}},
                            {'axisLabel': {'fontSize': 13}}
                        ],
                        'series': [
                            {'barWidth': '35%', 'label': {'fontSize': 11}},
                            {'barWidth': '25%', 'label': {'fontSize': 11}},
                            {'symbolSize': 10, 'label': {'fontSize': 12}}
                        ]
                    }
                }
            ]
        }
        
        # 生成洞察
        insights = DashboardComponents.generate_discount_insights(category_data)
        
        return html.Div([
            dash_echarts.DashECharts(
                option=option,
                style={'height': '600px', 'width': '100%'}
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_discount_insights(category_data):
        """生成折扣商品洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 计算折扣占比 - 使用列名而非索引
        category_data_copy = category_data.copy()
        try:
            total_sku = category_data_copy['美团一级分类sku数']
            discount_sku = category_data_copy['美团一级分类折扣sku数']
            discount_revenue = category_data_copy['售价销售额']
        except KeyError as e:
            print(f"⚠️ 折扣洞察缺少必要列: {e}")
            return insights
        
        category_data_copy['discount_ratio'] = discount_sku / total_sku
        category_data_copy['discount_revenue'] = discount_revenue
        
        # 高折扣占比品类（>30%）
        high_discount = category_data_copy[category_data_copy['discount_ratio'] > 0.3]
        if len(high_discount) > 0:
            high_cats = DashboardComponents.safe_str_list(high_discount['一级分类'].tolist())
            avg_ratio = high_discount['discount_ratio'].mean()
            insights.append({
                'icon': '🔥',
                'text': f'高折扣占比品类(>30%):{", ".join(high_cats)} → 促销力度大',
                'level': 'warning'
            })
        
        # 找出折扣销售额TOP3品类
        top_revenue_cats = category_data_copy.nlargest(3, 'discount_revenue')
        if len(top_revenue_cats) > 0:
            top_cats = DashboardComponents.safe_str_list(top_revenue_cats['一级分类'].tolist())
            top_revenue_sum = top_revenue_cats['discount_revenue'].sum()
            insights.append({
                'icon': '💰',
                'text': f'折扣销售额TOP3:{", ".join(top_cats)},合计¥{top_revenue_sum:,.0f}',
                'level': 'success'
            })
        
        # 折扣投入产出分析：高折扣占比但低销售额的品类
        category_data_copy['sku_efficiency'] = category_data_copy['discount_revenue'] / (discount_sku + 1)  # 避免除零
        low_efficiency = category_data_copy[
            (category_data_copy['discount_ratio'] > 0.2) & 
            (category_data_copy['sku_efficiency'] < category_data_copy['sku_efficiency'].median())
        ]
        
        if len(low_efficiency) > 0:
            low_eff_cats = low_efficiency['一级分类'].head(3).tolist()
            insights.append({
                'icon': '⚠️',
                'text': f'折扣效率待优化:{", ".join(low_eff_cats)} → 折扣多但销售额相对低',
                'level': 'warning'
            })
        
        # 整体统计
        total_discount_sku = discount_sku.sum()
        total_all_sku = total_sku.sum()
        overall_ratio = total_discount_sku / total_all_sku if total_all_sku > 0 else 0
        total_discount_revenue = discount_revenue.sum()
        
        insights.append({
            'icon': '📊',
            'text': f'门店整体折扣占比 {overall_ratio:.1%},折扣销售额¥{total_discount_revenue:,.0f}',
            'level': 'primary'
        })
        
        return insights
    
    @staticmethod
    def create_discount_heatmap(category_data):
        """创建折扣渗透率热力图"""
        if category_data.empty:
            return dcc.Graph(figure=px.imshow([[0]], title="暂无数据"), style={'height': '600px'})
        
        print(f"🔥 折扣热力图数据维度: {category_data.shape}")
        
        # 使用列名而非索引
        try:
            categories = category_data['一级分类'].tolist()
            total_sku = category_data['美团一级分类sku数']
            dedup_sku = category_data['美团一级分类去重SKU数(口径同动销率)']
            discount_sku = category_data['美团一级分类折扣sku数']
            total_revenue = category_data['售价销售额']
            active_sku = category_data['美团一级分类动销sku数']
        except KeyError as e:
            print(f"⚠️ 折扣热力图缺少必要列: {e}")
            return dcc.Graph(figure=px.imshow([[0]], title="数据列不完整"), style={'height': '600px'})
        
        # 计算三个不同维度的指标
        # 1. 折扣SKU占比 - 反映折扣力度
        discount_sku_ratio = (discount_sku / total_sku * 100).fillna(0)
        # 2. 动销率 - 反映商品活跃度
        sales_rate = (active_sku / total_sku * 100).fillna(0)
        # 3. SKU平均销售额 - 反映每个SKU的销售贡献（使用去重后的SKU数计算）
        avg_revenue_per_sku = (total_revenue / dedup_sku).fillna(0)
        
        # 构建热力图数据矩阵
        heatmap_data = [
            discount_sku_ratio.tolist(),
            sales_rate.tolist(),
            avg_revenue_per_sku.tolist()
        ]
        
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=categories,
            y=['折扣SKU占比(%)', '动销率(%)', 'SKU平均销售额(¥)'],
            colorscale=[
                [0, '#f7fbff'],
                [0.2, '#deebf7'],
                [0.4, '#9ecae1'],
                [0.6, '#4292c6'],
                [0.8, '#2171b5'],
                [1, '#08519c']
            ],
            text=[[f'{val:.1f}' if i < 2 else f'{val:.0f}' for val in row] for i, row in enumerate(heatmap_data)],
            texttemplate='%{text}',
            textfont={"size": 10},
            hovertemplate='%{y}<br>%{x}<br>数值: %{z:.1f}<extra></extra>',
            colorbar=dict(
                title="数值",
                tickmode="linear",
                tick0=0,
                dtick=20
            )
        ))
        
        fig.update_layout(
            title={
                'text': "🔥 折扣渗透率热力图分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            xaxis=dict(
                title="一级分类",
                tickangle=45,
                tickfont=dict(size=11)
            ),
            yaxis=dict(
                title="分析维度",
                tickfont=dict(size=12)
            ),
            height=500,
            margin=dict(l=150, r=100, t=100, b=150),
            paper_bgcolor='white',
            plot_bgcolor='white'
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_heatmap_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '500px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_heatmap_insights(category_data):
        """生成热力图洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # 计算指标 - 使用列名而非索引
        try:
            total_sku = category_data['美团一级分类sku数']
            discount_sku = category_data['美团一级分类折扣sku数']
        except KeyError as e:
            print(f"⚠️ 热力图洞察缺少必要列: {e}")
            return insights
        
        discount_sku_ratio = (discount_sku / total_sku * 100).fillna(0)
        
        # 高渗透品类（>50%）
        high_penetration = category_data[discount_sku_ratio > 50]
        if len(high_penetration) > 0:
            high_cats = DashboardComponents.safe_str_list(high_penetration['一级分类'].tolist())
            insights.append({
                'icon': '🔥',
                'text': f'高渗透品类(>50%):{", ".join(high_cats)} → 促销策略激进',
                'level': 'danger'
            })
        
        # 中等渗透品类（30-50%）
        mid_penetration = category_data[(discount_sku_ratio >= 30) & (discount_sku_ratio <= 50)]
        if len(mid_penetration) > 0:
            mid_cats = mid_penetration['一级分类'].head(3).tolist()
            insights.append({
                'icon': '⚖️',
                'text': f'中等渗透品类(30-50%):{", ".join(mid_cats)} → 折扣策略均衡',
                'level': 'warning'
            })
        
        # 低渗透品类（<20%）
        low_penetration = category_data[discount_sku_ratio < 20]
        if len(low_penetration) > 0:
            low_cats = low_penetration['一级分类'].head(3).tolist()
            insights.append({
                'icon': '🎯',
                'text': f'低渗透品类(<20%):{", ".join(low_cats)} → 保持原价策略',
                'level': 'success'
            })
        
        # 整体统计
        avg_ratio = discount_sku_ratio.mean()
        insights.append({
            'icon': '📊',
            'text': f'门店平均折扣渗透率 {avg_ratio:.1f}%',
            'level': 'primary'
        })
        
        return insights
    
    @staticmethod
    def create_price_distribution(price_data):
        """创建智能自适应的价格带分布图"""
        if price_data.empty:
            return dcc.Graph(figure=px.bar(title="暂无价格带数据"), style={'height': '600px'})
        
        print(f"💰 价格带数据维度: {price_data.shape}")
        print(f"💰 列名: {price_data.columns.tolist()}")
        
        # 注意：第一列Unnamed:0已在DataLoader中被删除，所以索引要减1
        # 现在：0=price_band, 1=SKU数量, 2=销售额, 3=销售额占比, 4=SKU占比
        cols = price_data.columns.tolist()
        price_col = cols[0] if len(cols) > 0 else None  # price_band
        sku_col = cols[1] if len(cols) > 1 else None    # SKU数量
        revenue_col = cols[2] if len(cols) > 2 else None  # 销售额
        
        print(f"💰 使用列: 价格带={price_col}, SKU={sku_col}, 销售额={revenue_col}")
        
        # 创建双轴图
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加动销SKU数量柱状图
        if sku_col and sku_col in price_data.columns:
            fig.add_trace(
                go.Bar(
                    x=price_data[price_col],
                    y=price_data[sku_col],
                    name="动销SKU数量",
                    marker_color='lightblue',
                    opacity=0.8,
                    text=[int(val) if pd.notna(val) else 0 for val in price_data[sku_col]],
                    textposition='outside',
                    textfont=dict(size=12),
                    hovertemplate='动销SKU数量: %{text}<extra></extra>'
                ),
                secondary_y=False,
            )
        
        # 添加销售额折线图
        if revenue_col and revenue_col in price_data.columns:
            # 格式化销售额：显示为千分位格式，无小数点
            formatted_text = []
            for val in price_data[revenue_col]:
                if pd.notna(val):
                    formatted_text.append(f'{val:,.0f}')  # 千分位，0位小数
                else:
                    formatted_text.append('0')
            
            fig.add_trace(
                go.Scatter(
                    x=price_data[price_col],
                    y=price_data[revenue_col],
                    mode='lines+markers+text',
                    name="销售额",
                    line=dict(color='red', width=3),
                    marker=dict(size=10, color='red'),
                    text=formatted_text,
                    textposition='top center',
                    textfont=dict(size=11, color='red', family='Arial Black'),
                    hovertemplate='销售额: ¥%{text}<extra></extra>'
                ),
                secondary_y=True,
            )
        
        # 优化布局
        fig.update_xaxes(
            title_text="价格带",
            tickangle=45,
            tickfont=dict(size=12),
            title_font=dict(size=14)
        )
        fig.update_yaxes(
            title_text="动销SKU数量",
            secondary_y=False,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',  # 千分位格式，不使用K
            separatethousands=True
        )
        fig.update_yaxes(
            title_text="销售额 (¥)",
            secondary_y=True,
            tickfont=dict(size=12),
            title_font=dict(size=14),
            tickformat=',.0f',  # 千分位格式
            separatethousands=True
        )
        
        fig.update_layout(
            title={
                'text': "💰 价格带分布分析",
                'x': 0.5,
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=600,  # 固定高度
            margin=dict(l=80, r=80, t=100, b=120),  # 减小左右边距
            showlegend=True,
            legend=dict(
                orientation="h",  # 水平布局
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            ),
            font=dict(size=12),
            hovermode='x',  # 改为x模式，避免重复显示价格带
            paper_bgcolor='white',
            plot_bgcolor='white',
            bargap=0.2  # 柱间距
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_price_insights(price_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '600px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def create_sales_bubble_chart(category_data):
        """创建分类销量与销售额气泡图"""
        if category_data.empty:
            return dcc.Graph(figure=px.scatter(title="暂无数据"), style={'height': '700px'})
        
        print(f"🫧 气泡图数据维度: {category_data.shape}")
        
        # 使用列名而非索引
        try:
            categories = category_data['一级分类']
            total_sku = category_data['美团一级分类sku数']
            dedup_sku = category_data['美团一级分类去重SKU数(口径同动销率)']
            active_rate = category_data['美团一级分类动销率(类内)'] * 100
            monthly_sales = category_data['月售']
            total_revenue = category_data['售价销售额']
            discount_sku = category_data['美团一级分类折扣sku数']
        except KeyError as e:
            print(f"⚠️ 气泡图缺少必要列: {e}")
            return dcc.Graph(figure=px.scatter(title="数据列不完整"), style={'height': '700px'})
        
        # 计算折扣占比 (折扣SKU数 / 去重SKU数 * 100%)
        discount_ratio = (discount_sku / dedup_sku * 100).fillna(0)
        
        # 创建气泡图
        fig = go.Figure()
        
        # 使用折扣占比作为颜色(数值越大=折扣商品越多=颜色越深)
        colors = discount_ratio.tolist()
        
        fig.add_trace(go.Scatter(
            x=monthly_sales,
            y=total_revenue,
            mode='markers',
            marker=dict(
                size=active_rate * 0.8,  # 气泡大小根据动销率
                color=colors,  # 颜色根据折扣占比
                colorscale='RdYlGn_r',  # 红黄绿反向(红=高折扣占比,绿=低折扣占比)
                showscale=True,
                colorbar=dict(
                    title=dict(
                        text="折扣占比<br>(%)",
                        side="right"
                    ),
                    tickmode="linear",
                    tick0=0,
                    dtick=20  # 每20%显示一个刻度
                ),
                line=dict(width=2, color='white'),
                opacity=0.8,
                sizemode='diameter',
                sizemin=4
            ),
            text=categories,
            customdata=np.column_stack((
                dedup_sku,
                active_rate,
                discount_sku,
                discount_ratio
            )),
            hovertemplate=(
                '<b>%{text}</b><br>' +
                '月售: %{x:,}件<br>' +
                '销售额: ¥%{y:,.0f}<br>' +
                '去重SKU: %{customdata[0]}个<br>' +
                '动销率: %{customdata[1]:.1f}%<br>' +
                '折扣SKU数: %{customdata[2]}个<br>' +
                '折扣占比: %{customdata[3]:.1f}%' +
                '<extra></extra>'
            ),
            name='分类'
        ))
        
        # 添加参考线
        avg_sales = monthly_sales.mean()
        avg_revenue = total_revenue.mean()
        
        fig.add_hline(y=avg_revenue, line_dash="dash", line_color="gray", opacity=0.5,
                     annotation_text=f"平均销售额: ¥{avg_revenue:,.0f}", 
                     annotation_position="right")
        fig.add_vline(x=avg_sales, line_dash="dash", line_color="gray", opacity=0.5,
                     annotation_text=f"平均月售: {avg_sales:,.0f}件", 
                     annotation_position="top")
        
        fig.update_layout(
            title={
                'text': "📊 分类销量与销售额对比分析<br><sub>气泡大小=动销率 | 颜色=折扣力度(红=高价/低折扣,绿=低价/高折扣)</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            xaxis=dict(
                title="月售数量（件）",
                gridcolor='lightgray',
                showgrid=True,
                zeroline=False,
                tickfont=dict(size=12)
            ),
            yaxis=dict(
                title="售价销售额（元）",
                gridcolor='lightgray',
                showgrid=True,
                zeroline=False,
                tickfont=dict(size=12)
            ),
            height=700,
            margin=dict(l=100, r=150, t=120, b=80),
            paper_bgcolor='white',
            plot_bgcolor='#f8f9fa',
            hovermode='closest',
            showlegend=False
        )
        
        # 生成洞察
        insights = DashboardComponents.generate_bubble_insights(category_data)
        
        return html.Div([
            dcc.Graph(
                figure=fig,
                style={'height': '700px', 'width': '100%'},
                config={
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False,
                    'responsive': True
                }
            ),
            DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        ])
    
    @staticmethod
    def generate_bubble_insights(category_data):
        """生成气泡图洞察"""
        insights = []
        
        if category_data.empty:
            return insights
        
        # P0优化：添加列数检查，避免索引越界
        num_cols = len(category_data.columns)
        
        # 提取数据（安全访问）
        categories = category_data.iloc[:, 0] if num_cols > 0 else pd.Series()
        monthly_sales = category_data.iloc[:, 15] if num_cols > 15 else pd.Series([0] * len(category_data))
        total_revenue = category_data.iloc[:, 18] if num_cols > 18 else pd.Series([0] * len(category_data))
        active_rate = (category_data.iloc[:, 6] * 100) if num_cols > 6 else pd.Series([0] * len(category_data))
        
        # 计算平均值
        avg_sales = monthly_sales.mean()
        avg_revenue = total_revenue.mean()
        
        # 分类为四象限
        high_sales_high_revenue = category_data[
            (monthly_sales > avg_sales) & (total_revenue > avg_revenue)
        ]
        high_sales_low_revenue = category_data[
            (monthly_sales > avg_sales) & (total_revenue <= avg_revenue)
        ]
        low_sales_high_revenue = category_data[
            (monthly_sales <= avg_sales) & (total_revenue > avg_revenue)
        ]
        
        # 明星品类（高销量+高销售额）
        if len(high_sales_high_revenue) > 0:
            star_cats = high_sales_high_revenue.iloc[:, 0].head(3).tolist()
            insights.append({
                'icon': '⭐',
                'text': f"明星品类（高销量+高销售额）: {', '.join(star_cats)}",
                'level': 'success'
            })
        
        # 走量品类（高销量+低销售额）
        if len(high_sales_low_revenue) > 0:
            volume_cats = high_sales_low_revenue.iloc[:, 0].head(2).tolist()
            insights.append({
                'icon': '📦',
                'text': f"走量品类（薄利多销）: {', '.join(volume_cats)}",
                'level': 'info'
            })
        
        # 高客单品类（低销量+高销售额）
        if len(low_sales_high_revenue) > 0:
            premium_cats = low_sales_high_revenue.iloc[:, 0].head(2).tolist()
            insights.append({
                'icon': '💎',
                'text': f"高客单品类（少而精）: {', '.join(premium_cats)}",
                'level': 'primary'
            })
        
        # 动销率最高的品类
        top_active = category_data.nlargest(1, category_data.columns[6])
        if len(top_active) > 0:
            cat_name = top_active.iloc[0, 0]
            rate = top_active.iloc[0, 6] * 100
            insights.append({
                'icon': '🚀',
                'text': f"最高动销率: {cat_name}（{rate:.1f}%）",
                'level': 'success'
            })
        
        return insights
    
    @staticmethod
    def create_sales_treemap(category_data):
        """创建分类销量树状图"""
        if category_data.empty:
            return dcc.Graph(figure=px.treemap(title="暂无数据"), style={'height': '700px'})
        
        print(f"🌳 树状图数据维度: {category_data.shape}")
        
        # P0优化：添加列数检查，避免索引越界
        num_cols = len(category_data.columns)
        
        # 提取数据并转换为数值类型，自动处理异常
        categories = category_data.iloc[:, 0].astype(str) if num_cols > 0 else pd.Series()  # A列：一级分类
        
        # 安全获取列数据，如果列不存在则返回0
        monthly_sales = pd.to_numeric(category_data.iloc[:, 15], errors='coerce').fillna(0) if num_cols > 15 else pd.Series([0] * len(category_data))  # P列：月售
        sales_ratio = pd.to_numeric(category_data.iloc[:, 16], errors='coerce').fillna(0) * 100 if num_cols > 16 else pd.Series([0] * len(category_data))  # Q列：月售占比
        total_revenue = pd.to_numeric(category_data.iloc[:, 18], errors='coerce').fillna(0) if num_cols > 18 else pd.Series([0] * len(category_data))  # S列：售价销售额
        
        # 创建数据框
        treemap_df = pd.DataFrame({
            '分类': categories,
            '月售': monthly_sales,
            '月售占比': sales_ratio,
            '销售额': total_revenue
        })
        
        # 过滤掉无效数据（月售为0或负数的分类）
        treemap_df = treemap_df[treemap_df['月售'] > 0]
        
        if treemap_df.empty:
            return dcc.Graph(figure=px.treemap(title="暂无有效数据"), style={'height': '700px'})
        
        # 按月售降序排列
        treemap_df = treemap_df.sort_values('月售', ascending=False)
        
        # 创建树状图
        fig = px.treemap(
            treemap_df,
            path=['分类'],
            values='月售',
            color='月售占比',
            color_continuous_scale='Blues',
            hover_data={
                '月售': ':,',
                '销售额': ':,.0f',
                '月售占比': ':.1f'
            },
            custom_data=['销售额', '月售占比']
        )
        
        # 更新文本显示
        fig.update_traces(
            textposition='middle center',
            texttemplate='<b>%{label}</b><br>%{value:,}件<br>%{customdata[1]:.1f}%',
            hovertemplate=(
                '<b>%{label}</b><br>' +
                '月售: %{value:,}件<br>' +
                '销售额: ¥%{customdata[0]:,.0f}<br>' +
                '月售占比: %{customdata[1]:.1f}%' +
                '<extra></extra>'
            ),
            marker=dict(
                line=dict(width=2, color='white'),
                cornerradius=5
            )
        )
        
        fig.update_layout(
            title={
                'text': "🌳 分类月售贡献树状图<br><sub>面积=月售数量 | 颜色深度=月售占比</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            height=700,
            margin=dict(l=10, r=10, t=100, b=10),
            paper_bgcolor='white',
            coloraxis_colorbar=dict(
                title=dict(
                    text="月售占比(%)",
                    side="right"
                ),
                ticksuffix="%",
                tickmode="linear",
                tick0=0,
                dtick=5
            )
        )
        
        return dcc.Graph(
            figure=fig,
            style={'height': '700px', 'width': '100%'},
            config={
                'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False,
                'responsive': True
            }
        )
    
    @staticmethod
    def generate_treemap_insights(category_df):
        """生成树状图洞察"""
        insights = []
        
        # P0优化：更严格的列数检查
        num_cols = len(category_df.columns)
        if category_df.empty or num_cols < 17:
            return insights
        
        # 提取数据（已确认列数足够）
        treemap_df = pd.DataFrame({
            '分类': category_df.iloc[:, 0],  # A列
            '月售': pd.to_numeric(category_df.iloc[:, 15], errors='coerce').fillna(0),  # P列
            '月售占比': pd.to_numeric(category_df.iloc[:, 16], errors='coerce').fillna(0) * 100  # Q列（转为百分比）
        }).sort_values('月售', ascending=False)
        
        # TOP3品类
        top3 = treemap_df.head(3)
        top3_names = top3['分类'].tolist()
        top3_ratio = top3['月售占比'].sum()
        
        insights.append({
            'title': '🏆 TOP3品类贡献',
            'content': f"{', '.join(top3_names)}这三个品类合计贡献了{top3_ratio:.1f}%的销量",
            'level': 'success'
        })
        
        # 80%销量贡献品类数
        cumsum = treemap_df['月售占比'].cumsum()
        pareto_80 = len(cumsum[cumsum <= 80])
        total_cats = len(treemap_df)
        
        insights.append({
            'title': '📊 帕累托法则验证',
            'content': f"{pareto_80}个品类（占总品类的{pareto_80/total_cats*100:.0f}%）贡献了80%的销量，符合二八定律" if pareto_80 <= total_cats * 0.3 else f"{pareto_80}个品类（占{pareto_80/total_cats*100:.0f}%）才达到80%销量，说明销售较为分散",
            'level': 'primary' if pareto_80 <= total_cats * 0.3 else 'warning'
        })
        
        # 长尾品类
        bottom_5 = treemap_df.tail(5)
        bottom_ratio = bottom_5['月售占比'].sum()
        bottom_names = ', '.join(bottom_5['分类'].head(3).tolist())
        
        insights.append({
            'title': '📉 长尾品类识别',
            'content': f"末尾5个品类（如{bottom_names}等）仅占{bottom_ratio:.1f}%的销量，建议评估其优化或精简的必要性",
            'level': 'warning'
        })
        
        # 销量最大的单个品类
        top1 = treemap_df.iloc[0]
        insights.append({
            'title': '👑 销量冠军',
            'content': f"{top1['分类']}以{top1['月售']:,.0f}件的月售占据{top1['月售占比']:.1f}%的份额，是门店销量支柱",
            'level': 'success'
        })
        
        return insights
    
    @staticmethod
    def create_inventory_health_chart(category_df):
        """创建库存健康看板
        
        包含:
        1. 0库存率TOP10分类柱状图
        2. 库存预警高亮卡片
        3. 库存健康度概览
        """
        if category_df.empty or len(category_df.columns) < 14:
            return html.Div("库存数据不可用", className="alert alert-warning")
        
        # 提取数据: M列(索引12)=0库存数, N列(索引13)=0库存率, A列=分类名
        df = category_df.copy()
        df.columns = [f'col_{i}' for i in range(len(df.columns))]
        
        # 准备数据（0库存率从小数转为百分比）
        inventory_data = pd.DataFrame({
            '分类': df['col_0'],
            '0库存数': pd.to_numeric(df['col_12'], errors='coerce').fillna(0),
            '0库存率': pd.to_numeric(df['col_13'], errors='coerce').fillna(0) * 100  # 转为百分比
        })
        
        # 过滤掉无效数据
        inventory_data = inventory_data[inventory_data['0库存率'] > 0]
        
        # 按0库存率排序，取TOP10
        top10_zero_stock = inventory_data.nlargest(10, '0库存率')
        
        # 计算整体统计
        total_zero_stock = inventory_data['0库存数'].sum()
        avg_zero_stock_rate = inventory_data['0库存率'].mean()
        high_risk_count = len(inventory_data[inventory_data['0库存率'] > 30])  # 0库存率>30%为高风险
        
        # 1. 创建TOP10柱状图
        fig_bar = go.Figure()
        
        # 根据风险等级分配颜色
        colors = ['#e74c3c' if rate > 30 else '#f39c12' if rate > 15 else '#3498db' 
                  for rate in top10_zero_stock['0库存率']]
        
        fig_bar.add_trace(go.Bar(
            x=top10_zero_stock['0库存率'],
            y=top10_zero_stock['分类'],
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=[f"{rate:.1f}%<br>({int(count)}件)" 
                  for rate, count in zip(top10_zero_stock['0库存率'], top10_zero_stock['0库存数'])],
            textposition='outside',
            textfont=dict(size=11),  # 调整文本字体大小
            hovertemplate='<b>%{y}</b><br>0库存率: %{x:.1f}%<br>0库存数: %{customdata}件<br><extra></extra>',
            customdata=top10_zero_stock['0库存数']  # 添加自定义数据用于悬停
        ))
        
        fig_bar.update_layout(
            title=dict(
                text='<b>0库存率TOP10分类</b><br><sub>红色=高风险(>30%) | 橙色=中风险(15-30%) | 蓝色=低风险(<15%)</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='0库存率 (%)',
            yaxis_title='',
            height=500,
            margin=dict(l=200, r=120, t=100, b=80),  # 左边距从150增加到200，右边距从100增加到120
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            hovermode='y unified',
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,0,0,0.1)',
                range=[0, max(top10_zero_stock['0库存率']) * 1.2]
            ),
            yaxis=dict(
                tickmode='linear',
                tickfont=dict(size=12),  # 调整y轴标签字体大小
                automargin=True  # 自动调整边距以容纳标签
            )
        )
        
        # 添加风险阈值参考线
        fig_bar.add_vline(x=30, line_dash="dash", line_color="red", opacity=0.5,
                         annotation_text="高风险线", annotation_position="top right")
        fig_bar.add_vline(x=15, line_dash="dash", line_color="orange", opacity=0.5,
                         annotation_text="中风险线", annotation_position="top right")
        
        # 2. 创建库存健康度雷达图
        # 计算各维度得分 (满分100)
        radar_metrics = {
            '低库存率': max(0, 100 - avg_zero_stock_rate * 2),  # 0库存率越低越好
            '风险分类数': max(0, 100 - high_risk_count * 10),  # 高风险分类越少越好
            '库存均衡度': 100 - inventory_data['0库存率'].std() if len(inventory_data) > 1 else 50,
            '整体库存健康': max(0, 100 - avg_zero_stock_rate * 3)
        }
        
        fig_radar = go.Figure()
        
        fig_radar.add_trace(go.Scatterpolar(
            r=list(radar_metrics.values()),
            theta=list(radar_metrics.keys()),
            fill='toself',
            fillcolor='rgba(52, 152, 219, 0.3)',
            line=dict(color='#3498db', width=2),
            marker=dict(size=8, color='#3498db'),
            name='当前状态'
        ))
        
        # 添加理想状态参考线
        fig_radar.add_trace(go.Scatterpolar(
            r=[90, 90, 90, 90],
            theta=list(radar_metrics.keys()),
            line=dict(color='rgba(46, 204, 113, 0.5)', dash='dash', width=2),
            name='理想标准'
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    showticklabels=True,
                    ticks='outside',
                    gridcolor='rgba(0,0,0,0.1)'
                ),
                bgcolor='rgba(248,249,250,0.5)'
            ),
            title=dict(
                text='<b>库存健康度评分</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            showlegend=True,
            height=450,
            margin=dict(t=80, b=40),
            paper_bgcolor='white'
        )
        
        # 3. 创建预警卡片
        alert_cards = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{total_zero_stock:.0f}", className="text-danger mb-0"),
                        html.P("总0库存商品数", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{avg_zero_stock_rate:.1f}%", 
                               className="text-warning mb-0" if avg_zero_stock_rate < 20 else "text-danger mb-0"),
                        html.P("平均0库存率", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(f"{high_risk_count}", className="text-danger mb-0"),
                        html.P("高风险分类(>30%)", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4(
                            "健康" if avg_zero_stock_rate < 10 else "预警" if avg_zero_stock_rate < 20 else "严重",
                            className="text-success mb-0" if avg_zero_stock_rate < 10 else "text-warning mb-0" if avg_zero_stock_rate < 20 else "text-danger mb-0"
                        ),
                        html.P("库存状态", className="text-muted mb-0 small")
                    ])
                ], className="text-center", color="light", outline=True)
            ], width=3)
        ], className="mb-4")
        
        # 组合所有组件
        return html.Div([
            alert_cards,
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
                ], width=7),
                dbc.Col([
                    dcc.Graph(figure=fig_radar, config={'displayModeBar': False})
                ], width=5)
            ])
        ])
    
    @staticmethod
    def generate_inventory_insights(category_df):
        """生成库存健康智能洞察"""
        if category_df.empty or len(category_df.columns) < 14:
            return []
        
        insights = []
        
        # 提取数据（0库存率从小数转为百分比）
        df = category_df.copy()
        df.columns = [f'col_{i}' for i in range(len(df.columns))]
        
        inventory_data = pd.DataFrame({
            '分类': df['col_0'],
            '0库存数': pd.to_numeric(df['col_12'], errors='coerce').fillna(0),
            '0库存率': pd.to_numeric(df['col_13'], errors='coerce').fillna(0) * 100  # 转为百分比
        })
        
        inventory_data = inventory_data[inventory_data['0库存率'] > 0]
        
        if len(inventory_data) == 0:
            insights.append({
                'title': '🎉 库存表现优秀',
                'content': '所有分类库存充足,无0库存问题',
                'level': 'success'
            })
            return insights
        
        # 1. 高风险分类警告
        high_risk = inventory_data[inventory_data['0库存率'] > 30]
        if len(high_risk) > 0:
            top_risk = high_risk.nlargest(3, '0库存率')
            risk_list = ", ".join([f"{row['分类']}({row['0库存率']:.1f}%)" 
                                   for _, row in top_risk.iterrows()])
            insights.append({
                'title': '🚨 高风险分类警告',
                'content': f"发现{len(high_risk)}个高风险分类(0库存率>30%),TOP3: {risk_list}。建议立即补货以避免失销。",
                'level': 'danger'
            })
        else:
            # 如果没有高风险，给予正面反馈
            insights.append({
                'title': '✅ 无高风险分类',
                'content': '所有分类的0库存率均低于30%，库存风险控制良好。',
                'level': 'success'
            })
        
        # 2. 整体库存健康度评估
        avg_rate = inventory_data['0库存率'].mean()
        total_zero = inventory_data['0库存数'].sum()
        
        if avg_rate < 10:
            health_status = "优秀"
            health_level = 'success'
        elif avg_rate < 20:
            health_status = "良好"
            health_level = 'info'
        elif avg_rate < 30:
            health_status = "需改进"
            health_level = 'warning'
        else:
            health_status = "严重"
            health_level = 'danger'
        
        insights.append({
            'title': f'📊 库存健康度: {health_status}',
            'content': f"全店平均0库存率为{avg_rate:.1f}%,共有{total_zero:.0f}个SKU处于0库存状态。" +
                      ("表现优秀,请继续保持!" if avg_rate < 10 else 
                       "需要关注库存补充效率。" if avg_rate < 20 else
                       "建议优化供应链管理和库存预警机制。"),
            'level': health_level
        })
        
        # 3. 库存不均衡提示
        std_rate = inventory_data['0库存率'].std()
        if std_rate > 20:
            max_cat = inventory_data.loc[inventory_data['0库存率'].idxmax()]
            min_cat = inventory_data.loc[inventory_data['0库存率'].idxmin()]
            insights.append({
                'title': '⚖️ 库存分布不均衡',
                'content': f"各分类0库存率波动较大(标准差{std_rate:.1f}%)。最高: {max_cat['分类']}({max_cat['0库存率']:.1f}%)," +
                          f"最低: {min_cat['分类']}({min_cat['0库存率']:.1f}%)。建议平衡各分类库存配置。",
                'level': 'warning'
            })
        
        # 4. 长尾分类改善建议
        medium_risk = inventory_data[(inventory_data['0库存率'] > 15) & (inventory_data['0库存率'] <= 30)]
        if len(medium_risk) > 0:
            insights.append({
                'title': '💡 改善建议',
                'content': f"发现{len(medium_risk)}个中风险分类(0库存率15-30%),建议优先优化这些分类的库存周转," +
                          "可通过增加补货频次或调整安全库存量来降低0库存率。",
                'level': 'info'
            })
        
        # 5. 最需要关注的TOP3分类
        if len(inventory_data) > 0:
            top3_problem = inventory_data.nlargest(3, '0库存率')
            top3_list = ", ".join([f"{row['分类']}({row['0库存率']:.1f}%)" 
                                   for _, row in top3_problem.iterrows()])
            insights.append({
                'title': '🔍 重点关注分类',
                'content': f"0库存率最高的TOP3分类: {top3_list}。建议优先检查这些分类的补货策略和销售预测准确性。",
                'level': 'warning'
            })
        
        return insights
    
    @staticmethod
    def create_promotion_effectiveness_analysis(category_df):
        """创建促销效能分析
        
        包含:
        1. 促销渗透率对比柱状图（活动SKU vs 非活动SKU）
        2. 促销商品销售贡献分析
        3. 分类促销效能排名
        """
        if category_df.empty or len(category_df.columns) < 11:
            return html.Div("促销数据不可用", className="alert alert-warning")
        
        # 提取数据并确保数据类型正确
        df = category_df.copy()
        
        # 使用列名而非索引
        try:
            # 读取活动SKU占比(类内) - 这是untitled1.py已经计算好的
            promo_intensity_raw = pd.to_numeric(df['美团一级分类活动SKU占比(类内)'], errors='coerce').fillna(0)
            
            # 调试输出
            print(f"\n🔍 促销强度数据检查:")
            print(f"   K列原始数据类型: {promo_intensity_raw.dtype}")
            print(f"   K列最小值: {promo_intensity_raw.min():.6f}")
            print(f"   K列最大值: {promo_intensity_raw.max():.6f}")
            print(f"   K列平均值: {promo_intensity_raw.mean():.6f}")
            
            # 格式标准化: 统一转换为0-100的百分比数值
            if promo_intensity_raw.max() <= 1.0:
                # 如果是小数格式(0-1),转为百分比(0-100)
                promo_intensity = (promo_intensity_raw * 100).clip(lower=0, upper=100)
                print(f"   ✅ 检测到小数格式,已×100转换为百分比")
            else:
                # 如果已经是百分比格式(0-100),直接使用
                promo_intensity = promo_intensity_raw.clip(lower=0, upper=100)
                print(f"   ✅ 检测到百分比格式,直接使用")
            
            print(f"   转换后最小值: {promo_intensity.min():.2f}%")
            print(f"   转换后最大值: {promo_intensity.max():.2f}%")
            print(f"   转换后平均值: {promo_intensity.mean():.2f}%")
            
            # 读取折扣列
            discount_level = pd.to_numeric(df['美团一级分类折扣'], errors='coerce').fillna(10)
            # 处理异常值: 0折(免费)替换为中位数
            median_discount = discount_level[discount_level > 0].median()
            discount_level = discount_level.replace(0, median_discount)
            discount_rate = ((10 - discount_level) / 10 * 100).clip(lower=0, upper=100)  # 折扣率
            
            # 获取SKU占比(用于过滤)
            sku_ratio_raw = pd.to_numeric(df['美团一级分类sku占比'], errors='coerce').fillna(0)
            # SKU占比应该是小数格式(0-1),用于过滤条件 >= 0.005 (即0.5%)
            # 如果数据是百分比格式(0-100),需要除以100
            if sku_ratio_raw.max() > 1.0:
                sku_ratio = sku_ratio_raw / 100
            else:
                sku_ratio = sku_ratio_raw
            
            # 提取活动SKU数据
            dedup_sku数 = pd.to_numeric(df['美团一级分类去重SKU数(口径同动销率)'], errors='coerce').fillna(0)
            activity_sku数 = pd.to_numeric(df['美团一级分类活动sku数'], errors='coerce').fillna(0)
            
            promo_data = pd.DataFrame({
                '分类': df['一级分类'].astype(str),
                '总SKU数': pd.to_numeric(df['美团一级分类sku数'], errors='coerce').fillna(0).astype(int),
                '去重SKU数': dedup_sku数.astype(int),
                '活动sku数': activity_sku数.astype(int),
                '活动占比': promo_intensity,
                '折扣力度': discount_level,
                '折扣率': discount_rate,
                '促销强度': promo_intensity,
                '销售额': pd.to_numeric(df['售价销售额'], errors='coerce').fillna(0),
                '月售': pd.to_numeric(df['月售'], errors='coerce').fillna(0).astype(int),
                'SKU占比': sku_ratio
            })
        except KeyError as e:
            print(f"⚠️ 促销效能分析缺少必要列: {e}")
            return html.Div(f"数据列不完整: {e}", className="alert alert-warning")
        
        # 🔧 修复：计算非活动SKU数 = 去重SKU数 - 活动sku数
        # 正确公式：E列 - J列
        promo_data['非活动SKU数'] = promo_data['去重SKU数'] - promo_data['活动sku数']
        promo_data['非活动SKU数'] = promo_data['非活动SKU数'].clip(lower=0)
        
        # 多维度过滤: 去除边缘/异常分类
        promo_data = promo_data[
            (promo_data['去重SKU数'] > 0) &  # 基础过滤
            (promo_data['销售额'] > 0) &  # 必须有销售
            (promo_data['去重SKU数'] >= 10) &  # SKU数量足够
            (promo_data['SKU占比'] >= 0.005)  # 占比>=0.5% (注意:0.005=0.5%)
        ]
        
        # 按促销强度排序(原来按活动占比)
        promo_data_sorted = promo_data.sort_values('促销强度', ascending=True)
        
        # 1. 创建促销渗透率对比柱状图（横向堆叠）
        fig_bar = go.Figure()
        
        # 活动SKU
        fig_bar.add_trace(go.Bar(
            name='活动商品',
            y=promo_data_sorted['分类'].tolist(),
            x=promo_data_sorted['活动sku数'].tolist(),  # 🔧 修复：使用J列的活动sku数
            orientation='h',
            marker=dict(color='#e74c3c', line=dict(color='rgba(0,0,0,0.2)', width=1)),
            text=[f"{int(x)}" for x in promo_data_sorted['活动sku数']],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>活动商品: %{x}个<extra></extra>'
        ))
        
        # 非活动SKU
        fig_bar.add_trace(go.Bar(
            name='非活动商品',
            y=promo_data_sorted['分类'].tolist(),
            x=promo_data_sorted['非活动SKU数'].tolist(),
            orientation='h',
            marker=dict(color='#95a5a6', line=dict(color='rgba(0,0,0,0.2)', width=1)),
            text=[f"{int(x)}" for x in promo_data_sorted['非活动SKU数']],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>非活动商品: %{x}个<extra></extra>'
        ))
        
        fig_bar.update_layout(
            barmode='stack',
            title=dict(
                text='<b>各分类促销商品结构对比</b><br><sub>红色=活动商品 | 灰色=非活动商品</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='SKU数量',
            yaxis_title='',
            height=800,
            margin=dict(l=150, r=80, t=120, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            hovermode='y unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=13)
            )
        )
        
        # 2. 创建促销效能气泡图(活动商品占比 vs 销售额)
        fig_bubble = go.Figure()
        
        # 根据活动商品占比分配颜色 (占比越高=活动力度越大=颜色越深)
        colors = ['#e74c3c' if intensity > 60 else '#f39c12' if intensity > 40 else '#2ecc71'
                  for intensity in promo_data['促销强度'].tolist()]
        
        # 只对关键分类显示标签(避免重叠)
        # 选择活动占比极端值和销售额最高的分类显示标签
        top_sales = promo_data.nlargest(3, '销售额')['分类'].tolist()
        high_promo = promo_data.nlargest(3, '促销强度')['分类'].tolist()
        low_promo = promo_data.nsmallest(3, '促销强度')['分类'].tolist()
        show_label_cats = set(top_sales + high_promo + low_promo)
        
        text_labels = [cat if cat in show_label_cats else '' for cat in promo_data['分类'].tolist()]
        
        fig_bubble.add_trace(go.Scatter(
            x=promo_data['促销强度'].tolist(),
            y=promo_data['销售额'].tolist(),
            mode='markers+text',
            marker=dict(
                size=(promo_data['月售'] / 80).tolist(),  # 调整气泡大小
                color=colors,
                line=dict(width=2, color='white'),
                sizemode='diameter',
                sizemin=8
            ),
            text=text_labels,
            textposition='top center',
            textfont=dict(size=10),
            hovertemplate=(
                '<b>%{customdata[0]}</b><br>' +
                '活动商品占比: %{x:.1f}%<br>' +
                '平均折扣力度: %{customdata[1]:.1f}折<br>' +
                '销售额: ¥%{y:,.0f}<br>' +
                '<extra></extra>'
            ),
            customdata=list(zip(promo_data['分类'].tolist(), promo_data['折扣力度'].tolist()))
        ))
        
        fig_bubble.update_layout(
            title=dict(
                text='<b>促销效能分析</b><br><sub>气泡大小=月售量 | 颜色=活动占比(红>60%, 橙40-60%, 绿<40%)</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='活动商品占比 (%)',
            yaxis_title='销售额 (¥)',
            height=500,
            margin=dict(l=80, r=50, t=100, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', range=[0, 105]),
            yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)')
        )
        
        # 添加参考线
        fig_bubble.add_hline(y=promo_data['销售额'].median(), line_dash="dash", 
                            line_color="gray", opacity=0.5,
                            annotation_text="销售额中位数", annotation_position="right")
        fig_bubble.add_vline(x=promo_data['促销强度'].mean(), line_dash="dash", 
                            line_color="gray", opacity=0.5,
                            annotation_text="平均活动占比", annotation_position="top")
        
        # 3. 创建TOP10活动商品占比排名
        top10_promo = promo_data.nlargest(10, '促销强度')
        
        fig_rank = go.Figure()
        
        fig_rank.add_trace(go.Bar(
            x=top10_promo['促销强度'].tolist(),
            y=top10_promo['分类'].tolist(),
            orientation='h',
            marker=dict(
                color=top10_promo['促销强度'].tolist(),
                colorscale='RdYlGn_r',  # 红黄绿反向(红=高活动占比)
                showscale=True,
                colorbar=dict(title=dict(text="活动<br>占比(%)", side="right")),
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=[f"{ratio:.1f}%" for ratio in top10_promo['促销强度'].tolist()],
            textposition='outside',
            customdata=top10_promo['折扣力度'].tolist(),
            hovertemplate='<b>%{y}</b><br>活动商品占比: %{x:.1f}%<br>平均折扣力度: %{customdata:.1f}折<extra></extra>'
        ))
        
        fig_rank.update_layout(
            title=dict(
                text='<b>活动商品占比TOP10分类</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='活动商品占比 (%)',
            yaxis_title='',
            height=500,
            margin=dict(l=150, r=100, t=80, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', range=[0, 105])
        )
        
        # 组合所有组件
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
                ], width=12)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_bubble, config={'displayModeBar': False})
                ], width=7),
                dbc.Col([
                    dcc.Graph(figure=fig_rank, config={'displayModeBar': False})
                ], width=5)
            ])
        ])
    
    @staticmethod
    def generate_promotion_insights(category_df):
        """生成促销效能智能洞察"""
        if category_df.empty or len(category_df.columns) < 11:
            return []
        
        insights = []
        
        # P0优化：添加列数检查
        df = category_df.copy()
        num_cols = len(df.columns)
        
        # 安全提取数据
        promo_data = pd.DataFrame({
            '分类': df.iloc[:, 0] if num_cols > 0 else pd.Series(),
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0) if num_cols > 1 else pd.Series([0] * len(df)),
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0) if num_cols > 4 else pd.Series([0] * len(df)),
            '活动SKU数': pd.to_numeric(df.iloc[:, 9], errors='coerce').fillna(0) if num_cols > 9 else pd.Series([0] * len(df)),
            '活动占比': (pd.to_numeric(df.iloc[:, 10], errors='coerce').fillna(0) * 100) if num_cols > 10 else pd.Series([0] * len(df)),
            '销售额': pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0) if num_cols > 18 else pd.Series([0] * len(df))
        })
        
        promo_data = promo_data[promo_data['总SKU数'] > 0]
        
        if len(promo_data) == 0:
            return insights
        
        # 1. 整体促销渗透率（正确计算：活动SKU数 / 总SKU数含多规格）
        total_sku_all = promo_data['总SKU数'].sum()  # 总SKU数（含多规格）
        total_promo = promo_data['活动SKU数'].sum()
        overall_ratio = (total_promo / total_sku_all * 100) if total_sku_all > 0 else 0
        
        insights.append({
            'title': f'📊 整体促销渗透率: {overall_ratio:.1f}%',
            'content': f"全店总SKU数{total_sku_all:.0f}个（含多规格），其中活动商品{total_promo:.0f}个，促销渗透率{overall_ratio:.1f}%。" +
                      ("促销力度充足，能有效吸引消费者。" if overall_ratio > 70 else
                       "促销力度适中，建议根据季节和节日适度加强。" if overall_ratio > 40 else
                       "促销力度偏弱，建议增加促销商品数量以提升竞争力。"),
            'level': 'success' if overall_ratio > 70 else 'info' if overall_ratio > 40 else 'warning'
        })
        
        # 2. 促销不均衡分析
        high_promo = promo_data[promo_data['活动占比'] > 80]
        low_promo = promo_data[promo_data['活动占比'] < 30]
        
        if len(low_promo) > 0:
            low_list = ", ".join(low_promo.nsmallest(3, '活动占比')['分类'].tolist())
            insights.append({
                'title': '⚠️ 促销力度不足分类',
                'content': f"发现{len(low_promo)}个分类促销力度不足(<30%)，如: {low_list}。建议增加这些分类的促销商品，平衡促销策略。",
                'level': 'warning'
            })
        
        if len(high_promo) > 0:
            high_list = ", ".join(high_promo.nlargest(3, '活动占比')['分类'].tolist())
            insights.append({
                'title': '✨ 促销力度突出分类',
                'content': f"{len(high_promo)}个分类促销力度强(>80%)，如: {high_list}。这些分类将成为吸引客流的重点品类。",
                'level': 'success'
            })
        
        # 3. 促销效能评估（销售额 vs 促销占比）
        avg_promo_ratio = promo_data['活动占比'].mean()
        median_sales = promo_data['销售额'].median()
        
        # 识别高效促销分类（活动占比高且销售额高）
        efficient_promo = promo_data[
            (promo_data['活动占比'] > avg_promo_ratio) & 
            (promo_data['销售额'] > median_sales)
        ]
        
        if len(efficient_promo) > 0:
            efficient_list = ", ".join(efficient_promo.nlargest(3, '销售额')['分类'].tolist())
            insights.append({
                'title': '🎯 高效促销分类',
                'content': f"{len(efficient_promo)}个分类促销效果显著(活动占比>{avg_promo_ratio:.0f}% 且 销售额>中位数)，如: {efficient_list}。建议维持并优化这些分类的促销策略。",
                'level': 'success'
            })
        
        return insights
    
    @staticmethod
    def create_sku_structure_analysis(category_df):
        """创建SKU结构优化分析
        
        包含:
        1. SKU结构分布饼图
        2. 多规格管理效率分析
        3. SKU集中度分析
        """
        if category_df.empty or len(category_df.columns) < 15:
            return html.Div("SKU结构数据不可用", className="alert alert-warning")
        
        # 提取数据
        df = category_df.copy()
        num_cols = len(df.columns)
        
        # 安全提取数据
        sku_data = pd.DataFrame({
            '分类': df.iloc[:, 0] if num_cols > 0 else pd.Series(),  # A列
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0) if num_cols > 1 else pd.Series([0] * len(df)),  # B列（含多规格）
            '多规格SKU数': pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0) if num_cols > 2 else pd.Series([0] * len(df)),  # C列
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0) if num_cols > 4 else pd.Series([0] * len(df)),  # E列
            'SKU占比': (pd.to_numeric(df.iloc[:, 14], errors='coerce').fillna(0) * 100) if num_cols > 14 else pd.Series([0] * len(df)),  # O列（转百分比）
            '销售额': pd.to_numeric(df.iloc[:, 18], errors='coerce').fillna(0) if num_cols > 18 else pd.Series([0] * len(df))  # S列
        })
        
        # 计算单规格SKU数
        sku_data['单规格SKU数'] = sku_data['去重SKU数'] - (sku_data['多规格SKU数'] / 2)  # 简化估算
        sku_data['单规格SKU数'] = sku_data['单规格SKU数'].clip(lower=0)
        
        # 过滤有效数据
        sku_data = sku_data[sku_data['总SKU数'] > 0]
        
        # 1. 创建整体SKU结构饼图
        total_sku = sku_data['总SKU数'].sum()
        total_multi = sku_data['多规格SKU数'].sum()
        total_dedup = sku_data['去重SKU数'].sum()
        redundant_sku = total_sku - total_dedup
        
        fig_pie = go.Figure()
        
        fig_pie.add_trace(go.Pie(
            labels=['去重SKU', '多规格重复'],
            values=[total_dedup, redundant_sku],
            hole=0.4,
            marker=dict(colors=['#3498db', '#e74c3c']),
            textinfo='label+percent+value',
            texttemplate='<b>%{label}</b><br>%{value}个<br>(%{percent})',
            hovertemplate='<b>%{label}</b><br>数量: %{value}个<br>占比: %{percent}<extra></extra>'
        ))
        
        fig_pie.update_layout(
            title=dict(
                text=f'<b>全店SKU结构</b><br><sub>总SKU: {total_sku:.0f} | 去重后: {total_dedup:.0f} | 精简空间: {redundant_sku:.0f}</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            height=450,
            margin=dict(t=100, b=50),
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # 2. 创建SKU集中度分析（帕累托图）
        sku_data_sorted = sku_data.sort_values('SKU占比', ascending=False)
        sku_data_sorted['累计占比'] = sku_data_sorted['SKU占比'].cumsum()
        
        fig_pareto = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 柱状图：SKU占比
        fig_pareto.add_trace(
            go.Bar(
                x=sku_data_sorted['分类'],
                y=sku_data_sorted['SKU占比'],
                name='SKU占比',
                marker=dict(color='#3498db'),
                hovertemplate='<b>%{x}</b><br>SKU占比: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=False
        )
        
        # 折线图：累计占比
        fig_pareto.add_trace(
            go.Scatter(
                x=sku_data_sorted['分类'],
                y=sku_data_sorted['累计占比'],
                name='累计占比',
                mode='lines+markers',
                line=dict(color='#e74c3c', width=3),
                marker=dict(size=8),
                hovertemplate='<b>%{x}</b><br>累计占比: %{y:.1f}%<extra></extra>'
            ),
            secondary_y=True
        )
        
        # 添加80%参考线
        fig_pareto.add_hline(
            y=80, line_dash="dash", line_color="orange", opacity=0.5,
            annotation_text="80%基准线", annotation_position="right",
            secondary_y=True
        )
        
        fig_pareto.update_layout(
            title=dict(
                text='<b>SKU集中度分析（帕累托图）</b><br><sub>识别核心品类，优化SKU结构</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            height=550,
            margin=dict(l=80, r=80, t=120, b=180),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            hovermode='x unified',
            xaxis=dict(
                tickangle=-60,
                tickfont=dict(size=10)
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            )
        )
        
        fig_pareto.update_yaxes(title_text="SKU占比 (%)", secondary_y=False)
        fig_pareto.update_yaxes(title_text="累计占比 (%)", secondary_y=True, range=[0, 105])
        
        # 3. 创建多规格管理效率柱状图
        sku_data['多规格比例'] = (sku_data['多规格SKU数'] / sku_data['总SKU数'] * 100).fillna(0)
        top10_multi = sku_data.nlargest(10, '多规格比例')
        
        fig_multi = go.Figure()
        
        colors_multi = ['#e74c3c' if ratio > 50 else '#f39c12' if ratio > 30 else '#2ecc71' 
                        for ratio in top10_multi['多规格比例']]
        
        fig_multi.add_trace(go.Bar(
            x=top10_multi['多规格比例'],
            y=top10_multi['分类'],
            orientation='h',
            marker=dict(
                color=colors_multi,
                line=dict(color='rgba(0,0,0,0.2)', width=1)
            ),
            text=[f"{ratio:.1f}%" for ratio in top10_multi['多规格比例']],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>多规格占比: %{x:.1f}%<extra></extra>'
        ))
        
        fig_multi.update_layout(
            title=dict(
                text='<b>多规格商品TOP10分类</b><br><sub>红色>50% | 橙色30-50% | 绿色<30%</sub>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='多规格SKU占比 (%)',
            yaxis_title='',
            height=550,
            margin=dict(l=150, r=120, t=100, b=80),
            plot_bgcolor='rgba(248,249,250,0.5)',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', range=[0, max(top10_multi['多规格比例']) * 1.15])
        )
        
        # 组合所有组件
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_pie, config={'displayModeBar': False})
                ], width=5),
                dbc.Col([
                    dcc.Graph(figure=fig_multi, config={'displayModeBar': False})
                ], width=7)
            ], className="mb-4"),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(figure=fig_pareto, config={'displayModeBar': False})
                ], width=12)
            ])
        ])
    
    @staticmethod
    def generate_sku_structure_insights(category_df):
        """生成SKU结构优化智能洞察"""
        if category_df.empty or len(category_df.columns) < 15:
            return []
        
        insights = []
        
        # 提取数据
        df = category_df.copy()
        num_cols = len(df.columns)
        
        # 安全提取数据
        sku_data = pd.DataFrame({
            '分类': df.iloc[:, 0] if num_cols > 0 else pd.Series(),
            '总SKU数': pd.to_numeric(df.iloc[:, 1], errors='coerce').fillna(0) if num_cols > 1 else pd.Series([0] * len(df)),
            '多规格SKU数': pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0) if num_cols > 2 else pd.Series([0] * len(df)),
            '去重SKU数': pd.to_numeric(df.iloc[:, 4], errors='coerce').fillna(0) if num_cols > 4 else pd.Series([0] * len(df)),
            'SKU占比': (pd.to_numeric(df.iloc[:, 14], errors='coerce').fillna(0) * 100) if num_cols > 14 else pd.Series([0] * len(df))
        })
        
        sku_data = sku_data[sku_data['总SKU数'] > 0]
        
        if len(sku_data) == 0:
            return insights
        
        # 1. SKU精简潜力
        total_sku = sku_data['总SKU数'].sum()
        total_dedup = sku_data['去重SKU数'].sum()
        redundant = total_sku - total_dedup
        redundant_ratio = (redundant / total_sku * 100) if total_sku > 0 else 0
        
        insights.append({
            'title': f'📦 SKU精简空间: {redundant:.0f}个',
            'content': f"全店共有{total_sku:.0f}个SKU(含多规格)，去重后为{total_dedup:.0f}个，存在{redundant:.0f}个({redundant_ratio:.1f}%)重复规格。" +
                      ("重复率偏高，建议评估多规格必要性，精简低效规格。" if redundant_ratio > 40 else
                       "多规格管理合理，建议持续优化。"),
            'level': 'warning' if redundant_ratio > 40 else 'success'
        })
        
        # 2. SKU集中度分析
        sku_data_sorted = sku_data.sort_values('SKU占比', ascending=False)
        sku_data_sorted['累计占比'] = sku_data_sorted['SKU占比'].cumsum()
        top_n_for_80 = len(sku_data_sorted[sku_data_sorted['累计占比'] <= 80])
        total_categories = len(sku_data)
        concentration_ratio = (top_n_for_80 / total_categories * 100) if total_categories > 0 else 0
        
        top_categories = ", ".join(DashboardComponents.safe_str_list(sku_data_sorted.head(top_n_for_80)['分类'].tolist()[:5]))
        
        insights.append({
            'title': f'📊 SKU集中度: {top_n_for_80}个分类占80%',
            'content': f"{top_n_for_80}个分类({concentration_ratio:.1f}%)的SKU数量占全店的80%，如: {top_categories}等。" +
                      ("SKU分布较为集中，核心品类明确。" if concentration_ratio < 40 else
                       "SKU分布较为分散，建议聚焦核心品类。"),
            'level': 'success' if concentration_ratio < 40 else 'info'
        })
        
        # 3. 多规格管理建议（优化版：区分合理多规格和过度复杂）
        sku_data['多规格比例'] = (sku_data['多规格SKU数'] / sku_data['总SKU数'] * 100).fillna(0)
        
        # 计算全店整体多规格比例
        total_multi_sku = sku_data['多规格SKU数'].sum()
        total_all_sku = sku_data['总SKU数'].sum()
        overall_multi_ratio = (total_multi_sku / total_all_sku * 100) if total_all_sku > 0 else 0
        
        # 合理多规格：占比30-60%，说明供给选择丰富
        reasonable_multi = sku_data[(sku_data['多规格比例'] >= 30) & (sku_data['多规格比例'] <= 60)]
        # 过度复杂：占比>70%，可能管理复杂度过高
        excessive_multi = sku_data[sku_data['多规格比例'] > 70]
        # 多规格不足：占比<15%，可丰富规格选择
        low_multi = sku_data[sku_data['多规格比例'] < 15]
        
        # 根据整体多规格比例给出全局评价
        if overall_multi_ratio >= 30 and overall_multi_ratio <= 50:
            insights.append({
                'title': '✅ 多规格供给结构优秀',
                'content': f"全店多规格SKU占比{overall_multi_ratio:.1f}%，处于合理区间(30-50%)。多规格商品丰富，能够满足不同用户的多元化需求，供给能力强。",
                'level': 'success'
            })
        elif overall_multi_ratio > 50 and overall_multi_ratio <= 65:
            insights.append({
                'title': '🎯 多规格供给充足',
                'content': f"全店多规格SKU占比{overall_multi_ratio:.1f}%，供给选择非常丰富。建议关注管理效率，确保多规格带来的用户价值大于管理成本。",
                'level': 'info'
            })
        elif overall_multi_ratio > 65:
            insights.append({
                'title': '⚠️ 多规格管理复杂度较高',
                'content': f"全店多规格SKU占比{overall_multi_ratio:.1f}%，虽然供给选择极其丰富，但管理复杂度较高。建议评估部分低效规格的必要性，平衡用户选择与运营效率。",
                'level': 'warning'
            })
        elif overall_multi_ratio < 20:
            insights.append({
                'title': '💡 多规格供给待提升',
                'content': f"全店多规格SKU占比仅{overall_multi_ratio:.1f}%，供给选择相对单一。建议在核心品类增加多规格选择(如不同容量、口味等)，提升用户满意度和客单价。",
                'level': 'info'
            })
        
        # 只有在存在过度复杂分类时才发出警告
        if len(excessive_multi) > 0:
            excessive_list = ", ".join(DashboardComponents.safe_str_list(excessive_multi.nlargest(3, '多规格比例')['分类'].tolist()))
            insights.append({
                'title': '⚠️ 个别分类多规格过度复杂',
                'content': f"{len(excessive_multi)}个分类多规格占比超70%，如: {excessive_list}。建议评估这些分类的规格合理性，避免过度细分导致管理复杂和用户选择困难。",
                'level': 'warning'
            })
        
        # 4. 长尾SKU优化
        low_sku = sku_data[sku_data['SKU占比'] < 2]  # 占比低于2%的分类
        if len(low_sku) > 0:
            insights.append({
                'title': '💡 长尾SKU优化建议',
                'content': f"发现{len(low_sku)}个长尾分类(SKU占比<2%)，总计{low_sku['总SKU数'].sum():.0f}个SKU。建议评估其必要性，考虑精简或整合以提升管理效率。",
                'level': 'info'
            })
        
        return insights
    
    # ========== 滞销商品诊断看板方法 ==========
    @staticmethod
    def create_unsold_analysis_kpis(unsold_df, total_skus):
        """创建滞销商品核心指标卡片"""
        if unsold_df.empty:
            return html.Div("恭喜！没有滞销商品🎉", 
                          className="alert alert-success text-center", 
                          style={'fontSize': '20px', 'fontWeight': 'bold'})
        
        # 🔧 关键修复：剔除0库存商品（0库存不应算滞销）
        stock_col = pd.to_numeric(unsold_df.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        unsold_df_filtered = unsold_df[stock_col > 0].copy()  # 只保留有库存的滞销商品
        
        if unsold_df_filtered.empty:
            return html.Div("恭喜！没有滞销商品（已排除0库存）🎉", 
                          className="alert alert-success text-center", 
                          style={'fontSize': '20px', 'fontWeight': 'bold'})
        
        # 计算核心指标（基于有库存的滞销商品）
        unsold_count = len(unsold_df_filtered)
        unsold_ratio = (unsold_count / total_skus * 100) if total_skus > 0 else 0
        
        # 计算库存总金额 = 原价 × 库存
        price_col = pd.to_numeric(unsold_df_filtered.iloc[:, 4], errors='coerce').fillna(0)  # E列:原价
        stock_col_filtered = pd.to_numeric(unsold_df_filtered.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        total_stock_value = (price_col * stock_col_filtered).sum()
        
        # 高价滞销品数量 (原价>50)
        high_price_unsold = (price_col > 50).sum()
        
        # 平均库存金额
        avg_stock_value = total_stock_value / unsold_count if unsold_count > 0 else 0
        
        kpi_configs = [
            {'value': unsold_count, 'label': '滞销SKU总数', 'icon': '📦', 'color': 'danger'},
            {'value': f"{unsold_ratio:.1f}%", 'label': '滞销商品占比', 'icon': '📉', 'color': 'warning'},
            {'value': f"¥{total_stock_value:,.0f}", 'label': '滞销库存总金额', 'icon': '💰', 'color': 'danger'},
            {'value': high_price_unsold, 'label': '高价滞销品(>50元)', 'icon': '💎', 'color': 'warning'},
            {'value': f"¥{avg_stock_value:,.0f}", 'label': '平均库存金额', 'icon': '📊', 'color': 'info'}
        ]
        
        cards = []
        for config in kpi_configs:
            card = dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div(config['icon'], style={'fontSize': '2.5rem', 'marginBottom': '0.5rem'}),
                        html.H3(config['value'], className="mb-1", style={'fontWeight': 'bold'}),
                        html.P(config['label'], className="text-muted mb-0", style={'fontSize': '0.9rem'})
                    ], className="text-center")
                ])
            ], color=config['color'], outline=True, className="h-100")
            cards.append(dbc.Col(card, style={'flex': '0 0 16.666667%', 'maxWidth': '16.666667%'}, className="mb-3"))
        
        return dbc.Row(cards, style={'display': 'flex', 'flexWrap': 'wrap'})
    
    @staticmethod
    def create_unsold_category_pie(unsold_df):
        """滞销分类分布饼图"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.pie(title="暂无滞销数据"), style={'height': '400px'})
        
        # 按一级分类统计
        category_counts = unsold_df.iloc[:, 3].value_counts().head(10)  # D列:一级分类
        
        fig = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="🍰 滞销分类分布TOP10",
            hole=0.4
        )
        
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>滞销数量: %{value}<br>占比: %{percent}<extra></extra>'
        )
        
        fig.update_layout(
            height=400,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
        )
        
        return dcc.Graph(figure=fig, style={'height': '400px'})
    
    @staticmethod
    def create_unsold_price_distribution(unsold_df):
        """滞销价格带分布柱状图"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.bar(title="暂无数据"), style={'height': '400px'})
        
        # 定义价格带
        price_col = pd.to_numeric(unsold_df.iloc[:, 1], errors='coerce').fillna(0)  # B列:售价
        
        price_bands = [
            ('0-10元', (price_col >= 0) & (price_col < 10)),
            ('10-20元', (price_col >= 10) & (price_col < 20)),
            ('20-50元', (price_col >= 20) & (price_col < 50)),
            ('50-100元', (price_col >= 50) & (price_col < 100)),
            ('100+元', price_col >= 100)
        ]
        
        band_counts = {band: mask.sum() for band, mask in price_bands}
        
        fig = go.Figure([
            go.Bar(
                x=list(band_counts.keys()),
                y=list(band_counts.values()),
                marker=dict(
                    color=list(band_counts.values()),
                    colorscale='Reds',
                    showscale=False
                ),
                text=list(band_counts.values()),
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title="📊 滞销价格带分布",
            xaxis_title="价格带",
            yaxis_title="SKU数量",
            height=450,
            showlegend=False,
            margin=dict(t=80, b=60, l=60, r=40)
        )
        
        return dcc.Graph(figure=fig, style={'height': '450px'})
    
    @staticmethod
    def create_unsold_stock_bubble(unsold_df):
        """滞销库存压力气泡图"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.scatter(title="暂无数据"), style={'height': '500px'})
        
        # 准备数据
        df_plot = unsold_df.copy()
        df_plot['price'] = pd.to_numeric(df_plot.iloc[:, 4], errors='coerce').fillna(0)  # E列:原价
        df_plot['stock'] = pd.to_numeric(df_plot.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        df_plot['stock_value'] = df_plot['price'] * df_plot['stock']
        df_plot['category'] = df_plot.iloc[:, 3]  # D列:一级分类
        df_plot['product_name'] = df_plot.iloc[:, 0]  # A列:商品名称
        
        # 只显示TOP50高风险商品
        df_plot = df_plot.nlargest(50, 'stock_value')
        
        fig = px.scatter(
            df_plot,
            x='price',
            y='stock',
            size='stock_value',
            color='category',
            hover_data={'product_name': True, 'stock_value': ':,.0f'},
            title="🔴 滞销库存压力气泡图 (TOP50)",
            labels={'price': '原价(元)', 'stock': '库存数量', 'category': '一级分类'}
        )
        
        fig.update_traces(
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                         '原价: ¥%{x:.2f}<br>' +
                         '库存: %{y}<br>' +
                         '库存金额: ¥%{customdata[1]}<br>' +
                         '<extra></extra>'
        )
        
        fig.update_layout(
            height=500,
            xaxis_title="原价(元)",
            yaxis_title="库存数量",
            showlegend=True
        )
        
        return dcc.Graph(figure=fig, style={'height': '500px'})
    
    @staticmethod
    def create_unsold_discount_scatter(unsold_df):
        """滞销原因分析矩阵(折扣力度 vs 售价)"""
        if unsold_df.empty:
            return dcc.Graph(figure=px.scatter(title="暂无数据"), style={'height': '400px'})
        
        # 准备数据
        df_plot = unsold_df.copy()
        df_plot['price'] = pd.to_numeric(df_plot.iloc[:, 1], errors='coerce').fillna(0)  # B列:售价
        df_plot['original_price'] = pd.to_numeric(df_plot.iloc[:, 4], errors='coerce').fillna(0)  # E列:原价
        
        # 计算折扣力度
        df_plot['discount_rate'] = ((df_plot['original_price'] - df_plot['price']) / df_plot['original_price'] * 100).fillna(0)
        df_plot['has_discount'] = df_plot['discount_rate'] > 0
        df_plot['product_name'] = df_plot.iloc[:, 0]
        
        # 标记折扣状态
        df_plot['discount_status'] = df_plot['has_discount'].map({True: '有折扣', False: '无折扣'})
        
        fig = px.scatter(
            df_plot,
            x='discount_rate',
            y='price',
            color='discount_status',
            hover_data={'product_name': True},
            title="🔍 滞销原因分析矩阵",
            labels={'discount_rate': '折扣力度(%)', 'price': '售价(元)', 'discount_status': '折扣状态'},
            color_discrete_map={'有折扣': '#28a745', '无折扣': '#dc3545'}
        )
        
        fig.update_traces(
            hovertemplate='<b>%{customdata[0]}</b><br>' +
                         '售价: ¥%{y:.2f}<br>' +
                         '折扣力度: %{x:.1f}%<br>' +
                         '<extra></extra>'
        )
        
        fig.update_layout(height=400)
        
        return dcc.Graph(figure=fig, style={'height': '400px'})
    
    @staticmethod
    def create_unsold_top_table(unsold_df):
        """创建TOP20高风险滞销商品表格"""
        if unsold_df.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        # 准备数据
        df_table = unsold_df.copy()
        df_table['product_name'] = df_table.iloc[:, 0]  # A列
        df_table['category'] = df_table.iloc[:, 3]  # D列
        df_table['price'] = pd.to_numeric(df_table.iloc[:, 1], errors='coerce').fillna(0)  # B列
        df_table['original_price'] = pd.to_numeric(df_table.iloc[:, 4], errors='coerce').fillna(0)  # E列
        df_table['stock'] = pd.to_numeric(df_table.iloc[:, 5], errors='coerce').fillna(0)  # F列
        df_table['stock_value'] = df_table['original_price'] * df_table['stock']
        df_table['discount_rate'] = ((df_table['original_price'] - df_table['price']) / df_table['original_price'] * 100).fillna(0)
        
        # 按库存金额降序
        df_table = df_table.nlargest(20, 'stock_value')
        
        # 生成建议操作
        def get_suggestion(row):
            if row['stock_value'] > 500:
                return "🔥 建议清仓"
            elif row['discount_rate'] == 0:
                return "💰 建议促销"
            elif row['price'] < 20 and row['stock'] > 20:
                return "🗑️ 建议下架"
            else:
                return "📊 需要调研"
        
        df_table['suggestion'] = df_table.apply(get_suggestion, axis=1)
        
        # 构建表格
        table_data = []
        for idx, row in df_table.iterrows():
            table_data.append(html.Tr([
                html.Td(row['product_name'], style={'maxWidth': '200px', 'overflow': 'hidden', 'textOverflow': 'ellipsis'}),
                html.Td(row['category']),
                html.Td(f"¥{row['price']:.2f}"),
                html.Td(f"¥{row['original_price']:.2f}"),
                html.Td(f"{row['discount_rate']:.1f}%"),
                html.Td(str(int(row['stock']))),
                html.Td(f"¥{row['stock_value']:,.0f}", style={'fontWeight': 'bold', 'color': '#dc3545'}),
                html.Td(row['suggestion'], style={'fontWeight': 'bold'})
            ]))
        
        table = dbc.Table([
            html.Thead(html.Tr([
                html.Th("商品名称"),
                html.Th("一级分类"),
                html.Th("售价"),
                html.Th("原价"),
                html.Th("折扣力度"),
                html.Th("库存"),
                html.Th("库存金额"),
                html.Th("建议操作")
            ])),
            html.Tbody(table_data)
        ], bordered=True, hover=True, responsive=True, striped=True, size='sm')
        
        return table
    
    @staticmethod
    def generate_unsold_insights(unsold_df, total_skus):
        """生成滞销商品智能洞察"""
        if unsold_df.empty:
            return []
        
        insights = []
        
        # 1. 滞销率分析
        unsold_ratio = len(unsold_df) / total_skus * 100 if total_skus > 0 else 0
        if unsold_ratio > 30:
            insights.append({
                'title': '⚠️ 滞销率较高',
                'content': f"滞销率{unsold_ratio:.1f}%，建议重点检查SKU结构",
                'level': 'danger'
            })
        
        # 2. 分类分析
        category_counts = unsold_df.iloc[:, 3].value_counts()
        if len(category_counts) > 0:
            top_category = category_counts.index[0]
            top_count = category_counts.values[0]
            insights.append({
                'title': '📉 滞销分类TOP1',
                'content': f"{top_category}分类滞销最多({top_count}个)，建议重点关注",
                'level': 'warning'
            })
        
        # 3. 高价滞销品
        price_col = pd.to_numeric(unsold_df.iloc[:, 4], errors='coerce').fillna(0)
        high_price_count = (price_col > 100).sum()
        if high_price_count > 0:
            stock_col = pd.to_numeric(unsold_df.iloc[:, 5], errors='coerce').fillna(0)
            high_price_value = (price_col[price_col > 100] * stock_col[price_col > 100]).sum()
            insights.append({
                'title': '💰 高价滞销品警告',
                'content': f"{high_price_count}个高价滞销品(>100元)占用资金¥{high_price_value:,.0f}，建议加大促销",
                'level': 'danger'
            })
        
        # 4. 无折扣商品
        original_price_col = pd.to_numeric(unsold_df.iloc[:, 4], errors='coerce').fillna(0)
        sale_price_col = pd.to_numeric(unsold_df.iloc[:, 1], errors='coerce').fillna(0)
        no_discount_count = (original_price_col == sale_price_col).sum()
        if no_discount_count > 0:
            insights.append({
                'title': '🏷️ 无折扣建议',
                'content': f"{no_discount_count}个滞销商品无折扣，建议设置促销活动",
                'level': 'info'
            })
        
        # 5. 高库存警告
        stock_col = pd.to_numeric(unsold_df.iloc[:, 5], errors='coerce').fillna(0)
        high_stock_count = (stock_col > 50).sum()
        if high_stock_count > 0:
            insights.append({
                'title': '📦 高库存警告',
                'content': f"{high_stock_count}个商品库存>50且滞销，建议清仓处理",
                'level': 'warning'
            })
        
        # 格式化为展示组件
        formatted_insights = []
        for insight in insights:
            color_map = {
                'danger': 'danger',
                'warning': 'warning',
                'info': 'info',
                'success': 'success'
            }
            formatted_insights.append(
                dbc.Alert([
                    html.H5(insight['title'], className="alert-heading"),
                    html.P(insight['content'], className="mb-0")
                ], color=color_map.get(insight['level'], 'info'))
            )
        
        return html.Div(formatted_insights) if formatted_insights else html.Div()

    @staticmethod
    def create_cost_analysis_charts(cost_summary, high_margin, low_margin):
        """创建成本&毛利分析图表"""
        if cost_summary.empty:
            return html.Div("暂无成本数据", className="alert alert-info")
        
        try:
            # ========== 第一部分: 成本分析汇总表 ==========
            cost_summary_display = cost_summary.copy()
            
            # 剔除"成本销售额"列
            if '成本销售额' in cost_summary_display.columns:
                cost_summary_display = cost_summary_display.drop(columns=['成本销售额'])
            
            # 格式化数值列（优化版：区分货币、百分比、纯数字）
            for col in cost_summary_display.columns:
                if '销售额' in col or '成本销售额' in col:
                    # 销售额、成本销售额格式化为货币
                    cost_summary_display[col] = cost_summary_display[col].apply(
                        lambda x: f'¥{x:,.2f}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                    )
                elif '毛利率' in col or '贡献度' in col:
                    # 毛利率、贡献度格式化为百分比
                    cost_summary_display[col] = cost_summary_display[col].apply(
                        lambda x: f'{x:.2%}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                    )
                elif '毛利' in col and '毛利率' not in col:
                    # 毛利（总毛利、定价毛利）格式化为货币，但排除毛利率
                    cost_summary_display[col] = cost_summary_display[col].apply(
                        lambda x: f'¥{x:,.2f}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                    )
            
            cost_table = dbc.Table.from_dataframe(
                cost_summary_display.head(20),
                striped=True,
                bordered=True,
                hover=True,
                responsive=True,
                className="align-middle text-center",
                style={'fontSize': '14px'}
            )
            
            # ========== 成本分析汇总可视化图表 ==========
            cost_viz_charts = DashboardComponents.create_cost_summary_visualizations(cost_summary)
            
            # 生成成本分析汇总洞察
            cost_summary_insights = DashboardComponents.generate_cost_summary_insights(cost_summary)
            
            # ========== 第二部分: 高毛利商品 TOP50 ==========
            high_margin_section = html.Div()
            if not high_margin.empty:
                high_margin_display = high_margin.head(20).copy()
                
                # 优化格式化逻辑：区分毛利率、价格、毛利
                for col in high_margin_display.columns:
                    if '毛利率' in col or '折扣' in col:
                        # 毛利率、折扣 → 百分比格式
                        high_margin_display[col] = high_margin_display[col].apply(
                            lambda x: f'{x:.2%}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                        )
                    elif '价' in col or '销售额' in col:
                        # 售价、原价、销售额 → 货币格式
                        high_margin_display[col] = high_margin_display[col].apply(
                            lambda x: f'¥{x:,.2f}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                        )
                    elif '毛利' in col and '毛利率' not in col:
                        # 毛利（不含毛利率）→ 货币格式，保留2位小数
                        high_margin_display[col] = high_margin_display[col].apply(
                            lambda x: f'¥{x:.2f}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                        )
                
                high_margin_table = dbc.Table.from_dataframe(
                    high_margin_display,
                    striped=True,
                    bordered=True,
                    hover=True,
                    responsive=True,
                    className="align-middle text-center",
                    style={'fontSize': '13px'}
                )
                
                # 生成高毛利商品洞察
                high_margin_insights = DashboardComponents.generate_high_margin_insights(high_margin)
                
                high_margin_section = html.Div([
                    html.H4("⭐ 高毛利商品TOP20 (售价毛利率≥30%)", className="mb-3", 
                           style={'color': '#28a745', 'fontWeight': 'bold'}),
                    high_margin_table,
                    html.Div(high_margin_insights, className="mt-3")
                ], className="mb-4")
            
            # ========== 第三部分: 低毛利预警商品 ==========
            low_margin_section = html.Div()
            if not low_margin.empty:
                low_margin_display = low_margin.head(20).copy()
                
                # 优化格式化逻辑：区分毛利率、价格、毛利
                for col in low_margin_display.columns:
                    if '毛利率' in col or '折扣' in col:
                        # 毛利率、折扣 → 百分比格式
                        low_margin_display[col] = low_margin_display[col].apply(
                            lambda x: f'{x:.2%}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                        )
                    elif '价' in col or '销售额' in col:
                        # 售价、原价、销售额 → 货币格式
                        low_margin_display[col] = low_margin_display[col].apply(
                            lambda x: f'¥{x:,.2f}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                        )
                    elif '毛利' in col and '毛利率' not in col:
                        # 毛利（不含毛利率）→ 货币格式，保留2位小数
                        low_margin_display[col] = low_margin_display[col].apply(
                            lambda x: f'¥{x:.2f}' if pd.notna(x) and isinstance(x, (int, float)) else str(x)
                        )
                
                low_margin_table = dbc.Table.from_dataframe(
                    low_margin_display,
                    striped=True,
                    bordered=True,
                    hover=True,
                    responsive=True,
                    className="align-middle text-center",
                    style={'fontSize': '13px'}
                )
                
                # 生成低毛利预警洞察
                low_margin_insights = DashboardComponents.generate_low_margin_insights(low_margin)
                
                low_margin_section = html.Div([
                    html.H4("⚠️ 低毛利预警商品TOP20 (售价毛利率<10%)", className="mb-3", 
                           style={'color': '#dc3545', 'fontWeight': 'bold'}),
                    low_margin_table,
                    html.Div(low_margin_insights, className="mt-3")
                ], className="mb-4")
            
            # 组合所有组件
            return html.Div([
                html.H4("📊 成本分析汇总", className="mb-3", style={'fontWeight': 'bold'}),
                cost_table,
                html.Div(cost_summary_insights, className="mt-3"),
                html.Hr(style={'margin': '30px 0'}),
                # 成本分析汇总可视化图表
                html.H4("📈 成本&毛利率可视化分析", className="mb-3", style={'fontWeight': 'bold'}),
                cost_viz_charts,
                html.Hr(style={'margin': '30px 0'}),
                high_margin_section,
                low_margin_section
            ])
        
        except Exception as e:
            import traceback
            print(f"成本图表生成错误: {e}")
            print(traceback.format_exc())
            return dbc.Alert(f"图表生成失败: {str(e)}", color="danger")
    
    @staticmethod
    def create_cost_summary_visualizations(cost_summary):
        """创建成本分析汇总的可视化图表"""
        try:
            if cost_summary.empty or len(cost_summary) <= 1:
                return html.Div("暂无可视化数据", className="alert alert-info")
            
            # 排除"全部分类汇总"行
            df = cost_summary[~cost_summary.iloc[:, 1].str.contains('全部|汇总', na=False)].copy()
            
            if df.empty:
                return html.Div("暂无分类数据", className="alert alert-info")
            
            # 获取列名
            category_col = df.columns[1]  # 第二列是分类名
            selling_margin_col = [col for col in df.columns if '售价毛利率' in col][0] if any('售价毛利率' in col for col in df.columns) else None
            pricing_margin_col = [col for col in df.columns if '定价毛利率' in col][0] if any('定价毛利率' in col for col in df.columns) else None
            contribution_col = [col for col in df.columns if '贡献度' in col][0] if any('贡献度' in col for col in df.columns) else None
            revenue_col = [col for col in df.columns if '售价销售额' in col][0] if any('售价销售额' in col for col in df.columns) else None
            original_revenue_col = [col for col in df.columns if '原价销售额' in col][0] if any('原价销售额' in col for col in df.columns) else None
            
            # 所有分类用于柱状图，TOP5用于饼图
            df_all = df  # 所有分类
            df_top5 = df.nlargest(5, contribution_col) if contribution_col else df.head(5)  # TOP5贡献分类
            
            charts = []
            
            # ========== 图表1: 售价毛利率 vs 定价毛利率对比（所有分类） ==========
            if selling_margin_col and pricing_margin_col:
                fig_margin = go.Figure()
                
                fig_margin.add_trace(go.Bar(
                    name='售价毛利率',
                    x=df_all[category_col],
                    y=df_all[selling_margin_col] * 100,
                    marker_color='#3b82f6',
                    text=[f'{v:.1f}%' for v in df_all[selling_margin_col] * 100],
                    textposition='outside',
                    textfont=dict(size=10)
                ))
                
                fig_margin.add_trace(go.Bar(
                    name='定价毛利率',
                    x=df_all[category_col],
                    y=df_all[pricing_margin_col] * 100,
                    marker_color='#10b981',
                    text=[f'{v:.1f}%' for v in df_all[pricing_margin_col] * 100],
                    textposition='outside',
                    textfont=dict(size=10)
                ))
                
                fig_margin.update_layout(
                    title=dict(text='各分类毛利率对比（实际售价 vs 原价定价）', font=dict(size=14, color='#2c3e50')),
                    xaxis=dict(
                        title='',
                        tickangle=-45,
                        tickfont=dict(size=11)
                    ),
                    yaxis_title='毛利率 (%)',
                    barmode='group',
                    height=700,
                    margin=dict(l=80, r=80, t=100, b=150),
                    hovermode='x unified',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
                    paper_bgcolor='white',
                    plot_bgcolor='white'
                )
                
                charts.append(dcc.Graph(
                    figure=fig_margin, 
                    className="mb-4",
                    style={'height': '700px', 'width': '100%'},
                    config={'displayModeBar': False, 'responsive': True}
                ))
            
            # ========== 图表2: 毛利贡献度TOP5（饼图） ==========
            if contribution_col:
                fig_contribution = go.Figure(data=[go.Pie(
                    labels=df_top5[category_col],
                    values=df_top5[contribution_col] * 100,
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='auto',
                    textfont=dict(size=11),
                    marker=dict(colors=px.colors.qualitative.Set3)
                )])
                
                fig_contribution.update_layout(
                    title=dict(text='毛利贡献度TOP5分类', font=dict(size=14, color='#2c3e50')),
                    height=600,
                    margin=dict(l=80, r=80, t=100, b=120),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom", 
                        y=-0.2,
                        xanchor="center", 
                        x=0.5,
                        font=dict(size=10)
                    ),
                    paper_bgcolor='white',
                    plot_bgcolor='white'
                )
                
                charts.append(dcc.Graph(
                    figure=fig_contribution, 
                    className="mb-4",
                    style={'height': '600px', 'width': '100%'},
                    config={'displayModeBar': False, 'responsive': True}
                ))
            
            # 返回所有图表 - 用Div包裹但强制100%宽度
            if charts:
                return html.Div([
                    dbc.Row([
                        dbc.Col(charts[0], width=12) if len(charts) > 0 else None,
                    ], className="mb-4"),
                    dbc.Row([
                        dbc.Col(charts[1], width=12) if len(charts) > 1 else None,
                    ], className="mb-4"),
                ], style={'width': '100%', 'margin': '0', 'padding': '0'})
            else:
                return html.Div("暂无可视化图表", className="alert alert-info")
        
        except Exception as e:
            import traceback
            print(f"成本汇总可视化生成错误: {e}")
            print(traceback.format_exc())
            return dbc.Alert(f"可视化生成失败: {str(e)}", color="warning")
    
    @staticmethod
    def generate_cost_summary_insights(cost_summary):
        """生成成本分析汇总的洞察"""
        insights = []
        try:
            if len(cost_summary) <= 1:
                return html.Div()
            
            # 排除"全部分类汇总"行
            df = cost_summary[~cost_summary.iloc[:, 1].str.contains('全部|汇总', na=False)]
            
            if df.empty:
                return html.Div()
            
            # 1. 最高售价毛利率分类
            margin_col = [col for col in df.columns if '售价毛利率' in col][0] if any('售价毛利率' in col for col in df.columns) else None
            if margin_col:
                top_margin = df.nlargest(1, margin_col).iloc[0]
                category = top_margin.iloc[1]  # 第二列是分类名
                margin_rate = top_margin[margin_col]
                insights.append({
                    'icon': '🏆',
                    'text': f'最高售价毛利率分类: {category} ({margin_rate:.1%})',
                    'level': 'success'
                })
            
            # 2. 最低售价毛利率分类
            if margin_col:
                bottom_margin = df.nsmallest(1, margin_col).iloc[0]
                category = bottom_margin.iloc[1]
                margin_rate = bottom_margin[margin_col]
                insights.append({
                    'icon': '⚠️',
                    'text': f'最低售价毛利率分类: {category} ({margin_rate:.1%}) - 需优化',
                    'level': 'warning'
                })
            
            # 3. 定价毛利率vs售价毛利率对比
            pricing_margin_col = [col for col in df.columns if '定价毛利率' in col][0] if any('定价毛利率' in col for col in df.columns) else None
            if pricing_margin_col and margin_col:
                # 计算全部分类的加权平均
                total_row = cost_summary[cost_summary.iloc[:, 1].str.contains('全部|汇总', na=False)]
                if not total_row.empty:
                    avg_pricing = total_row[pricing_margin_col].iloc[0]
                    avg_selling = total_row[margin_col].iloc[0]
                    discount_impact = avg_pricing - avg_selling
                    insights.append({
                        'icon': '🔄',
                        'text': f'定价毛利率 {avg_pricing:.1%} vs 售价毛利率 {avg_selling:.1%}，促销影响 {discount_impact:.1%}',
                        'level': 'info'
                    })
            
            # 4. 毛利贡献TOP1
            margin_value_col = [col for col in df.columns if '毛利' in col and '毛利率' not in col and '贡献' not in col and '定价' not in col][0] if any('毛利' in col and '毛利率' not in col and '贡献' not in col and '定价' not in col for col in df.columns) else None
            if margin_value_col:
                top_contributor = df.nlargest(1, margin_value_col).iloc[0]
                category = top_contributor.iloc[1]
                margin_value = top_contributor[margin_value_col]
                insights.append({
                    'icon': '💰',
                    'text': f'毛利贡献TOP1: {category} (¥{margin_value:,.0f})',
                    'level': 'info'
                })
            
            return DashboardComponents.create_insights_panel(insights)
        except Exception as e:
            print(f"成本汇总洞察生成错误: {e}")
            return html.Div()
    
    @staticmethod
    def generate_high_margin_insights(high_margin):
        """生成高毛利商品的洞察"""
        insights = []
        try:
            if high_margin.empty:
                return html.Div()
            
            # 1. 商品数量统计
            total_count = len(high_margin)
            insights.append({
                'icon': '📊',
                'text': f'共发现 {total_count} 个高毛利商品(售价毛利率≥30%)',
                'level': 'success'
            })
            
            # 2. 平均售价毛利率和定价毛利率
            selling_margin_col = [col for col in high_margin.columns if '售价毛利率' in col][0] if any('售价毛利率' in col for col in high_margin.columns) else None
            pricing_margin_col = [col for col in high_margin.columns if '定价毛利率' in col][0] if any('定价毛利率' in col for col in high_margin.columns) else None
            
            if selling_margin_col:
                avg_selling_margin = high_margin[selling_margin_col].mean()
                insights.append({
                    'icon': '⭐',
                    'text': f'平均售价毛利率: {avg_selling_margin:.1%} - 表现优秀',
                    'level': 'success'
                })
            
            if pricing_margin_col:
                avg_pricing_margin = high_margin[pricing_margin_col].mean()
                insights.append({
                    'icon': '💡',
                    'text': f'平均定价毛利率: {avg_pricing_margin:.1%} (按原价计算)',
                    'level': 'info'
                })
            
            # 3. TOP1商品
            if len(high_margin) > 0:
                top_product = high_margin.iloc[0]
                product_name = top_product.iloc[0] if len(top_product) > 0 else '未知'
                if margin_col and margin_col in top_product.index:
                    top_margin_rate = top_product[margin_col]
                    insights.append({
                        'icon': '🥇',
                        'text': f'毛利率第一: {product_name[:20]}... ({top_margin_rate:.1%})',
                        'level': 'info'
                    })
            
            # 4. 建议
            insights.append({
                'icon': '💡',
                'text': '建议: 加大高毛利商品的推广力度，通过促销活动提升销量',
                'level': 'primary'
            })
            
            return DashboardComponents.create_insights_panel(insights)
        except Exception as e:
            print(f"高毛利洞察生成错误: {e}")
            return html.Div()
    
    @staticmethod
    def generate_low_margin_insights(low_margin):
        """生成低毛利预警商品的洞察"""
        insights = []
        try:
            if low_margin.empty:
                return html.Div()
            
            # 1. 预警商品数量
            total_count = len(low_margin)
            insights.append({
                'icon': '⚠️',
                'text': f'发现 {total_count} 个低毛利预警商品(售价毛利率<10%)',
                'level': 'danger'
            })
            
            # 2. 平均售价毛利率和定价毛利率
            selling_margin_col = [col for col in low_margin.columns if '售价毛利率' in col][0] if any('售价毛利率' in col for col in low_margin.columns) else None
            pricing_margin_col = [col for col in low_margin.columns if '定价毛利率' in col][0] if any('定价毛利率' in col for col in low_margin.columns) else None
            
            if selling_margin_col:
                avg_selling_margin = low_margin[selling_margin_col].mean()
                insights.append({
                    'icon': '📉',
                    'text': f'平均售价毛利率: {avg_selling_margin:.1%} - 严重偏低',
                    'level': 'danger'
                })
            
            if pricing_margin_col:
                avg_pricing_margin = low_margin[pricing_margin_col].mean()
                insights.append({
                    'icon': '💰',
                    'text': f'平均定价毛利率: {avg_pricing_margin:.1%} (按原价可实现)',
                    'level': 'warning'
                })
            
            # 3. 负毛利商品统计
            if selling_margin_col:
                negative_count = (low_margin[selling_margin_col] < 0).sum()
                if negative_count > 0:
                    insights.append({
                        'icon': '🚨',
                        'text': f'其中 {negative_count} 个商品毛利为负(亏损销售) - 售价低于成本',
                        'level': 'danger'
                    })
            
            # 4. 建议
            insights.append({
                'icon': '💡',
                'text': '建议: 对比定价毛利率和售价毛利率差异，考虑调整促销策略或优化成本',
                'level': 'warning'
            })
            
            return DashboardComponents.create_insights_panel(insights)
        except Exception as e:
            print(f"低毛利洞察生成错误: {e}")
            return html.Div()
    
    @staticmethod
    def generate_cost_insights(cost_summary):
        """生成成本分析智能洞察"""
        insights = []
        
        try:
            if cost_summary.empty:
                return html.Div()
            
            # 1. 平均毛利率分析
            if '毛利率' in cost_summary.columns or '平均毛利率' in cost_summary.columns:
                margin_col = '毛利率' if '毛利率' in cost_summary.columns else '平均毛利率'
                avg_margin = cost_summary[margin_col].mean()
                
                if avg_margin < 0.15:
                    insights.append({
                        'title': '⚠️ 毛利率偏低',
                        'content': f"平均毛利率{avg_margin:.1%}，低于行业标准(25-35%)，建议优化定价或降低成本",
                        'level': 'danger'
                    })
                elif avg_margin < 0.25:
                    insights.append({
                        'title': '📊 毛利率一般',
                        'content': f"平均毛利率{avg_margin:.1%}，处于合理区间，但仍有提升空间",
                        'level': 'warning'
                    })
                else:
                    insights.append({
                        'title': '✅ 毛利率健康',
                        'content': f"平均毛利率{avg_margin:.1%}，达到良好水平，请继续保持",
                        'level': 'success'
                    })
            
            # 2. 分类毛利贡献分析
            if len(cost_summary) > 1:
                if '毛利' in cost_summary.columns:
                    top_category = cost_summary.nlargest(1, '毛利').iloc[0]
                    category_name = top_category.iloc[0] if len(top_category) > 0 else '未知'
                    margin_value = top_category['毛利'] if '毛利' in top_category.index else 0
                    
                    insights.append({
                        'title': '💰 毛利贡献TOP1',
                        'content': f"{category_name}分类贡献毛利¥{margin_value:,.0f}，是主要利润来源",
                        'level': 'info'
                    })
            
            # 格式化为展示组件
            formatted_insights = []
            for insight in insights:
                color_map = {
                    'danger': 'danger',
                    'warning': 'warning',
                    'info': 'info',
                    'success': 'success'
                }
                formatted_insights.append(
                    dbc.Alert([
                        html.H5(insight['title'], className="alert-heading"),
                        html.P(insight['content'], className="mb-0")
                    ], color=color_map.get(insight['level'], 'info'))
                )
            
            return html.Div(formatted_insights) if formatted_insights else html.Div()
        
        except Exception as e:
            print(f"成本洞察生成错误: {e}")
            return html.Div()


# 初始化数据加载器
loader = DataLoader(DEFAULT_REPORT_PATH)

# 初始化门店管理器和分析器
store_manager = StoreManager()
analyzer = get_store_analyzer()

# 初始化对比数据加载器
comparison_loader = ComparisonDataLoader()

# 初始化Dash应用 - 使用国内CDN加速
app = dash.Dash(
    __name__, 
    external_stylesheets=[
        'https://cdn.bootcdn.net/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css',  # 国内CDN
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',  # 备用CDN1
        dbc.themes.BOOTSTRAP  # 原有CDN作为最后备份
    ],
    suppress_callback_exceptions=True  # 【修复】允许回调引用动态生成的组件ID
)
app.title = APP_TITLE

# 自定义CSS样式 - 添加多CDN备份
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no, maximum-scale=1, user-scalable=no">
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/bootstrap-icons/1.11.1/font/bootstrap-icons.min.css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
            /* 强制响应式布局 - 确保在CSS加载失败时也能正常显示 */
            * {
                box-sizing: border-box;
            }
            
            body {
                margin: 0;
                padding: 0;
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* Bootstrap Grid 备用系统 */
            .container, .container-fluid {
                width: 100%;
                padding-right: 15px;
                padding-left: 15px;
                margin-right: auto;
                margin-left: auto;
            }
            
            .row {
                display: flex;
                flex-wrap: wrap;
                margin-right: -15px;
                margin-left: -15px;
            }
            
            [class*="col-"] {
                position: relative;
                width: 100%;
                padding-right: 15px;
                padding-left: 15px;
            }
            
            /* 响应式列宽 - 完整Bootstrap 5规范 */
            .col-xs-12 { flex: 0 0 100%; max-width: 100%; }
            
            @media (min-width: 576px) {
                .col-sm-6 { flex: 0 0 50%; max-width: 50%; }
            }
            
            @media (min-width: 768px) {
                .col-md-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
            }
            
            @media (min-width: 992px) {
                .col-lg-3 { flex: 0 0 25%; max-width: 25%; }
                .col-lg-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
            }
            
            /* 固定列宽类 - Bootstrap标准 */
            .col-1 { flex: 0 0 8.333333%; max-width: 8.333333%; }
            .col-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
            .col-3 { flex: 0 0 25%; max-width: 25%; }
            .col-4 { flex: 0 0 33.333333%; max-width: 33.333333%; }
            .col-6 { flex: 0 0 50%; max-width: 50%; }
            .col-12 { flex: 0 0 100%; max-width: 100%; }
            
            @media (min-width: 1200px) {
                .col-xl-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
                .col-xl-3 { flex: 0 0 25%; max-width: 25%; }
            }
            
            @media (min-width: 1400px) {
                .col-xxl-2 { flex: 0 0 16.666667%; max-width: 16.666667%; }
            }
            
            /* 卡片样式优化 */
            .card {
                position: relative;
                display: flex;
                flex-direction: column;
                min-width: 0;
                word-wrap: break-word;
                background-color: #fff;
                background-clip: border-box;
                border: 1px solid rgba(0,0,0,.125);
                border-radius: 0.5rem;
                height: 100%;
                box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            
            .card:hover {
                transform: translateY(-2px);
                box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
            }
            
            /* 图表容器响应式 */
            .dash-graph, .js-plotly-plot {
                width: 100% !important;
                max-width: 100% !important;
            }
            
            /* 移动端优化 */
            @media (max-width: 575.98px) {
                body { font-size: 14px; }
                h1 { font-size: 1.5rem !important; }
                h2 { font-size: 1.3rem !important; }
                h3 { font-size: 1.1rem !important; }
                .section-title { font-size: 1.2rem; }
                .card-body { padding: 0.75rem; }
            }
            
            /* Card 样式备用 */
            .card {
                position: relative;
                display: flex;
                flex-direction: column;
                min-width: 0;
                word-wrap: break-word;
                background-color: #fff;
                background-clip: border-box;
                border: 1px solid rgba(0,0,0,.125);
                border-radius: 0.375rem;
                height: 100%;
            }
            
            .card-body {
                flex: 1 1 auto;
                padding: 1rem;
            }
            
            .h-100 {
                height: 100% !important;
            }
            
            .mb-3 {
                margin-bottom: 1rem !important;
            }
            
            .g-3 {
                gap: 1rem;
            }
            
            /* 容器响应式优化 */
            .main-container {
                padding: 20px;
                max-width: 100%;
                margin: 0 auto;
            }
            
            @media (max-width: 767.98px) {
                .main-container {
                    padding: 10px;
                }
            }
            
            /* 章节标题响应式 */
            .section-title {
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
                font-weight: bold;
            }
            .chart-section {
                background: white;
                border-radius: 10px;
                padding: 25px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: 1px solid #e9ecef;
            }
            
            @media (max-width: 767.98px) {
                .chart-section {
                    padding: 15px;
                    margin-bottom: 20px;
                }
                .section-title {
                    font-size: 1.2rem;
                    margin-bottom: 20px;
                }
            }
            
            /* Plotly图表响应式 */
            .js-plotly-plot .plotly {
                width: 100% !important;
                height: auto !important;
            }
            
            .js-plotly-plot .plotly .main-svg {
                width: 100% !important;
            }
            
            /* PDF生成优化样式 */
            #pdf-export-status {
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
            }
            #pdf-export-status.generating {
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffc107;
            }
            #pdf-export-status.success {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #28a745;
            }
            #pdf-export-status.error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #dc3545;
            }
            
            /* KPI卡片问号图标hover效果 */
            .bi-question-circle:hover {
                opacity: 1 !important;
                color: #007bff !important;
                transform: scale(1.15);
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ========== 图片处理API ==========
from flask import request, jsonify
from modules.utils.image_processor import white_to_transparent

@app.server.route('/api/process-image', methods=['POST'])
def process_image_api():
    """处理图片API - 将白色背景转换为透明"""
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        
        if not image_data:
            return jsonify({'success': False, 'error': '未提供图片数据'})
        
        # 处理图片
        transparent_image = white_to_transparent(image_data)
        
        return jsonify({
            'success': True,
            'image': transparent_image
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 应用布局
app.layout = html.Div([
    # 隐藏的Store组件用于触发所有图表更新
    dcc.Store(id='upload-trigger', data=0),
    dcc.Store(id='category-filter-state', data=[]),  # 存储选中的分类
    dcc.Store(id='data-source-store', data='own-store'),  # 存储当前数据源: 'own-store' 或 'competitor'
    
    # ========== 新对比模式Store组件 ==========
    dcc.Store(id='comparison-mode', data='off'),  # 对比模式状态: 'off' | 'on'
    dcc.Store(id='selected-competitor', data=None),  # 选中的竞对门店名称
    dcc.Store(id='competitor-data-cache', data={}),  # 竞对数据缓存
    
    # ========== 全局标题区域（始终显示） ==========
    html.Div([
        html.Div([
            html.H1("📊 O2O门店数据分析看板 v2.0", className="text-center mb-4", 
                   style={'color': '#2c3e50', 'fontWeight': 'bold', 'display': 'inline-block', 'width': '100%'}),
            html.Div([
                html.Button(
                    "🖼️ 导出PNG图片", 
                    id="export-png-btn",
                    n_clicks=0,
                    style={
                        'position': 'absolute',
                        'right': '220px',
                        'top': '20px',
                        'padding': '12px 30px',
                        'backgroundColor': '#17a2b8',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '8px',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'cursor': 'pointer',
                        'boxShadow': '0 4px 6px rgba(23, 162, 184, 0.3)',
                        'transition': 'all 0.3s ease'
                    },
                    title="导出当前看板为高清PNG图片"
                ),
                html.Button(
                    "📄 下载PDF报告", 
                    id="export-pdf-btn",
                    n_clicks=0,
                    style={
                        'position': 'absolute',
                        'right': '30px',
                        'top': '20px',
                        'padding': '12px 30px',
                        'backgroundColor': '#28a745',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '8px',
                        'fontSize': '16px',
                        'fontWeight': 'bold',
                        'cursor': 'pointer',
                        'boxShadow': '0 4px 6px rgba(40, 167, 69, 0.3)',
                        'transition': 'all 0.3s ease'
                    },
                    title="一键生成并下载高质量PDF报告（包含所有图表和分析）"
                ),
                dcc.Download(id='download-pdf'),
                dcc.Download(id='download-png'),
                html.Div(id='pdf-export-status', style={'textAlign': 'right', 'marginTop': '70px', 'marginRight': '30px', 'fontSize': '13px', 'fontWeight': 'bold'}),
                html.Div(id='png-export-status', style={'textAlign': 'right', 'marginTop': '95px', 'marginRight': '30px', 'fontSize': '13px', 'fontWeight': 'bold'})
            ], style={'position': 'relative'})
        ], style={'position': 'relative'}),
        html.P("智能自适应 · 数据驱动 · 一目了然", 
              className="text-center text-muted mb-4")
    ]),
    
    # ========== TAB切换区域（始终显示） ==========
    html.Div([
        dbc.Tabs(
            id='main-tabs',
            active_tab='tab-own-store',
            children=[
                dbc.Tab(label='🏪 本店数据看板', tab_id='tab-own-store', 
                       label_style={'fontSize': '18px', 'fontWeight': 'bold', 'padding': '15px 30px'}),
                dbc.Tab(label='🎯 竞对数据看板', tab_id='tab-competitor',
                       label_style={'fontSize': '18px', 'fontWeight': 'bold', 'padding': '15px 30px'}),
                dbc.Tab(label='🏙️ 城市新增竞对分析', tab_id='tab-city-competitor',
                       label_style={'fontSize': '18px', 'fontWeight': 'bold', 'padding': '15px 30px'}),
            ],
            style={'marginBottom': '20px'}
        )
    ]),
    
    # ========== 单店看板内容区域（本店TAB和竞对TAB共用） ==========
    html.Div([
        
        # 原始数据上传分析区域
        html.Div([
            html.Label("� 上传原始数据并分析:", style={'fontWeight': 'bold', 'fontSize': '18px', 'color': '#28a745', 'marginBottom': '15px'}),
            dbc.Row([
                dbc.Col([
                    dcc.Upload(
                        id='upload-raw-data',
                        children=html.Div([
                            html.Div("📁 拖拽或点击上传门店原始数据", style={'fontSize': '16px', 'fontWeight': 'bold', 'color': '#28a745'}),
                            html.Div("支持格式: Excel (.xlsx) 或 CSV (.csv)", style={'fontSize': '13px', 'color': '#666', 'marginTop': '5px'}),
                            html.Div("必须包含: 商品名、售价、销量、分类", style={'fontSize': '12px', 'color': '#999', 'marginTop': '3px'})
                        ], style={'padding': '20px'}),
                        style={
                            'width': '100%',
                            'height': '120px',
                            'borderWidth': '3px',
                            'borderStyle': 'dashed',
                            'borderRadius': '10px',
                            'textAlign': 'center',
                            'borderColor': '#28a745',
                            'backgroundColor': '#f0fff4',
                            'cursor': 'pointer',
                            'transition': 'all 0.3s ease'
                        },
                        multiple=False
                    ),
                ], width=8),
                dbc.Col([
                    html.Label("📝 门店名称:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                    dcc.Input(
                        id='store-name-input',
                        type='text',
                        placeholder='输入门店名称(如: 北京朝阳店)',
                        style={
                            'width': '100%', 
                            'padding': '12px', 
                            'borderRadius': '8px', 
                            'border': '2px solid #ced4da',
                            'fontSize': '14px'
                        }
                    ),
                    html.Div([
                        dbc.Button(
                            [html.I(className="fas fa-play-circle", style={'marginRight': '8px'}), "开始分析"],
                            id='btn-run-analysis',
                            color='success',
                            className='mt-3',
                            size='lg',
                            style={'width': '100%', 'fontWeight': 'bold', 'fontSize': '16px', 'padding': '12px'},
                            disabled=True
                        )
                    ])
                ], width=4)
            ], className="mb-3"),
            
            # 分析状态显示区
            html.Div(id='analysis-status', style={
                'marginTop': '15px', 
                'padding': '15px',
                'borderRadius': '8px',
                'fontSize': '14px', 
                'fontWeight': 'bold',
                'minHeight': '60px'
            }),
            
            # 上传文件状态(隐藏的旧组件,保持兼容性)
            html.Div(id='upload-status', style={'display': 'none'}),
            html.Div(id='store-selector', style={'display': 'none'})
        ], className="chart-section", style={
            'backgroundColor': '#f8fff9', 
            'padding': '25px', 
            'borderRadius': '12px', 
            'marginBottom': '20px',
            'border': '2px solid #d4edda'
        }),
        
        # 竞对数据上传分析区域
        html.Div([
            html.Label("🎯 竞对数据上传:", style={'fontWeight': 'bold', 'fontSize': '18px', 'color': '#dc3545', 'marginBottom': '15px'}),
            dbc.Row([
                dbc.Col([
                    dcc.Upload(
                        id='upload-competitor-data',
                        children=html.Div([
                            html.Div("📁 拖拽或点击上传竞对原始数据", style={'fontSize': '16px', 'fontWeight': 'bold', 'color': '#dc3545'}),
                            html.Div("支持格式: Excel (.xlsx) 或 CSV (.csv)", style={'fontSize': '13px', 'color': '#666', 'marginTop': '5px'}),
                            html.Div("用于门店对比分析,找到竞争优势", style={'fontSize': '12px', 'color': '#999', 'marginTop': '3px'})
                        ], style={'padding': '20px'}),
                        style={
                            'width': '100%',
                            'height': '120px',
                            'borderWidth': '3px',
                            'borderStyle': 'dashed',
                            'borderRadius': '10px',
                            'textAlign': 'center',
                            'borderColor': '#dc3545',
                            'backgroundColor': '#fff5f5',
                            'cursor': 'pointer',
                            'transition': 'all 0.3s ease'
                        },
                        multiple=False
                    ),
                ], width=8),
                dbc.Col([
                    html.Label("📝 竞对名称:", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                    dcc.Input(
                        id='competitor-name-input',
                        type='text',
                        placeholder='输入竞对名称(如: 美团优选店)',
                        style={
                            'width': '100%', 
                            'padding': '12px', 
                            'borderRadius': '8px', 
                            'border': '2px solid #ced4da',
                            'fontSize': '14px'
                        }
                    ),
                    html.Div([
                        dbc.Button(
                            [html.I(className="fas fa-chart-line", style={'marginRight': '8px'}), "分析竞对"],
                            id='btn-run-competitor-analysis',
                            color='danger',
                            className='mt-3',
                            size='lg',
                            style={'width': '100%', 'fontWeight': 'bold', 'fontSize': '16px', 'padding': '12px'},
                            disabled=True
                        )
                    ])
                ], width=4)
            ], className="mb-3"),
            
            # 竞对分析状态显示区
            html.Div(id='competitor-analysis-status', style={
                'marginTop': '15px', 
                'padding': '15px',
                'borderRadius': '8px',
                'fontSize': '14px', 
                'fontWeight': 'bold',
                'minHeight': '60px'
            })
        ], className="chart-section", style={
            'backgroundColor': '#fff5f5', 
            'padding': '25px', 
            'borderRadius': '12px', 
            'marginBottom': '30px',
            'border': '2px solid #f5c6cb'
        }),
        
        # 全局分类筛选器与门店切换（本店TAB和竞对TAB使用）
        html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("🏪 门店切换:", style={'fontWeight': 'bold', 'fontSize': '16px', 'marginBottom': '8px'}),
                        dcc.Dropdown(
                            id='store-switcher',
                            options=[],
                            value=None,
                            placeholder="选择门店查看数据...",
                            style={'width': '100%'},
                            clearable=False
                        ),
                        html.Div(id='store-switch-status', style={'marginTop': '5px', 'fontSize': '13px', 'color': '#666'})
                    ], width=4),
                    dbc.Col([
                        html.Label("🔍 一级分类筛选:", style={'fontWeight': 'bold', 'fontSize': '16px', 'marginBottom': '8px'}),
                        dcc.Dropdown(
                            id='category-filter',
                            options=[],
                            value=[],
                            multi=True,
                            placeholder="选择分类筛选(默认显示全部)...",
                            style={'width': '100%'}
                        ),
                        html.Div(id='filter-status', style={'marginTop': '5px', 'fontSize': '13px', 'color': '#666'})
                    ], width=8)
                ])
            ], className="chart-section", style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '20px'}),
        
        # ========== 对比模式控制栏 ==========
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Label("对比模式:", style={'fontWeight': '600', 'marginRight': '10px', 'fontSize': '14px'}),
                    dbc.Switch(
                        id='comparison-mode-switch',
                        value=False,
                        label="OFF",
                        style={'display': 'inline-block'}
                    )
                ], width=3, style={'display': 'flex', 'alignItems': 'center'}),
                
                dbc.Col([
                    html.Label("选择竞对:", style={'fontWeight': '600', 'marginRight': '10px', 'fontSize': '14px'}),
                    dcc.Dropdown(
                        id='competitor-selector',
                        options=[],
                        value=[],
                        multi=True,
                        placeholder="请选择竞对门店（最多3个）",
                        disabled=True,
                        style={'width': '450px'}
                    ),
                    html.Span(id='competitor-count-hint', style={'marginLeft': '10px', 'fontSize': '12px', 'color': '#7f8c8d'})
                ], width=7, style={'display': 'flex', 'alignItems': 'center'})
            ], align='center', style={'padding': '15px 20px'})
        ], id='comparison-control-bar', style={
            'marginBottom': '20px',
            'backgroundColor': '#f8f9fa',
            'borderRadius': '8px',
            'border': '1px solid #dee2e6',
            'position': 'sticky',
            'top': '0',
            'zIndex': '1000',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
        }),
        
        # KPI指标卡片
        html.Div([
            html.H2("🎯 核心指标概览", className="section-title"),
            html.Div(id="kpi-cards"),
            html.Div(id="kpi-insights"),
            
            # KPI看板AI分析区域已删除（P0优化）
            
            # KPI指标说明Modal弹窗
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(id="kpi-modal-title")),
                dbc.ModalBody(id="kpi-modal-body"),
                dbc.ModalFooter(
                    dbc.Button("关闭", id="kpi-modal-close", className="ms-auto")
                ),
            ], id="kpi-modal", is_open=False, size="lg"),
            
            # 【新增】数据下钻Modal弹窗
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle(id="drilldown-modal-title")),
                dbc.ModalBody(id="drilldown-modal-body", style={'maxHeight': '70vh', 'overflowY': 'auto'}),
                dbc.ModalFooter(
                    dbc.Button("关闭", id="drilldown-modal-close-btn", className="ms-auto")
                ),
            ], id="drilldown-modal", is_open=False, size="xl")  # xl = 超大尺寸
        ], className="chart-section"),
        
        # 一级分类动销分析
        html.Div([
            html.H2("📊 一级分类动销分析", className="section-title"),
            html.P("💡 提示：点击图表中的柱状图可查看该分类的详细SKU列表", 
                   className="text-muted", style={'fontSize': '0.9rem', 'fontStyle': 'italic'}),
            html.Div(id="category-sales-analysis"),
            
            # 【新增】分类看板AI分析区域
            # 分类看板AI分析区域已删除（P0优化）
        ], className="chart-section"),
        
        # 多规格商品供给分析 - ECharts版本（支持对比模式）
        html.Div([
            html.H2("🔀 多规格商品供给分析", className="section-title"),
            # 多规格分析内容容器（动态更新）
            html.Div(id="multispec-analysis-content")
        ], className="chart-section"),
        
        # 折扣商品分析
        html.Div([
            html.H2("💸 折扣商品供给与销售分析", className="section-title"),
            html.Div(id="discount-analysis")
        ], className="chart-section"),
        
        # 折扣渗透率热力图
        html.Div([
            html.H2("🔥 折扣渗透率热力图分析", className="section-title"),
            html.Div(id="discount-heatmap")
        ], className="chart-section"),
        
        # 价格带分析
        html.Div([
            html.H2("💰 价格带分布分析", className="section-title"),
            html.Div(id="price-distribution"),
            
            # 【新增】价格带看板AI分析区域
            # 价格带看板AI分析区域已删除（P0优化）
        ], className="chart-section"),
        
        # 销量与销售额气泡图
        html.Div([
            html.H2("🫧 分类销量与销售额对比分析", className="section-title"),
            html.Div(id="sales-bubble-chart")
        ], className="chart-section"),
        
        # 销量贡献树状图
        html.Div([
            html.H2("🌳 分类月售贡献树状图", className="section-title"),
            html.Div(id="sales-treemap")
        ], className="chart-section"),
        
        # 库存健康看板
        html.Div([
            html.H2("🏥 库存健康看板", className="section-title"),
            html.Div(id="inventory-health-analysis"),
            html.Div(id="inventory-insights", className="mt-3")
        ], className="chart-section"),
        
        # 促销效能分析
        html.Div([
            html.H2("🎯 促销效能分析", className="section-title"),
            html.Div(id="promotion-effectiveness-analysis"),
            html.Div(id="promotion-insights", className="mt-3"),
            
            # 【新增】促销看板AI分析区域
            # 促销看板AI分析区域已删除（P0优化）
        ], className="chart-section"),
        
        # ========== 成本&毛利分析（P0功能） ==========
        html.Div([
            html.H2("💰 成本&毛利分析", className="section-title"),
            html.Div(id="cost-analysis-content"),
            html.Div(id="cost-insights", className="mt-3"),
            
            # 成本看板AI分析区域已删除（P0优化）
        ], className="chart-section"),
        
        # SKU结构优化建议
        html.Div([
            html.H2("📊 SKU结构优化分析", className="section-title"),
            html.Div(id="sku-structure-analysis"),
            html.Div(id="sku-structure-insights", className="mt-3")
        ], className="chart-section"),
        
        # ========== 滞销商品诊断看板 ==========
        html.Div([
            html.H2("🚫 滞销商品诊断看板", className="section-title"),
            
            # 核心指标卡片
            html.Div(id="unsold-kpis", className="mb-4"),
            
            # 智能洞察面板
            html.Div(id="unsold-insights", className="mb-4"),
            
            # 第一行: 分类分布 + 价格带分布
            dbc.Row([
                dbc.Col(html.Div(id="unsold-category-pie"), width=6),
                dbc.Col(html.Div(id="unsold-price-distribution"), width=6)
            ], className="mb-4"),
            
            # 第二行: TOP20高风险滞销商品表格
            html.Div([
                html.H4("📄 TOP20高风险滞销商品详情", className="mb-3", 
                       style={'color': '#dc3545', 'fontWeight': 'bold'}),
                html.Div(id="unsold-top-table")
            ])
        ], className="chart-section"),
        
        # 主AI综合洞察区域已删除（P0优化）
        # AI智能分析区域已删除（P0优化）
        
    ], id='single-store-dashboard-area'),  # 单店看板内容区域（本店TAB和竞对TAB共用）
    
    # ========== 城市新增竞对分析TAB内容区域 ==========
    html.Div(
        create_city_competitor_tab_layout(),
        id='city-competitor-tab-content',
        style={'display': 'none'}  # 默认隐藏
    ),
    
])  # 闭合app.layout

# ========== TAB切换回调 ==========
@app.callback(
    [Output('data-source-store', 'data'),
     Output('single-store-dashboard-area', 'style'),
     Output('city-competitor-tab-content', 'style')],
    Input('main-tabs', 'active_tab'),
    prevent_initial_call=True
)
def update_data_source(active_tab):
    """TAB切换时更新数据源标记和显示区域
    
    注意：门店切换由update_store_switcher回调处理，这里只负责：
    1. 更新数据源标记
    2. 控制显示区域的可见性
    """
    if active_tab == 'tab-competitor':
        print("🎯 切换到竞对数据看板TAB")
        return 'competitor', {'display': 'block'}, {'display': 'none'}
    elif active_tab == 'tab-city-competitor':
        print("🏙️ 切换到城市新增竞对分析TAB")
        return 'city-competitor', {'display': 'none'}, {'display': 'block'}
    else:
        print("🏪 切换到本店数据看板TAB")
        return 'own-store', {'display': 'block'}, {'display': 'none'}

# ========== 对比模式开关回调 ==========
@app.callback(
    [Output('competitor-selector', 'disabled'),
     Output('competitor-selector', 'options'),
     Output('comparison-mode-switch', 'label'),
     Output('comparison-mode', 'data')],
    Input('comparison-mode-switch', 'value'),
    prevent_initial_call=True
)
def update_comparison_control(mode_on):
    """更新对比模式控制栏状态"""
    if mode_on:
        # 获取竞对门店列表
        competitor_list = store_manager.get_store_list('competitor')
        
        if not competitor_list:
            # 没有可用的竞对门店
            logger.warning("⚠️ 没有可用的竞对门店")
            return True, [], "ON (无可用竞对)", 'off'
        
        # 格式化为Dropdown options
        options = [{'label': f"🎯 {store}", 'value': store} for store in competitor_list]
        
        logger.info(f"✅ 对比模式已开启，可用竞对: {competitor_list}")
        return False, options, "ON", 'on'
    else:
        # 关闭对比模式
        logger.info("🔄 对比模式已关闭")
        return True, [], "OFF", 'off'


# ========== 竞对选择数量提示回调 ==========
@app.callback(
    Output('competitor-count-hint', 'children'),
    Input('competitor-selector', 'value'),
    prevent_initial_call=True
)
def update_competitor_count_hint(selected_competitors):
    """更新竞对选择数量提示"""
    if not selected_competitors:
        return ""
    count = len(selected_competitors)
    if count > 3:
        return html.Span(f"⚠️ 已选{count}个，建议不超过3个", style={'color': '#e74c3c'})
    return html.Span(f"已选{count}个", style={'color': '#27ae60'})


# ========== 竞对数据加载回调（支持多竞对） ==========
@app.callback(
    [Output('competitor-data-cache', 'data'),
     Output('selected-competitor', 'data')],
    Input('competitor-selector', 'value'),
    prevent_initial_call=True
)
def load_competitor_data_callback(competitor_names):
    """加载多个竞对数据并缓存
    
    数据结构: {
        'competitor_name_1': {'kpi': {...}, 'category': [...], 'price': [...], 'role': [...]},
        'competitor_name_2': {'kpi': {...}, 'category': [...], 'price': [...], 'role': [...]},
        ...
    }
    """
    if not competitor_names:
        logger.info("⚠️ 未选择竞对门店")
        return {}, []
    
    # 确保是列表格式
    if isinstance(competitor_names, str):
        competitor_names = [competitor_names]
    
    # 限制最多3个竞对
    if len(competitor_names) > 3:
        logger.warning(f"⚠️ 选择了{len(competitor_names)}个竞对，仅加载前3个")
        competitor_names = competitor_names[:3]
    
    logger.info(f"🔍 开始加载{len(competitor_names)}个竞对数据: {competitor_names}")
    
    all_competitor_data = {}
    loaded_competitors = []
    
    for competitor_name in competitor_names:
        # 使用ComparisonDataLoader加载数据
        data_loader = comparison_loader.load_competitor_data(competitor_name)
        
        if not data_loader:
            logger.error(f"❌ 竞对数据加载失败: {competitor_name}")
            continue
        
        # 提取关键数据
        try:
            competitor_data = {
                'kpi': data_loader.get_kpi_summary(),
                'category': data_loader.get_category_analysis().to_dict('records') if not data_loader.get_category_analysis().empty else [],
                'price': data_loader.get_price_analysis().to_dict('records') if not data_loader.get_price_analysis().empty else [],
                'role': data_loader.get_role_analysis().to_dict('records') if not data_loader.get_role_analysis().empty else []
            }
            
            all_competitor_data[competitor_name] = competitor_data
            loaded_competitors.append(competitor_name)
            
            logger.info(f"✅ 竞对数据加载成功: {competitor_name}")
            logger.info(f"📊 KPI数据: {len(competitor_data['kpi'])} 项, 分类数据: {len(competitor_data['category'])} 条")
            
        except Exception as e:
            logger.error(f"❌ 竞对数据提取失败: {competitor_name}, 错误: {e}")
            continue
    
    if not loaded_competitors:
        logger.error("❌ 所有竞对数据加载失败")
        return {}, []
    
    logger.info(f"✅ 成功加载{len(loaded_competitors)}个竞对数据")
    return all_competitor_data, loaded_competitors


# ========== KPI指标说明Modal回调 ==========
# 为13个KPI指标创建统一的Modal弹窗回调
@app.callback(
    [Output('kpi-modal', 'is_open'),
     Output('kpi-modal-title', 'children'),
     Output('kpi-modal-body', 'children')],
    [Input({'type': 'kpi-help', 'index': ALL}, 'n_clicks'),
     Input('kpi-modal-close', 'n_clicks')],
    [State('kpi-modal', 'is_open')],
    prevent_initial_call=True
)
def toggle_kpi_modal(help_clicks, close_clicks, is_open):
    """处理KPI指标说明弹窗的打开和关闭"""
    ctx = dash.callback_context
    
    # 没有触发源，不做任何更新
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    
    # 获取触发的组件信息
    trigger = ctx.triggered[0]
    trigger_prop_id = trigger['prop_id']
    
    # 检查是否真的有按钮被点击（n_clicks 不为 None）
    if trigger['value'] is None:
        raise dash.exceptions.PreventUpdate
    
    # 关闭按钮
    if 'kpi-modal-close' in trigger_prop_id:
        return False, "", ""
    
    # 检查是否是KPI帮助按钮被点击
    if 'kpi-help' in trigger_prop_id:
        # 从prop_id中提取索引: {"index":0,"type":"kpi-help"}.n_clicks
        import json
        import re
        try:
            # 提取JSON部分 - 使用正则表达式更稳定
            match = re.search(r'\{[^}]+\}', trigger_prop_id)
            if match:
                json_str = match.group(0)
                trigger_id = json.loads(json_str)
                clicked_idx = trigger_id.get('index')
            else:
                raise dash.exceptions.PreventUpdate
        except Exception as e:
            print(f"解析trigger_id失败: {e}")
            raise dash.exceptions.PreventUpdate
        
        # KPI指标定义列表(与kpi_configs顺序一致)
        kpi_definitions = [
            {
                'title': '📦 总SKU数(含规格)',
                'content': '所有商品规格的总数量,包括多规格商品的各个子SKU。用于衡量商品丰富度。'
            },
            {
                'title': '🧩 多规格SKU总数',
                'content': '同一商品拥有多个规格选项的SKU数量。例如:可乐(300ml/500ml/1L)有3个多规格SKU。'
            },
            {
                'title': '📈 动销SKU数',
                'content': '有实际销量的商品数量(月售>0)。反映门店商品的活跃程度。'
            },
            {
                'title': '📉 滞销SKU数',
                'content': '月销量为0的商品数量。滞销商品占用库存资源,建议及时优化。'
            },
            {
                'title': '💰 总销售额(去重后)',
                'content': '门店当期总销售收入,已去除多规格商品的重复计算。用于评估门店整体营收能力。'
            },
            {
                'title': '💹 动销率',
                'content': '动销SKU数 ÷ 总SKU数。反映商品周转效率,建议保持在60%以上。'
            },
            {
                'title': '🔀 唯一多规格商品数',
                'content': '去重后的多规格商品种类数。例如:可乐有3个规格,但只算1个唯一商品。'
            },
            {
                'title': '🔥 门店爆品数',
                'content': '月销量超过10的热销商品数量。爆品驱动门店销售增长。'
            },
            {
                'title': '🏷️ 门店平均折扣',
                'content': '门店所有商品的平均折扣力度(售价÷原价)。7.8折表示平均优惠22%。'
            },
            {
                'title': '🔖 平均SKU单价',
                'content': '门店商品的平均售价。反映门店价格定位:高单价=高端定位,低单价=大众定位。'
            },
            {
                'title': '💎 高价值SKU占比(>50元)',
                'content': '售价超过50元的商品占比。高价值商品占比高说明门店盈利能力强。'
            },
            {
                'title': '📊 促销强度',
                'content': '参与促销活动的商品比例。高促销强度可提升销量但会影响利润率。'
            },
            {
                'title': '🚀 爆款集中度(TOP10)',
                'content': 'TOP10爆款商品的销售额占比。过高(>60%)说明依赖爆款,需优化长尾商品。'
            }
        ]
        
        if clicked_idx is not None and clicked_idx < len(kpi_definitions):
            kpi_info = kpi_definitions[clicked_idx]
            return True, kpi_info['title'], html.Div([
                html.P(kpi_info['content'], style={'fontSize': '16px', 'lineHeight': '1.8'}),
                html.Hr(),
                html.P("💡 提示: 该指标可帮助您了解门店当前运营状态,结合其他指标综合分析效果更佳。", 
                      style={'fontSize': '14px', 'color': '#6c757d', 'fontStyle': 'italic'})
            ])
    
    raise dash.exceptions.PreventUpdate

# ========== 旧的上传回调已废弃 ==========
# 已移除upload-data组件,使用upload-raw-data代替
# 门店选择器已改为隐藏的Div,不再使用options/value属性

# ========== 门店切换相关回调 ==========
@app.callback(
    [Output('store-switcher', 'options'),
     Output('store-switcher', 'value'),
     Output('store-switch-status', 'children'),
     Output('upload-trigger', 'data', allow_duplicate=True)],
    [Input('main-tabs', 'active_tab')],
    [State('upload-trigger', 'data')],
    prevent_initial_call='initial_duplicate'  # 允许初始调用时也能使用allow_duplicate
)
def update_store_switcher(active_tab, current_trigger):
    """更新门店切换下拉框选项（根据TAB显示本店或竞对）并强制刷新数据"""
    global loader
    
    try:
        # 根据当前TAB决定显示哪种门店列表
        if active_tab == 'tab-competitor':
            # 竞对数据看板TAB：显示竞对列表
            store_list = store_manager.get_store_list('competitor')
            store_type = 'competitor'
            icon = '🎯'
            type_label = '竞对'
        else:
            # 本店数据看板TAB（默认）：显示本店列表
            store_list = store_manager.get_store_list('own')
            store_type = 'own'
            icon = '🏪'
            type_label = '本店'
        
        if not store_list:
            return [], None, html.Div(f"暂无{type_label}数据", style={'color': '#999'}), current_trigger
        
        # 创建选项
        options = [{'label': f"{icon} {store}", 'value': store} for store in store_list]
        
        # 默认选中第一个门店
        default_store = store_list[0] if store_list else None
        
        # 【关键修复】TAB切换时，强制加载对应类型的第一个门店数据
        if default_store:
            new_loader = store_manager.switch_store(default_store)
            if new_loader:
                loader = new_loader
                logger.info(f"✅ TAB切换时自动加载{type_label}数据: {default_store}")
        
        status_msg = html.Div([
            html.I(className="fas fa-check-circle", style={'marginRight': '5px', 'color': '#28a745'}),
            f"当前: {default_store if default_store else f'请选择{type_label}'}"
        ], style={'color': '#28a745', 'fontWeight': 'bold'})
        
        logger.info(f"📋 门店切换器已更新: TAB={active_tab}, 类型={type_label}, 门店数={len(store_list)}")
        
        # 增加trigger值，强制刷新所有依赖upload-trigger的组件
        new_trigger = (current_trigger or 0) + 1
        
        return options, default_store, status_msg, new_trigger
        
    except Exception as e:
        logger.error(f"门店切换器更新错误: {e}")
        return [], None, html.Div("门店列表加载失败", style={'color': 'red'}), current_trigger


@app.callback(
    [Output('upload-trigger', 'data', allow_duplicate=True),
     Output('store-switch-status', 'children', allow_duplicate=True)],
    [Input('store-switcher', 'value')],
    [State('upload-trigger', 'data'),
     State('main-tabs', 'active_tab')],
    prevent_initial_call=True
)
def switch_store(selected_store, current_trigger, active_tab):
    """切换门店数据（支持本店和竞对）"""
    global loader
    
    if not selected_store:
        raise PreventUpdate
    
    try:
        # 切换门店
        new_loader = store_manager.switch_store(selected_store)
        
        if new_loader:
            loader = new_loader
            
            # 判断是本店还是竞对
            is_competitor = selected_store in store_manager.competitor_stores
            icon = '🎯' if is_competitor else '🏪'
            type_label = '竞对' if is_competitor else '本店'
            
            status_msg = html.Div([
                html.I(className="fas fa-sync-alt", style={'marginRight': '5px', 'color': '#28a745'}),
                f"✅ 已切换到{type_label}: {icon} {selected_store}"
            ], style={'color': '#28a745', 'fontWeight': 'bold'})
            
            logger.info(f"✅ 门店已切换: {type_label} - {selected_store}")
            
            return current_trigger + 1, status_msg
        else:
            raise Exception("切换失败")
            
    except Exception as e:
        error_msg = html.Div([
            html.I(className="fas fa-exclamation-circle", style={'marginRight': '5px', 'color': '#dc3545'}),
            f"❌ 切换失败: {str(e)}"
        ], style={'color': '#dc3545', 'fontWeight': 'bold'})
        
        return current_trigger, error_msg


# ========== 分类筛选器相关回调 ==========
@app.callback(
    [Output('category-filter', 'options'),
     Output('filter-status', 'children')],
    Input('upload-trigger', 'data')
)
def update_category_filter_options(upload_trigger):
    """上传文件后更新分类筛选器选项"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return [], html.Div("等待数据上传...", style={'color': '#999'})
        
        # 获取所有一级分类
        categories = sku_details.iloc[:, 3].dropna().unique().tolist()  # D列:一级分类
        categories = sorted([cat for cat in categories if cat])  # 排序并去除空值
        
        options = [{'label': cat, 'value': cat} for cat in categories]
        
        status_msg = html.Div([
            html.I(className="fas fa-info-circle", style={'marginRight': '5px'}),
            f"共 {len(categories)} 个分类可选 | 默认显示全部"
        ], style={'color': '#28a745'})
        
        return options, status_msg
    except Exception as e:
        print(f"分类筛选器选项更新错误: {e}")
        return [], html.Div("分类加载失败", style={'color': 'red'})

@app.callback(
    Output('category-filter-state', 'data'),
    Input('category-filter', 'value')
)
def update_category_filter_state(selected_categories):
    """更新分类筛选状态"""
    if not selected_categories:
        return []
    return selected_categories

@app.callback(
    [Output('kpi-cards', 'children'),
     Output('kpi-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('comparison-mode', 'data'),
     Input('selected-competitor', 'data'),
     Input('competitor-data-cache', 'data')]
)
def update_kpi_cards(upload_trigger, comparison_mode, selected_competitors, competitor_cache):
    """更新KPI卡片和洞察（支持多竞对对比模式）"""
    try:
        # 获取本店KPI数据
        own_kpi = loader.get_kpi_summary()
        
        # 检查对比模式状态（支持多竞对）
        if comparison_mode == 'on' and selected_competitors and competitor_cache:
            # 确保是列表格式
            if isinstance(selected_competitors, str):
                selected_competitors = [selected_competitors]
            
            logger.info(f"🔄 多竞对对比模式: 本店 vs {selected_competitors}")
            
            # 收集所有竞对的KPI数据
            competitors_kpi = {}
            for comp_name in selected_competitors:
                comp_data = competitor_cache.get(comp_name, {})
                if comp_data and 'kpi' in comp_data:
                    competitors_kpi[comp_name] = comp_data['kpi']
            
            if not competitors_kpi:
                logger.warning("⚠️ 所有竞对KPI数据为空，返回单店视图")
                cards = DashboardComponents.create_kpi_cards(own_kpi)
                insights = DashboardComponents.generate_kpi_insights(own_kpi)
                insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
                return cards, insights_panel
            
            # 获取当前门店名称
            own_store_name = store_manager.current_store or '本店'
            
            # 创建多竞对对比卡片
            comparison_cards = DashboardComponents.create_multi_competitor_kpi_cards(own_kpi, competitors_kpi, own_store_name)
            
            # 生成KPI差异分析洞察（使用第一个竞对作为主要对比对象）
            first_competitor = list(competitors_kpi.keys())[0]
            first_comp_kpi = competitors_kpi[first_competitor]
            logger.info(f"📊 差异分析 - 本店KPI keys: {list(own_kpi.keys())[:5]}...")
            logger.info(f"📊 差异分析 - 竞对KPI keys: {list(first_comp_kpi.keys())[:5] if isinstance(first_comp_kpi, dict) else type(first_comp_kpi)}...")
            
            kpi_insights = DifferenceAnalyzer.analyze_kpi_differences(own_kpi, first_comp_kpi)
            logger.info(f"📊 差异分析洞察数量: {len(kpi_insights)}")
            
            # 生成改进建议
            recommendations = DifferenceAnalyzer.generate_recommendations(kpi_insights)
            logger.info(f"📊 改进建议数量: {len(recommendations)}")
            
            # 合并洞察和建议
            all_insights = kpi_insights + recommendations
            logger.info(f"📊 总洞察数量: {len(all_insights)}")
            
            # 创建差异分析面板
            if all_insights:
                insights_panel = DashboardComponents.create_insights_panel(all_insights)
            else:
                insights_panel = html.Div([
                    html.P("✅ 本店在所有核心指标上均领先或持平", className="text-success text-center p-3")
                ])
            
            # 构建竞对名称显示
            comp_names_str = " / ".join(selected_competitors)
            
            # 组合对比视图（多竞对模式）
            comparison_view = html.Div([
                html.Div([
                    html.H5("📊 核心指标对比", className="mb-1"),
                    html.P(f"本店 vs {comp_names_str}", className="text-muted small mb-3")
                ]),
                comparison_cards,
                html.Hr(className="my-4"),
                html.H5("🔍 差异分析", className="mb-3"),
                insights_panel
            ])
            
            return comparison_view, html.Div()
        
        else:
            # 单店视图
            cards = DashboardComponents.create_kpi_cards(own_kpi)
            insights = DashboardComponents.generate_kpi_insights(own_kpi)
            insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
            return cards, insights_panel
            
    except Exception as e:
        logger.error(f"❌ KPI卡片更新错误: {e}")
        import traceback
        traceback.print_exc()
        return html.Div("KPI数据加载失败"), html.Div()

@app.callback(
    Output('category-sales-analysis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data'),
     Input('comparison-mode', 'data'),
     Input('selected-competitor', 'data'),
     Input('competitor-data-cache', 'data')]
)
def update_category_sales(upload_trigger, selected_categories, comparison_mode, selected_competitors, competitor_cache):
    """更新一级分类动销分析（支持多竞对对比模式）"""
    try:
        # 获取本店数据
        category_data = loader.get_category_analysis()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]  # A列:一级分类
        
        # 检查是否为对比模式（支持多竞对）
        logger.info(f"🔍 一级分类动销分析检查: comparison_mode={comparison_mode}, selected_competitors={selected_competitors}, cache_keys={list(competitor_cache.keys()) if competitor_cache else 'None'}")
        
        if comparison_mode == 'on' and selected_competitors and competitor_cache:
            # 确保是列表格式
            if isinstance(selected_competitors, str):
                selected_competitors = [selected_competitors]
            
            logger.info(f"一级分类动销分析：多竞对对比模式 ({len(selected_competitors)}个竞对)")
            
            # 使用第一个竞对进行对比（分类对比暂时只支持单竞对）
            first_competitor = selected_competitors[0]
            comp_data = competitor_cache.get(first_competitor, {})
            competitor_category = comp_data.get('category', []) if comp_data else []
            
            logger.info(f"📊 竞对分类数据: len={len(competitor_category) if competitor_category else 0}")
            if not competitor_category:
                logger.warning("⚠️ 竞对分类数据为空")
                return DashboardComponents.create_category_sales_analysis(category_data)
            
            # 转换为DataFrame
            competitor_df = pd.DataFrame(competitor_category)
            
            # 应用相同的分类筛选
            if selected_categories and len(selected_categories) > 0:
                competitor_df = competitor_df[competitor_df.iloc[:, 0].isin(selected_categories)]
            
            # 获取本店名称
            own_store_name = store_manager.current_store or '本店'
            
            # 创建对比视图（显示多竞对提示）
            comparison_view = create_category_comparison_view(category_data, competitor_df, first_competitor, own_store_name)
            
            # 如果有多个竞对，添加提示
            if len(selected_competitors) > 1:
                hint = html.Div([
                    html.P(f"💡 当前显示与 {first_competitor} 的对比，其他竞对: {', '.join(selected_competitors[1:])}", 
                           className="text-muted small", style={'textAlign': 'center', 'marginBottom': '10px'})
                ])
                return html.Div([hint, comparison_view])
            
            return comparison_view
        else:
            # 单店视图
            return DashboardComponents.create_category_sales_analysis(category_data)
            
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"❌ 分类动销分析更新错误: {e}")
        logger.error(f"详细错误: {error_detail}")
        return html.Div([
            html.H5("❌ 分类动销数据加载失败", className="text-danger"),
            html.P(f"错误信息: {str(e)}", className="text-muted small"),
            html.Pre(error_detail, className="text-muted small", style={'fontSize': '0.7rem'})
        ], className="p-3")

@app.callback(
    Output('multispec-analysis-content', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data'),
     Input('comparison-mode', 'data'),
     Input('selected-competitor', 'data'),
     Input('competitor-data-cache', 'data')]
)
def update_multispec_supply(upload_trigger, selected_categories, comparison_mode, selected_competitors, competitor_cache):
    """更新多规格商品供给分析（ECharts版本，支持多竞对对比模式）"""
    from modules.charts.multispec_echarts import (
        create_multispec_echarts, create_multispec_comparison_echarts,
        create_multispec_sku_comparison_echarts, create_multispec_structure_comparison_echarts,
        generate_multispec_insights, generate_multispec_comparison_insights,
        create_multispec_insights_display
    )
    
    try:
        # 加载本店数据
        category_data = loader.get_category_analysis()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        # 检查是否为对比模式（支持多竞对）
        logger.info(f"🔍 多规格供给分析检查: comparison_mode={comparison_mode}, selected_competitors={selected_competitors}, cache_keys={list(competitor_cache.keys()) if competitor_cache else 'None'}")
        
        if comparison_mode == 'on' and selected_competitors and competitor_cache:
            # 确保是列表格式
            if isinstance(selected_competitors, str):
                selected_competitors = [selected_competitors]
            
            # 使用第一个竞对进行对比
            selected_competitor = selected_competitors[0]
            # 获取本店名称
            own_store_name = store_manager.current_store or '本店'
            logger.info(f"🔀 多规格供给分析 - 对比模式: {own_store_name} vs {selected_competitor}")
            
            # 从缓存获取竞对数据
            comp_data = competitor_cache.get(selected_competitor, {})
            competitor_category = comp_data.get('category') if comp_data else None
            logger.info(f"📊 竞对分类数据: type={type(competitor_category)}, len={len(competitor_category) if competitor_category else 0}")
            
            # 确保competitor_df是DataFrame而不是list
            if isinstance(competitor_category, list):
                competitor_df = pd.DataFrame(competitor_category) if competitor_category else pd.DataFrame()
            elif competitor_category is None:
                competitor_df = pd.DataFrame()
            else:
                competitor_df = competitor_category
            
            if not competitor_df.empty:
                # 应用相同的分类筛选
                if selected_categories and len(selected_categories) > 0:
                    competitor_df = competitor_df[competitor_df.iloc[:, 0].isin(selected_categories)]
                
                # 生成对比洞察卡片
                comparison_cards = create_multispec_comparison_cards(category_data, competitor_df, selected_competitor, own_store_name)
                
                # 生成3个对比图表
                logger.info(f"📈 开始生成多规格对比图表...")
                ratio_chart = create_multispec_comparison_echarts(category_data, competitor_df, selected_competitor)
                logger.info(f"📊 图表1生成完成: yAxis.data长度={len(ratio_chart.get('yAxis', {}).get('data', []))}")
                
                sku_chart = create_multispec_sku_comparison_echarts(category_data, competitor_df, selected_competitor, own_store_name)
                logger.info(f"📊 图表2生成完成: xAxis.data长度={len(sku_chart.get('xAxis', {}).get('data', []))}")
                
                structure_chart = create_multispec_structure_comparison_echarts(category_data, competitor_df, selected_competitor, own_store_name)
                logger.info(f"📊 图表3生成完成: xAxis.data长度={len(structure_chart.get('xAxis', {}).get('data', []))}")
                
                # 生成对比洞察
                comparison_insights = generate_multispec_comparison_insights(category_data, competitor_df, selected_competitor, own_store_name)
                comparison_insights_display = create_multispec_insights_display(comparison_insights)
                logger.info(f"💡 洞察生成完成: {len(comparison_insights)} 条")
                
                # 返回对比模式视图（动态生成完整HTML结构）
                return html.Div([
                    # 洞察卡片
                    comparison_cards,
                    # 图表1：多规格占比差异分析（全部品类）
                    html.Div([
                        html.H5("📊 多规格占比差异分析（全部品类）", 
                               style={'textAlign': 'center', 'marginBottom': '5px', 'color': '#2c3e50'}),
                        html.P("差异 = 本店多规格占比 - 竞对多规格占比 | 绿色=本店领先 | 红色=本店落后", 
                               style={'textAlign': 'center', 'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '10px'}),
                        dash_echarts.DashECharts(
                            option=ratio_chart,
                            style={'height': '500px', 'width': '100%'}
                        )
                    ], style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                    # 图表2：多规格SKU数量对比（TOP15）
                    html.Div([
                        html.H5("📦 多规格SKU数量对比（TOP15）", 
                               style={'textAlign': 'center', 'marginBottom': '5px', 'color': '#2c3e50'}),
                        html.P("按加权分排序：多规格占比 × log(SKU总数) | 蓝色=本店 | 红色=竞对", 
                               style={'textAlign': 'center', 'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '10px'}),
                        dash_echarts.DashECharts(
                            option=sku_chart,
                            style={'height': '400px', 'width': '100%'}
                        )
                    ], style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                    # 图表3：多规格占比分组对比（TOP15）
                    html.Div([
                        html.H5("📈 各品类多规格占比对比（TOP15）", 
                               style={'textAlign': 'center', 'marginBottom': '5px', 'color': '#2c3e50'}),
                        html.P("多规格占比 = 多规格SKU数 ÷ 总SKU数 × 100% | 按平均占比排序 | 蓝色=本店 | 红色=竞对", 
                               style={'textAlign': 'center', 'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '10px'}),
                        dash_echarts.DashECharts(
                            option=structure_chart,
                            style={'height': '420px', 'width': '100%'}
                        )
                    ], style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'marginBottom': '15px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
                    # 智能洞察
                    comparison_insights_display
                ])
            else:
                logger.warning(f"⚠️ 竞对分类数据为空: {selected_competitor}")
        
        # 单店模式：返回ECharts视图
        chart_option = create_multispec_echarts(category_data)
        insights = generate_multispec_insights(category_data)
        insights_display = create_multispec_insights_display(insights)
        
        return html.Div([
            dash_echarts.DashECharts(
                option=chart_option,
                style={'height': '500px', 'width': '100%'}
            ),
            insights_display
        ])
        
    except Exception as e:
        logger.error(f"❌ 多规格供给分析更新错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return html.Div([
            html.H5("❌ 多规格供给分析数据加载失败", className="text-danger"),
            html.P(f"错误信息: {str(e)}", className="text-muted small")
        ], className="p-3")


def create_multispec_comparison_cards(own_data: pd.DataFrame, competitor_data: pd.DataFrame, competitor_name: str, own_store_name: str = '本店'):
    """创建多规格对比洞察卡片"""
    
    # 计算统计数据
    own_total_sku = own_data.iloc[:, 1].sum() if not own_data.empty else 0
    own_multi_sku = own_data.iloc[:, 2].sum() if not own_data.empty else 0
    own_overall_ratio = own_multi_sku / own_total_sku * 100 if own_total_sku > 0 else 0
    
    comp_total_sku = competitor_data.iloc[:, 1].sum() if not competitor_data.empty else 0
    comp_multi_sku = competitor_data.iloc[:, 2].sum() if not competitor_data.empty else 0
    comp_overall_ratio = comp_multi_sku / comp_total_sku * 100 if comp_total_sku > 0 else 0
    
    ratio_diff = own_overall_ratio - comp_overall_ratio
    sku_diff = int(own_multi_sku - comp_multi_sku)
    
    # 计算高/低多规格品类数
    own_high_cats = 0
    own_low_cats = 0
    comp_high_cats = 0
    comp_low_cats = 0
    
    if not own_data.empty:
        for _, row in own_data.iterrows():
            total = row.iloc[1]
            multi = row.iloc[2]
            ratio = multi / total * 100 if total > 0 else 0
            if ratio > 50:
                own_high_cats += 1
            elif ratio < 20:
                own_low_cats += 1
    
    if not competitor_data.empty:
        for _, row in competitor_data.iterrows():
            total = row.iloc[1]
            multi = row.iloc[2]
            ratio = multi / total * 100 if total > 0 else 0
            if ratio > 50:
                comp_high_cats += 1
            elif ratio < 20:
                comp_low_cats += 1
    
    # 创建卡片
    def make_card(title, own_val, comp_val, diff_val, is_pct=False, reverse_color=False):
        """创建对比卡片"""
        if is_pct:
            own_text = f"{own_val:.1f}%"
            comp_text = f"{comp_val:.1f}%"
            diff_text = f"{diff_val:+.1f}%"
        else:
            own_text = f"{int(own_val)}"
            comp_text = f"{int(comp_val)}"
            diff_text = f"{int(diff_val):+d}"
        
        # 差异颜色
        if reverse_color:
            diff_color = '#27ae60' if diff_val < 0 else '#e74c3c' if diff_val > 0 else '#7f8c8d'
        else:
            diff_color = '#27ae60' if diff_val > 0 else '#e74c3c' if diff_val < 0 else '#7f8c8d'
        
        return html.Div([
            html.Div(title, style={'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '5px'}),
            html.Div([
                html.Span(f"本店: {own_text}", style={'color': '#3498db', 'fontWeight': 'bold'}),
                html.Span(" | ", style={'color': '#bdc3c7', 'margin': '0 5px'}),
                html.Span(f"竞对: {comp_text}", style={'color': '#e74c3c', 'fontWeight': 'bold'})
            ], style={'fontSize': '14px', 'marginBottom': '3px'}),
            html.Div(f"差异: {diff_text}", style={'fontSize': '16px', 'fontWeight': 'bold', 'color': diff_color})
        ], style={
            'backgroundColor': 'white',
            'padding': '12px',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'textAlign': 'center',
            'flex': '1',
            'margin': '0 5px'
        })
    
    cards = [
        make_card("整体多规格占比", own_overall_ratio, comp_overall_ratio, ratio_diff, is_pct=True),
        make_card("多规格SKU总数", own_multi_sku, comp_multi_sku, sku_diff),
        make_card("高多规格品类数(>50%)", own_high_cats, comp_high_cats, own_high_cats - comp_high_cats),
        make_card("低多规格品类数(<20%)", own_low_cats, comp_low_cats, own_low_cats - comp_low_cats, reverse_color=True)
    ]
    
    return html.Div(cards, style={
        'display': 'flex',
        'justifyContent': 'space-between',
        'marginBottom': '15px'
    })

@app.callback(
    Output('discount-analysis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data'),
     Input('comparison-mode', 'data'),
     Input('selected-competitor', 'data'),
     Input('competitor-data-cache', 'data')]
)
def update_discount_analysis(upload_trigger, selected_categories, comparison_mode, selected_competitors, competitor_cache):
    """更新折扣商品分析（支持对比模式）"""
    try:
        # 获取本店数据
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        # 检查是否为对比模式
        logger.info(f"🔍 折扣分析检查: comparison_mode={comparison_mode}, selected_competitors={selected_competitors}")
        
        if comparison_mode == 'on' and selected_competitors and competitor_cache:
            # 确保是列表格式
            if isinstance(selected_competitors, str):
                selected_competitors = [selected_competitors]
            
            logger.info(f"💸 折扣分析：对比模式 ({len(selected_competitors)}个竞对)")
            
            # 使用第一个竞对进行对比
            first_competitor = selected_competitors[0]
            comp_data = competitor_cache.get(first_competitor, {})
            competitor_category = comp_data.get('category', []) if comp_data else []
            
            if not competitor_category:
                logger.warning("⚠️ 竞对分类数据为空，显示单店视图")
                return DashboardComponents.create_discount_analysis(category_data)
            
            # 转换为DataFrame
            competitor_df = pd.DataFrame(competitor_category)
            
            # 应用相同的分类筛选
            if selected_categories and len(selected_categories) > 0:
                competitor_df = competitor_df[competitor_df.iloc[:, 0].isin(selected_categories)]
            
            # 获取本店名称
            own_store_name = store_manager.current_store or '本店'
            
            # 创建对比视图
            return create_discount_comparison_view(category_data, competitor_df, first_competitor, own_store_name, selected_competitors)
        else:
            # 单店视图
            return DashboardComponents.create_discount_analysis(category_data)
            
    except Exception as e:
        import traceback
        logger.error(f"❌ 折扣分析更新错误: {e}")
        logger.error(traceback.format_exc())
        return html.Div("折扣数据加载失败")

@app.callback(
    Output('discount-heatmap', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_discount_heatmap(upload_trigger, selected_categories):
    """更新折扣渗透率热力图"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        return DashboardComponents.create_discount_heatmap(category_data)
    except Exception as e:
        print(f"折扣热力图更新错误: {e}")
        return html.Div("折扣热力图数据加载失败")

@app.callback(
    Output('price-distribution', 'children'),
    Input('upload-trigger', 'data')
)
def update_price_distribution(upload_trigger):
    """更新价格带分析"""
    try:
        price_data = loader.get_price_analysis()
        return DashboardComponents.create_price_distribution(price_data)
    except Exception as e:
        print(f"价格带分析更新错误: {e}")
        return html.Div("价格带数据加载失败")

@app.callback(
    Output('sales-bubble-chart', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_sales_bubble(upload_trigger, selected_categories):
    """更新销量与销售额气泡图"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        return DashboardComponents.create_sales_bubble_chart(category_data)
    except Exception as e:
        print(f"气泡图更新错误: {e}")
        return html.Div("气泡图数据加载失败")

@app.callback(
    Output('sales-treemap', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_sales_treemap(upload_trigger, selected_categories):
    """更新销量贡献树状图"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"🌳 树状图数据维度: {category_data.shape}")
        
        # 创建树状图
        treemap_chart = DashboardComponents.create_sales_treemap(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_treemap_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return html.Div([
            treemap_chart,
            insights_panel
        ])
    except Exception as e:
        import traceback
        print(f"树状图更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"树状图生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    [Output('inventory-health-analysis', 'children'),
     Output('inventory-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_inventory_health(upload_trigger, selected_categories):
    """更新库存健康看板"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"🏥 库存健康数据维度: {category_data.shape}")
        
        if category_data.empty:
            return html.Div("库存数据不可用", className="alert alert-warning"), html.Div()
        
        # 创建库存健康图表
        health_chart = DashboardComponents.create_inventory_health_chart(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_inventory_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return health_chart, insights_panel
    except Exception as e:
        import traceback
        print(f"库存健康分析更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"库存健康分析生成失败: {str(e)}", className="alert alert-danger"), html.Div()

@app.callback(
    [Output('promotion-effectiveness-analysis', 'children'),
     Output('promotion-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_promotion_effectiveness(upload_trigger, selected_categories):
    """更新促销效能分析"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"🎯 促销效能数据维度: {category_data.shape}")
        
        if category_data.empty:
            return html.Div("促销数据不可用", className="alert alert-warning"), html.Div()
        
        # 创建促销效能图表
        promo_chart = DashboardComponents.create_promotion_effectiveness_analysis(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_promotion_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return promo_chart, insights_panel
    except Exception as e:
        import traceback
        print(f"促销效能分析更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"促销效能分析生成失败: {str(e)}", className="alert alert-danger"), html.Div()

@app.callback(
    [Output('sku-structure-analysis', 'children'),
     Output('sku-structure-insights', 'children')],
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_sku_structure(upload_trigger, selected_categories):
    """更新SKU结构优化分析"""
    try:
        category_data = loader.get_category_analysis()
        if selected_categories and len(selected_categories) > 0:
            category_data = category_data[category_data.iloc[:, 0].isin(selected_categories)]
        
        print(f"📊 SKU结构数据维度: {category_data.shape}")
        
        if category_data.empty:
            return html.Div("SKU结构数据不可用", className="alert alert-warning"), html.Div()
        
        # 创建SKU结构图表
        sku_chart = DashboardComponents.create_sku_structure_analysis(category_data)
        
        # 生成洞察
        insights = DashboardComponents.generate_sku_structure_insights(category_data)
        insights_panel = DashboardComponents.create_insights_panel(insights) if insights else html.Div()
        
        return sku_chart, insights_panel
    except Exception as e:
        import traceback
        print(f"SKU结构分析更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"SKU结构分析生成失败: {str(e)}", className="alert alert-danger"), html.Div()

# ========== 滞销商品诊断看板回调函数 ==========
@app.callback(
    Output('unsold-kpis', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_kpis(upload_trigger, selected_categories):
    """更新滞销商品核心指标"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("SKU详细数据不可用", className="alert alert-warning")
        
        # 筛选滞销商品 (月售=0 且 库存>0)
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)  # C列:月售
        stock_col = pd.to_numeric(sku_details.iloc[:, 5], errors='coerce').fillna(0)  # F列:库存
        unsold_df = sku_details[(sales_col == 0) & (stock_col > 0)].copy()  # 🔧 剔除0库存
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]  # D列:一级分类
        
        total_skus = len(sku_details)
        
        print(f"🚫 滞销商品数量(有库存): {len(unsold_df)} / {total_skus}")
        
        return DashboardComponents.create_unsold_analysis_kpis(unsold_df, total_skus)
    except Exception as e:
        import traceback
        print(f"滞销KPI更新错误: {e}")
        print(traceback.format_exc())
        return html.Div(f"滞销KPI生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    Output('unsold-insights', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_insights(upload_trigger, selected_categories):
    """更新滞销商品智能洞察"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div()
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        stock_col = pd.to_numeric(sku_details.iloc[:, 5], errors='coerce').fillna(0)
        unsold_df = sku_details[(sales_col == 0) & (stock_col > 0)].copy()  # 🔧 剔除0库存
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        total_skus = len(sku_details)
        
        return DashboardComponents.generate_unsold_insights(unsold_df, total_skus)
    except Exception as e:
        print(f"滞销洞察更新错误: {e}")
        return html.Div()

@app.callback(
    Output('unsold-category-pie', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_category_pie(upload_trigger, selected_categories):
    """更新滞销分类分布饼图"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        stock_col = pd.to_numeric(sku_details.iloc[:, 5], errors='coerce').fillna(0)
        unsold_df = sku_details[(sales_col == 0) & (stock_col > 0)].copy()  # 🔧 剔除0库存
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        return DashboardComponents.create_unsold_category_pie(unsold_df)
    except Exception as e:
        print(f"滞销分类饼图更新错误: {e}")
        return html.Div(f"图表生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    Output('unsold-price-distribution', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_price_distribution(upload_trigger, selected_categories):
    """更新滞销价格带分布"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        unsold_df = sku_details[sales_col == 0].copy()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        return DashboardComponents.create_unsold_price_distribution(unsold_df)
    except Exception as e:
        print(f"滞销价格分布更新错误: {e}")
        return html.Div(f"图表生成失败: {str(e)}", className="alert alert-danger")

@app.callback(
    Output('unsold-top-table', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_unsold_top_table(upload_trigger, selected_categories):
    """更新TOP20高风险滞销商品表格"""
    try:
        sku_details = loader.data.get('sku_details', pd.DataFrame())
        if sku_details.empty:
            return html.Div("暂无数据", className="alert alert-info")
        
        sales_col = pd.to_numeric(sku_details.iloc[:, 2], errors='coerce').fillna(0)
        unsold_df = sku_details[sales_col == 0].copy()
        
        # 应用分类筛选
        if selected_categories and len(selected_categories) > 0:
            unsold_df = unsold_df[unsold_df.iloc[:, 3].isin(selected_categories)]
        
        return DashboardComponents.create_unsold_top_table(unsold_df)
    except Exception as e:
        print(f"滞销TOP表格更新错误: {e}")
        return html.Div(f"表格生成失败: {str(e)}", className="alert alert-danger")

# ========== 成本&毛利分析Callbacks（P0功能） ==========
@app.callback(
    Output('cost-analysis-content', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_cost_analysis(upload_trigger, selected_categories):
    """更新成本&毛利分析内容"""
    try:
        # 检查是否有成本数据
        cost_summary = loader.data.get('cost_summary', pd.DataFrame())
        high_margin = loader.data.get('high_margin_products', pd.DataFrame())
        low_margin = loader.data.get('low_margin_warning', pd.DataFrame())
        
        if cost_summary.empty and high_margin.empty and low_margin.empty:
            return dbc.Alert([
                html.H5("⚠️ 未检测到成本数据", className="alert-heading"),
                html.Hr(),
                html.P([
                    "当前报告不包含成本相关数据。如需启用成本分析，请确保原始数据包含以下列之一：",
                    html.Ul([
                        html.Li("成本 / 成本价 / cost"),
                        html.Li("进价 / 进货价 / 采购价")
                    ]),
                    "然后重新上传数据并分析。"
                ], className="mb-0")
            ], color="warning", style={'margin': '20px 0'})
        
        # 生成成本分析可视化
        return DashboardComponents.create_cost_analysis_charts(cost_summary, high_margin, low_margin)
    
    except Exception as e:
        import traceback
        print(f"成本分析更新错误: {e}")
        print(traceback.format_exc())
        return dbc.Alert(f"❌ 成本分析生成失败: {str(e)}", color="danger")

@app.callback(
    Output('cost-insights', 'children'),
    [Input('upload-trigger', 'data'),
     Input('category-filter-state', 'data')]
)
def update_cost_insights(upload_trigger, selected_categories):
    """更新成本分析智能洞察"""
    try:
        cost_summary = loader.data.get('cost_summary', pd.DataFrame())
        if cost_summary.empty:
            return html.Div()
        
        return DashboardComponents.generate_cost_insights(cost_summary)
    except Exception as e:
        print(f"成本洞察更新错误: {e}")
        return html.Div()

@app.callback(
    [Output('download-png', 'data'),
     Output('png-export-status', 'children')],
    Input('export-png-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_to_png(n_clicks):
    """导出所有图表为PNG图片压缩包"""
    if n_clicks > 0:
        try:
            import zipfile
            import tempfile
            import shutil
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建图表列表（需要重新生成所有图表的figure对象）
            charts_to_export = []
            
            try:
                # 从loader获取数据
                category_df = loader.data.get('category_l1', pd.DataFrame())
                price_df = loader.data.get('price_analysis', pd.DataFrame())
                
                if not category_df.empty:
                    # 1. 分类月售柱状图
                    fig1 = px.bar(
                        category_df.head(15), 
                        x='一级分类', 
                        y='月售',
                        title='各分类月售TOP15'
                    )
                    charts_to_export.append(('01_分类月售分析.png', fig1))
                    
                    # 2. 多规格SKU对比图
                    if '美团一级分类多规格SKU数' in category_df.columns:
                        fig2 = go.Figure()
                        fig2.add_trace(go.Bar(
                            name='多规格SKU',
                            x=category_df['一级分类'].head(10),
                            y=category_df['美团一级分类多规格SKU数'].head(10)
                        ))
                        fig2.update_layout(title='多规格商品分布TOP10')
                        charts_to_export.append(('02_多规格商品分析.png', fig2))
                    
                    # 3. 动销率对比图
                    if '美团一级分类动销率(类内)' in category_df.columns:
                        fig3 = px.bar(
                            category_df.head(15),
                            x='一级分类',
                            y='美团一级分类动销率(类内)',
                            title='各分类动销率对比TOP15'
                        )
                        charts_to_export.append(('03_动销率分析.png', fig3))
                
                if not price_df.empty and 'price_band' in price_df.columns:
                    # 4. 价格带分布图
                    fig4 = px.bar(
                        price_df,
                        x='price_band',
                        y='SKU数量',
                        title='价格带SKU分布'
                    )
                    charts_to_export.append(('04_价格带分析.png', fig4))
                
                # 导出所有图表为PNG
                exported_files = []
                for filename, fig in charts_to_export:
                    try:
                        img_path = os.path.join(temp_dir, filename)
                        fig.write_image(img_path, width=1200, height=800, scale=2)
                        exported_files.append(filename)
                    except Exception as e:
                        print(f"导出图表 {filename} 失败: {e}")
                        continue
                
                if len(exported_files) == 0:
                    raise Exception("没有图表可以导出，请确保已安装kaleido库")
                
                # 创建ZIP压缩包
                zip_filename = f"O2O看板图表_{timestamp}.zip"
                zip_path = os.path.join(temp_dir, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for filename in exported_files:
                        file_path = os.path.join(temp_dir, filename)
                        zipf.write(file_path, filename)
                
                # 读取ZIP文件
                with open(zip_path, 'rb') as f:
                    zip_bytes = f.read()
                
                # 清理临时文件
                shutil.rmtree(temp_dir)
                
                success_msg = html.Div([
                    html.Div(f"✅ 成功导出 {len(exported_files)} 张高清图表！", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div(f"文件名: {zip_filename}", style={'fontSize': '12px'}),
                    html.Div(f"包含图表: {', '.join([f.replace('.png', '') for f in exported_files])}", 
                            style={'fontSize': '11px', 'marginTop': '5px', 'color': '#155724'})
                ], style={'color': '#155724', 'backgroundColor': '#d4edda', 
                         'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #28a745'})
                
                return dcc.send_bytes(zip_bytes, zip_filename), success_msg
                
            except ImportError as ie:
                # kaleido未安装
                error_msg = html.Div([
                    html.Div("⚠️ 需要安装图表导出库", style={'fontWeight': 'bold', 'marginBottom': '5px'}),
                    html.Div("请在终端运行: pip install kaleido", style={'fontSize': '12px', 'marginTop': '5px'}),
                    html.Div("或使用浏览器截图: F12 → Ctrl+Shift+P → 输入'screenshot'", 
                            style={'fontSize': '11px', 'marginTop': '5px', 'color': '#856404'})
                ], style={'color': '#856404', 'backgroundColor': '#fff3cd', 
                         'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #ffc107'})
                return None, error_msg
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"PNG导出错误详情:\n{error_detail}")
            error_msg = html.Div(f"❌ 导出失败: {str(e)}", 
                                style={'color': '#721c24', 'backgroundColor': '#f8d7da', 
                                      'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #dc3545'})
            return None, error_msg
    
    return None, ""


@app.callback(
    [Output('download-pdf', 'data'),
     Output('pdf-export-status', 'children')],
    Input('export-pdf-btn', 'n_clicks'),
    prevent_initial_call=True
)
def export_to_pdf(n_clicks):
    """服务端生成高质量PDF报告"""
    if n_clicks > 0:
        try:
            # 从loader获取数据
            kpi_df = loader.data.get('kpi', pd.DataFrame())
            category_df = loader.data.get('category_l1', pd.DataFrame())
            price_df = loader.data.get('price_analysis', pd.DataFrame())
            
            # 生成PDF
            pdf_bytes = generate_dashboard_pdf(kpi_df, category_df, price_df)
            
            # 生成文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"O2O门店分析报告_{timestamp}.pdf"
            
            success_msg = html.Div(f"✅ PDF报告生成成功！文件名: {filename}", 
                                  style={'color': '#155724', 'backgroundColor': '#d4edda', 
                                        'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #28a745'})
            
            return dcc.send_bytes(pdf_bytes, filename), success_msg
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"PDF生成错误详情:\n{error_detail}")
            error_msg = html.Div(f"❌ PDF生成失败: {str(e)}", 
                                style={'color': '#721c24', 'backgroundColor': '#f8d7da', 
                                      'padding': '10px', 'borderRadius': '5px', 'border': '1px solid #dc3545'})
            return None, error_msg
    
    return None, ""


def generate_dashboard_pdf(kpi_df, category_df, price_df):
    """生成完整的数据看板PDF报告"""
    # 创建PDF缓冲区
    buffer = io.BytesIO()
    
    # 使用横向A4纸张
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    
    # 注册中文字体（使用系统自带字体）
    try:
        # Windows系统字体路径（优先使用.ttf格式）
        font_paths = [
            "C:\\Windows\\Fonts\\simhei.ttf",   # 黑体（推荐）
            "C:\\Windows\\Fonts\\msyh.ttf",    # 微软雅黑
            "C:\\Windows\\Fonts\\simkai.ttf",  # 楷体
            "C:\\Windows\\Fonts\\simsun.ttc",  # 宋体
        ]
        
        font_registered = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('chinese', font_path))
                    c.setFont('chinese', 12)
                    font_registered = True
                    print(f"✅ 成功加载字体: {font_path}")
                    break
                except Exception as e:
                    print(f"⚠️ 字体加载失败 {font_path}: {e}")
                    continue
        
        if not font_registered:
            print("⚠️ 未找到中文字体，使用默认字体")
            c.setFont('Helvetica', 12)
    except Exception as e:
        print(f"字体注册错误: {e}")
        c.setFont('Helvetica', 12)
    
    page_num = 1
    
    # ===== 第1页：封面 =====
    draw_cover_page(c, page_width, page_height)
    c.showPage()
    page_num += 1
    
    # ===== 第2页：核心指标概览 =====
    try:
        c.setFont('chinese', 20)
        c.drawString(50, page_height - 50, "核心指标概览")
        
        # 绘制KPI卡片
        y_offset = page_height - 120
        if kpi_df is not None and not kpi_df.empty:
            draw_kpi_cards(c, kpi_df, 50, y_offset, page_width)
        else:
            c.setFont('chinese', 12)
            c.drawString(50, y_offset, "KPI数据不可用")
        
        c.setFont('chinese', 10)
        c.drawString(page_width - 100, 30, f"第 {page_num} 页")
        c.showPage()
        page_num += 1
    except Exception as e:
        print(f"KPI页面生成错误: {e}")
        import traceback
        print(traceback.format_exc())
    
    # ===== 第3页：数据摘要表格 =====
    try:
        c.setFont('chinese', 20)
        c.drawString(50, page_height - 50, "� 分类数据摘要")
        
        # 绘制摘要表格
        if category_data is not None and not category_data.empty:
            draw_summary_table(c, category_data, 50, page_height - 100, page_width - 100, page_num)
        
        c.setFont('chinese', 10)
        c.drawString(page_width - 100, 30, f"第 {page_num} 页")
        c.showPage()
        page_num += 1
    except Exception as e:
        print(f"摘要表格生成错误: {e}")
    
    # ===== 第4页：图表导出说明 =====
    try:
        c.setFont('chinese', 18)
        c.drawString(50, page_height - 50, "关于图表导出")
        
        c.setFont('chinese', 12)
        y_pos = page_height - 120
        
        notes = [
            "本PDF报告包含核心数据指标和摘要信息。",
            "",
            "完整的交互式图表（包括11个分析看板）请在浏览器中查看：",
            "- 分类月售分析",
            "- 多规格商品供给分析", 
            "- 折扣供给与销售分析",
            "- 价格带分布分析",
            "- 销售四维气泡图",
            "- 销售树状图",
            "- 库存健康看板",
            "- 促销效能分析",
            "- SKU结构优化建议",
            "",
            "如需导出特定图表，可在浏览器中右键点击图表，选择'保存图片'。",
            "",
            "本报告生成时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        
        for note in notes:
            c.drawString(80, y_pos, note)
            y_pos -= 25
        
        c.setFont('chinese', 10)
        c.drawString(page_width - 100, 30, f"第 {page_num} 页")
        c.showPage()
        page_num += 1
        
    except Exception as e:
        print(f"说明页生成错误: {e}")
    
    # 保存PDF
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def draw_summary_table(c, data, x, y, max_width, page_num):
    """绘制数据摘要表格"""
    try:
        c.setFont('chinese', 10)
    except:
        c.setFont('Helvetica', 10)
    
    # 选择关键列
    key_columns = ['一级分类', '美团一级分类sku数', '月售', '售价销售额', 
                   '美团一级分类动销率(类内)', '美团一级分类活动SKU占比(类内)',
                   '美团一级分类0库存率']
    
    # 筛选存在的列
    available_cols = [col for col in key_columns if col in data.columns]
    
    if not available_cols:
        c.drawString(x, y, "数据表格不可用")
        return
    
    # 表格参数
    row_height = 20
    col_width = max_width / len(available_cols)
    
    # 绘制表头
    c.setFillColor(colors.HexColor('#2c3e50'))
    c.rect(x, y - row_height, max_width, row_height, fill=1)
    
    c.setFillColor(colors.white)
    for idx, col in enumerate(available_cols):
        col_name = col.replace('美团一级分类', '')
        c.drawString(x + idx * col_width + 5, y - row_height + 5, col_name)
    
    # 绘制数据行（前10行）
    c.setFillColor(colors.black)
    for row_idx, (_, row) in enumerate(data.head(10).iterrows()):
        row_y = y - (row_idx + 2) * row_height
        
        # 交替行背景
        if row_idx % 2 == 0:
            c.setFillColor(colors.HexColor('#f8f9fa'))
            c.rect(x, row_y, max_width, row_height, fill=1)
        
        c.setFillColor(colors.black)
        for col_idx, col in enumerate(available_cols):
            value = row[col]
            
            # 格式化数值
            if isinstance(value, (int, float)):
                if '率' in col or '占比' in col:
                    display_value = f"{value:.1%}" if value < 1 else f"{value:.1f}%"
                elif '销售额' in col:
                    display_value = f"{int(value):,}"
                else:
                    display_value = f"{int(value)}" if value == int(value) else f"{value:.1f}"
            else:
                display_value = str(value)[:15]  # 限制长度
            
            c.drawString(x + col_idx * col_width + 5, row_y + 5, display_value)


def draw_cover_page(c, page_width, page_height):
    """绘制PDF封面"""
    try:
        c.setFont('chinese', 36)
    except:
        c.setFont('Helvetica-Bold', 36)
    
    # 标题
    title = "O2O门店数据分析报告"
    c.drawCentredString(page_width / 2, page_height - 150, title)
    
    # 副标题
    try:
        c.setFont('chinese', 18)
    except:
        c.setFont('Helvetica', 18)
    
    subtitle = "数据驱动 · 精准洞察 · 科学决策"
    c.drawCentredString(page_width / 2, page_height - 200, subtitle)
    
    # 生成时间
    try:
        c.setFont('chinese', 14)
    except:
        c.setFont('Helvetica', 14)
    
    report_date = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    c.drawCentredString(page_width / 2, page_height - 400, f"生成时间: {report_date}")
    
    # 页脚
    try:
        c.setFont('chinese', 10)
    except:
        c.setFont('Helvetica', 10)
    
    c.drawCentredString(page_width / 2, 50, "本报告由O2O门店数据分析看板自动生成")


def draw_kpi_cards(c, kpi_data, x, y, page_width):
    """在PDF中绘制KPI指标卡片"""
    try:
        c.setFont('chinese', 12)
    except:
        c.setFont('Helvetica', 12)
    
    # KPI列配置
    kpi_cols = [
        '总SKU数(含多规格)', '多规格SKU数', '多规格SPU数', '去重SKU数', 
        '动销SKU数', '动销率', '活动SKU数', '活动SKU占比', 
        '爆品SKU数', '折扣SKU数', '折扣'
    ]
    
    # 每行显示4个指标
    cards_per_row = 4
    card_width = (page_width - 100) / cards_per_row - 20
    card_height = 80
    
    for idx, col in enumerate(kpi_cols):
        if col not in kpi_data.columns:
            continue
            
        value = kpi_data[col].iloc[0] if not kpi_data[col].empty else "N/A"
        
        # 计算卡片位置
        row = idx // cards_per_row
        col_pos = idx % cards_per_row
        
        card_x = x + col_pos * (card_width + 20)
        card_y = y - row * (card_height + 20)
        
        # 绘制卡片边框
        c.setStrokeColor(colors.HexColor('#e9ecef'))
        c.setFillColor(colors.HexColor('#f8f9fa'))
        c.rect(card_x, card_y - card_height, card_width, card_height, fill=1)
        
        # 绘制标题
        c.setFillColor(colors.HexColor('#6c757d'))
        try:
            c.setFont('chinese', 10)
        except:
            c.setFont('Helvetica', 10)
        c.drawString(card_x + 10, card_y - 25, col)
        
        # 绘制数值
        c.setFillColor(colors.HexColor('#2c3e50'))
        try:
            c.setFont('chinese', 16)
        except:
            c.setFont('Helvetica-Bold', 16)
        
        # 格式化数值
        if isinstance(value, (int, float)):
            if '率' in col or '占比' in col or '折扣' in col:
                display_value = f"{value:.1%}" if value < 1 else f"{value:.1f}%"
            else:
                display_value = f"{int(value):,}"
        else:
            display_value = str(value)
        
        c.drawString(card_x + 10, card_y - 55, display_value)


def export_charts_to_pdf(c, chart_element, x, y, max_width, max_height):
    """将Dash图表元素导出为PDF图片"""
    try:
        # 由于Dash回调中的图表是动态生成的，我们需要重新创建图表
        # 这里使用占位符文本，实际实现中需要访问存储的图表数据
        
        try:
            c.setFont('chinese', 12)
        except:
            c.setFont('Helvetica', 12)
        
        c.setFillColor(colors.HexColor('#6c757d'))
        c.drawString(x, y, "图表区域（动态内容需在浏览器中查看）")
        
        # 绘制边框表示图表位置
        c.setStrokeColor(colors.HexColor('#dee2e6'))
        c.setFillColor(colors.white)
        c.rect(x, y - 300, max_width, 280, fill=0)
        
    except Exception as e:
        print(f"图表导出错误: {e}")
        try:
            c.setFont('chinese', 12)
        except:
            c.setFont('Helvetica', 12)
        c.setFillColor(colors.HexColor('#dc3545'))
        c.drawString(x, y, f"图表区域")


# ========== 数据下钻回调 ==========
@app.callback(
    [Output('drilldown-modal', 'is_open'),
     Output('drilldown-modal-title', 'children'),
     Output('drilldown-modal-body', 'children')],
    [Input('category-sales-graph', 'clickData'),
     Input('drilldown-modal-close-btn', 'n_clicks')],
    [State('drilldown-modal', 'is_open')],
    prevent_initial_call=True  # 防止初始加载时触发，因为graph是动态生成的
)
def handle_category_drilldown(clickData, n_clicks, is_open):
    """处理一级分类图表的点击下钻事件"""
    ctx = dash.callback_context
    
    # 如果点击关闭按钮，则关闭Modal
    if ctx.triggered and ctx.triggered[0]['prop_id'].split('.')[0] == 'drilldown-modal-close-btn':
        return False, "", ""

    # 如果有点击数据，则打开Modal并显示内容
    if clickData:
        try:
            # 1. 提取点击的分类名称
            clicked_category = clickData['points'][0]['x']
            
            # 2. 获取详细SKU数据
            sku_details_df = loader.data.get('sku_details', pd.DataFrame())
            
            if sku_details_df.empty:
                return True, f"分类: {clicked_category}", html.Div("无法加载详细SKU数据", className="alert alert-warning")

            # 3. 查找"一级分类"列
            category_col_name = None
            if '一级分类' in sku_details_df.columns:
                category_col_name = '一级分类'
            else:
                # 尝试从列名中找到包含"分类"的列
                for col in sku_details_df.columns:
                    if '分类' in str(col) and '一级' in str(col):
                        category_col_name = col
                        break

            if not category_col_name:
                return True, f"分类: {clicked_category}", html.Div(
                    f"在SKU明细表中未找到'一级分类'列。可用列：{', '.join(sku_details_df.columns[:5])}...", 
                    className="alert alert-danger"
                )

            # 4. 筛选属于该分类的SKU
            filtered_df = sku_details_df[sku_details_df[category_col_name] == clicked_category].copy()
            
            # 5. 创建要显示的表格
            if filtered_df.empty:
                table_content = html.Div(
                    f'在"{clicked_category}"分类下未找到任何SKU', 
                    className="alert alert-info"
                )
            else:
                # 选择性展示关键列
                display_cols = ['商品名称', '售价', '月售', '库存', '商品角色', '规格', '条码']
                existing_display_cols = [col for col in display_cols if col in filtered_df.columns]
                
                if not existing_display_cols:
                    # 如果预定义列都不存在，则显示前7列
                    existing_display_cols = filtered_df.columns[:7].tolist()
                
                # 格式化数值列
                display_df = filtered_df[existing_display_cols].copy()
                for col in ['售价', '月售', '库存']:
                    if col in display_df.columns:
                        display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0)
                
                if '售价' in display_df.columns:
                    display_df['售价'] = display_df['售价'].apply(lambda x: f'¥{x:,.2f}' if pd.notna(x) else '¥0.00')

                table_content = dbc.Table.from_dataframe(
                    display_df, 
                    striped=True, 
                    bordered=True, 
                    hover=True,
                    responsive=True,
                    className="align-middle text-center"
                )

            # 6. 设置Modal标题和内容，并打开
            modal_title = f"📊 下钻详情: {clicked_category} (共 {len(filtered_df)} 个SKU)"
            return True, modal_title, table_content
            
        except Exception as e:
            import traceback
            error_content = html.Div([
                html.H5("❌ 处理下钻数据时出错", className="text-danger"),
                html.Pre(f"{str(e)}\n\n{traceback.format_exc()}", style={'fontSize': '0.8rem'})
            ])
            return True, "发生错误", error_content

    return is_open, "", ""


# AI智能分析Callback已删除（P0优化）

def collect_dashboard_data(selected_categories=None):
    """收集Dashboard所有数据用于AI分析 - 深度版本"""
    
    # 获取当前加载的数据 - 使用正确的键名
    kpi_data = loader.data.get('kpi', pd.DataFrame())
    category_data = loader.data.get('category_l1', pd.DataFrame())
    price_data = loader.data.get('price_analysis', pd.DataFrame())
    
    # 如果有分类筛选,应用筛选
    if selected_categories and len(selected_categories) > 0:
        if '一级分类' in category_data.columns:
            category_data = category_data[category_data['一级分类'].isin(selected_categories)]
    
    # ========== 1. 提取核心KPI ==========
    kpi_dict = {}
    if not kpi_data.empty and len(kpi_data) > 0:
        for col in kpi_data.columns:
            value = kpi_data[col].iloc[0]
            # 处理数值,转换百分比等
            if pd.notna(value):
                if isinstance(value, str) and '%' in value:
                    # 处理百分比字符串
                    try:
                        kpi_dict[col] = float(value.replace('%', ''))
                    except:
                        kpi_dict[col] = value
                else:
                    kpi_dict[col] = value
            else:
                kpi_dict[col] = 0
    
    # ========== 2. 分类数据深度提取 ==========
    category_summary = []
    if not category_data.empty:
        # 确保必要列存在
        required_cols = ['一级分类', '售价销售额']
        if all(col in category_data.columns for col in required_cols):
            # 按销售额排序,获取全部分类(不只是TOP10)
            sorted_cats = category_data.sort_values('售价销售额', ascending=False).copy()
            
            # 提取关键字段
            for idx, row in sorted_cats.iterrows():
                cat_info = {
                    '一级分类': row['一级分类'] if '一级分类' in row and pd.notna(row['一级分类']) else '未知',
                    '售价销售额': row['售价销售额'] if '售价销售额' in row and pd.notna(row['售价销售额']) else 0,
                    '美团一级分类去重SKU数(口径同动销率)': row['美团一级分类去重SKU数(口径同动销率)'] if '美团一级分类去重SKU数(口径同动销率)' in row and pd.notna(row['美团一级分类去重SKU数(口径同动销率)']) else 0,
                    '美团一级分类动销率(类内)': row['美团一级分类动销率(类内)'] if '美团一级分类动销率(类内)' in row and pd.notna(row['美团一级分类动销率(类内)']) else 0,
                    '美团一级分类折扣': row['美团一级分类折扣'] if '美团一级分类折扣' in row and pd.notna(row['美团一级分类折扣']) else 10,
                }
                
                # 添加爆品/滞销数据(如果有)
                if '爆品数' in category_data.columns:
                    cat_info['爆品数'] = row['爆品数'] if pd.notna(row['爆品数']) else 0
                if '滞销数' in category_data.columns:
                    cat_info['滞销数'] = row['滞销数'] if pd.notna(row['滞销数']) else 0
                
                # 添加促销相关(如果有)
                if len(category_data.columns) > 24:  # Y列：折扣力度
                    discount_level = row.iloc[24] if pd.notna(row.iloc[24]) else 10
                    cat_info['折扣力度'] = discount_level
                    cat_info['促销强度'] = ((10 - discount_level) / 9 * 100) if discount_level < 10 else 0
                
                category_summary.append(cat_info)
    
    # ========== 3. 价格带数据提取 ==========
    price_summary = []
    if not price_data.empty and 'price_band' in price_data.columns:
        for idx, row in price_data.iterrows():
            price_info = {
                'price_band': row['price_band'] if 'price_band' in row and pd.notna(row['price_band']) else '未知',
                'SKU数量': row['SKU数量'] if 'SKU数量' in row and pd.notna(row['SKU数量']) else 0,
                '销售额': row['销售额'] if '销售额' in row and pd.notna(row['销售额']) else 0,
                '销售额占比': row['销售额占比'] if '销售额占比' in row and pd.notna(row['销售额占比']) else 0
            }
            price_summary.append(price_info)
    
    # ========== 4. 促销强度TOP分类 ==========
    promo_summary = []
    if category_summary:  # 已在category_summary中计算
        # 按促销强度排序
        promo_cats = sorted(
            [c for c in category_summary if '促销强度' in c],
            key=lambda x: x.get('促销强度', 0),
            reverse=True
        )[:10]
        
        for cat in promo_cats:
            promo_summary.append({
                '分类': cat.get('一级分类', '未知'),
                '促销强度': cat.get('促销强度', 0),
                '折扣力度': cat.get('折扣力度', 10)
            })
    
    # ========== 5. 计算衍生指标 ==========
    meta_info = {
        '总分类数': len(category_data),
        '筛选分类': selected_categories if selected_categories else '全部',
        '分析时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'TOP3销售额占比': 0,
        '健康分类数': 0,
        '问题分类数': 0
    }
    
    if category_summary:
        # TOP3集中度
        total_revenue = sum(c.get('售价销售额', 0) for c in category_summary)
        top3_revenue = sum(c.get('售价销售额', 0) for c in category_summary[:3])
        if total_revenue > 0:
            meta_info['TOP3销售额占比'] = (top3_revenue / total_revenue) * 100
        
        # 健康分类统计
        for cat in category_summary:
            moverate = cat.get('美团一级分类动销率(类内)', 0)
            if moverate >= 60:
                meta_info['健康分类数'] += 1
            else:
                meta_info['问题分类数'] += 1
    
    return {
        'kpi': kpi_dict,
        'category': category_summary,  # 全部分类,不只TOP10
        'price': price_summary,
        'promo': promo_summary,
        'meta': meta_info
    }


# Panel AI分析回调函数已全部删除（P0优化）
# 包括: KPI看板AI、分类看板AI、价格带看板AI、促销看板AI、成本看板AI、主AI综合诊断


# ========================================
# 原始数据分析回调 - untitled1.py集成
# ========================================

# 回调1: 上传原始数据后自动填充门店名称
@app.callback(
    [Output('store-name-input', 'value'),
     Output('btn-run-analysis', 'disabled'),
     Output('upload-raw-data', 'style'),
     Output('analysis-status', 'children', allow_duplicate=True)],
    [Input('upload-raw-data', 'contents'),
     Input('upload-raw-data', 'filename')],
    [State('store-name-input', 'value')],
    prevent_initial_call=True
)
def enable_analysis_button(file_contents, filename, current_store_name):
    """上传文件后自动填充门店名称并显示信息"""
    
    # 调试输出
    print(f"\n{'='*60}")
    print(f"🔔 enable_analysis_button 回调被触发!")
    print(f"   - filename: {filename}")
    print(f"   - file_contents存在: {bool(file_contents)}")
    print(f"   - current_store_name: {current_store_name}")
    print(f"{'='*60}\n")
    
    # 基础上传样式
    base_style = {
        'width': '100%',
        'height': '120px',
        'borderWidth': '3px',
        'borderRadius': '10px',
        'textAlign': 'center',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease'
    }
    
    if file_contents and filename:
        # 文件已上传 - 高亮显示
        upload_style = {
            **base_style,
            'borderStyle': 'solid',
            'borderColor': '#28a745',
            'backgroundColor': '#d4edda'
        }
        
        # 自动提取门店名称(去除文件扩展名和特殊字符)
        import re
        # 去除扩展名
        store_name_from_file = filename.rsplit('.', 1)[0]
        # 去除括号中的数字 如: 鲸星购(1) -> 鲸星购
        store_name_from_file = re.sub(r'\(\d+\)$', '', store_name_from_file).strip()
        
        # 如果用户已经手动输入了门店名,保留用户输入
        # 否则使用从文件名提取的名称
        final_store_name = current_store_name if current_store_name else store_name_from_file
        
        # 显示文件信息
        file_info = html.Div([
            html.Div([
                html.I(className="fas fa-check-circle", style={'color': '#28a745', 'marginRight': '8px', 'fontSize': '18px'}),
                html.Span(f"✅ 文件已上传: {filename}", style={'color': '#28a745', 'fontWeight': 'bold', 'fontSize': '15px'})
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.Span("📝 门店名称: ", style={'color': '#666', 'fontSize': '14px', 'marginRight': '5px'}),
                html.Span(final_store_name, style={'color': '#28a745', 'fontSize': '14px', 'fontWeight': 'bold'}),
                html.Br(),
                html.Small("(可在右侧输入框修改门店名称)", style={'color': '#999', 'fontSize': '12px'})
            ], style={'marginTop': '5px'})
        ], style={'backgroundColor': '#d4edda', 'padding': '12px', 'borderRadius': '8px', 'border': '1px solid #c3e6cb'})
        
        # 有文件就启用按钮
        return final_store_name, False, upload_style, file_info
    else:
        # 未上传文件 - 默认样式
        upload_style = {
            **base_style,
            'borderStyle': 'dashed',
            'borderColor': '#28a745',
            'backgroundColor': '#f0fff4'
        }
        return '', True, upload_style, html.Div()


# 回调2: 运行untitled1.py分析
@app.callback(
    [Output('analysis-status', 'children'),
     Output('upload-trigger', 'data', allow_duplicate=True)],
    [Input('btn-run-analysis', 'n_clicks')],
    [State('upload-raw-data', 'contents'),
     State('upload-raw-data', 'filename'),
     State('store-name-input', 'value'),
     State('upload-trigger', 'data')],
    prevent_initial_call=True,
    running=[
        (Output('btn-run-analysis', 'disabled'), True, False),
        (Output('store-name-input', 'disabled'), True, False),
    ]
)
def run_untitled1_analysis(n_clicks, file_contents, filename, store_name, current_trigger):
    """运行完整的门店分析流程"""
    global loader, store_manager
    
    if not n_clicks or n_clicks == 0:
        raise PreventUpdate
    
    if not file_contents or not store_name:
        error_msg = html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-circle", style={'marginRight': '8px', 'fontSize': '18px'}),
                "❌ 请上传文件并输入门店名称"
            ], style={'color': '#dc3545', 'fontWeight': 'bold', 'fontSize': '15px'})
        ], style={'backgroundColor': '#f8d7da', 'padding': '12px', 'borderRadius': '8px', 'border': '1px solid #f5c6cb'})
        return error_msg, current_trigger
    
    try:
        # 显示开始分析状态
        print(f"\n{'='*60}")
        print(f"🚀 开始分析门店: {store_name}")
        print(f"📁 文件: {filename}")
        print(f"{'='*60}\n")
        
        # 步骤1: 解码上传文件
        print("📥 步骤1/6: 解码上传文件...")
        content_type, content_string = file_contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # 步骤2: 保存临时文件
        print("💾 步骤2/6: 保存临时文件...")
        temp_dir = Path("./temp")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / filename
        
        with open(temp_file, 'wb') as f:
            f.write(decoded)
        print(f"   ✅ 临时文件已保存: {temp_file}")
        
        # 步骤3: 运行untitled1.py分析
        print("🔬 步骤3/6: 运行数据分析...")
        print("   - 列名映射与数据清洗")
        print("   - 多规格商品识别")
        print("   - 商品角色自动分类")
        print("   - 价格带分析")
        print("   - 分类统计计算")
        
        analysis_result = analyzer.analyze_file(
            str(temp_file),
            store_name
        )
        
        if not analysis_result or analysis_result is None:
            error_msg = html.Div([
                html.Div([
                    html.I(className="fas fa-times-circle", style={'marginRight': '8px', 'fontSize': '18px'}),
                    f"❌ 分析失败"
                ], style={'color': '#dc3545', 'fontWeight': 'bold', 'fontSize': '15px', 'marginBottom': '8px'}),
                html.Div("数据分析返回空结果,请检查文件格式", style={'fontSize': '13px', 'color': '#666'})
            ], style={'backgroundColor': '#f8d7da', 'padding': '12px', 'borderRadius': '8px', 'border': '1px solid #f5c6cb'})
            return error_msg, current_trigger
        
        # 从分析结果中获取商品数量
        summary = analyzer.get_summary(store_name)
        total_products = summary.get('总SKU数(含规格)', 0) if summary else 0
        print(f"   ✅ 分析完成! 共处理 {total_products} 个商品")
        
        # 步骤4: 导出Excel报告
        print("📊 步骤4/6: 生成Excel报告...")
        # 保存到本店目录
        report_dir = store_manager.own_stores_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"{store_name}_分析报告.xlsx"
        report_path = report_dir / report_name
        
        export_result = analyzer.export_report(store_name, str(report_path))
        
        if not export_result:
            error_msg = html.Div([
                html.Div("❌ 报告导出失败", style={'color': '#dc3545', 'fontWeight': 'bold', 'fontSize': '15px'})
            ], style={'backgroundColor': '#f8d7da', 'padding': '12px', 'borderRadius': '8px'})
            return error_msg, current_trigger
        
        print(f"   ✅ Excel报告已生成")
        print(f"   📂 保存路径: {report_path.absolute()}")
        
        # 步骤5: 更新系统状态
        print("🔄 步骤5/6: 更新系统状态...")
        store_manager.add_store(store_name, str(report_path), is_competitor=False)
        
        new_loader = store_manager.switch_store(store_name)
        if new_loader:
            loader = new_loader
            print(f"   ✅ DataLoader已切换到新报告")
        
        # 步骤6: 清理临时文件
        print("🧹 步骤6/6: 清理临时文件...")
        temp_file.unlink()
        print(f"   ✅ 临时文件已删除")
        
        # 显示成功消息
        print(f"\n{'='*60}")
        print(f"🎉 分析完成! 看板数据已自动刷新")
        print(f"{'='*60}\n")
        
        success_msg = html.Div([
            html.Div([
                html.I(className="fas fa-check-circle", style={'marginRight': '8px', 'fontSize': '20px'}),
                "🎉 分析完成!"
            ], style={'color': '#28a745', 'fontWeight': 'bold', 'fontSize': '16px', 'marginBottom': '10px'}),
            html.Hr(style={'margin': '10px 0', 'borderTop': '1px solid #c3e6cb'}),
            html.Div([
                html.Div([
                    html.Strong("📊 分析结果: ", style={'marginRight': '5px'}),
                    f"共分析 {total_products} 个商品"
                ], style={'marginBottom': '5px', 'fontSize': '14px'}),
                html.Div([
                    html.Strong("📂 报告路径: ", style={'marginRight': '5px'}),
                    html.Code(str(report_path.absolute()), style={'backgroundColor': '#e9ecef', 'padding': '2px 6px', 'borderRadius': '3px', 'fontSize': '12px'})
                ], style={'marginBottom': '5px', 'fontSize': '14px'}),
                html.Div([
                    html.Strong("� 文件名称: ", style={'marginRight': '5px'}),
                    report_name
                ], style={'fontSize': '14px'})
            ]),
            html.Hr(style={'margin': '10px 0', 'borderTop': '1px solid #c3e6cb'}),
            html.Div("✅ 看板数据已自动刷新，可直接查看最新分析结果", style={'fontSize': '13px', 'color': '#155724', 'fontWeight': 'bold'})
        ], style={
            'backgroundColor': '#d4edda', 
            'padding': '20px', 
            'borderRadius': '10px', 
            'border': '2px solid #c3e6cb',
            'boxShadow': '0 2px 8px rgba(40,167,69,0.2)'
        })
        
        return success_msg, current_trigger + 1
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"❌ 分析过程出错:")
        print(error_detail)
        print(f"{'='*60}\n")
        
        error_msg = html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle", style={'marginRight': '8px', 'fontSize': '18px'}),
                "❌ 分析失败"
            ], style={'color': '#dc3545', 'fontWeight': 'bold', 'fontSize': '15px', 'marginBottom': '10px'}),
            html.Div([
                html.Strong("错误信息: "),
                html.Br(),
                html.Code(str(e), style={'backgroundColor': '#f8d7da', 'padding': '8px', 'display': 'block', 'marginTop': '5px', 'borderRadius': '4px', 'fontSize': '12px'})
            ], style={'fontSize': '13px'}),
            html.Div("💡 请检查上传的文件格式是否正确（需包含: 商品名、售价、销量、分类）", style={'marginTop': '10px', 'fontSize': '12px', 'color': '#856404'})
        ], style={'backgroundColor': '#f8d7da', 'padding': '15px', 'borderRadius': '8px', 'border': '1px solid #f5c6cb'})
        
        return error_msg, current_trigger


# 回调3: 竞对数据上传后自动填充名称
@app.callback(
    [Output('competitor-name-input', 'value'),
     Output('btn-run-competitor-analysis', 'disabled'),
     Output('upload-competitor-data', 'style'),
     Output('competitor-analysis-status', 'children', allow_duplicate=True)],
    [Input('upload-competitor-data', 'contents'),
     Input('upload-competitor-data', 'filename')],
    [State('competitor-name-input', 'value')],
    prevent_initial_call=True
)
def enable_competitor_analysis_button(file_contents, filename, current_name):
    """竞对文件上传后自动填充名称并显示信息"""
    
    # 调试输出
    print(f"\n{'='*60}")
    print(f"🔔 enable_competitor_analysis_button 回调被触发!")
    print(f"   - filename: {filename}")
    print(f"   - file_contents存在: {bool(file_contents)}")
    print(f"   - current_name: {current_name}")
    print(f"{'='*60}\n")
    
    # 基础上传样式
    base_style = {
        'width': '100%',
        'height': '120px',
        'borderWidth': '3px',
        'borderRadius': '10px',
        'textAlign': 'center',
        'cursor': 'pointer',
        'transition': 'all 0.3s ease'
    }
    
    if file_contents and filename:
        # 文件已上传 - 高亮显示
        upload_style = {
            **base_style,
            'borderStyle': 'solid',
            'borderColor': '#dc3545',
            'backgroundColor': '#f8d7da'
        }
        
        # 自动提取竞对名称
        import re
        competitor_name_from_file = filename.rsplit('.', 1)[0]
        competitor_name_from_file = re.sub(r'\(\d+\)$', '', competitor_name_from_file).strip()
        
        final_name = current_name if current_name else competitor_name_from_file
        
        file_info = html.Div([
            html.Div([
                html.I(className="fas fa-check-circle", style={'color': '#dc3545', 'marginRight': '8px', 'fontSize': '18px'}),
                html.Span(f"✅ 竞对文件已上传: {filename}", style={'color': '#dc3545', 'fontWeight': 'bold', 'fontSize': '15px'})
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.I(className="fas fa-info-circle", style={'color': '#666', 'marginRight': '5px'}),
                f"竞对名称: {final_name}"
            ], style={'fontSize': '13px', 'color': '#666'})
        ], style={'backgroundColor': '#fff3cd', 'padding': '12px', 'borderRadius': '8px', 'border': '1px solid #ffeaa7'})
        
        return final_name, False, upload_style, file_info
    else:
        upload_style = {
            **base_style,
            'borderStyle': 'dashed',
            'borderColor': '#dc3545',
            'backgroundColor': '#fff5f5'
        }
        return '', True, upload_style, html.Div()


# 回调4: 运行竞对分析
@app.callback(
    [Output('competitor-analysis-status', 'children'),
     Output('upload-trigger', 'data', allow_duplicate=True),
     Output('main-tabs', 'active_tab', allow_duplicate=True),  # 新增：自动切换到竞对TAB
     Output('store-switcher', 'value', allow_duplicate=True)],  # 新增：自动选择刚上传的竞对门店
    [Input('btn-run-competitor-analysis', 'n_clicks')],
    [State('upload-competitor-data', 'contents'),
     State('upload-competitor-data', 'filename'),
     State('competitor-name-input', 'value'),
     State('upload-trigger', 'data')],
    prevent_initial_call=True,
    running=[
        (Output('btn-run-competitor-analysis', 'disabled'), True, False),
        (Output('competitor-name-input', 'disabled'), True, False),
    ]
)
def run_competitor_analysis(n_clicks, file_contents, filename, competitor_name, current_trigger):
    """运行竞对门店分析流程"""
    global loader, store_manager
    
    if not n_clicks or n_clicks == 0:
        raise PreventUpdate
    
    if not file_contents or not competitor_name:
        error_msg = html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-circle", style={'marginRight': '8px'}),
                "❌ 请上传竞对文件并输入竞对名称"
            ], style={'color': '#dc3545', 'fontWeight': 'bold'})
        ], style={'backgroundColor': '#f8d7da', 'padding': '12px', 'borderRadius': '8px'})
        return error_msg, current_trigger, dash.no_update, dash.no_update  # 不切换TAB和门店
    
    try:
        print(f"\n{'='*60}")
        print(f"🎯 开始分析竞对: {competitor_name}")
        print(f"📁 文件: {filename}")
        print(f"{'='*60}\n")
        
        # 解码上传文件
        content_type, content_string = file_contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # 保存临时文件
        temp_dir = Path("./temp")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / filename
        
        with open(temp_file, 'wb') as f:
            f.write(decoded)
        
        # 运行分析
        analysis_result = analyzer.analyze_file(str(temp_file), competitor_name)
        
        if not analysis_result:
            error_msg = html.Div([
                html.Div("❌ 竞对分析失败", style={'color': '#dc3545', 'fontWeight': 'bold'})
            ], style={'backgroundColor': '#f8d7da', 'padding': '12px', 'borderRadius': '8px'})
            return error_msg, current_trigger, dash.no_update, dash.no_update  # 分析失败不切换TAB和门店
        
        # 获取分析结果
        summary = analyzer.get_summary(competitor_name)
        total_products = summary.get('总SKU数(含规格)', 0) if summary else 0
        
        # 导出Excel报告到竞对目录
        report_dir = store_manager.competitor_stores_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        report_name = f"{competitor_name}_分析报告.xlsx"
        report_path = report_dir / report_name
        
        analyzer.export_report(competitor_name, str(report_path))
        
        # 添加到门店管理器(标记为竞对)
        store_manager.add_store(competitor_name, str(report_path), is_competitor=True)
        
        # 清理临时文件
        temp_file.unlink()
        
        print(f"\n{'='*60}")
        print(f"🎉 竞对分析完成!")
        print(f"{'='*60}\n")
        
        success_msg = html.Div([
            html.Div([
                html.I(className="fas fa-chart-line", style={'marginRight': '8px', 'fontSize': '20px'}),
                "🎯 竞对分析完成!"
            ], style={'color': '#dc3545', 'fontWeight': 'bold', 'fontSize': '16px', 'marginBottom': '10px'}),
            html.Hr(style={'margin': '10px 0'}),
            html.Div([
                html.Div([
                    html.Strong("📊 分析结果: "),
                    f"共分析 {total_products} 个商品"
                ], style={'marginBottom': '5px', 'fontSize': '14px'}),
                html.Div([
                    html.Strong("📂 报告路径: "),
                    html.Code(str(report_path.absolute()), style={'backgroundColor': '#e9ecef', 'padding': '2px 6px', 'borderRadius': '3px', 'fontSize': '12px'})
                ], style={'fontSize': '14px'})
            ]),
            html.Hr(style={'margin': '10px 0'}),
            html.Div("💡 竞对数据已保存,可用于后续对比分析", style={'fontSize': '13px', 'color': '#721c24', 'fontWeight': 'bold'})
        ], style={
            'backgroundColor': '#f8d7da', 
            'padding': '20px', 
            'borderRadius': '10px', 
            'border': '2px solid #f5c6cb',
            'boxShadow': '0 2px 8px rgba(220,53,69,0.2)'
        })
        
        # 分析成功：返回成功消息 + 刷新触发器 + 切换到竞对TAB + 选择该竞对门店
        return success_msg, current_trigger + 1, 'tab-competitor', competitor_name
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"❌ 竞对分析出错:")
        print(error_detail)
        print(f"{'='*60}\n")
        
        error_msg = html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle", style={'marginRight': '8px'}),
                "❌ 竞对分析失败"
            ], style={'color': '#dc3545', 'fontWeight': 'bold', 'marginBottom': '10px'}),
            html.Div([
                html.Strong("错误信息: "),
                html.Code(str(e), style={'backgroundColor': '#f8d7da', 'padding': '8px', 'display': 'block', 'marginTop': '5px', 'borderRadius': '4px', 'fontSize': '12px'})
            ], style={'fontSize': '13px'})
        ], style={'backgroundColor': '#f8d7da', 'padding': '15px', 'borderRadius': '8px'})
        
        return error_msg, current_trigger, dash.no_update, dash.no_update  # 错误时不切换TAB和门店


# ========== 对比看板渲染辅助函数 ==========

def render_kpi_comparison(own_kpi, competitor_kpi):
    """渲染KPI对比卡片"""
    try:
        cards = []
        metrics = [
            ('总销售额(去重后)', '💰 销售额', True),
            ('总SKU数(去重后)', '📦 SKU数', False),
            ('动销率', '📈 动销率', False),
            ('平均毛利率', '💹 毛利率', False)
        ]
        
        for key, label, is_currency in metrics:
            own_val = own_kpi.get(key, 0) or 0
            comp_val = competitor_kpi.get(key, 0) or 0
            
            try:
                own_val = float(own_val)
                comp_val = float(comp_val)
            except:
                own_val, comp_val = 0, 0
            
            diff = own_val - comp_val
            diff_color = '#27ae60' if diff >= 0 else '#e74c3c'
            
            if is_currency:
                own_text = f"¥{own_val:,.0f}"
                comp_text = f"¥{comp_val:,.0f}"
                diff_text = f"+¥{diff:,.0f}" if diff >= 0 else f"¥{diff:,.0f}"
            elif '率' in label:
                own_text = f"{own_val:.1f}%"
                comp_text = f"{comp_val:.1f}%"
                diff_text = f"+{diff:.1f}%" if diff >= 0 else f"{diff:.1f}%"
            else:
                own_text = f"{int(own_val):,}"
                comp_text = f"{int(comp_val):,}"
                diff_text = f"+{int(diff):,}" if diff >= 0 else f"{int(diff):,}"
            
            cards.append(
                dbc.Col([
                    html.Div([
                        html.Div(label, style={'fontSize': '12px', 'color': '#7f8c8d', 'marginBottom': '5px'}),
                        html.Div([
                            html.Span(f"本店: {own_text}", style={'color': '#1ABC9C', 'fontWeight': 'bold'}),
                            html.Span(" vs ", style={'color': '#95a5a6', 'margin': '0 5px'}),
                            html.Span(f"竞对: {comp_text}", style={'color': '#95a5a6'})
                        ], style={'fontSize': '14px'}),
                        html.Div(f"差异: {diff_text}", style={'fontSize': '13px', 'color': diff_color, 'fontWeight': 'bold', 'marginTop': '3px'})
                    ], style={'backgroundColor': '#f8f9fa', 'padding': '12px', 'borderRadius': '8px', 'textAlign': 'center'})
                ], md=3)
            )
        
        return dbc.Row(cards)
    except Exception as e:
        logger.error(f"KPI对比渲染失败: {e}")
        return html.Div("KPI对比数据加载失败", className="text-muted")


def render_category_comparison(own_category, competitor_category):
    """渲染分类销售额对比图"""
    try:
        if not own_category or not competitor_category:
            return html.Div("分类数据不足", className="text-muted text-center p-3")
        
        own_df = pd.DataFrame(own_category)
        comp_df = pd.DataFrame(competitor_category)
        
        if own_df.empty or comp_df.empty:
            return html.Div("分类数据为空", className="text-muted text-center p-3")
        
        # 获取列名
        cat_col = own_df.columns[0]
        rev_col = None
        for col in own_df.columns:
            if '销售额' in str(col) or '金额' in str(col):
                rev_col = col
                break
        if not rev_col and len(own_df.columns) > 1:
            rev_col = own_df.columns[1]
        
        if not rev_col:
            return html.Div("未找到销售额列", className="text-muted text-center p-3")
        
        # 取TOP10
        own_top = own_df.nlargest(10, rev_col)[[cat_col, rev_col]].rename(columns={rev_col: '本店销售额'})
        comp_top = comp_df.nlargest(10, rev_col)[[cat_col, rev_col]].rename(columns={rev_col: '竞对销售额'})
        
        merged = pd.merge(own_top, comp_top, on=cat_col, how='outer').fillna(0)
        
        # 创建ECharts图表
        categories = merged[cat_col].tolist()
        own_values = merged['本店销售额'].tolist()
        comp_values = merged['竞对销售额'].tolist()
        
        echarts_option = {
            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
            'legend': {'data': ['本店', '竞对'], 'top': 5},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '15%', 'top': '40px', 'containLabel': True},
            'xAxis': {'type': 'category', 'data': categories, 'axisLabel': {'rotate': 30, 'fontSize': 10}},
            'yAxis': {'type': 'value', 'name': '销售额'},
            'series': [
                {'name': '本店', 'type': 'bar', 'data': own_values, 'itemStyle': {'color': '#1ABC9C'}},
                {'name': '竞对', 'type': 'bar', 'data': comp_values, 'itemStyle': {'color': '#95a5a6'}}
            ]
        }
        
        return dash_echarts.DashECharts(option=echarts_option, style={'height': '350px', 'width': '100%'})
    except Exception as e:
        logger.error(f"分类对比渲染失败: {e}")
        return html.Div("分类对比数据加载失败", className="text-muted")


def render_price_comparison(own_price, competitor_price):
    """渲染价格带分布对比图（使用最新的对比视图组件，包含洞察和差异分析引擎）"""
    try:
        if not own_price or not competitor_price:
            return html.Div("价格带数据不足", className="text-muted text-center p-3")
        
        own_df = pd.DataFrame(own_price)
        comp_df = pd.DataFrame(competitor_price)
        
        if own_df.empty or comp_df.empty:
            return html.Div("价格带数据为空", className="text-muted text-center p-3")
        
        # 使用最新的价格带对比视图组件（包含洞察和差异分析引擎）
        return create_price_comparison_view(own_df, comp_df, '竞对', '本店')
    except Exception as e:
        logger.error(f"价格带对比渲染失败: {e}")
        return html.Div("价格带对比数据加载失败", className="text-muted")


def render_radar_comparison(own_kpi, competitor_kpi):
    """渲染综合指标雷达图"""
    try:
        # 定义雷达图指标
        indicators = [
            {'name': '销售额', 'max': 100},
            {'name': 'SKU数', 'max': 100},
            {'name': '动销率', 'max': 100},
            {'name': '毛利率', 'max': 100}
        ]
        
        # 归一化数据
        def normalize(own_val, comp_val):
            max_val = max(own_val, comp_val, 1)
            return (own_val / max_val * 100, comp_val / max_val * 100)
        
        own_sales = float(own_kpi.get('总销售额(去重后)', 0) or 0)
        comp_sales = float(competitor_kpi.get('总销售额(去重后)', 0) or 0)
        own_sku = float(own_kpi.get('总SKU数(去重后)', 0) or 0)
        comp_sku = float(competitor_kpi.get('总SKU数(去重后)', 0) or 0)
        own_rate = float(own_kpi.get('动销率', 0) or 0)
        comp_rate = float(competitor_kpi.get('动销率', 0) or 0)
        own_margin = float(own_kpi.get('平均毛利率', 0) or 0)
        comp_margin = float(competitor_kpi.get('平均毛利率', 0) or 0)
        
        own_data = [
            normalize(own_sales, comp_sales)[0],
            normalize(own_sku, comp_sku)[0],
            own_rate,
            own_margin
        ]
        comp_data = [
            normalize(own_sales, comp_sales)[1],
            normalize(own_sku, comp_sku)[1],
            comp_rate,
            comp_margin
        ]
        
        echarts_option = {
            'tooltip': {'trigger': 'item'},
            'legend': {'data': ['本店', '竞对'], 'top': 5},
            'radar': {
                'indicator': indicators,
                'center': ['50%', '55%'],
                'radius': '65%'
            },
            'series': [{
                'type': 'radar',
                'data': [
                    {'value': own_data, 'name': '本店', 'itemStyle': {'color': '#1ABC9C'}, 'areaStyle': {'opacity': 0.3}},
                    {'value': comp_data, 'name': '竞对', 'itemStyle': {'color': '#95a5a6'}, 'areaStyle': {'opacity': 0.3}}
                ]
            }]
        }
        
        return dash_echarts.DashECharts(option=echarts_option, style={'height': '350px', 'width': '100%'})
    except Exception as e:
        logger.error(f"雷达图渲染失败: {e}")
        return html.Div("雷达图数据加载失败", className="text-muted")


def render_comparison_dashboard(own_data, competitor_data, data_source):
    """渲染对比分析看板内容（不包含选择器，选择器在布局中固定）"""
    global _last_comparison_hash
    
    # 只在对比TAB时渲染
    if data_source != 'comparison':
        return dash.no_update
    
    # 检查数据是否加载
    if own_data is None or competitor_data is None or len(own_data) == 0 or len(competitor_data) == 0:
        return html.Div([
            html.Div([
                html.H3("📌 请在上方选择要对比的门店", className="text-center text-muted", style={'marginTop': '50px', 'marginBottom': '50px'})
            ], style={'padding': '40px'})
        ])
    
    # 检查是否有KPI数据
    own_kpi = own_data.get('kpi', {})
    competitor_kpi = competitor_data.get('kpi', {})
    
    if len(own_kpi) == 0 or len(competitor_kpi) == 0:
        return html.Div([
            html.Div([
                html.H3("⚠️ 数据加载中...", className="text-center text-muted", style={'marginTop': '50px'})
            ], style={'padding': '40px'})
        ])
    
    # � 防止重复渲染：计算数据哈希值
    import json
    try:
        data_hash = hash(json.dumps(own_data, sort_keys=True) + json.dumps(competitor_data, sort_keys=True))
        if _last_comparison_hash == data_hash:
            print(f"🔄 数据未变化，跳过重复渲染（hash={data_hash}）")
            raise PreventUpdate
        _last_comparison_hash = data_hash
        print(f"✅ 对比数据变化，开始渲染（hash={data_hash}）")
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"⚠️ 哈希计算异常: {e}")
    
    if len(own_kpi) == 0 or len(competitor_kpi) == 0:
        return html.Div([
            html.Div([
                html.H3("⚠️ 数据加载中...", className="text-center text-muted", style={'marginTop': '50px'})
            ], style={'padding': '40px'})
        ])
    
    try:
        # 1. 核心KPI对比卡片
        kpi_comparison = render_kpi_comparison(own_kpi, competitor_kpi)
        
        # 2. 一级分类销售额对比图
        category_comparison = render_category_comparison(
            own_data.get('category', []), 
            competitor_data.get('category', [])
        )
        
        # 3. 价格带分布对比
        price_comparison = render_price_comparison(
            own_data.get('price_band', []),
            competitor_data.get('price_band', [])
        )
        
        # 4. 综合指标雷达图
        radar_comparison = render_radar_comparison(own_kpi, competitor_kpi)
        
        # 组装看板（不包含选择器，选择器在布局中固定）
        # 🔧 添加固定key属性，防止React重复挂载组件
        dashboard = html.Div([
            html.Div([
                # 核心KPI对比区域（卡片+表格）
                html.Div([
                    html.H3("📊 核心指标对比", className="mb-3", style={'fontSize': '1.1rem', 'fontWeight': '600'}),
                    kpi_comparison
                ], key='kpi-section', style={'marginBottom': '25px'}),
                
                # 分类对比 + 雷达图（左右分栏）
                dbc.Row([
                    dbc.Col([
                        html.H3("📈 TOP10分类销售额对比", className="mb-3", style={'fontSize': '1.1rem', 'fontWeight': '600'}),
                        category_comparison
                    ], md=7, style={'paddingRight': '15px'}),
                    
                    dbc.Col([
                        html.H3("🎯 综合运营指标对比", className="mb-3", style={'fontSize': '1.1rem', 'fontWeight': '600'}),
                        radar_comparison
                    ], md=5, style={'paddingLeft': '15px'})
                ], key='charts-row', style={'marginBottom': '25px'}),
                
                # 价格带对比
                html.Div([
                    html.H3("💰 价格带分布对比", className="mb-3", style={'fontSize': '1.1rem', 'fontWeight': '600'}),
                    price_comparison
                ], key='price-section', style={'marginBottom': '20px'})
                
            ], style={
                'maxWidth': '1600px',
                'margin': '0 auto',
                'padding': '20px',
                'backgroundColor': 'white'  # 添加白色背景
            })
        ], key='comparison-dashboard-stable')  # 🔧 顶层固定key，防止React误判需要重新挂载
        
        return dashboard
        
    except Exception as e:
        print(f"❌ 对比看板渲染失败: {e}")
        import traceback
        traceback.print_exc()
        
        return html.Div([
            dbc.Alert([
                html.H4("❌ 渲染失败", className="alert-heading"),
                html.P(f"错误信息: {str(e)}")
            ], color="danger", style={'marginTop': '20px'})
        ])

# ========== 门店切换回调已废弃 ==========
# 门店选择器已改为隐藏的Div,不再需要切换功能
# 每次分析后直接刷新当前看板即可

# 回调3: 门店切换 (已废弃 - store-selector现在是隐藏的Div)
# @app.callback(
#     [Output('upload-status', 'children', allow_duplicate=True),
#      Output('upload-trigger', 'data', allow_duplicate=True)],
#     [Input('store-selector', 'value')],
#     [State('upload-trigger', 'data')],
#     prevent_initial_call=True
# )
# def switch_store(selected_store, current_trigger):
#     """切换查看的门店"""
#     global loader, store_manager
#     
#     if not selected_store:
#         raise PreventUpdate
#     
#     try:
#         new_loader = store_manager.switch_store(selected_store)
#         if new_loader:
#             loader = new_loader
#             return html.Div(f"✅ 已切换到门店: {selected_store}", style={'color': '#28a745'}), current_trigger + 1
#         else:
#             return html.Div(f"❌ 门店报告不存在", style={'color': 'red'}), current_trigger
#     except Exception as e:
#         return html.Div(f"❌ 切换失败: {str(e)}", style={'color': 'red'}), current_trigger


# ========== 城市新增竞对分析回调 ==========

# 全局变量存储城市竞对数据
_city_competitor_data = {
    'long_df': None,
    'store_df': None,
    'analyzer': None
}

def load_city_competitor_data():
    """加载城市新增竞对数据"""
    global _city_competitor_data
    
    file_path = Path("城市新增竞对数据/新增竞对.xlsx")
    if not file_path.exists():
        logger.warning(f"⚠️ 城市竞对数据文件不存在: {file_path}")
        return None
    
    try:
        # 加载数据
        loader = CompetitorDataLoader(str(file_path))
        df = loader.load_data()
        
        # 解析宽表转长表
        parser = CompetitorDataParser(df)
        long_df = parser.parse_wide_to_long()
        
        # 添加区域分类
        classifier = get_region_classifier()
        long_df = classifier.classify_batch(long_df)
        store_df = classifier.classify_batch(df)
        
        # 创建分析器
        analyzer = CompetitorAnalyzer(long_df, store_df=store_df)
        
        _city_competitor_data['long_df'] = long_df
        _city_competitor_data['store_df'] = store_df
        _city_competitor_data['analyzer'] = analyzer
        
        logger.info(f"✅ 城市竞对数据加载成功: {len(long_df)}条竞对记录")
        return analyzer
    except Exception as e:
        logger.error(f"❌ 城市竞对数据加载失败: {e}")
        return None


@app.callback(
    [Output('city-competitor-overview-cards', 'children'),
     Output('city-competitor-city-chart', 'option'),
     Output('city-competitor-brand-chart', 'option'),
     Output('city-competitor-circle-region-chart', 'option'),
     Output('city-competitor-region-chart', 'option'),
     Output('city-competitor-urban-circle-chart', 'option'),
     Output('city-competitor-county-circle-chart', 'option'),
     Output('city-competitor-urban-new-circle-chart', 'option'),
     Output('city-competitor-county-new-circle-chart', 'option'),
     Output('city-competitor-new15-chart', 'option'),
     Output('city-competitor-sku-chart', 'option'),
     Output('city-competitor-subsidy-chart', 'option'),
     Output('city-competitor-heatmap-chart', 'option'),
     Output('city-competitor-5km-chart', 'option'),
     Output('city-competitor-brand-expansion-chart', 'option'),
     Output('city-competitor-insights', 'children'),
     Output('city-competitor-keywords', 'children'),
     Output('city-competitor-detail-table', 'children'),
     Output('city-competitor-city-filter', 'options'),
     Output('city-competitor-city-chart', 'resize_id'),
     Output('city-competitor-brand-chart', 'resize_id'),
     Output('city-competitor-circle-region-chart', 'resize_id'),
     Output('city-competitor-region-chart', 'resize_id'),
     Output('city-competitor-urban-circle-chart', 'resize_id'),
     Output('city-competitor-county-circle-chart', 'resize_id'),
     Output('city-competitor-urban-new-circle-chart', 'resize_id'),
     Output('city-competitor-county-new-circle-chart', 'resize_id'),
     Output('city-competitor-new15-chart', 'resize_id'),
     Output('city-competitor-sku-chart', 'resize_id'),
     Output('city-competitor-subsidy-chart', 'resize_id'),
     Output('city-competitor-heatmap-chart', 'resize_id'),
     Output('city-competitor-5km-chart', 'resize_id'),
     Output('city-competitor-brand-expansion-chart', 'resize_id')],
    [Input('main-tabs', 'active_tab'),
     Input('city-competitor-refresh-btn', 'n_clicks'),
     Input('city-competitor-city-filter', 'value'),
     Input('city-competitor-circle-filter', 'value'),
     Input('city-competitor-region-filter', 'value'),
     Input('city-competitor-brand-search', 'value')],
    prevent_initial_call=False
)
def update_city_competitor_analysis(active_tab, n_clicks, city_filter, circle_filter, region_filter, brand_search):
    """更新城市新增竞对分析（ECharts版本）"""
    global _city_competitor_data
    
    # 导入ECharts图表生成函数
    from modules.components.city_competitor_tab import (
        create_overview_cards, create_city_echarts, create_brand_echarts,
        create_circle_region_echarts, create_region_echarts, create_region_circle_echarts,
        create_new_competitor_circle_echarts, create_5km_distribution_echarts, 
        create_keywords_display, create_detail_table, create_brand_expansion_echarts,
        create_insights_display,
        create_new15_echarts, create_sku_scale_echarts, create_subsidy_echarts, create_brand_city_heatmap_echarts
    )
    
    # 检查触发源 - 如果是TAB切换且不是城市竞对TAB，则跳过
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    print(f"🏙️ 城市竞对回调触发: triggered_id={triggered_id}, active_tab={active_tab}")
    
    # 如果是TAB切换触发，且不是城市竞对TAB，则跳过
    if triggered_id == 'main-tabs' and active_tab != 'tab-city-competitor':
        print("⏭️ 跳过：不是城市竞对TAB")
        return (dash.no_update,) * 33
    
    # 加载数据
    print("📊 开始加载城市竞对数据...")
    analyzer = _city_competitor_data.get('analyzer')
    print(f"📊 缓存中的analyzer: {analyzer}")
    if analyzer is None:
        try:
            analyzer = load_city_competitor_data()
            print(f"📊 数据加载结果: analyzer={'成功' if analyzer else '失败'}")
        except Exception as e:
            print(f"❌ 加载异常: {e}")
            import traceback
            traceback.print_exc()
    
    if analyzer is None:
        empty_option = {'title': {'text': '数据加载失败', 'left': 'center', 'top': 'center'}}
        return (
            html.Div("数据加载失败，请检查文件", style={'color': 'red'}),
            empty_option, empty_option, empty_option, empty_option,
            empty_option, empty_option, empty_option, empty_option, empty_option,
            empty_option, empty_option, empty_option, empty_option, empty_option,
            html.Div("暂无洞察"),
            html.Div("暂无数据"),
            html.Div("暂无数据"),
            [],
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  # resize_id
        )
    
    # 构建筛选条件
    filters = {}
    if city_filter:
        filters['city'] = city_filter
    if circle_filter:
        filters['business_circle'] = circle_filter
    if region_filter:
        filters['region'] = region_filter
    if brand_search:
        filters['brand'] = brand_search
    
    # 获取分析数据
    stats = analyzer.get_overview_stats()
    city_summary = analyzer.get_city_summary()
    brand_ranking = analyzer.get_brand_ranking(top_n=10)
    cross_stats = analyzer.get_circle_region_cross_analysis()
    region_stats = analyzer.get_region_analysis()
    region_dist = analyzer.get_region_competitor_distribution()
    keywords = analyzer.extract_brand_keywords()
    details = analyzer.get_competitor_details(filters=filters)
    
    # 新增4个分析数据
    new15_stats = analyzer.get_new_competitor_by_city()
    sku_dist = analyzer.get_sku_scale_distribution()
    subsidy_dist = analyzer.get_subsidy_distribution()
    heatmap_df = analyzer.get_brand_city_heatmap()
    
    print(f"📊 城市竞对数据: stats={stats}")
    
    # 生成城市筛选选项
    city_options = [{'label': city, 'value': city} for city in city_summary['城市'].tolist()]
    
    # 创建ECharts配置
    overview_cards = create_overview_cards(stats)
    city_option = create_city_echarts(city_summary)
    brand_option = create_brand_echarts(brand_ranking)
    circle_region_option = create_circle_region_echarts(cross_stats)
    region_option = create_region_echarts(region_stats)
    
    # 市区/县城门店商圈分布图表
    region_circle_dist = analyzer.get_region_circle_distribution()
    urban_circle_option = create_region_circle_echarts(region_circle_dist.get('市区', {}), '市区')
    county_circle_option = create_region_circle_echarts(region_circle_dist.get('县城', {}), '县城')
    
    # 市区/县城新增竞对商圈分布图表
    new_competitor_circle_dist = analyzer.get_new_competitor_circle_distribution()
    urban_new_circle_option = create_new_competitor_circle_echarts(new_competitor_circle_dist.get('市区', {}), '市区')
    county_new_circle_option = create_new_competitor_circle_echarts(new_competitor_circle_dist.get('县城', {}), '县城')
    
    # 新增4个图表
    new15_option = create_new15_echarts(new15_stats)
    sku_option = create_sku_scale_echarts(sku_dist)
    subsidy_option = create_subsidy_echarts(subsidy_dist)
    heatmap_option = create_brand_city_heatmap_echarts(heatmap_df)
    
    dist_5km_option = create_5km_distribution_echarts(region_dist)
    
    # 品牌扩张趋势
    brand_expansion = analyzer.get_brand_region_expansion()
    brand_expansion_option = create_brand_expansion_echarts(brand_expansion)
    
    # 智能洞察分析
    insights = analyzer.generate_insights()
    insights_display = create_insights_display(insights)
    
    keywords_display = create_keywords_display(keywords)
    detail_table = create_detail_table(details)
    
    # 生成唯一的resize_id来触发图表重绘
    import time
    resize_id = int(time.time() * 1000)
    
    return (
        overview_cards,
        city_option,
        brand_option,
        circle_region_option,
        region_option,
        urban_circle_option,
        county_circle_option,
        urban_new_circle_option,
        county_new_circle_option,
        new15_option,
        sku_option,
        subsidy_option,
        heatmap_option,
        dist_5km_option,
        brand_expansion_option,
        insights_display,
        keywords_display,
        detail_table,
        city_options,
        resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id, resize_id
    )


# 运行应用
if __name__ == '__main__':
    print("🚀 启动O2O门店数据分析看板...")
    print("📊 本机访问地址: http://localhost:8055")
    print("📊 局域网访问地址: http://119.188.71.47:8055")
    print("🌐 花生壳外网访问: https://2bn637md7241.vicp.fun")
    print("💡 提示: 使用0.0.0.0允许花生壳和局域网访问")
    print("🔄 热重载已启用: 代码修改后自动刷新")
    # 使用0.0.0.0允许花生壳客户端访问，启用热重载
    app.run(
        debug=True, 
        host='0.0.0.0', 
        port=8055,
        use_reloader=True,  # 启用热重载
        dev_tools_hot_reload=True  # 启用Dash热重载
    )


