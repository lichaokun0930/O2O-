"""
日志系统 - P0+P2优化
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import get_config


def setup_logger(name='dashboard', level=None):
    """
    设置日志系统
    
    Args:
        name: 日志器名称
        level: 日志级别，None表示使用配置文件中的级别
    
    Returns:
        logger对象
    """
    log_config = get_config('log')
    
    # 创建日志目录
    log_dir = Path(log_config['log_dir'])
    log_dir.mkdir(exist_ok=True)
    
    # 创建logger
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = level or log_config['level']
    logger.setLevel(getattr(logging, log_level))
    
    # 文件处理器（带轮转）
    log_file = log_dir / log_config['log_file']
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=log_config['max_bytes'],
        backupCount=log_config['backup_count'],
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter(log_config['format'])
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# 创建默认logger
logger = setup_logger()
