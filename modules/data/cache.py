"""
数据缓存管理器 - P0+P2优化
"""
import pickle
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"缓存目录: {self.cache_dir.absolute()}")
    
    def _get_file_hash(self, file_path):
        """计算文件MD5哈希"""
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
        """
        获取缓存数据
        
        Args:
            file_path: 原始文件路径
        
        Returns:
            缓存的数据，如果不存在返回None
        """
        try:
            cache_path = self._get_cache_path(file_path)
            if cache_path.exists():
                logger.info(f"✅ 使用缓存数据: {cache_path.name}")
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            return None
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
            return None
    
    def set(self, file_path, data):
        """
        保存数据到缓存
        
        Args:
            file_path: 原始文件路径
            data: 要缓存的数据
        """
        try:
            cache_path = self._get_cache_path(file_path)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            size_mb = cache_path.stat().st_size / (1024 * 1024)
            logger.info(f"💾 缓存已保存: {cache_path.name} ({size_mb:.2f}MB)")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def clear(self):
        """清除所有缓存文件"""
        count = 0
        for cache_file in self.cache_dir.glob('*.cache'):
            cache_file.unlink()
            count += 1
        logger.info(f"🗑️ 已清除 {count} 个缓存文件")
        return count
    
    def get_cache_size(self):
        """获取缓存总大小（MB）"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob('*.cache'))
        return total_size / (1024 * 1024)
    
    def get_cache_count(self):
        """获取缓存文件数量"""
        return len(list(self.cache_dir.glob('*.cache')))
