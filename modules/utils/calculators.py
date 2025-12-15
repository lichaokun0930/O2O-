"""
计算工具
"""
import numpy as np
import pandas as pd


def calculate_growth_rate(current, previous):
    """
    计算增长率
    
    Args:
        current: 当前值
        previous: 之前值
    
    Returns:
        增长率（小数形式）
    """
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return 0
    
    try:
        return (float(current) - float(previous)) / float(previous)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def calculate_ratio(numerator, denominator, default=0):
    """
    计算比率
    
    Args:
        numerator: 分子
        denominator: 分母
        default: 默认值（当分母为0时）
    
    Returns:
        比率（小数形式）
    """
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return default
    
    try:
        return float(numerator) / float(denominator)
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def calculate_cagr(start_value, end_value, periods):
    """
    计算复合年增长率（CAGR）
    
    Args:
        start_value: 起始值
        end_value: 结束值
        periods: 期数
    
    Returns:
        CAGR（小数形式）
    """
    if pd.isna(start_value) or pd.isna(end_value) or start_value == 0 or periods == 0:
        return 0
    
    try:
        return (float(end_value) / float(start_value)) ** (1 / float(periods)) - 1
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


def calculate_moving_average(data, window=7):
    """
    计算移动平均
    
    Args:
        data: 数据序列（Series或list）
        window: 窗口大小
    
    Returns:
        移动平均序列
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    return data.rolling(window=window, min_periods=1).mean()


def calculate_percentile(data, percentile=50):
    """
    计算百分位数
    
    Args:
        data: 数据序列
        percentile: 百分位（0-100）
    
    Returns:
        百分位数值
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    return data.quantile(percentile / 100)


def calculate_zscore(data):
    """
    计算Z分数（标准化）
    
    Args:
        data: 数据序列
    
    Returns:
        Z分数序列
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    mean = data.mean()
    std = data.std()
    
    if std == 0:
        return pd.Series([0] * len(data))
    
    return (data - mean) / std


def safe_divide(numerator, denominator, default=0):
    """
    安全除法（处理除零和NaN）
    
    Args:
        numerator: 分子（可以是数组）
        denominator: 分母（可以是数组）
        default: 默认值
    
    Returns:
        结果
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.divide(numerator, denominator)
        result = np.nan_to_num(result, nan=default, posinf=default, neginf=default)
    return result


def calculate_contribution_rate(part, total):
    """
    计算贡献率
    
    Args:
        part: 部分值
        total: 总值
    
    Returns:
        贡献率（小数形式）
    """
    return calculate_ratio(part, total, default=0)


def calculate_concentration(data, top_n=5):
    """
    计算集中度（前N项占比）
    
    Args:
        data: 数据序列
        top_n: 前N项
    
    Returns:
        集中度（小数形式）
    """
    if isinstance(data, list):
        data = pd.Series(data)
    
    total = data.sum()
    if total == 0:
        return 0
    
    top_sum = data.nlargest(top_n).sum()
    return top_sum / total
