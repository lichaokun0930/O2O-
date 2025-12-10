#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试API详细信息"""

import os
import json
from zhipuai import ZhipuAI

# 设置API密钥
api_key = "9f6f4134b7854fff87297a183a6dd0f9.ntVxfTOqYgmr7dCQ"

print("=" * 80)
print("智谱AI API详细信息测试")
print("=" * 80)

# 1. 创建客户端
client = ZhipuAI(api_key=api_key)

print("\n【配置信息】")
print(f"API密钥: {api_key[:20]}...{api_key[-10:]}")
print(f"SDK默认base_url: {client.base_url if hasattr(client, 'base_url') else '(SDK内部管理)'}")

# 2. 测试API调用
print("\n【API调用参数】")
model_name = 'glm-4-plus'
print(f"model参数值: '{model_name}'")

print("\n【发送测试请求】")
print("提示词: 你好，请用一句话介绍你自己，包括你的模型名称")

try:
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "user", "content": "你好，请用一句话介绍你自己，包括你的模型名称"}
        ],
        temperature=0.7,
        max_tokens=100
    )
    
    print("\n【返回的完整响应对象】")
    print("=" * 80)
    
    # 尝试获取原始JSON
    if hasattr(response, 'model_dump_json'):
        raw_json = response.model_dump_json(indent=2)
        print(raw_json)
        
        # 解析JSON
        response_dict = json.loads(raw_json)
        
        print("\n【关键字段提取】")
        print("=" * 80)
        print(f"✅ 返回的model字段: '{response_dict.get('model', 'N/A')}'")
        print(f"✅ id: {response_dict.get('id', 'N/A')}")
        print(f"✅ created: {response_dict.get('created', 'N/A')}")
        print(f"✅ object: {response_dict.get('object', 'N/A')}")
        
    elif hasattr(response, 'model_dump'):
        response_dict = response.model_dump()
        print(json.dumps(response_dict, indent=2, ensure_ascii=False))
        
        print("\n【关键字段提取】")
        print("=" * 80)
        print(f"✅ 返回的model字段: '{response_dict.get('model', 'N/A')}'")
    
    else:
        # 手动访问属性
        print(f"Response对象类型: {type(response)}")
        print(f"可用属性: {dir(response)}")
        
        print("\n【关键字段提取】")
        print("=" * 80)
        print(f"✅ 返回的model字段: '{response.model if hasattr(response, 'model') else 'N/A'}'")
        print(f"✅ id: {response.id if hasattr(response, 'id') else 'N/A'}")
        print(f"✅ created: {response.created if hasattr(response, 'created') else 'N/A'}")
        print(f"✅ object: {response.object if hasattr(response, 'object') else 'N/A'}")
    
    print("\n【AI回复内容】")
    print("=" * 80)
    print(response.choices[0].message.content)
    
    print("\n【请求-响应总结】")
    print("=" * 80)
    print(f"请求时使用的model参数: '{model_name}'")
    print(f"响应中返回的model字段: '{response.model if hasattr(response, 'model') else 'N/A'}'")
    
    if hasattr(response, 'model'):
        if response.model == model_name:
            print("✅ 响应中的model字段与请求参数一致")
        else:
            print(f"⚠️ 响应中的model字段({response.model})与请求参数({model_name})不一致")
    
except Exception as e:
    print(f"\n❌ 请求失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("测试完成")
print("=" * 80)
