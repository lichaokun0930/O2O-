"""
数据加载器 - P0+P2优化
负责从Excel报告中读取和预处理数据
"""
import pandas as pd
import logging
from .cache import DataCache
from config import get_config

logger = logging.getLogger(__name__)


class DataLoader:
    """数据加载器 - 支持缓存和智能列名映射"""
    
    def __init__(self, excel_path, use_cache=True):
        self.excel_path = excel_path
        self.use_cache = use_cache
        self.data_config = get_config('data')
        self.cache = DataCache() if use_cache else None
        self.data = {
            'kpi': pd.DataFrame(),
            'category_l1': pd.DataFrame(),
            'price_analysis': pd.DataFrame(),
            'role_analysis': pd.DataFrame(),
            'sku_details': pd.DataFrame(),
        }
        self.load_all_data()
    
    def load_all_data(self):
        """加载所有sheet数据（支持缓存）"""
        try:
            # 尝试从缓存加载
            if self.use_cache and self.cache:
                cached_data = self.cache.get(self.excel_path)
                if cached_data:
                    logger.info(f"📦 从缓存加载数据: {self.excel_path}")
                    self.data = cached_data
                    self._log_data_summary()
                    return
            
            # 从Excel加载
            logger.info(f"📂 从Excel加载数据: {self.excel_path}")
            excel_file = pd.ExcelFile(self.excel_path)
            
            # 加载各个sheet
            sheet_mapping = self.data_config['sheet_names']
            
            for key, possible_names in sheet_mapping.items():
                for name in possible_names:
                    if name in excel_file.sheet_names:
                        self.data[key] = pd.read_excel(excel_file, sheet_name=name)
                        logger.info(f"✅ 加载 {key}: '{name}'")
                        break
            
            # 保存到缓存
            if self.use_cache and self.cache:
                self.cache.set(self.excel_path, self.data)
            
            logger.info(f"✅ 数据加载成功: {self.excel_path}")
            self._log_data_summary()
            
        except Exception as e:
            logger.error(f"❌ 数据加载失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _log_data_summary(self):
        """记录数据摘要"""
        logger.info("📊 数据加载完成:")
        logger.info(f"  - KPI数据: {self.data['kpi'].shape}")
        logger.info(f"  - 分类数据: {self.data['category_l1'].shape}")
        logger.info(f"  - 价格带数据: {self.data['price_analysis'].shape}")
        logger.info(f"  - 角色分析: {self.data['role_analysis'].shape}")
    
    def get_kpi_summary(self):
        """获取KPI摘要数据"""
        if self.data['kpi'].empty:
            return {}
        
        kpi_df = self.data['kpi']
        if len(kpi_df) == 0:
            return {}
        
        row = kpi_df.iloc[0]
        summary = {}
        
        # 按列索引提取KPI数据
        for i, col in enumerate(kpi_df.columns):
            value = row.iloc[i] if i < len(row) else 0
            
            if i == 0:  # 门店名称
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
        
        return summary
    
    def get_category_data(self):
        """获取分类数据"""
        return self.data['category_l1']
    
    def get_price_data(self):
        """获取价格带数据"""
        return self.data['price_analysis']
    
    def get_role_data(self):
        """获取角色分析数据"""
        return self.data['role_analysis']
    
    def get_sku_details(self):
        """获取SKU详情数据"""
        return self.data['sku_details']
    
    def reload(self, use_cache=None):
        """
        重新加载数据
        
        Args:
            use_cache: 是否使用缓存，None表示使用初始化时的设置
        """
        if use_cache is not None:
            self.use_cache = use_cache
        self.load_all_data()
