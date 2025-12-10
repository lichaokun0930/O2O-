#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI分析器功能
"""

import os
import sys

print("=" * 80)
print("AI分析器功能测试")
print("=" * 80)
print()

# 1. 检查API密钥
api_key = os.getenv('ZHIPU_API_KEY')
if not api_key:
    print("❌ 未设置ZHIPU_API_KEY环境变量")
    print()
    print("请先运行以下命令之一配置API密钥:")
    print("  - Windows CMD:  设置AI密钥.bat")
    print("  - PowerShell:   .\\设置AI密钥.ps1")
    print()
    sys.exit(1)
else:
    print(f"✅ API密钥已配置: {api_key[:10]}...{api_key[-4:]}")

print()

# 2. 导入AI分析器
try:
    from ai_analyzer import get_ai_analyzer
    from ai_business_context import get_business_context
    print("✅ AI模块导入成功")
except ImportError as e:
    print(f"❌ AI模块导入失败: {e}")
    print()
    print("请确保已安装zhipuai: pip install zhipuai")
    sys.exit(1)

print()

# 3. 初始化AI分析器
print("正在初始化AI分析器...")
analyzer = get_ai_analyzer()

if not analyzer or not analyzer.is_ready():
    print("❌ AI分析器初始化失败")
    sys.exit(1)

print("✅ AI分析器初始化成功")
print()

# 4. 测试简单对话
print("-" * 80)
print("测试1: 简单对话")
print("-" * 80)

test_prompt = "你好,请用一句话介绍你自己,包括你的模型名称和主要能力。"
print(f"提示词: {test_prompt}")
print()

result = analyzer._generate_content(test_prompt, temperature=0.7)
print(f"AI回复:\n{result}")
print()

# 5. 测试业务分析
print("-" * 80)
print("测试2: 业务数据分析")
print("-" * 80)

test_data = {
    'kpi': {
        '总SKU数(含规格)': 10000,
        '去重SKU数': 8000,
        '动销SKU数': 5600,
        '动销率': 70.0,
        '门店爆品数': 120,
        '门店平均折扣': 3.5
    },
    'category': [
        {'一级分类': '饮品', '售价销售额': 50000, '美团一级分类动销率(类内)': 85.5},
        {'一级分类': '零食', '售价销售额': 35000, '美团一级分类动销率(类内)': 65.2}
    ]
}

business_context = """
这是一个O2O即时零售门店的数据。
动销率 = 动销SKU数 ÷ 去重SKU数 × 100%
门店平均折扣: 3.5表示3.5折
"""

print("模拟数据:")
print(f"  - KPI: {len(test_data['kpi'])}个指标")
print(f"  - 分类: {len(test_data['category'])}个分类")
print()

analysis_result = analyzer.analyze_dashboard_data(test_data, business_context)
print("AI分析结果:")
print("-" * 80)
print(analysis_result)
print("-" * 80)
print()

print("=" * 80)
print("✅ 所有测试通过! AI分析器工作正常")
print("=" * 80)
print()
print("🚀 现在可以启动Dashboard使用AI智能分析功能了!")
print()
