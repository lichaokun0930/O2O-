#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看SDK的base_url配置"""

from zhipuai import ZhipuAI
import inspect

client = ZhipuAI(api_key='test_key')

print("=" * 80)
print("ZhipuAI SDK配置信息")
print("=" * 80)

print(f"\nZhipuAI类定义位置: {inspect.getfile(ZhipuAI)}")

print("\n【客户端关键属性】")
for attr in ['base_url', 'api_base', '_base_url', 'api_key', 'api_url']:
    if hasattr(client, attr):
        value = getattr(client, attr)
        print(f"  {attr}: {value}")

print("\n【所有公开属性】")
public_attrs = [a for a in dir(client) if not a.startswith('_')]
for attr in public_attrs[:20]:  # 只显示前20个
    print(f"  - {attr}")

# 检查内部属性
print("\n【检查私有属性中的URL配置】")
for attr in dir(client):
    if 'url' in attr.lower() or 'base' in attr.lower():
        try:
            value = getattr(client, attr)
            if isinstance(value, str):
                print(f"  {attr}: {value}")
        except:
            pass

print("\n" + "=" * 80)
