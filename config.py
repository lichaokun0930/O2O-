"""
Dashboard配置文件 - P2优化：配置外部化
集中管理所有配置项，便于部署和维护
"""
from pathlib import Path

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
DEFAULT_REPORT_PATH = REPORTS_DIR / "示例门店_分析报告.xlsx"

# ==================== 应用配置 ====================
APP_CONFIG = {
    'title': 'O2O门店数据分析看板 v2.1 (P2优化版)',
    'host': '0.0.0.0',
    'port': 8050,
    'debug': False,
    'dev_tools_hot_reload': True,
}

# ==================== 缓存配置 ====================
CACHE_CONFIG = {
    'enabled': True,
    'cache_dir': str(CACHE_DIR),
    'max_size_mb': 100,  # 最大缓存大小
    'ttl_hours': 24,  # 缓存有效期（小时）
}

# ==================== 日志配置 ====================
LOG_CONFIG = {
    'log_dir': str(LOGS_DIR),
    'log_file': 'dashboard.log',
    'level': 'INFO',
    'max_bytes': 10 * 1024 * 1024,  # 10MB
    'backup_count': 5,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
}

# ==================== 数据加载配置 ====================
DATA_CONFIG = {
    'use_cache': True,
    'sheet_names': {
        'kpi': ['核心指标对比', 'KPI对比', '核心指标'],
        'role_analysis': ['商品角色分析', '角色分析'],
        'price_analysis': ['价格带分析', '价格分析'],
        'category_l1': ['美团一级分类详细指标', '一级分类详细指标', '一级分类'],
        'sku_details': ['详细SKU报告(去重后)', 'SKU报告', '详细SKU报告']
    },
}

# ==================== 图表配置 ====================
CHART_CONFIG = {
    'default_height': 600,
    'default_template': 'plotly_white',
    'color_schemes': {
        'primary': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
        'sequential': ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6'],
        'diverging': ['#d73027', '#fc8d59', '#fee090', '#e0f3f8', '#91bfdb'],
    },
    'font_family': 'Arial, sans-serif',
    'title_font_size': 20,
    'axis_font_size': 14,
}

# ==================== KPI指标配置 ====================
KPI_CONFIG = {
    'metrics': [
        {
            'key': '总SKU数(含规格)',
            'title': '总SKU数(含规格)',
            'icon': '📦',
            'color': 'primary',
            'format': 'number',
            'definition': '所有商品规格的总数量，包括多规格商品的各个子SKU。用于衡量商品丰富度。'
        },
        {
            'key': '总SKU数(去重后)',
            'title': '总SKU数(去重后)',
            'icon': '📋',
            'color': 'info',
            'format': 'number',
            'definition': '去除多规格商品重复统计后的总SKU数。反映门店实际商品种类数量。'
        },
        {
            'key': '动销SKU数',
            'title': '动销SKU数',
            'icon': '✅',
            'color': 'success',
            'format': 'number',
            'definition': '有销售记录的商品数量。动销率 = 动销SKU数 / 总SKU数(去重后)。'
        },
        {
            'key': '多规格SKU总数',
            'title': '多规格SKU总数',
            'icon': '🧩',
            'color': 'secondary',
            'format': 'number',
            'definition': '同一商品拥有多个规格选项的SKU数量。例如：可乐(300ml/500ml/1L)算3个多规格SKU。'
        },
        {
            'key': '滞销SKU数',
            'title': '滞销SKU数',
            'icon': '⚠️',
            'color': 'danger',
            'format': 'number',
            'definition': '无销售记录的商品数量。滞销率 = 滞销SKU数 / 总SKU数(去重后)。'
        },
        {
            'key': '总销售额(去重后)',
            'title': '总销售额(去重后)',
            'icon': '💰',
            'color': 'warning',
            'format': 'currency',
            'definition': '门店当期总销售收入，已去除多规格商品的重复计算。用于评估门店整体营收能力。'
        },
        {
            'key': '动销率',
            'title': '动销率',
            'icon': '📈',
            'color': 'success',
            'format': 'percent',
            'definition': '动销SKU数 / 总SKU数(去重后)。反映商品周转效率，建议保持在70%以上。'
        },
        {
            'key': '唯一多规格商品数',
            'title': '唯一多规格商品数',
            'icon': '🔀',
            'color': 'dark',
            'format': 'number',
            'definition': '去重后的多规格商品种类数。例如：可乐有3个规格，但只算1个唯一商品。'
        },
    ],
    'thresholds': {
        'active_rate_good': 0.7,  # 动销率良好阈值
        'active_rate_warning': 0.5,  # 动销率警告阈值
        'multispec_ratio_high': 0.3,  # 高多规格占比
        'multispec_ratio_low': 0.15,  # 低多规格占比
    }
}

# ==================== 多规格识别配置 ====================
MULTISPEC_CONFIG = {
    'high_threshold': 0.5,  # 高多规格品类阈值 (>50%)
    'low_threshold': 0.15,  # 低多规格品类阈值 (<15%)
    'mid_range': (0.2, 0.4),  # 中等多规格品类范围 (20-40%)
    'max_display_categories': 3,  # 最多显示的分类数量
}

# ==================== 性能配置 ====================
PERFORMANCE_CONFIG = {
    'max_workers': 4,  # 并发处理的最大工作线程数
    'chunk_size': 1000,  # 数据分块处理大小
    'enable_profiling': False,  # 是否启用性能分析
}

# ==================== UI配置 ====================
UI_CONFIG = {
    'theme': 'light',
    'sidebar_width': 250,
    'chart_section_padding': '20px',
    'card_border_radius': '8px',
    'animation_duration': 300,  # 毫秒
}

# ==================== 导出配置 ====================
EXPORT_CONFIG = {
    'formats': ['xlsx', 'csv', 'pdf'],
    'default_format': 'xlsx',
    'include_charts': True,
    'max_rows': 10000,
}

# ==================== ECharts工具栏配置 ====================
ECHARTS_TOOLBOX = {
    'show': True,
    'right': 15,
    'top': 5,
    'feature': {
        'saveAsImage': {
            'type': 'png',
            'pixelRatio': 2,  # 2倍分辨率，高清下载
            'title': '下载图片',
            'backgroundColor': '#fff'
        }
    },
    'iconStyle': {
        'borderColor': '#999'
    },
    'emphasis': {
        'iconStyle': {
            'borderColor': '#3498db'
        }
    }
}


def get_echarts_toolbox(chart_name: str = None) -> dict:
    """获取ECharts工具栏配置
    
    Args:
        chart_name: 图表名称，用于下载文件命名
        
    Returns:
        toolbox配置字典
    """
    toolbox = ECHARTS_TOOLBOX.copy()
    toolbox['feature'] = {'saveAsImage': ECHARTS_TOOLBOX['feature']['saveAsImage'].copy()}
    if chart_name:
        toolbox['feature']['saveAsImage']['name'] = chart_name
    return toolbox

# ==================== 开发配置 ====================
DEV_CONFIG = {
    'show_debug_info': False,
    'enable_hot_reload': True,
    'log_sql_queries': False,
}


def get_config(section=None):
    """
    获取配置
    
    Args:
        section: 配置节名称，如 'app', 'cache', 'log' 等
                如果为None，返回所有配置
    
    Returns:
        配置字典
    """
    all_configs = {
        'app': APP_CONFIG,
        'cache': CACHE_CONFIG,
        'log': LOG_CONFIG,
        'data': DATA_CONFIG,
        'chart': CHART_CONFIG,
        'kpi': KPI_CONFIG,
        'multispec': MULTISPEC_CONFIG,
        'performance': PERFORMANCE_CONFIG,
        'ui': UI_CONFIG,
        'export': EXPORT_CONFIG,
        'dev': DEV_CONFIG,
    }
    
    if section is None:
        return all_configs
    
    return all_configs.get(section, {})


def update_config(section, key, value):
    """
    更新配置项
    
    Args:
        section: 配置节名称
        key: 配置键
        value: 新值
    """
    config = get_config(section)
    if config and key in config:
        config[key] = value
        return True
    return False


# 确保必要的目录存在
def ensure_directories():
    """确保所有必要的目录存在"""
    for directory in [CACHE_DIR, LOGS_DIR, REPORTS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# 初始化时创建目录
ensure_directories()
