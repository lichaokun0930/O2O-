#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三个版本快速验证工具
"""

import os
import sys

os.environ['ZHIPU_API_KEY'] = '9f6f4134b7854fff87297a183a6dd0f9.ntVxfTOqYgmr7dCQ'

print("=" * 80)
print("三个版本验证测试")
print("=" * 80)

# 测试1: 纯GLM版
print("\n1️⃣ 测试纯GLM版本")
print("-" * 80)
os.environ['USE_PURE_GLM'] = '1'
os.environ['ENABLE_VECTOR_RETRIEVAL'] = '0'

# 重新导入
if 'ai_analyzer' in sys.modules:
    del sys.modules['ai_analyzer']

from ai_analyzer import get_ai_analyzer, VECTOR_RETRIEVAL_ENABLED

try:
    print(f"向量检索: {VECTOR_RETRIEVAL_ENABLED}")
    analyzer = get_ai_analyzer()
    print(f"分析器状态: {'✅ 就绪' if analyzer and analyzer.is_ready() else '❌ 未就绪'}")
    if analyzer:
        print(f"模型: {analyzer.model_name}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 测试2: 基础版
print("\n2️⃣ 测试基础版本")
print("-" * 80)
os.environ['USE_PURE_GLM'] = '0'
os.environ['ENABLE_VECTOR_RETRIEVAL'] = '0'

if 'ai_analyzer' in sys.modules:
    del sys.modules['ai_analyzer']

from ai_analyzer import get_ai_analyzer as get_ai_analyzer2, VECTOR_RETRIEVAL_ENABLED as VR2

try:
    print(f"向量检索: {VR2}")
    analyzer2 = get_ai_analyzer2()
    print(f"分析器状态: {'✅ 就绪' if analyzer2 and analyzer2.is_ready() else '❌ 未就绪'}")
    if analyzer2:
        print(f"模型: {analyzer2.model_name}")
except Exception as e:
    print(f"❌ 错误: {e}")

# 测试3: 增强版(不实际加载,只检测)
print("\n3️⃣ 测试增强版本(检测缓存)")
print("-" * 80)

import pathlib
cache_path = pathlib.Path("./cache/business_knowledge_vectorstore")
model_cache = pathlib.Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"

print(f"向量库缓存: {'✅ 存在' if cache_path.exists() else '❌ 不存在'}")
print(f"嵌入模型缓存: {'✅ 存在' if model_cache.exists() else '❌ 不存在'}")

if cache_path.exists() and model_cache.exists():
    print("✅ 增强版已预热,可直接使用")
else:
    print("⚠️  增强版需要预热,运行: 启用向量检索.bat")

print("\n" + "=" * 80)
print("✅ 验证完成!")
print("=" * 80)
print("\n📋 启动脚本:")
print("  - 纯GLM版: 启动Dashboard_纯GLM版.bat")
print("  - 基础版: 启动Dashboard.bat")
print("  - 增强版: 启动Dashboard_AI增强版.bat")
