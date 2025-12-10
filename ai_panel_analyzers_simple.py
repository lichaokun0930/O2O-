#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯净版看板专项AI分析器 - 只调用GLM，无复杂业务基因

功能:
- KPI看板分析器
- 分类看板分析器
- 价格带看板分析器
- 促销看板分析器
- 主AI汇总分析器
"""

import os
from typing import Dict, Any, List, Optional
import json
import numpy as np
import time


def convert_to_serializable(obj):
    """将numpy/pandas类型转换为JSON可序列化的Python原生类型"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


class BasePanelAnalyzer:
    """纯净版看板分析器基类"""
    
    def __init__(self, api_key: str = None):
        """
        初始化分析器
        
        Args:
            api_key: GLM API密钥
        """
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')
        self.client = None
        self.model_name = 'glm-4-plus'  # 使用glm-4-plus而不是glm-4.6
        self.ready = False
        
        if self.api_key:
            self._init_client()
    
    def _init_client(self):
        """初始化GLM客户端"""
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(
                api_key=self.api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4/"  # 使用标准API端点
            )
            self.ready = True
            print(f"✅ 纯净版Panel AI已就绪 ({self.model_name})")
        except Exception as e:
            print(f"❌ AI客户端初始化失败: {e}")
            self.ready = False
    
    def _generate_content(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """调用AI生成内容 - 带重试机制"""
        if not self.ready:
            return "❌ AI分析器未就绪，请检查API密钥配置"
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"🔄 第{attempt + 1}次调用GLM API...")
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                result = response.choices[0].message.content
                print(f"✅ GLM返回内容长度: {len(result) if result else 0}字符")
                
                if not result or len(result.strip()) == 0:
                    print("⚠️ GLM返回了空内容")
                    return "⚠️ AI返回了空内容，请重试"
                
                return result
                
            except Exception as e:
                error_str = str(e)
                print(f"❌ 第{attempt + 1}次尝试失败: {error_str}")
                
                # 检查是否是429错误（频率限制）
                if '429' in error_str or '1302' in error_str:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"⏳ API请求过于频繁，等待{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                
                if attempt == max_retries - 1:
                    return f"❌ 分析失败: {error_str}"
                
                time.sleep(retry_delay)
        
        return "❌ 分析失败: 超过最大重试次数"
    
    def analyze(self, data: Dict[str, Any]) -> str:
        """
        分析数据 - 子类需实现
        
        Args:
            data: 看板数据
            
        Returns:
            分析结果
        """
        raise NotImplementedError("子类需实现analyze方法")


class KPIAnalyzer(BasePanelAnalyzer):
    """KPI看板分析器 - 纯净版"""
    
    def analyze(self, kpi_data: Dict[str, Any]) -> str:
        """分析KPI数据"""
        if not self.ready:
            return "❌ AI分析器未就绪"
        
        # 构建简洁提示词
        prompt = f"""
你是O2O零售数据分析专家。请分析以下KPI数据，给出简洁、实用的建议。

# KPI数据
```
动销率: {kpi_data.get('动销率', 0):.2f}%
滞销占比: {kpi_data.get('滞销占比', 0):.2f}%
去重SKU数: {kpi_data.get('去重SKU数', 0)}个
售价销售额: ¥{kpi_data.get('售价销售额', 0):,.2f}
平均售价: ¥{kpi_data.get('平均售价', 0):.2f}
平均折扣: {kpi_data.get('平均折扣', 10):.2f}折
爆品数: {kpi_data.get('爆品数', 0)}个 ({kpi_data.get('爆品占比', 0):.2f}%)
```

# 分析要求
1. 健康度评估（50字内）：当前KPI处于什么水平？
2. 核心问题（1-2个）：最需要改进的指标是什么？为什么？
3. 优化建议（2-3条）：具体、可执行的改进措施

要求：简洁、实用、可执行。避免空话套话。
"""
        
        return self._generate_content(prompt, temperature=0.7, max_tokens=1500)


class CategoryAnalyzer(BasePanelAnalyzer):
    """分类看板分析器 - 纯净版"""
    
    def analyze(self, category_data: List[Dict[str, Any]]) -> str:
        """分析分类数据"""
        if not self.ready:
            return "❌ AI分析器未就绪"
        
        if not category_data:
            return "⚠️ 暂无分类数据可分析"
        
        # 构建分类数据表格
        table = "```\n"
        table += f"{'序号':<4} {'分类':<15} {'销售额':<12} {'动销率':<10} {'SKU数':<8}\n"
        table += "-" * 60 + "\n"
        
        for idx, cat in enumerate(category_data[:10], 1):
            name = cat.get('一级分类', '未知')[:12]
            revenue = cat.get('售价销售额', 0)
            moverate = cat.get('美团一级分类动销率(类内)', 0)
            sku_count = cat.get('美团一级分类去重SKU数(口径同动销率)', 0)
            
            table += f"{idx:<4} {name:<15} ¥{revenue:>10,.0f}  {moverate:>6.1f}%  {sku_count:>6}个\n"
        
        table += "```"
        
        # 构建提示词
        prompt = f"""
你是O2O零售数据分析专家。请分析以下分类销售数据。

# 分类销售TOP10
{table}

# 分析要求
1. 分类结构评估（50字内）：销售集中度如何？是否合理？
2. 核心发现（1-2个）：哪些分类表现好？哪些需要改进？
3. 优化建议（2-3条）：如何调整分类结构？

要求：简洁、实用、可执行。避免空话套话。
"""
        
        return self._generate_content(prompt, temperature=0.7, max_tokens=1500)


class PriceBandAnalyzer(BasePanelAnalyzer):
    """价格带看板分析器 - 纯净版"""
    
    def analyze(self, price_data: List[Dict[str, Any]]) -> str:
        """分析价格带数据"""
        if not self.ready:
            return "❌ AI分析器未就绪"
        
        if not price_data:
            return "⚠️ 暂无价格带数据可分析"
        
        # 构建价格带表格
        table = "```\n"
        table += f"{'价格带':<15} {'SKU数':<10} {'销售额':<15} {'占比':<10}\n"
        table += "-" * 55 + "\n"
        
        for band in price_data:
            price_range = band.get('price_band', '未知')
            sku_num = band.get('SKU数量', 0)
            revenue = band.get('销售额', 0)
            ratio = band.get('销售额占比', 0)
            
            table += f"{price_range:<15} {sku_num:>8}个  ¥{revenue:>11,.0f}  {ratio:>7.1f}%\n"
        
        table += "```"
        
        # 构建提示词
        prompt = f"""
你是O2O零售数据分析专家。请分析以下价格带分布数据。

# 价格带分布
{table}

# 分析要求
1. 结构评估（50字内）：价格带分布是否合理？
2. 核心发现（1-2个）：哪个价格带表现好？哪个需调整？
3. 优化建议（2-3条）：如何优化价格结构？

要求：简洁、实用、可执行。避免空话套话。
"""
        
        return self._generate_content(prompt, temperature=0.7, max_tokens=1500)


class PromoAnalyzer(BasePanelAnalyzer):
    """促销看板分析器 - 纯净版"""
    
    def analyze(self, promo_data: List[Dict[str, Any]]) -> str:
        """分析促销数据"""
        if not self.ready:
            return "❌ AI分析器未就绪"
        
        if not promo_data:
            return "⚠️ 暂无促销数据可分析"
        
        # 构建促销表格
        table = "```\n"
        table += f"{'序号':<4} {'分类':<15} {'促销强度':<12} {'折扣力度':<10}\n"
        table += "-" * 45 + "\n"
        
        for idx, item in enumerate(promo_data[:10], 1):
            name = item.get('分类', '未知')[:12]
            intensity = item.get('促销强度', 0)
            discount = item.get('折扣力度', 10)
            
            table += f"{idx:<4} {name:<15} {intensity:>8.1f}%   {discount:>6.1f}折\n"
        
        table += "```"
        
        # 构建提示词
        prompt = f"""
你是O2O零售数据分析专家。请分析以下促销数据。

# 促销强度TOP10
{table}

# 分析要求
1. 促销力度评估（50字内）：整体促销力度如何？
2. 核心发现（1-2个）：哪些分类促销过度？哪些不足？
3. 优化建议（2-3条）：如何调整促销策略？

要求：简洁、实用、可执行。避免空话套话。
"""
        
        return self._generate_content(prompt, temperature=0.7, max_tokens=1500)


class MasterAnalyzer(BasePanelAnalyzer):
    """主AI分析器 - 纯净版"""
    
    def analyze(self, dashboard_data: Dict[str, Any]) -> str:
        """综合分析所有数据"""
        if not self.ready:
            return "❌ AI分析器未就绪"
        
        # 提取数据
        kpi_data = dashboard_data.get('kpi', {})
        category_data = dashboard_data.get('category', [])
        
        # 构建综合提示词
        prompt = f"""
你是O2O零售数据分析专家。请基于以下门店数据，给出综合性的经营分析和建议。

# 核心KPI
```
动销率: {kpi_data.get('动销率', 0):.2f}%
滞销占比: {kpi_data.get('滞销占比', 0):.2f}%
去重SKU数: {kpi_data.get('去重SKU数', 0)}个
售价销售额: ¥{kpi_data.get('售价销售额', 0):,.2f}
平均折扣: {kpi_data.get('平均折扣', 10):.2f}折
```

# 分类TOP5
"""
        
        if category_data:
            prompt += "```\n"
            for idx, cat in enumerate(category_data[:5], 1):
                name = cat.get('一级分类', '未知')[:12]
                revenue = cat.get('售价销售额', 0)
                moverate = cat.get('美团一级分类动销率(类内)', 0)
                prompt += f"{idx}. {name:<15} ¥{revenue:>10,.0f}  动销率{moverate:>6.1f}%\n"
            prompt += "```\n"
        else:
            prompt += "⚠️ 暂无分类数据\n"
        
        prompt += """

# 分析要求
1. 整体健康度评估（100字内）：当前门店经营状况如何？
2. 核心问题识别（2-3个）：最需要关注的问题是什么？
3. 优化建议（3-5条）：具体、可执行的改进措施，按优先级排序
4. 快速收益建议（1-2条）：能立即执行且见效快的措施

要求：
- 避免空话套话，所有建议必须具体、可执行
- 引用具体数据支撑观点
- 量化影响和收益
- 如果某项数据为0或缺失，说明"暂无数据"即可

现在请开始你的综合分析！
"""
        
        return self._generate_content(prompt, temperature=0.7, max_tokens=3000)


# 创建全局分析器实例
_kpi_analyzer = None
_category_analyzer = None
_price_analyzer = None
_promo_analyzer = None
_master_analyzer = None


def get_kpi_analyzer(api_key: str = None) -> Optional[KPIAnalyzer]:
    """获取KPI分析器"""
    global _kpi_analyzer
    if _kpi_analyzer is None:
        _kpi_analyzer = KPIAnalyzer(api_key=api_key)
    return _kpi_analyzer if _kpi_analyzer.ready else None


def get_category_analyzer(api_key: str = None) -> Optional[CategoryAnalyzer]:
    """获取分类分析器"""
    global _category_analyzer
    if _category_analyzer is None:
        _category_analyzer = CategoryAnalyzer(api_key=api_key)
    return _category_analyzer if _category_analyzer.ready else None


def get_price_analyzer(api_key: str = None) -> Optional[PriceBandAnalyzer]:
    """获取价格带分析器"""
    global _price_analyzer
    if _price_analyzer is None:
        _price_analyzer = PriceBandAnalyzer(api_key=api_key)
    return _price_analyzer if _price_analyzer.ready else None


def get_promo_analyzer(api_key: str = None) -> Optional[PromoAnalyzer]:
    """获取促销分析器"""
    global _promo_analyzer
    if _promo_analyzer is None:
        _promo_analyzer = PromoAnalyzer(api_key=api_key)
    return _promo_analyzer if _promo_analyzer.ready else None


def get_master_analyzer(api_key: str = None) -> Optional[MasterAnalyzer]:
    """获取主分析器"""
    global _master_analyzer
    if _master_analyzer is None:
        _master_analyzer = MasterAnalyzer(api_key=api_key)
    return _master_analyzer if _master_analyzer.ready else None


if __name__ == '__main__':
    print("=" * 60)
    print("纯净版Panel AI分析器测试")
    print("=" * 60)
    
    # 测试KPI分析器
    kpi_analyzer = get_kpi_analyzer()
    if kpi_analyzer:
        print("\n✅ KPI分析器初始化成功")
    else:
        print("\n❌ KPI分析器初始化失败")
