#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析器模块 - 纯GLM-4.6版本(无向量检索)

功能:
- 智能分析门店数据
- 生成业务洞察
- 提供策略建议

特点:
- 无向量检索依赖
- 启动速度最快
- 使用完整业务知识库
"""

import os
from typing import Optional, Dict, Any
import json


class AIAnalyzerPure:
    """纯GLM-4.6 AI分析器(无向量检索)"""
    
    def __init__(self, api_key: str = None, model_type: str = 'glm'):
        """
        初始化AI分析器
        
        Args:
            api_key: API密钥
            model_type: 模型类型 ('glm' 或 'openai')
        """
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')
        self.model_type = model_type
        self.client = None
        self.model_name = None
        
        if self.api_key:
            self._init_client()
    
    def _init_client(self):
        """初始化API客户端"""
        try:
            if self.model_type == 'glm':
                from zhipuai import ZhipuAI
                self.client = ZhipuAI(api_key=self.api_key)
                # 使用GLM-4.6编码专用版
                self.model_name = 'glm-4.6'
                print(f"✅ 已配置GLM-4.6 (编码专用API)")
            else:
                # OpenAI兼容模式
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                self.model_name = 'gpt-4'
                print(f"✅ 已配置OpenAI")
        except Exception as e:
            print(f"⚠️ API客户端初始化失败: {e}")
            self.client = None
    
    def is_ready(self) -> bool:
        """检查分析器是否就绪"""
        return self.client is not None
    
    def analyze_store_health(
        self,
        kpi_data: Dict[str, Any],
        category_data: list,
        meta_data: Dict[str, Any]
    ) -> str:
        """
        分析门店经营健康度
        
        Args:
            kpi_data: 核心KPI数据
            category_data: 分类数据
            meta_data: 元数据(门店名称等)
        
        Returns:
            分析结果文本
        """
        if not self.is_ready():
            return "AI分析器未就绪,请检查API密钥配置"
        
        try:
            # 构建分析提示词(使用完整业务知识)
            prompt = self._build_analysis_prompt(kpi_data, category_data, meta_data)
            # 调用API
            if self.model_type == 'glm':
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位资深的零售数据分析专家,擅长O2O门店经营分析。请基于提供的数据和业务知识,给出专业的分析和建议。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content
            else:
                # OpenAI模式
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "你是一位资深的零售数据分析专家。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=2000
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"AI分析过程出错: {str(e)}"
    
    def _build_analysis_prompt(
        self,
        kpi_data: Dict,
        category_data: list,
        meta_data: Dict
    ) -> str:
        """
        构建分析提示词(纯GLM版本,使用完整业务知识)
        
        Args:
            kpi_data: KPI数据
            category_data: 分类数据
            meta_data: 元数据
        
        Returns:
            完整提示词
        """
        # 加载完整业务知识库
        from ai_business_context import get_business_context
        business_context = get_business_context()
        
        # 格式化KPI数据
        kpi_text = "\n".join([f"- {k}: {v}" for k, v in kpi_data.items()])
        
        # 格式化分类数据(取前5个主要分类)
        category_text = ""
        if category_data:
            top_categories = sorted(
                category_data[:5],
                key=lambda x: x.get('销售额', 0),
                reverse=True
            )
            category_text = "\n".join([
                f"- {cat.get('一级分类', 'N/A')}: "
                f"销售额 {cat.get('销售额', 0)}, "
                f"动销率 {cat.get('动销率', 'N/A')}%, "
                f"滞销占比 {cat.get('滞销占比', 'N/A')}%"
                for cat in top_categories
            ])
        

        # 构建完整提示词
        business_rule = (
            "【❗数据分析铁律 - 必须严格遵守】\n\n"
            "1️⃣ **先审查数据有效性，再开始分析**：\n"
            "   - 如果动销率=0%、销售额=0、订单量=0，首先判断：这是筛选条件导致的'无数据'，还是真实的'零销售'？\n"
            "   - 如果多个核心指标同时为0，大概率是筛选条件(如选了某个分类)导致数据为空，而非门店休克。\n"
            "   - ⚠️ 禁止基于0值臆测'门店休克'、'完全停滞'等结论！\n\n"
            "2️⃣ **只分析有实际业务意义的数据**：\n"
            "   - 只分析外卖渠道，不区分渠道字段。\n"
            "   - 只分析当前看板/底表实际有值的字段。\n"
            "   - 如果某字段为0或空，明确说明'该指标暂无数据，无法分析'，而非臆测业务问题。\n\n"
            "3️⃣ **逐项数据结论输出格式**（核心要求）：\n"
            "   对每个有值的核心指标，必须按以下格式输出：\n"
            "   ```\n"
            "   【指标名称】: 当前值XXX\n"
            "   - 数据解释: 该值的业务含义\n"
            "   - 行业对标: 对比健康基准(优秀/合格/预警/危险)\n"
            "   - 具体结论: 量化影响(如'损失¥X'、'占用¥X资金'、'距目标差Xpp')\n"
            "   - 可执行建议: 1-2条具体动作\n"
            "   ```\n\n"
            "4️⃣ **禁止空话和套话**：\n"
            "   - ❌ 错误示例: '建议优化商品结构'、'可能存在问题'\n"
            "   - ✅ 正确示例: '动销率65%，距优秀线75%还差10pp，建议下架120个零销量SKU，释放约¥6000库存资金'\n\n"
            "5️⃣ **缺失数据处理规则**：\n"
            "   - 如果KPI数据为空或全0，输出：'当前筛选条件下暂无KPI数据，请调整筛选条件或检查数据源'\n"
            "   - 如果分类数据为空，输出：'当前筛选条件下暂无分类数据'\n"
            "   - 不要基于缺失数据编造分析内容。\n"
        )
        prompt = f"""
# 业务知识库
{business_context[:3000]}

{business_rule}

# 门店数据分析任务

## 门店信息
- 门店名称: {meta_data.get('门店', 'N/A')}
- 数据日期: {meta_data.get('数据日期', 'N/A')}
- 总SKU数: {meta_data.get('总SKU数', 'N/A')}

## 核心KPI指标
{kpi_text}

## 主要分类表现
{category_text}

## 分析要求
请基于以上业务知识和门店数据,从以下维度进行分析:

1. **经营健康度诊断**
    - 评估各项KPI指标的健康状况，必须逐项引用并解释每个有值的核心指标（数据+业务解释+对标+建议）。
    - 识别核心问题和风险点

2. **问题根因分析**
    - 深入分析问题背后的原因
    - 结合分类数据找出薄弱环节

3. **优化策略建议**
    - 提供具体可执行的改进措施
    - 按优先级排序,给出实施路径

4. **预期效果**
    - 预估优化后的KPI改善幅度
    - 给出合理的时间预期

请用专业、清晰、结构化的方式呈现分析结果。
"""
        return prompt
        
        if analyzer.is_ready():
            print(f"✅ AI分析器已就绪 (模型: {analyzer.model_name})")
            return analyzer
        else:
            print("⚠️ AI分析器未就绪,请检查API密钥")
            return None
    
    except Exception as e:
        print(f"❌ AI分析器初始化失败: {e}")
        return None


# 导出
__all__ = ['AIAnalyzerPure', 'get_ai_analyzer_pure']
