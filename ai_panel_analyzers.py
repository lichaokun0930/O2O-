#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看板专项AI分析器模块

功能:
- 为每个看板提供专项AI分析
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
    """看板分析器基类"""
    
    def __init__(self, api_key: str = None):
        """
        初始化分析器
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')
        self.client = None
        self.model_name = 'glm-4.6'
        self.ready = False
        
        if self.api_key:
            self._init_client()
    
    def _init_client(self):
        """初始化GLM客户端"""
        try:
            from zhipuai import ZhipuAI
            self.client = ZhipuAI(
                api_key=self.api_key,
                base_url="https://open.bigmodel.cn/api/coding/paas/v4"
            )
            self.ready = True
        except Exception as e:
            print(f"❌ AI客户端初始化失败: {e}")
            self.ready = False
    
    def _generate_content(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """调用AI生成内容 - 带重试机制"""
        if not self.ready:
            return "❌ AI分析器未就绪，请检查API密钥配置"
        
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 正在调用AI生成分析...模型:{self.model_name}, 提示词长度:{len(prompt)}字符 (尝试 {attempt + 1}/{max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                result = response.choices[0].message.content
                print(f"✅ AI分析完成，返回内容长度:{len(result) if result else 0}字符")
                
                if not result or len(result.strip()) == 0:
                    return "⚠️ AI返回了空内容，请重试或检查提示词"
                
                return result
                
            except Exception as e:
                error_str = str(e)
                print(f"❌ 第{attempt + 1}次尝试失败: {error_str}")
                
                # 检查是否是429错误（频率限制）
                if "429" in error_str or "1302" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)  # 递增等待时间
                        print(f"⏳ API调用频率受限，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return f"❌ API调用频率超限: 请稍后再试，或联系管理员增加API配额。错误详情: {error_str}"
                else:
                    # 其他错误直接返回
                    return f"❌ AI分析失败: {error_str}"
        
        return "❌ AI分析失败: 多次重试后仍然失败，请稍后再试"


class KPIPanelAnalyzer(BasePanelAnalyzer):
    """KPI看板专项分析器"""
    
    def analyze(self, kpi_data: Dict[str, Any]) -> str:
        """
        分析KPI看板数据
        
        Args:
            kpi_data: KPI数据字典
            
        Returns:
            分析结果文本
        """
        # 宽松的数据检查：只要有数据就分析
        if not kpi_data or len(kpi_data) == 0:
            return "⚠️ 当前筛选条件下暂无KPI数据，请调整筛选条件"
        
        # 检查是否所有值都是0或空
        has_valid_data = False
        for key, value in kpi_data.items():
            if value and value != 0:
                has_valid_data = True
                break
        
        if not has_valid_data:
            return "⚠️ 当前筛选条件下KPI数据全部为0，请调整筛选条件或选择'全部'查看整体数据"
        
        prompt = self._build_kpi_prompt(kpi_data)
        return self._generate_content(prompt, temperature=0.7, max_tokens=2500)
    
    def _check_validity(self, kpi_data: Dict) -> str:
        """检查数据有效性"""
        moverate = kpi_data.get('动销率', 0)
        total_sku = kpi_data.get('去重SKU数', 0)
        
        if moverate == 0 and total_sku == 0:
            return "⚠️ 当前筛选条件下暂无KPI数据，请调整筛选条件或选择'全部'查看整体数据"
        return "✅ 数据有效"
    
    def _build_kpi_prompt(self, kpi_data: Dict) -> str:
        """构建KPI分析提示词 - 包含完整指标定义和计算逻辑"""
        
        prompt = f"""
你是一位资深的零售数据分析专家，现在需要你专注分析"KPI核心指标看板"。

【📚 核心指标定义与计算逻辑】

**SKU相关指标**
1. **总SKU数(含规格)**: 所有商品SKU的总数，包括单规格和多规格的所有子SKU
2. **去重SKU数**: 同一商品的不同规格只算1个（如可乐300ml/500ml/1L算1个）
   - 计算: 去除多规格商品的规格重复后的唯一商品数
3. **多规格SKU总数**: 拥有多个规格的商品的SKU总数
   - 示例: 可乐(300ml/500ml/1L) = 3个多规格SKU

**动销指标（核心）**
4. **动销SKU数**: 月售 > 0 的商品数量（有销量的商品）
5. **滞销SKU数**: 月售 = 0 的商品数量（没有销量的商品）
6. **动销率** = 动销SKU数 ÷ 去重SKU数 × 100%
   - 行业标准:
     * 优秀: ≥80%（大部分商品在卖）
     * 健康: 60-80%（正常水平）
     * 预警: 40-60%（需优化）
     * 危险: <40%（大量死库存）
   - 公式验证: 动销率 + 滞销率 = 100%

**销售指标**
7. **总销售额(去重后)**: 所有SKU的 售价 × 月售 之和（单位：元）
8. **平均售价**: 总销售额 ÷ 总销量
   - 反映客单价水平
   - 行业参考: 便利店35-50元，超市20-35元
9. **客单价**: 总销售额 ÷ 订单数
   - 衡量单次购买金额

**促销指标**
10. **平均折扣**: 所有SKU的折扣力度平均值（单位：折）
    - 10折 = 无折扣（原价）
    - 9折 = 优惠10%
    - 5折 = 优惠50%
    - 数值越小，折扣越大，促销越激进
    - 健康范围: 8.5-9.5折（适度促销）
    - 过度促销: <7折（利润压力大）

**爆品指标**
11. **爆品数/爆品占比**: 月售排名TOP20%的商品数量及占比
    - 爆品是店铺的核心竞争力
    - 健康占比: 5-10%
    - 爆品贡献: 通常带来60-80%的销售额

【📊 当前KPI数据】
```json
{json.dumps(convert_to_serializable(kpi_data), ensure_ascii=False, indent=2)}
```

【🎯 分析任务】

请基于以上指标定义，逐项分析当前门店的健康度：

**第一步：数据有效性检查**
- 检查关键指标是否为0或异常值
- 验证动销率+滞销率是否=100%
- 如有异常，说明原因

**第二步：逐项KPI诊断**（只分析有值的指标）

对每个指标，必须包含：
1. 📌 **当前值**: 具体数字
2. 📊 **对标**: 与行业标准对比
3. ✅/⚠️ **判断**: 优秀/健康/预警/危险
4. 💡 **建议**: 1-2条可执行的优化动作

重点分析指标:
- 动销率（最重要）
- 滞销SKU数（资源浪费）
- 爆品数/占比（盈利能力）
- 平均折扣（利润健康度）

**第三步：综合评分**
- 整体健康度评分: 0-100分
- 核心问题识别: 列出1-3个最urgent的问题
- 优先级建议: 按ROI排序的优化动作

【⚠️ 输出要求】

1. 必须基于指标定义进行分析，不要凭感觉
2. 必须引用计算公式验证数据合理性
3. 必须量化影响（如"滞销SKU占XX%，浪费XX元库存资金"）
4. 禁止空话套话（如"建议优化"没有具体怎么优化）
5. 每个建议必须可执行（谁做、做什么、预期效果）

【📝 输出格式】

## ✅ 数据有效性检查
[验证结果]

## 📊 逐项KPI诊断

### 1. 动销率 (XX%)
- 当前值: XX%
- 对标: [行业标准]
- 判断: ✅优秀 / ⚠️预警 / ❌危险
- 建议: [具体动作]

### 2. 滞销SKU数 (XX个)
[同上格式]

...（其他有值的指标）

## 🎯 综合评分与建议

**健康度评分**: XX/100分
**核心问题**: 
1. [问题1]: [影响]
2. [问题2]: [影响]

**优先级行动清单**:
1. ⚡立即: [动作] (ROI: XX)
2. 📅本周: [动作] (ROI: XX)
3. �本月: [动作] (ROI: XX)

现在开始分析！
"""
        return prompt


class CategoryPanelAnalyzer(BasePanelAnalyzer):
    """分类看板专项分析器"""
    
    def analyze(self, category_data: List[Dict]) -> str:
        """
        分析分类看板数据
        
        Args:
            category_data: 分类数据列表
            
        Returns:
            分析结果文本
        """
        # 宽松的数据检查
        if not category_data or len(category_data) == 0:
            return "⚠️ 当前筛选条件下暂无分类数据，请调整筛选条件"
        
        prompt = self._build_category_prompt(category_data)
        return self._generate_content(prompt, temperature=0.7, max_tokens=2500)
    
    def _build_category_prompt(self, category_data: List[Dict]) -> str:
        """构建分类分析提示词 - 包含完整指标定义和计算逻辑"""
        
        # 计算总销售额和TOP3集中度
        total_revenue = sum(cat.get('售价销售额', 0) for cat in category_data)
        top3_revenue = sum(cat.get('售价销售额', 0) for cat in category_data[:3])
        concentration = (top3_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # 提取TOP10分类数据
        top10_data = []
        for idx, cat in enumerate(category_data[:10], 1):
            top10_data.append({
                '排名': idx,
                '分类': cat.get('一级分类', '未知'),
                '销售额': cat.get('售价销售额', 0),
                '动销率(类内)': cat.get('美团一级分类动销率(类内)', 0),
                'SKU数': cat.get('美团一级分类去重SKU数(口径同动销率)', 0),
                '折扣力度': cat.get('美团一级分类折扣', 10),
                '促销强度': cat.get('促销强度', 0)
            })
        
        prompt = f"""
你是一位资深的零售数据分析专家，现在需要你专注分析"分类看板"。

【📚 分类指标定义与计算逻辑】

**销售指标**
1. **售价销售额**: 该分类所有SKU的 售价 × 月售 之和（单位：元）
   - 反映该分类的销售贡献
   - 用于计算分类排名和集中度

2. **销售额占比** = 该分类销售额 ÷ 总销售额 × 100%
   - 衡量该分类的重要性

**动销指标**
3. **动销率(类内)** = 该分类动销SKU数 ÷ 该分类总SKU数 × 100%
   - 只看该分类内部的动销情况
   - 与全局动销率不同！这是"类内"动销率
   - 行业标准:
     * 优秀: ≥80%（分类健康）
     * 健康: 60-80%（正常水平）
     * 预警: 40-60%（需优化）
     * 危险: <40%（大量滞销）

4. **SKU数**: 该分类的去重SKU总数
   - 反映分类丰富度
   - 过多: SKU臃肿，管理困难
   - 过少: 品类单薄，选择少

**促销指标**
5. **折扣力度**: 该分类所有SKU的平均折扣（单位：折）
   - 10折 = 无折扣（原价销售）
   - 数值越小，折扣越大
   - 示例: 4.70折 = 打4.7折，折扣53%

6. **促销强度** = (10 - 折扣力度) ÷ 9 × 100%
   - 计算公式: 将折扣力度转换为0-100%的促销强度
   - 示例: 折扣力度4.70 → 促销强度 = (10-4.7)/9×100 = 58.87%
   - 促销强度分级:
     * 0-30%: 轻度促销（8-10折）
     * 30-60%: 中度促销（5-8折）
     * 60-100%: 强促销（0-5折）
   - ⚠️ 注意: 促销强度越高，折扣越大，利润越低！

**集中度指标**
7. **TOP3集中度** = TOP3分类销售额 ÷ 总销售额 × 100%
   - 衡量销售的集中程度
   - 风险评估:
     * >60%: 过度集中，依赖度高，风险大
     * 45-60%: 中度集中，正常水平
     * <45%: 分散均衡，抗风险能力强
   - 集中度过高的风险: TOP分类出问题会严重影响整体

【📊 当前分类数据】

**总销售额**: ¥{total_revenue:,.2f}
**TOP3集中度**: {concentration:.1f}%
**分类总数**: {len(category_data)}个

**TOP10分类明细** (已按销售额降序排列):
```json
{json.dumps(convert_to_serializable(top10_data), ensure_ascii=False, indent=2)}
```

【🎯 分析任务】

**第一步：TOP分类表现分析**

分析TOP3分类:
1. 📊 销售贡献: 每个分类的销售额和占比
2. 📈 动销健康度: 动销率(类内)是否≥60%
3. 💰 促销依赖度: 促销强度是否过高(>60%)
4. 🏷️ SKU效率: 平均每个SKU的销售额（销售额÷SKU数）

判断标准:
- ✅ 健康分类: 动销率≥60% + 促销强度<60%
- ⚠️ 促销依赖: 动销率<60% + 促销强度>60%（靠打折维持销量）
- ❌ 问题分类: 动销率<40%（即使促销也卖不动）

**第二步：集中度风险评估**

当前集中度: {concentration:.1f}%
- 与标准对比（<45%/45-60%/>60%）
- 风险提示: 如果TOP3集中度过高，需要培育其他分类
- 机会识别: 哪些分类有增长潜力

**第三步：问题分类识别**

筛选标准:
1. 动销率(类内) < 60% 的分类
2. 促销强度 > 60% 但销售额占比 < 5% 的分类（促销无效）
3. SKU数 > 50 但动销率 < 40% 的分类（SKU臃肿）

对每个问题分类:
- 问题诊断: 为什么卖不好？
- 量化影响: 占用多少SKU和库存？
- 优化建议: 缩品/促销/下架？

**第四步：机会分类挖掘**

筛选标准:
1. 动销率(类内) > 80%（商品卖得好）
2. 销售额占比 < 5%（还有增长空间）
3. 促销强度 < 40%（不靠打折也能卖）

机会分析:
- 为什么动销好但销售额低？（SKU太少？定价太低？）
- 扩品潜力: 建议增加多少SKU
- 预期效果: 扩品后销售额能提升多少

【⚠️ 输出要求】

1. 必须基于指标定义进行分析
2. 必须理解"促销强度"是(10-折扣力度)/9×100%
3. 必须区分"动销率(类内)"和"全局动销率"
4. 必须量化影响（如"饮料促销强度58.87%，打4.7折，利润率低"）
5. 每个建议必须可执行

【📝 输出格式】

## 📊 分类看板核心洞察

### 1. TOP3分类表现
- **第1名**: [分类名]（销售额¥XXX，占比XX%）
  * 动销率: XX%（✅健康/⚠️预警）
  * 促销依赖: 促销强度XX%（折扣X.X折）
  * SKU效率: ¥XXX/SKU
  * 评价: [健康度判断]

[第2、3名同上]

### 2. 集中度风险评估
- TOP3集中度: {concentration:.1f}%
- 风险等级: ✅低风险/⚠️中风险/❌高风险
- 分析: [集中度合理性]
- 建议: [是否需要培育其他分类]

### 3. 问题分类识别（动销率<60%）
1. **[分类名]**: 动销率XX%，促销强度XX%
   - 问题: [诊断]
   - 影响: 占用XX个SKU
   - 建议: [具体动作]

### 4. 机会分类挖掘（高动销低销额）
1. **[分类名]**: 动销率XX%，销售额占比XX%
   - 潜力: [分析]
   - 建议: 扩品XX个SKU
   - 预期: 销售额提升¥XXX

## 🎯 综合建议

**优先级行动**:
1. ⚡立即: [动作]
2. 📅本周: [动作]
3. 📆本月: [动作]

现在开始分析！
"""
        return prompt


class PricePanelAnalyzer(BasePanelAnalyzer):
    """价格带看板专项分析器"""
    
    def analyze(self, price_data: List[Dict]) -> str:
        """
        分析价格带看板数据
        
        Args:
            price_data: 价格带数据列表
            
        Returns:
            分析结果文本
        """
        if not price_data or len(price_data) == 0:
            return "⚠️ 当前筛选条件下暂无价格带数据，请调整筛选条件"
        
        prompt = self._build_price_prompt(price_data)
        return self._generate_content(prompt, temperature=0.7, max_tokens=2000)
    
    def _build_price_prompt(self, price_data: List[Dict]) -> str:
        """构建价格带分析提示词 - 包含完整指标定义和计算逻辑"""
        
        # 计算总销售额和总SKU数
        total_revenue = sum(p.get('销售额', 0) for p in price_data)
        total_sku = sum(p.get('SKU数量', 0) for p in price_data)
        
        # 为每个价格带计算占比
        enriched_data = []
        for p in price_data:
            revenue = p.get('销售额', 0)
            sku_count = p.get('SKU数量', 0)
            enriched_data.append({
                '价格带': p.get('价格带', '未知'),
                'SKU数量': sku_count,
                'SKU占比': f"{(sku_count / total_sku * 100) if total_sku > 0 else 0:.1f}%",
                '销售额': revenue,
                '销售额占比': f"{(revenue / total_revenue * 100) if total_revenue > 0 else 0:.1f}%",
                'SKU效率': f"¥{(revenue / sku_count) if sku_count > 0 else 0:.2f}/SKU"
            })
        
        prompt = f"""
你是一位资深的零售数据分析专家，现在需要你专注分析"价格带看板"。

【📚 价格带指标定义与计算逻辑】

**基础指标**
1. **价格带**: 按商品单价分组，如0-5元、5-10元、10-15元等
   - 用于评估价格结构和消费层次

2. **SKU数量**: 该价格带内的去重SKU总数
   - 反映该价格带的商品丰富度

3. **SKU占比** = 该价格带SKU数 ÷ 全部SKU数 × 100%
   - 反映SKU资源在各价格带的分布

4. **销售额**: 该价格带所有SKU的 售价 × 月售 之和（单位：元）
   - 反映该价格带的销售贡献

5. **销售额占比** = 该价格带销售额 ÷ 总销售额 × 100%
   - 衡量该价格带的销售贡献度

**效率指标**
6. **SKU效率** = 该价格带销售额 ÷ 该价格带SKU数（单位：元/SKU）
   - 衡量单个SKU的平均销售能力
   - 效率越高，SKU越优质
   - 低效率价格带: SKU效率 < 整体平均效率的50%
   - 高效率价格带: SKU效率 > 整体平均效率的150%

**健康价格带结构标准**（适用于便利店/超市）

| 价格带 | SKU占比 | 销售额占比 | 功能定位 | 备注 |
|--------|---------|-----------|----------|------|
| 0-10元 | 15-25% | 10-20% | 引流/高频 | 必备款，薄利多销 |
| 10-20元 | 30-40% | 35-45% | 主力/走量 | 核心价格带，销售主力 |
| 20-50元 | 25-35% | 30-40% | 利润贡献 | 中高端，利润来源 |
| 50元+ | 5-15% | 5-15% | 品质/品牌 | 高端款，树立形象 |

⚠️ 注意事项:
1. **低价带过大**: SKU占比>30% → SKU臃肿，管理成本高
2. **中低价不足**: 10-20元SKU占比<25% → 缺少走量主力
3. **高价带缺失**: 50元+销售额占比<3% → 品质感不足
4. **效率失衡**: 某价格带SKU占比远高于销售额占比 → SKU浪费严重

【📊 当前价格带数据】

**总销售额**: ¥{total_revenue:,.2f}
**总SKU数**: {total_sku}
**整体SKU效率**: ¥{(total_revenue / total_sku) if total_sku > 0 else 0:.2f}/SKU

**各价格带明细**:
```json
{json.dumps(convert_to_serializable(enriched_data), ensure_ascii=False, indent=2)}
```

【🎯 分析任务】

**第一步：价格带结构健康度评估**

对比当前结构与健康标准:
1. 📊 低价带(0-10元): SKU占比是否15-25%？销售额占比是否10-20%？
2. 📈 中低价(10-20元): SKU占比是否30-40%？销售额占比是否35-45%？
3. 💰 中高价(20-50元): SKU占比是否25-35%？销售额占比是否30-40%？
4. 🏆 高价带(50元+): SKU占比是否5-15%？销售额占比是否5-15%？

评分标准:
- ✅ 健康: 各价格带占比都在标准范围内
- ⚠️ 偏差: 1-2个价格带偏离标准±5%
- ❌ 失衡: 多个价格带严重偏离或主力价格带缺失

**第二步：SKU效率分析**

计算整体平均SKU效率: ¥{(total_revenue / total_sku) if total_sku > 0 else 0:.2f}/SKU

对每个价格带:
1. 计算SKU效率 = 销售额 ÷ SKU数量
2. 与整体平均对比:
   - 高效价格带: 效率 > 平均×1.5
   - 正常价格带: 平均×0.5 < 效率 < 平均×1.5
   - 低效价格带: 效率 < 平均×0.5
3. 低效价格带诊断: 为什么卖不好？（定价不合理？商品不对？过度促销？）

**第三步：结构性问题识别**

问题1: SKU资源浪费
- 识别标准: SKU占比 > 销售额占比 + 10%
- 举例: 某价格带SKU占比30%但销售额占比仅15% → SKU浪费严重
- 建议: 缩减该价格带的低效SKU

问题2: 主力价格带不突出
- 识别标准: 10-20元价格带销售额占比 < 30%
- 影响: 缺少走量主力，整体销售不稳定
- 建议: 增加10-20元性价比产品

问题3: 高价带缺失或过弱
- 识别标准: 50元+销售额占比 < 3%
- 影响: 品质形象不足，利润空间受限
- 建议: 引入中高端品牌

**第四步：价格策略优化建议**

基于以上分析，给出:
1. **扩品建议**: 哪些价格带需要增加SKU？增加多少？
2. **缩品建议**: 哪些价格带需要减少SKU？减少多少？
3. **调价建议**: 是否有商品定价不合理需要调整？
4. **预期效果**: 优化后销售额能提升多少？

【⚠️ 输出要求】

1. 必须基于指标定义进行分析
2. 必须理解"SKU效率"是销售额÷SKU数
3. 必须对比健康标准给出偏差度
4. 必须量化问题（如"低价带SKU占比35%，超标准上限10个百分点"）
5. 每个建议必须可执行

【📝 输出格式】

## 💰 价格带看板核心洞察

### 1. 结构健康度评估（对标行业标准）
- **低价带(0-10元)**: SKU占比XX%，销售额占比XX%
  * 对比标准: SKU应15-25%，销售额应10-20%
  * 评价: ✅健康/⚠️偏高/❌过低
  
- **中低价(10-20元)**: SKU占比XX%，销售额占比XX%
  * 对比标准: SKU应30-40%，销售额应35-45%
  * 评价: ✅主力突出/⚠️不足

- **中高价(20-50元)**: SKU占比XX%，销售额占比XX%
  * 对比标准: SKU应25-35%，销售额应30-40%
  * 评价: [判断]

- **高价带(50元+)**: SKU占比XX%，销售额占比XX%
  * 对比标准: SKU应5-15%，销售额应5-15%
  * 评价: [判断]

**综合评分**: ✅健康/⚠️偏差/❌失衡

### 2. SKU效率分析（整体平均¥{(total_revenue / total_sku) if total_sku > 0 else 0:.2f}/SKU）
**高效价格带**（效率>平均×1.5）:
- [价格带]: ¥XXX/SKU（效率是平均的X.X倍）

**低效价格带**（效率<平均×0.5）:
- [价格带]: ¥XXX/SKU（仅为平均的X%）
  * 问题: [诊断]
  * 建议: [具体动作]

### 3. 结构性问题识别
**问题1 - SKU资源浪费**: [价格带]SKU占比XX%，销售额占比XX%，浪费XX个百分点
**问题2 - 主力价格带**: 10-20元销售额占比XX%（✅正常/>30%/⚠️不足<30%）
**问题3 - 高价带表现**: 50元+销售额占比XX%（✅健康/>5%/⚠️缺失<3%）

### 4. 价格策略优化建议
**扩品建议**:
- [价格带]: 建议增加XX个SKU，理由[XXX]

**缩品建议**:
- [价格带]: 建议减少XX个低效SKU，释放资源

**调价建议**:
- [具体建议]

**预期效果**: 优化后销售额预计提升¥XXX（XX%）

## 🎯 优先级行动

**P0立即**: [最紧急的结构性问题]
**P1本周**: [重要优化动作]
**P2本月**: [长期调整方向]

现在开始分析！
"""
        return prompt


class PromoPanelAnalyzer(BasePanelAnalyzer):
    """促销看板专项分析器"""
    
    def analyze(self, promo_data: List[Dict]) -> str:
        """
        分析促销看板数据
        
        Args:
            promo_data: 促销数据列表
            
        Returns:
            分析结果文本
        """
        if not promo_data or len(promo_data) == 0:
            return "⚠️ 当前筛选条件下暂无促销数据，请调整筛选条件"
        
        prompt = self._build_promo_prompt(promo_data)
        return self._generate_content(prompt, temperature=0.7, max_tokens=2000)
    
    def _build_promo_prompt(self, promo_data: List[Dict]) -> str:
        """构建促销分析提示词 - 包含完整指标定义和计算逻辑"""
        
        # 按促销强度排序，识别过度促销和促销不足
        sorted_data = sorted(promo_data, key=lambda x: x.get('促销强度', 0), reverse=True)
        
        # 统计促销强度分布
        over_promo = [d for d in sorted_data if d.get('促销强度', 0) > 70]
        normal_promo = [d for d in sorted_data if 30 <= d.get('促销强度', 0) <= 70]
        low_promo = [d for d in sorted_data if d.get('促销强度', 0) < 30]
        
        # 计算平均促销强度
        avg_promo = sum(d.get('促销强度', 0) for d in sorted_data) / len(sorted_data) if sorted_data else 0
        
        # 提取TOP10高促销强度数据
        top10_promo = []
        for d in sorted_data[:10]:
            top10_promo.append({
                '分类/角色': d.get('分类', d.get('角色', '未知')),
                '折扣力度': d.get('折扣', 10),
                '促销强度': d.get('促销强度', 0),
                '销售额': d.get('销售额', 0),
                '动销率': d.get('动销率', 0)
            })
        
        prompt = f"""
你是一位资深的零售数据分析专家，现在需要你专注分析"促销看板"。

【📚 促销指标定义与计算逻辑】

**核心指标**
1. **折扣力度**: 该分类/角色所有SKU的平均折扣（单位：折）
   - 10折 = 原价销售（无折扣）
   - 数值越小，折扣越大
   - 示例: 
     * 折扣力度 8.5 → 打8.5折，优惠15%
     * 折扣力度 5.0 → 打5折，优惠50%
     * 折扣力度 3.0 → 打3折，优惠70%

2. **促销强度** = (10 - 折扣力度) ÷ 9 × 100%
   - **这是核心计算公式！**
   - 计算逻辑: 将折扣力度(0-10)线性转换为促销强度(0-100%)
   - 示例计算:
     * 折扣力度 10折 → 促销强度 = (10-10)/9×100 = 0%（无促销）
     * 折扣力度 8.5折 → 促销强度 = (10-8.5)/9×100 = 16.67%（轻度促销）
     * 折扣力度 5.0折 → 促销强度 = (10-5)/9×100 = 55.56%（中度促销）
     * 折扣力度 3.0折 → 促销强度 = (10-3)/9×100 = 77.78%（强促销）
     * 折扣力度 1.0折 → 促销强度 = (10-1)/9×100 = 100%（极限促销）

3. **促销强度分级标准**

| 促销强度 | 折扣范围 | 等级 | 利润影响 | 适用场景 |
|----------|----------|------|----------|----------|
| 0-15% | 9-10折 | 无促销/微促 | 利润健康 | 正常销售 |
| 15-30% | 7.5-9折 | 轻度促销 | 利润良好 | 节日/会员 |
| 30-60% | 4.5-7.5折 | 中度促销 | 利润承压 | 推新/清库 |
| 60-80% | 2-4.5折 | 强促销 | 利润微薄 | 清仓/爆破 |
| >80% | <2折 | 过度促销 | 亏损风险 | 紧急处理 |

**健康促销评估标准**

✅ 健康促销(30-60%):
- 有一定折扣吸引力
- 保留合理利润空间
- 适合常态化促销

⚠️ 过度促销(>70%):
- 折扣过大（<3折）
- 利润严重受损
- 长期不可持续
- 风险: 损害品牌价值、挤压利润、培养顾客"不促不买"习惯

⚠️ 促销不足(<30%):
- 折扣太小（>7折）
- 竞争力不足
- 难以吸引顾客
- 风险: 滞销库存积压

**促销ROI评估框架**

高效促销（好）:
- 促销强度 30-60% + 动销率 > 60%
- 解读: 中度促销带来良好销售，ROI高

低效促销（差）:
- 促销强度 > 70% 但 动销率 < 40%
- 解读: 强促销仍卖不动，促销无效，亏损严重

过度依赖（风险）:
- 促销强度 > 70% + 销售额占比 > 20%
- 解读: 重度依赖强促销维持销售，利润堪忧

【📊 当前促销数据】

**促销强度分布**:
- 过度促销(>70%): {len(over_promo)}个分类/角色
- 正常促销(30-70%): {len(normal_promo)}个分类/角色
- 促销不足(<30%): {len(low_promo)}个分类/角色

**平均促销强度**: {avg_promo:.1f}%

**TOP10高促销强度明细** (已按促销强度降序排列):
```json
{json.dumps(convert_to_serializable(top10_promo), ensure_ascii=False, indent=2)}
```

【🎯 分析任务】

**第一步：过度促销风险识别**

筛选标准:
1. 促销强度 > 70%（折扣力度 < 3折）
2. 销售额占比 > 5%（依赖度高）

对每个过度促销对象:
1. 💰 利润风险: 折扣X折，促销强度XX%，利润严重受损
2. 📊 销售依赖: 销售额¥XXX，占比XX%，过度依赖促销
3. 🔍 效果评估: 动销率XX%，判断促销是否有效
4. ⚠️ 建议: 
   - 如动销率高(>60%): 尝试减小折扣，测试价格弹性
   - 如动销率低(<40%): 促销无效，考虑下架或重新定位

**第二步：低效促销识别**

筛选标准:
1. 促销强度 > 60%（强促销）
2. 动销率 < 40%（卖不动）

问题诊断:
- 为什么强促销仍卖不动？（商品不对？定位错误？库存积压？）
- 量化损失: 占用多少SKU和库存？
- 建议: 立即止损，考虑清仓或下架

**第三步：促销不足机会识别**

筛选标准:
1. 促销强度 < 30%（轻度或无促销）
2. 动销率 > 80%（卖得好）
3. 销售额占比 < 10%（还有增长空间）

机会分析:
- 不促销也能卖得好 → 商品力强
- 销售额占比低 → 扩品机会
- 建议: 增加SKU或适度促销放大销售

**第四步：促销策略优化建议**

基于以上分析，给出:
1. **减少促销**: 哪些对象促销过度需要收紧？
2. **加强促销**: 哪些对象促销不足可以加大？
3. **停止促销**: 哪些对象促销无效需要止损？
4. **预期效果**: 优化后利润能提升多少？

【⚠️ 输出要求】

1. 必须理解"促销强度 = (10-折扣力度)/9×100%"
2. 必须区分"过度促销"(>70%)和"健康促销"(30-60%)
3. 必须结合动销率评估促销ROI
4. 必须量化利润影响（如"促销强度77.8%，打3折，利润亏损"）
5. 每个建议必须可执行

【📝 输出格式】

## 🔥 促销看板核心洞察

### 1. 促销强度总览
- **平均促销强度**: {avg_promo:.1f}%（对应折扣X.X折）
- **分布统计**:
  * 过度促销(>70%): {len(over_promo)}个，⚠️ 利润风险
  * 正常促销(30-70%): {len(normal_promo)}个，✅ 健康水平
  * 促销不足(<30%): {len(low_promo)}个，💡 可能机会

### 2. 过度促销风险识别（促销强度>70%）
1. **[分类/角色]**: 促销强度XX%（折扣X.X折）
   - 销售额: ¥XXX（占比XX%）
   - 动销率: XX%
   - 风险评估: [高依赖/利润微薄/长期不可持续]
   - 建议: [减小折扣/测试价格弹性/考虑下架]

[其他过度促销对象同上]

### 3. 低效促销识别（强促销但卖不动）
1. **[分类/角色]**: 促销强度XX%，但动销率仅XX%
   - 问题: [商品不对/定位错误/促销无效]
   - 损失: 占用XX个SKU
   - 建议: ⚡立即止损，清仓或下架

### 4. 促销不足机会（轻促销高动销）
1. **[分类/角色]**: 促销强度XX%（几乎无促销），动销率XX%
   - 潜力: 商品力强，不促销也能卖
   - 机会: 销售额占比仅XX%，扩品空间大
   - 建议: 增加XX个SKU或适度促销（促销强度提至30-40%）

### 5. 促销策略优化建议

**减少促销**（收紧过度促销）:
- [对象]: 促销强度从XX%降至XX%，折扣从X折调至X折
- 理由: [XXX]
- 预期: 利润率提升XX%

**加强促销**（放大机会分类）:
- [对象]: 促销强度从XX%提至XX%
- 理由: [XXX]
- 预期: 销售额提升¥XXX

**停止促销**（止损无效促销）:
- [对象]: 立即停止促销或清仓下架
- 理由: 强促销仍动销率<40%，促销无效

## 🎯 优先级行动

**P0紧急**: 停止XX的无效促销，止损（促销强度XX%但动销率<40%）
**P1重点**: 收紧XX的过度促销，提升利润（促销强度>70%）
**P2机会**: 放大XX的促销力度，扩大销售（高动销低促销）

现在开始分析！
"""
        return prompt


class MasterAnalyzer(BasePanelAnalyzer):
    """主AI汇总分析器"""
    
    def analyze(self, dashboard_data: Dict, panel_insights: Dict[str, str] = None) -> str:
        """
        分析完整Dashboard数据并汇总各看板洞察
        
        Args:
            dashboard_data: 完整的dashboard数据字典 (包含kpi, category, price, promo, meta)
            panel_insights: 各看板的AI分析结果 (可选)
            
        Returns:
            综合分析结果
        """
        # 如果没有panel_insights，使用原始数据的synthesize方法
        if not panel_insights:
            panel_insights = {}
        
        # 提取元数据
        meta_data = dashboard_data.get('meta', {})
        
        return self.synthesize(panel_insights, meta_data)
    
    def synthesize(self, panel_insights: Dict[str, str], meta_data: Dict = None) -> str:
        """
        汇总各看板洞察，生成综合诊断
        
        Args:
            panel_insights: 各看板的分析结果字典
                {
                    'kpi': 'KPI看板分析结果',
                    'category': '分类看板分析结果',
                    'price': '价格带看板分析结果',
                    'promo': '促销看板分析结果'
                }
            meta_data: 元数据（门店名称等）
            
        Returns:
            综合分析结果
        """
        prompt = self._build_master_prompt(panel_insights, meta_data)
        return self._generate_content(prompt, temperature=0.8, max_tokens=4000)
    
    def _build_master_prompt(self, panel_insights: Dict[str, str], meta_data: Dict = None) -> str:
        """构建主AI汇总提示词"""
        store_name = meta_data.get('门店', '未知') if meta_data else '未知'
        filter_category = meta_data.get('筛选分类', '全部') if meta_data else '全部'
        
        prompt = f"""
你是一位资深的零售运营总监，现在需要你基于各看板的AI分析结果，生成综合诊断和优化方案。

【门店信息】
- 门店名称: {store_name}
- 筛选条件: {filter_category}

【各看板AI洞察】

## 📊 KPI看板洞察
{panel_insights.get('kpi', '暂无KPI分析')}

---

## 🏪 分类看板洞察
{panel_insights.get('category', '暂无分类分析')}

---

## 💰 价格带看板洞察
{panel_insights.get('price', '暂无价格带分析')}

---

## 🔥 促销看板洞察
{panel_insights.get('promo', '暂无促销分析')}

---

【你的汇总任务】

请基于以上各看板的分析结果，进行跨看板综合诊断：

**1. 整体健康度诊断（100-150字）**
- 综合评估：优秀/健康/预警/危险
- 核心问题总结（从各看板洞察中提炼）
- 一句话总结门店现状

**2. 关联问题识别（2-3个）**
- 识别跨看板的关联问题
  * 例如：KPI显示动销率低 + 分类显示某类动销率差 + 促销显示该类促销不足 → 关联问题：XXX分类缺乏促销导致动销低
- 每个问题必须：
  * 问题描述
  * 涉及看板：[KPI/分类/价格/促销]
  * 量化影响
  * 根因分析

**3. 综合优化方案（按ROI和优先级排序）**

**🚨 P0紧急（本周内执行）**
- 方案1：[名称] (ROI: X.X, 投入¥XXX)
  * 执行内容：[3-5步]
  * 预期效果：[量化]
  * 执行周期：X天

**⚡ P1重点（2周内执行）**
- 方案2：[名称] (ROI: X.X)
  * 执行内容：[3-5步]
  * 预期效果：[量化]

**📈 P2长期（本月内执行）**
- 方案3：[名称]
  * 执行内容：[3-5步]
  * 预期效果：[量化]

**4. 整体效果预估**
- 核心指标变化：
  * 动销率: X% → Y% (+Zpp)
  * 日销售额: +¥XXX
  * 月净利润: +¥XXX
- 整体ROI: X.X

**5. 执行风险提示**
- 风险1：[描述]，应对措施：[XXX]
- 风险2：[描述]，应对措施：[XXX]

【输出格式要求】

请按以下结构输出（600-800字）：

# 🧠 门店综合诊断报告

## 一、整体健康度诊断
[内容]

## 二、关联问题识别
### 问题1: [标题]
[内容]

### 问题2: [标题]
[内容]

## 三、综合优化方案

### 🚨 P0紧急（本周内）
[方案详情]

### ⚡ P1重点（2周内）
[方案详情]

### 📈 P2长期（本月内）
[方案详情]

## 四、效果预估
[内容]

## 五、执行风险
[内容]

---

【重要提示】
1. 必须基于各看板的洞察进行汇总，不要凭空编造
2. 识别跨看板的关联问题（这是主AI的核心价值）
3. 优化方案必须量化ROI和效果
4. 禁止空话套话

现在开始汇总分析！
"""
        return prompt


# 工厂函数
def get_kpi_analyzer(api_key: str = None) -> KPIPanelAnalyzer:
    """获取KPI看板分析器"""
    return KPIPanelAnalyzer(api_key=api_key)


def get_category_analyzer(api_key: str = None) -> CategoryPanelAnalyzer:
    """获取分类看板分析器"""
    return CategoryPanelAnalyzer(api_key=api_key)


def get_price_analyzer(api_key: str = None) -> PricePanelAnalyzer:
    """获取价格带看板分析器"""
    return PricePanelAnalyzer(api_key=api_key)


def get_promo_analyzer(api_key: str = None) -> PromoPanelAnalyzer:
    """获取促销看板分析器"""
    return PromoPanelAnalyzer(api_key=api_key)


def get_master_analyzer(api_key: str = None) -> MasterAnalyzer:
    """获取主AI汇总分析器"""
    return MasterAnalyzer(api_key=api_key)


if __name__ == '__main__':
    print("=" * 60)
    print("看板专项AI分析器模块")
    print("=" * 60)
    print("\n可用分析器：")
    print("1. KPIPanelAnalyzer - KPI看板分析")
    print("2. CategoryPanelAnalyzer - 分类看板分析")
    print("3. PricePanelAnalyzer - 价格带看板分析")
    print("4. PromoPanelAnalyzer - 促销看板分析")
    print("5. MasterAnalyzer - 主AI汇总分析")
    print("\n使用方式：")
    print("analyzer = get_kpi_analyzer()")
    print("result = analyzer.analyze(kpi_data)")
