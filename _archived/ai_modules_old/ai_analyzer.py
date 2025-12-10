#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI分析器模块 - 支持GLM-4.6大模型

功能:
- 智能分析门店数据
- 生成业务洞察
- 提供策略建议
"""

import os
from typing import Optional, Dict, Any
import json

# Phase 1: 向量检索增强
# 启用方式:
#   方式1: 修改下方 VECTOR_RETRIEVAL_ENABLED = True
#   方式2: 设置环境变量 ENABLE_VECTOR_RETRIEVAL=1
#   方式3: 运行 快速切换向量检索.py
# 纯GLM模式: 设置环境变量 USE_PURE_GLM=1 (完全不加载向量检索依赖)

USE_PURE_GLM = os.getenv('USE_PURE_GLM', '0') == '1'

if USE_PURE_GLM:
    # 纯GLM模式,不加载任何向量检索依赖
    VECTOR_RETRIEVAL_ENABLED = False
    print("⚡ 纯GLM-4.6模式(无向量检索依赖)")
else:
    # 标准模式,支持向量检索切换
    VECTOR_RETRIEVAL_ENABLED = os.getenv('ENABLE_VECTOR_RETRIEVAL', '0') == '1' or False
    if VECTOR_RETRIEVAL_ENABLED:
        try:
            from ai_knowledge_retriever import get_knowledge_retriever
            print("🚀 向量检索增强模式已启用")
        except ImportError as e:
            VECTOR_RETRIEVAL_ENABLED = False
            print(f"⚠️ 向量检索模块加载失败,已降级到基础模式: {e}")


class AIAnalyzer:
    """AI分析器 - 支持GLM-4.6"""
    
    def __init__(self, api_key: str = None, model_type: str = 'glm'):
        """
        初始化AI分析器
        
        Args:
            api_key: API密钥
            model_type: 模型类型 ('glm', 'qwen', 'gemini')
        """
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')
        self.model_type = model_type.lower()
        self.client = None
        self.model_name = None
        self.ready = False
        
        # Phase 1: 初始化向量检索器
        self.knowledge_retriever = None
        if VECTOR_RETRIEVAL_ENABLED:
            try:
                self.knowledge_retriever = get_knowledge_retriever()
                print("✅ 向量检索器已加载")
            except Exception as e:
                print(f"⚠️ 向量检索器加载失败: {e}")
        
        # 尝试初始化模型
        if self.api_key:
            self._init_model()
        else:
            print("⚠️ 未提供API密钥,AI分析器未初始化")
    
    def _init_model(self):
        """初始化AI模型"""
        try:
            if self.model_type == 'glm':
                self._init_glm()
            else:
                print(f"⚠️ 不支持的模型类型: {self.model_type}")
                return
            
            self.ready = True
            print(f"✅ AI分析器已就绪 (模型: {self.model_name})")
            
        except Exception as e:
            print(f"❌ AI模型初始化失败: {e}")
            self.ready = False
    
    def _init_glm(self):
        """初始化智谱GLM-4.6"""
        try:
            from zhipuai import ZhipuAI
            
            # 创建客户端 - 使用编码专用API端点
            # 原配置: base_url = "https://open.bigmodel.cn/api/paas/v4/"
            # 新配置: 编码专用地址（强烈推荐）
            self.client = ZhipuAI(
                api_key=self.api_key,
                base_url="https://open.bigmodel.cn/api/coding/paas/v4"
            )
            
            # 设置模型版本 - 明确指定为GLM-4.6
            # 原配置: model = "glm-4-plus"
            # 新配置: 直接使用GLM-4.6
            self.model_name = 'glm-4.6'
            self.use_zai = False
            
            print(f"✅ 已配置GLM-4.6 (编码专用API)")
            
        except ImportError:
            print("❌ 未安装zhipuai库,请运行: pip install zhipuai")
            raise
        except Exception as e:
            print(f"❌ GLM初始化失败: {e}")
            raise
    
    def is_ready(self) -> bool:
        """检查AI分析器是否就绪"""
        return self.ready and self.client is not None
    
    def _generate_content(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4096) -> str:
        """
        生成内容
        
        Args:
            prompt: 提示词
            temperature: 温度参数 (0-1, 越高越有创造性)
            max_tokens: 最大输出长度
            
        Returns:
            生成的文本内容
        """
        if not self.is_ready():
            return "❌ AI分析器未就绪,请检查API密钥配置"
        
        try:
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
            return f"❌ 内容生成失败: {str(e)}"
    
    def analyze_dashboard_data(self, dashboard_data: Dict[str, Any], business_context: str = "") -> str:
        """
        分析Dashboard数据
        
        Args:
            dashboard_data: Dashboard的所有数据
            business_context: 业务上下文
            
        Returns:
            分析结果
        """
        if not self.is_ready():
            return "❌ AI分析器未就绪"
        
        # 构建提示词
        prompt = self._build_analysis_prompt(dashboard_data, business_context)
        
        # 调用AI生成分析 - 增加token上限到8000,提高温度到0.8增强创造性
        return self._generate_content(prompt, temperature=0.8, max_tokens=8000)
    
    def _build_analysis_prompt(self, dashboard_data: Dict[str, Any], business_context: str) -> str:
        """构建分析提示词 - 仅分析外卖渠道且不区分渠道，仅分析底表/看板实际有数据的部分"""

        # 明确业务规则提示
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

        # 提取关键数据
        kpi_data = dashboard_data.get('kpi', {})
        category_data = dashboard_data.get('category', [])
        price_data = dashboard_data.get('price', [])
        promo_data = dashboard_data.get('promo', [])
        meta_data = dashboard_data.get('meta', {})

        # ========== Phase 1: 智能知识检索 ========== 
        contextual_knowledge = business_context  # 默认使用全量知识
        if self.knowledge_retriever:
            analysis_query = self._build_retrieval_query(kpi_data, category_data, meta_data)
            try:
                contextual_knowledge = self.knowledge_retriever.get_contextual_knowledge(
                    query=analysis_query,
                    analysis_type="门店经营健康度诊断"
                )
                print(f"✅ 已检索相关业务知识 ({len(contextual_knowledge)} 字符)")
            except Exception as e:
                print(f"⚠️ 向量检索失败,使用全量知识: {e}")
                contextual_knowledge = business_context

        # ========== 数据深度解读 ==========（自动跳过缺失数据）
        kpi_analysis = self._interpret_kpi(kpi_data)
        category_analysis = self._interpret_categories(category_data)
        price_analysis = self._interpret_price_bands(price_data)
        promo_analysis = self._interpret_promo(promo_data)
        product_role_insight = self._auto_classify_product_roles(category_data)
        health_diagnosis = self._diagnose_health_status(kpi_data, category_data)
        
        # ========== 数据有效性检查 ==========
        data_validity_check = self._check_data_validity(kpi_data, category_data, meta_data)

        # ========== 构建超详细提示词(Phase 1增强版) ========== 
        prompt = f"""
{business_rule}

{contextual_knowledge}

---

# ⚠️ 数据有效性检查（必须先看这个！）

{data_validity_check}

---

# 🔬 当前门店深度数据画像(筛选: {meta_data.get('筛选分类', '全部')})

{health_diagnosis}

---

# 🏪 商品角色自动识别

{product_role_insight}

---

# 当前门店数据全景

## 📊 一、核心经营指标解读

{kpi_analysis}

**🎯 标准对标(行业基准):**
- 动销率健康线: 75%以上(优秀) | 60-75%(合格) | 60%以下(需改进)
- 滞销占比警戒线: <15%(健康) | 15-25%(预警) | >25%(危险)
- 爆品占比目标: >8%(优秀) | 5-8%(合格) | <5%(不足)
- 客单价目标: 根据城市定位,通常35-50元
- 折扣力度: 7-8折(常态) | 5-7折(大促) | <5折(清仓)

---

## 🏪 二、分类维度深度拆解

{category_analysis}

**📌 分类健康度判断标准:**
- 类内动销率 >80%: 健康品类,继续投入
- 类内动销率 60-80%: 需优化,调整商品结构
- 类内动销率 <60%: 问题品类,考虑缩减或重组
- 销售额占比 >10%: 支柱品类
- 销售额占比 5-10%: 潜力品类
- 销售额占比 <5%: 长尾品类(评估ROI)

---

## 💰 三、价格带结构分析

{price_analysis}

**🎯 价格带健康结构(参考):**
- 低价带(0-10元): 15-25% (引流/高频)
- 中低价(10-20元): 30-40% (主力/走量)
- 中高价(20-50元): 25-35% (利润贡献)
- 高价带(50元+): 5-15% (品质/品牌)

---

## 🔥 四、促销效能诊断

{promo_analysis}

**⚠️ 促销强度判断:**
- 促销强度 >70%: 过度促销,利润压力大
- 促销强度 50-70%: 正常促销水平
- 促销强度 30-50%: 促销力度不足
- 促销强度 <30%: 几乎无促销,可能缺乏竞争力

---

# 🎯 你的分析任务(必须严格遵守)

**你现在要基于上述真实数据,以O2O零售专家的身份,进行深度经营诊断。**

## 🚫 禁止行为(绝对不能出现):

1. ❌ **空泛建议**:
   - 错误: "建议优化商品结构"
   - 正确: "建议下架滞销占比{kpi_data.get('滞销占比', 0):.1f}%中的长尾SKU,预计可释放约{int(kpi_data.get('去重SKU数', 0) * kpi_data.get('滞销占比', 0) / 100 * 0.6)}个SKU的库存资金"

2. ❌ **未考虑商品角色**:
   - 错误: "建议所有低毛利商品提价"
   - 正确: "流量品(如XXX)核心是引流,不应提价;利润品(如XXX)应保护毛利,避免过度促销"

3. ❌ **忽略健康度基准**:
   - 错误: "动销率还可以"
   - 正确: "动销率{kpi_data.get('动销率', 0):.1f}%,{'已达优秀水平(≥75%)' if kpi_data.get('动销率', 0) >= 75 else '距优秀水平还差' + str(round(75 - kpi_data.get('动销率', 0), 1)) + '个百分点'}"

4. ❌ **无法量化收益**:
   - 错误: "可能会增加销售"
   - 正确: "基于价格弹性,降价10%预计销量提升20-25%,净利润增加约¥X"

5. ❌ **未区分优先级**:
   - 错误: "建议做这些优化..."
   - 正确: "P0紧急(本周):XX | P1重点(2周):XX | P2长期(本月):XX"

## ✅ 必须遵守的分析框架:

### 📋 一、健康度总评(200-300字)

**必须包含:**
- 当前健康等级明确判断(优秀/健康/预警/危险)
- 3-5个核心数据支撑(必须引用具体数字)
- 对比行业基准的差距量化
- 一句话总结核心问题

**示例开头:**
"当前门店整体处于**[健康度等级]**状态。动销率{kpi_data.get('动销率', 0):.1f}%...[对标基准]...滞销占比{kpi_data.get('滞销占比', 0):.1f}%...[影响]...核心问题是..."

---

### 🔍 二、关键问题识别(3-5个)

**每个问题必须包含:**

**问题X: [一句话概括]**
- **数据依据**: [引用2-3个具体指标]
- **影响程度**: [量化损失,如"每天损失¥X" 或 "占压¥X库存资金"]
- **根因分析**: [为什么会这样,1-2句话]
- **商品角色关联**: [是流量品/利润品/形象品问题?]

**示例:**
**问题1: 滞销SKU过多,资金周转效率低**
- **数据依据**: 滞销占比{kpi_data.get('滞销占比', 0):.1f}%,约{int(kpi_data.get('去重SKU数', 0) * kpi_data.get('滞销占比', 0) / 100)}个SKU零销量
- **影响程度**: 假设每SKU平均库存成本¥50,约占压¥{int(kpi_data.get('去重SKU数', 0) * kpi_data.get('滞销占比', 0) / 100 * 50):,}库存资金
- **根因分析**: 可能是盲目扩充品类,未做需求验证,或长尾商品未及时淘汰
- **商品角色**: 可能误将低频商品当流量品引入,实际无引流效果

---

### 💡 三、优化策略矩阵(按ROI排序)

**每个方案必须包含:**
- **方案名称**: 简洁明确
- **ROI评估**: 高(>3.0) | 中(1.5-3.0) | 低(<1.5) | 优化型(¥0成本)
- **优先级**: P0紧急 | P1重点 | P2长期
- **执行内容**: 3-5个具体步骤
- **预期效果**: 量化收益(如"动销率+5pp" "日增利¥X")
- **执行周期**: X天
- **风险等级**: 低/中/高 + 具体风险

**输出分组:**

#### 🚨 紧急优化(P0 - 本周内执行)
**方案1: [方案名] (ROI: X.X, 优化型/投入¥X)**
- 执行内容:
  1. [具体步骤1]
  2. [具体步骤2]
  3. [具体步骤3]
- 预期效果: [量化,如"动销率提升至XX%,日增利¥XX"]
- 执行周期: X天
- 风险等级: 低 - [具体风险描述]

#### ⚡ 重点优化(P1 - 2周内执行)
[同上结构]

#### 📈 长期优化(P2 - 本月内执行)
[同上结构]

---

### 📊 四、效果预估(必须量化)

**必须包含:**
- 核心指标变化: 动销率 X% → Y% (+Zpp)
- 财务影响: 日销售额影响 +¥X, 月利润影响 +¥Y
- 库存优化: 释放库存资金约¥Z
- 整体ROI: 综合ROI X.X

---

### ⚠️ 五、风险提示

**必须包含:**
1. 执行风险(如供应链/平台规则/用户接受度)
2. 应对措施(具体2-3条)
3. 数据监控(需要盯哪些指标)

---

## 📝 输出检查清单(提交前自查):

- [ ] 每条建议都引用了具体数据?
- [ ] 区分了商品角色(流量品/利润品/形象品)?
- [ ] 对标了健康度基准(优秀/健康/预警/危险)?
- [ ] 所有优化方案都量化了收益?
- [ ] 明确了优先级(P0/P1/P2)?
- [ ] 计算了ROI?
- [ ] 提示了风险?
- [ ] 避免了空话套话?

---

**🎯 现在,请开始你的深度分析!记住,你的每一个建议都将影响真实的门店利润!**
"""
        
        return prompt
    
    def _check_data_validity(self, kpi_data: Dict, category_data: list, meta_data: Dict) -> str:
        """
        检查数据有效性 - 判断是筛选导致的无数据，还是真实的业务问题
        """
        lines = []
        lines.append("## 🔍 数据有效性诊断\n")
        
        # 检查KPI数据
        if not kpi_data:
            lines.append("❌ **KPI数据缺失** - 当前筛选条件下无任何KPI数据")
            lines.append("   原因: 可能是筛选条件过于严格(如选了某个无数据的分类)")
            lines.append("   建议: 调整筛选条件为'全部'，或检查数据源")
            return '\n'.join(lines)
        
        # 关键指标检查
        moverate = kpi_data.get('动销率', 0)
        total_sku = kpi_data.get('去重SKU数', 0)
        total_revenue = kpi_data.get('售价销售额', 0)
        
        # 判断数据有效性
        zero_count = 0
        if moverate == 0:
            zero_count += 1
        if total_sku == 0:
            zero_count += 1
        if total_revenue == 0:
            zero_count += 1
        
        if zero_count >= 2:
            # 多个核心指标为0，大概率是筛选导致
            lines.append("⚠️ **疑似筛选条件导致的无数据状态**\n")
            lines.append("```")
            lines.append(f"动销率: {moverate}%")
            lines.append(f"SKU数: {total_sku}个")
            lines.append(f"销售额: ¥{total_revenue:,.2f}")
            lines.append("```\n")
            lines.append("**诊断结论**: 多个核心指标同时为0，极大概率是当前筛选条件(如分类/门店/时间)导致数据为空，而非真实的零销售。")
            lines.append("\n**⚠️ 重要提示**: 请基于实际有数据的字段进行分析，不要臆测'门店休克'等结论。如需分析整体经营状况，请将筛选条件调整为'全部'。")
        else:
            # 数据有效，可以正常分析
            lines.append("✅ **数据有效** - 当前数据可用于业务分析\n")
            lines.append("```")
            lines.append(f"动销率: {moverate:.2f}%")
            lines.append(f"SKU数: {total_sku}个")
            if total_revenue > 0:
                lines.append(f"销售额: ¥{total_revenue:,.2f}")
            lines.append("```")
        
        # 检查分类数据
        if not category_data:
            lines.append("\n⚠️ **分类数据缺失** - 当前筛选条件下无分类数据")
        
        return '\n'.join(lines)
    
    def _build_retrieval_query(self, kpi_data: Dict, category_data: list, meta_data: Dict) -> str:
        """
        Phase 1: 构建智能检索查询
        根据当前数据特征构建查询,检索最相关的业务知识
        """
        query_parts = []
        
        # 1. 基于KPI指标构建查询
        moverate = kpi_data.get('动销率', 0)
        unsell_rate = kpi_data.get('滞销占比', 0)
        avg_discount = kpi_data.get('平均折扣', 10)
        
        if moverate < 60:
            query_parts.append("动销率低 如何优化商品结构")
        elif moverate < 75:
            query_parts.append("动销率合格 提升空间")
        
        if unsell_rate > 25:
            query_parts.append("滞销占比过高 清理库存")
        elif unsell_rate > 15:
            query_parts.append("滞销占比预警 SKU管理")
        
        if avg_discount < 7:
            query_parts.append("折扣过深 成本压力 利润优化")
        
        # 2. 基于分类数据构建查询
        if category_data:
            # 计算分类集中度
            total_revenue = sum(cat.get('售价销售额', 0) for cat in category_data)
            if total_revenue > 0:
                top3_revenue = sum(cat.get('售价销售额', 0) for cat in category_data[:3])
                concentration = (top3_revenue / total_revenue) * 100
                
                if concentration > 70:
                    query_parts.append("爆品集中度过高 分散风险")
                elif concentration > 60:
                    query_parts.append("爆品集中度 培育新品")
        
        # 3. 添加分析类型
        query_parts.append("健康度标准 商品角色 ROI优化 优先级排序")
        
        # 组合查询
        query = " ".join(query_parts)
        print(f"🔍 检索查询: {query[:100]}...")
        
        return query
    
    def _auto_classify_product_roles(self, category_data: list) -> str:
        """商品角色自动识别 - 基于业务基因"""
        if not category_data:
            return "⚠️ 暂无分类数据,无法识别商品角色"
        
        lines = []
        lines.append("**基于毛利率/销量/价格的商品角色识别:**\n")
        
        traffic_products = []  # 流量品
        profit_products = []   # 利润品
        image_products = []    # 形象品
        
        for cat in category_data[:15]:  # 分析TOP15分类
            name = cat.get('一级分类', '未知')
            discount = cat.get('美团一级分类折扣', 10)
            revenue = cat.get('售价销售额', 0)
            
            # 简易毛利率估算: (1 - 成本占比) × 100
            # 假设折扣越深,毛利率越低(简化版)
            estimated_margin = (discount / 10) * 25  # 粗略估算
            
            # 角色分类
            if estimated_margin < 15:
                traffic_products.append(f"- {name} (预估毛利{estimated_margin:.1f}%, 销售额¥{revenue:,.0f})")
            elif estimated_margin > 30:
                profit_products.append(f"- {name} (预估毛利{estimated_margin:.1f}%, 销售额¥{revenue:,.0f})")
            else:
                image_products.append(f"- {name} (预估毛利{estimated_margin:.1f}%, 销售额¥{revenue:,.0f})")
        
        lines.append("```")
        lines.append("🎯 流量品(引流获客, 毛利<15%, 可亏本)")
        if traffic_products:
            lines.extend(traffic_products)
        else:
            lines.append("   未识别到明显流量品")
        
        lines.append("\n💰 利润品(核心盈利, 毛利>30%, 绝对保护)")
        if profit_products:
            lines.extend(profit_products)
        else:
            lines.append("   ⚠️ 未识别到高毛利产品,利润压力大!")
        
        lines.append("\n🏆 形象品(品牌背书, 毛利15-30%, 平衡)")
        if image_products:
            lines.extend(image_products)
        else:
            lines.append("   未识别到明显形象品")
        
        lines.append("```\n")
        
        # 策略提示
        lines.append("**商品角色策略建议:**")
        lines.append("- 流量品: 价格必须对标竞品最低,哪怕亏本,核心是引流")
        lines.append("- 利润品: 绝对不能过度促销,保护毛利率,这是盈利根本")
        lines.append("- 形象品: 保持品牌调性,不过度打折,提升门店信任度")
        
        return '\n'.join(lines)
    
    def _diagnose_health_status(self, kpi_data: Dict, category_data: list) -> str:
        """健康度自动对标诊断"""
        lines = []
        lines.append("## 🏥 门店健康度诊断(自动对标行业基准)\n")
        
        # 利润健康度
        moverate = kpi_data.get('动销率', 0)
        unsell_rate = kpi_data.get('滞销占比', 0)
        avg_discount = kpi_data.get('平均折扣', 10)
        
        # 估算利润率(简化版: 基于折扣推算)
        estimated_profit_margin = (avg_discount - 7) * 2 if avg_discount > 7 else 0
        
        lines.append("### 💰 利润健康卡\n")
        lines.append("```")
        lines.append(f"预估净利润率: {estimated_profit_margin:.1f}%")
        if estimated_profit_margin >= 15:
            lines.append("   ✅ 优秀水平(>15%)")
        elif estimated_profit_margin >= 8:
            lines.append("   ✅ 健康水平(8-15%)")
        elif estimated_profit_margin >= 5:
            lines.append("   ⚠️ 预警水平(5-8%),利润承压")
        else:
            lines.append("   🚨 危险水平(<5%),可能亏损!")
        
        lines.append(f"\n平均折扣: {avg_discount:.2f}折")
        if avg_discount < 7:
            lines.append("   🚨 过深(商品成本压力极大,可能>70%)")
        elif avg_discount < 8:
            lines.append("   ⚠️ 正常促销(商品成本约65-70%)")
        else:
            lines.append("   ✅ 健康(商品成本约55-65%)")
        lines.append("```\n")
        
        # 运营健康度
        lines.append("### 📊 运营健康卡\n")
        lines.append("```")
        lines.append(f"动销率: {moverate:.1f}%")
        if moverate >= 75:
            lines.append("   ✅ 优秀(≥75%)")
        elif moverate >= 60:
            lines.append("   ⚠️ 合格(60-75%),距优秀还差{:.1f}个百分点".format(75 - moverate))
        else:
            lines.append("   🚨 需改进(<60%),{:.1f}%的商品无人购买".format(100 - moverate))
        
        lines.append(f"\n滞销占比: {unsell_rate:.1f}%")
        if unsell_rate < 15:
            lines.append("   ✅ 健康(<15%)")
        elif unsell_rate < 25:
            lines.append("   ⚠️ 预警(15-25%),约有{:.0f}个SKU零销量".format(kpi_data.get('去重SKU数', 0) * unsell_rate / 100))
        else:
            lines.append("   🚨 危险(>25%),约有{:.0f}个SKU占用资金无产出".format(kpi_data.get('去重SKU数', 0) * unsell_rate / 100))
        lines.append("```\n")
        
        # 风险预警
        lines.append("### ⚠️ 风险预警\n")
        warnings = []
        if estimated_profit_margin < 5:
            warnings.append("🚨 **P0级风险**: 利润率危险低,可能亏损,立即降低成本!")
        if unsell_rate > 25:
            warnings.append("🚨 **P0级风险**: 超1/4商品滞销,大量资金沉淀,立即清库!")
        if moverate < 60:
            warnings.append("⚠️ **P1级风险**: 动销率不达标,商品运营效率低")
        
        if warnings:
            lines.extend(warnings)
        else:
            lines.append("✅ 当前运营状态相对健康,继续保持并优化")
        
        return '\n'.join(lines)
    
    def _interpret_kpi(self, kpi_data: Dict) -> str:
        """解读KPI指标"""
        if not kpi_data:
            return "⚠️ 暂无KPI数据"
        
        lines = []
        lines.append("```")
        
        # 动销率
        moverate = kpi_data.get('动销率', 0)
        lines.append(f"📈 动销率: {moverate:.2f}%")
        if moverate >= 75:
            lines.append(f"   ✅ 优秀水平(>75%),商品周转健康")
        elif moverate >= 60:
            lines.append(f"   ⚠️ 合格水平(60-75%),仍有提升空间")
        else:
            lines.append(f"   🚨 低于健康线(<60%),存在大量滞销商品")
        
        # 滞销占比
        unsell_rate = kpi_data.get('滞销占比', 0)
        lines.append(f"\n📉 滞销占比: {unsell_rate:.2f}%")
        if unsell_rate < 15:
            lines.append(f"   ✅ 健康水平(<15%)")
        elif unsell_rate < 25:
            lines.append(f"   ⚠️ 预警水平(15-25%),需优化商品结构")
        else:
            lines.append(f"   🚨 危险水平(>25%),大量资金沉淀在滞销品")
        
        # 爆品数据
        hot_count = kpi_data.get('爆品数', 0)
        hot_rate = kpi_data.get('爆品占比', 0)
        lines.append(f"\n🔥 爆品数量: {hot_count}个 (占比{hot_rate:.2f}%)")
        if hot_rate >= 8:
            lines.append(f"   ✅ 优秀水平(>8%)")
        elif hot_rate >= 5:
            lines.append(f"   ⚠️ 合格水平(5-8%)")
        else:
            lines.append(f"   🚨 不足(<5%),爆品打造能力弱")
        
        # 客单价
        avg_price = kpi_data.get('平均售价', 0)
        lines.append(f"\n💰 平均售价: {avg_price:.2f}元")
        
        # 折扣力度
        discount = kpi_data.get('平均折扣', 0)
        lines.append(f"🏷️ 平均折扣: {discount:.2f}折")
        if discount < 7:
            lines.append(f"   🚨 折扣过深(<7折),利润压力大")
        elif discount < 8:
            lines.append(f"   ⚠️ 正常促销水平(7-8折)")
        else:
            lines.append(f"   ✅ 原价销售为主(>8折),利润健康")
        
        # SKU数据
        total_sku = kpi_data.get('去重SKU数', 0)
        lines.append(f"\n📦 SKU总数: {total_sku}个")
        
        lines.append("```")
        return '\n'.join(lines)
    
    def _interpret_categories(self, category_data: list) -> str:
        """解读分类数据"""
        if not category_data:
            return "⚠️ 暂无分类数据"
        
        lines = []
        lines.append("**TOP10 销售额分类明细:**\n")
        lines.append("```")
        lines.append(f"{'序号':<4} {'分类':<12} {'销售额(元)':<12} {'动销率':<10} {'SKU数':<8} {'折扣':<8} {'诊断'}")
        lines.append("-" * 80)
        
        for idx, cat in enumerate(category_data[:10], 1):
            name = cat.get('一级分类', '未知')[:10]
            revenue = cat.get('售价销售额', 0)
            moverate = cat.get('美团一级分类动销率(类内)', 0)
            sku_count = cat.get('美团一级分类去重SKU数(口径同动销率)', 0)
            discount = cat.get('美团一级分类折扣', 10)
            
            # 健康度诊断
            if moverate >= 80:
                health = "✅健康"
            elif moverate >= 60:
                health = "⚠️需优化"
            else:
                health = "🚨问题"
            
            lines.append(
                f"{idx:<4} {name:<12} {revenue:>10.0f}   "
                f"{moverate:>6.1f}%   {sku_count:>6}个  {discount:>5.1f}折  {health}"
            )
        
        lines.append("```")
        
        # 计算总销售额
        total_revenue = sum(cat.get('售价销售额', 0) for cat in category_data)
        if total_revenue > 0:
            top3_revenue = sum(cat.get('售价销售额', 0) for cat in category_data[:3])
            concentration = (top3_revenue / total_revenue) * 100
            lines.append(f"\n**📊 TOP3分类集中度: {concentration:.1f}%**")
            if concentration > 60:
                lines.append("   🚨 过度集中,风险较高,需拓展品类")
            elif concentration > 45:
                lines.append("   ⚠️ 中度集中,建议培育更多支柱品类")
            else:
                lines.append("   ✅ 结构分散,抗风险能力强")
        
        return '\n'.join(lines)
    
    def _interpret_price_bands(self, price_data: list) -> str:
        """解读价格带数据"""
        if not price_data:
            return "⚠️ 暂无价格带数据"
        
        lines = []
        lines.append("**价格带SKU分布与销售贡献:**\n")
        lines.append("```")
        lines.append(f"{'价格带':<15} {'SKU数':<10} {'销售额(元)':<15} {'销售占比':<10} {'评价'}")
        lines.append("-" * 70)
        
        for band in price_data:
            price_range = band.get('price_band', '未知')
            sku_num = band.get('SKU数量', 0)
            revenue = band.get('销售额', 0)
            ratio = band.get('销售额占比', 0)
            
            # 判断合理性
            if '0-10' in price_range:
                comment = "引流价格带" if ratio < 25 else "⚠️占比过高"
            elif '10-20' in price_range:
                comment = "✅主力价格带" if ratio > 25 else "⚠️占比偏低"
            elif '20-50' in price_range:
                comment = "利润贡献" if ratio > 20 else "⚠️待加强"
            else:
                comment = "高端品质"
            
            lines.append(
                f"{price_range:<15} {sku_num:>8}个  {revenue:>12.0f}  "
                f"{ratio:>7.1f}%   {comment}"
            )
        
        lines.append("```")
        return '\n'.join(lines)
    
    def _interpret_promo(self, promo_data: list) -> str:
        """解读促销强度数据"""
        if not promo_data:
            return "⚠️ 暂无促销数据"
        
        lines = []
        lines.append("**TOP10 促销强度分类:**\n")
        lines.append("```")
        lines.append(f"{'序号':<4} {'分类':<12} {'促销强度':<12} {'折扣力度':<10} {'诊断'}")
        lines.append("-" * 60)
        
        for idx, item in enumerate(promo_data[:10], 1):
            name = item.get('分类', '未知')[:10]
            intensity = item.get('促销强度', 0)
            discount = item.get('折扣力度', 10)
            
            # 促销诊断
            if intensity > 70:
                diag = "🚨过度促销"
            elif intensity > 50:
                diag = "⚠️促销偏高"
            elif intensity > 30:
                diag = "✅正常水平"
            else:
                diag = "📈促销不足"
            
            lines.append(
                f"{idx:<4} {name:<12} {intensity:>8.1f}%   {discount:>6.1f}折   {diag}"
            )
        
        lines.append("```")
        return '\n'.join(lines)
    
    def _get_kpi_comment(self, value: float, kpi_type: str) -> str:
        """获取KPI评价"""
        if kpi_type == 'moverate':
            if value >= 75:
                return "超过"
            elif value >= 60:
                return "接近"
            else:
                return "低于"
        return ""


def get_ai_analyzer(api_key: str = None, model_type: str = 'glm') -> Optional[AIAnalyzer]:
    """
    获取AI分析器实例(工厂函数)
    
    Args:
        api_key: API密钥
        model_type: 模型类型
        
    Returns:
        AIAnalyzer实例或None
    """
    try:
        analyzer = AIAnalyzer(api_key=api_key, model_type=model_type)
        return analyzer if analyzer.is_ready() else None
    except Exception as e:
        print(f"❌ AI分析器创建失败: {e}")
        return None


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("AI分析器测试")
    print("=" * 60)
    
    # 初始化
    analyzer = get_ai_analyzer()
    
    if analyzer and analyzer.is_ready():
        print("\n✅ AI分析器初始化成功")
        
        # 测试简单对话
        test_prompt = "你好,请介绍一下你自己"
        print(f"\n测试提示词: {test_prompt}")
        
        result = analyzer._generate_content(test_prompt)
        print(f"\nAI响应:\n{result}")
        
    else:
        print("\n❌ AI分析器初始化失败")
        print("请设置ZHIPU_API_KEY环境变量")
