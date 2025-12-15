"""
数据格式化工具
"""
import pandas as pd


def format_number(value, decimals=0):
    """
    格式化数字
    
    Args:
        value: 数值
        decimals: 小数位数
    
    Returns:
        格式化后的字符串
    """
    if pd.isna(value):
        return "0"
    
    try:
        if decimals == 0:
            return f"{int(value):,}"
        else:
            return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_currency(value, symbol='¥', decimals=2):
    """
    格式化货币
    
    Args:
        value: 数值
        symbol: 货币符号
        decimals: 小数位数
    
    Returns:
        格式化后的字符串
    """
    if pd.isna(value):
        return f"{symbol}0"
    
    try:
        return f"{symbol}{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return f"{symbol}{value}"


def format_percent(value, decimals=1, multiply_100=False):
    """
    格式化百分比
    
    Args:
        value: 数值
        decimals: 小数位数
        multiply_100: 是否需要乘以100（如果value是0-1之间的小数）
    
    Returns:
        格式化后的字符串
    """
    if pd.isna(value):
        return "0%"
    
    try:
        if multiply_100:
            value = float(value) * 100
        return f"{float(value):.{decimals}f}%"
    except (ValueError, TypeError):
        return f"{value}%"


def format_large_number(value):
    """
    格式化大数字（自动转换为万、亿）
    
    Args:
        value: 数值
    
    Returns:
        格式化后的字符串
    """
    if pd.isna(value):
        return "0"
    
    try:
        value = float(value)
        if value >= 100000000:  # 亿
            return f"{value/100000000:.2f}亿"
        elif value >= 10000:  # 万
            return f"{value/10000:.2f}万"
        else:
            return f"{value:.0f}"
    except (ValueError, TypeError):
        return str(value)


def format_duration(seconds):
    """
    格式化时长
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化后的字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def truncate_text(text, max_length=50, suffix='...'):
    """
    截断文本
    
    Args:
        text: 文本
        max_length: 最大长度
        suffix: 后缀
    
    Returns:
        截断后的文本
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
