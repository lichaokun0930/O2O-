#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯净版AI分析器 - 只调用GLM，无复杂业务基因

功能:
- 简洁的GLM-4.6调用
- 基础数据分析
- 无向量检索、无业务基因库
"""

import os
from typing import Optional, Dict, Any


class AIAnalyzer:
    """纯净版AI分析器 - 只用GLM-4.6"""
    
    def __init__(self, api_key: str = None):
        """
        初始化AI分析器
        
        Args:
            api_key: GLM API密钥
        """
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')
        self.client = None
        self.model_name = 'glm-4-plus'  # 使用glm-4-plus
        self.ready = False
        
        if self.api_key:
            self._init_glm()
        else:
            print("⚠️ 未提供API密钥，AI分析器未初始化")
    
    def _init_glm(self):
        """初始化GLM客户端"""
        try:
            from zhipuai import ZhipuAI
            
            self.client = ZhipuAI(
                api_key=self.api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4"  # 使用标准API端点
            )

            self.model_name = 'glm-4.6'  # 使用glm-4.6
            self.ready = True
            
            print(f"✅ 纯净版AI分析器已就绪 ({self.model_name})")
            
        except ImportError:
            print("❌ 未安装zhipuai库，请运行: pip install zhipuai")
            raise
        except Exception as e:
            print(f"❌ GLM初始化失败: {e}")
            raise
    
    def is_ready(self) -> bool:
        """检查AI分析器是否就绪"""
        return self.ready and self.client is not None
    
    def _generate_content(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """
        生成内容 - 带重试机制
        
        Args:
            prompt: 提示词
            temperature: 温度参数 (0-1)
            max_tokens: 最大输出长度
            
        Returns:
            生成的文本内容
        """
        if not self.is_ready():
            return "❌ AI分析器未就绪，请检查API密钥配置"
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                import time
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return response.choices[0].message.content
                
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
                
                # 其他错误或最后一次重试失败
                if attempt == max_retries - 1:
                    return f"❌ 内容生成失败: {error_str}"
                
                time.sleep(retry_delay)
        
        return "❌ 内容生成失败: 超过最大重试次数"
    
    def analyze_dashboard_data(self, dashboard_data: Dict[str, Any]) -> str:
        """
        分析Dashboard数据 - 纯净版，无复杂业务基因
        
        Args:
            dashboard_data: Dashboard的所有数据
            
        Returns:
            分析结果
        """
        if not self.is_ready():
            return "❌ AI分析器未就绪"
        
        # 构建简洁的分析提示词
        prompt = self._build_simple_prompt(dashboard_data)
        
        # 调用AI生成分析
        return self._generate_content(prompt, temperature=0.7, max_tokens=8000)
    
    def _build_simple_prompt(self, dashboard_data: Dict[str, Any]) -> str:
        """构建简洁的分析提示词 - 无复杂业务基因"""
        
        # 提取关键数据
        kpi_data = dashboard_data.get('kpi', {})
        category_data = dashboard_data.get('category', [])
        price_data = dashboard_data.get('price', [])
        promo_data = dashboard_data.get('promo', [])
        meta_data = dashboard_data.get('meta', {})
        
        # 构建简洁提示词
        prompt = f"""
你是一位O2O零售数据分析专家。请基于以下门店数据，给出专业、简洁、可执行的分析建议。

# 当前筛选条件
{meta_data.get('筛选分类', '全部分类')}

# 核心经营数据

## 一、关键指标
```
动销率: {kpi_data.get('动销率', 0):.2f}%
滞销占比: {kpi_data.get('滞销占比', 0):.2f}%
去重SKU数: {kpi_data.get('去重SKU数', 0)}个
售价销售额: ¥{kpi_data.get('售价销售额', 0):,.2f}
平均售价: ¥{kpi_data.get('平均售价', 0):.2f}
平均折扣: {kpi_data.get('平均折扣', 10):.2f}折
爆品数: {kpi_data.get('爆品数', 0)}个
爆品占比: {kpi_data.get('爆品占比', 0):.2f}%
```

## 二、分类销售TOP10
"""
        
        # 添加分类数据
        if category_data:
            prompt += "\n```\n"
            prompt += f"{'序号':<4} {'分类':<15} {'销售额':<12} {'动销率':<10} {'SKU数':<8}\n"
            prompt += "-" * 60 + "\n"
            
            for idx, cat in enumerate(category_data[:10], 1):
                name = cat.get('一级分类', '未知')[:12]
                revenue = cat.get('售价销售额', 0)
                moverate = cat.get('美团一级分类动销率(类内)', 0)
                sku_count = cat.get('美团一级分类去重SKU数(口径同动销率)', 0)
                
                prompt += f"{idx:<4} {name:<15} ¥{revenue:>10,.0f}  {moverate:>6.1f}%  {sku_count:>6}个\n"
            
            prompt += "```\n"
        else:
            prompt += "⚠️ 暂无分类数据\n"
        
        # 添加价格带数据
        if price_data:
            prompt += "\n## 三、价格带分布\n\n```\n"
            prompt += f"{'价格带':<15} {'SKU数':<10} {'销售额':<15} {'占比':<10}\n"
            prompt += "-" * 55 + "\n"
            
            for band in price_data:
                price_range = band.get('price_band', '未知')
                sku_num = band.get('SKU数量', 0)
                revenue = band.get('销售额', 0)
                ratio = band.get('销售额占比', 0)
                
                prompt += f"{price_range:<15} {sku_num:>8}个  ¥{revenue:>11,.0f}  {ratio:>7.1f}%\n"
            
            prompt += "```\n"
        
        # 分析要求
        prompt += """

# 分析要求

请基于以上数据，提供**简洁、实用、可执行**的分析：

## 1. 整体健康度评估（100字内）
- 当前门店经营状况如何？
- 最突出的问题是什么？

## 2. 核心问题识别（列出2-3个）
每个问题包含：
- 问题描述（一句话）
- 数据依据（引用具体数字）
- 影响程度（量化）

## 3. 优化建议（列出3-5条）
每条建议包含：
- 具体措施
- 预期效果
- 优先级（P0紧急/P1重要/P2常规）

## 4. 快速收益建议（1-2条）
- 能立即执行且见效快的措施

# 注意事项
1. 避免空话套话，所有建议必须具体、可执行
2. 引用具体数据支撑观点
3. 量化影响和收益
4. 如果某项数据为0或缺失，说明"暂无数据"即可，不要臆测

现在请开始你的分析！
"""
        
        return prompt


def get_ai_analyzer(api_key: str = None) -> Optional[AIAnalyzer]:
    """
    获取纯净版AI分析器实例
    
    Args:
        api_key: API密钥
        
    Returns:
        AIAnalyzer实例或None
    """
    try:
        analyzer = AIAnalyzer(api_key=api_key)
        return analyzer if analyzer.is_ready() else None
    except Exception as e:
        print(f"❌ AI分析器创建失败: {e}")
        return None


# 兼容性函数 - 保持与旧版本接口一致
def get_business_context():
    """返回空字符串，保持兼容性"""
    return ""


def get_kpi_definitions():
    """返回空字典，保持兼容性"""
    return {}


if __name__ == '__main__':
    print("=" * 60)
    print("纯净版AI分析器测试")
    print("=" * 60)
    
    analyzer = get_ai_analyzer()
    
    if analyzer and analyzer.is_ready():
        print("\n✅ 纯净版AI分析器初始化成功")
        
        test_prompt = "你好，请介绍一下你自己"
        print(f"\n测试提示词: {test_prompt}")
        
        result = analyzer._generate_content(test_prompt)
        print(f"\nAI响应:\n{result}")
    else:
        print("\n❌ AI分析器初始化失败")
        print("请设置ZHIPU_API_KEY环境变量")
