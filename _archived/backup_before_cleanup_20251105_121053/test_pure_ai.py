#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试纯净版AI分析器
"""

import os
import sys

# 确保导入路径正确
sys.path.insert(0, os.path.dirname(__file__))

from ai_panel_analyzers_simple import get_kpi_analyzer

def test_kpi_analyzer():
    """测试KPI分析器"""
    print("=" * 60)
    print("测试纯净版KPI分析器")
    print("=" * 60)
    
    # 检查API密钥
    api_key = os.getenv('ZHIPU_API_KEY')
    if not api_key:
        print("❌ 未设置ZHIPU_API_KEY环境变量")
        print("请运行: .\\设置AI密钥.bat")
        return False
    
    print(f"✅ API密钥已配置: {api_key[:10]}...")
    
    # 获取分析器
    print("\n正在初始化KPI分析器...")
    analyzer = get_kpi_analyzer()
    
    if not analyzer:
        print("❌ 分析器初始化失败")
        return False
    
    print("✅ 分析器初始化成功")
    
    # 测试数据
    test_kpi = {
        '动销率': 65.5,
        '滞销占比': 34.5,
        '去重SKU数': 150,
        '售价销售额': 125000.0,
        '平均售价': 35.5,
        '平均折扣': 8.5,
        '爆品数': 12,
        '爆品占比': 8.0
    }
    
    print("\n测试数据:")
    for key, value in test_kpi.items():
        print(f"  {key}: {value}")
    
    # 调用分析
    print("\n正在调用AI分析...")
    result = analyzer.analyze(test_kpi)
    
    print("\n" + "=" * 60)
    print("AI分析结果:")
    print("=" * 60)
    print(result)
    print("=" * 60)
    
    if "❌" in result or "未就绪" in result:
        print("\n❌ 分析失败")
        return False
    
    print("\n✅ 测试通过！")
    return True


if __name__ == '__main__':
    success = test_kpi_analyzer()
    sys.exit(0 if success else 1)
