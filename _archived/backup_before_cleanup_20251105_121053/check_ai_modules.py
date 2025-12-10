#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模块配置检查工具
快速诊断是否会触发检索问题
"""

import os
import sys

def check_modules():
    """检查AI模块配置"""
    print("🔍 AI模块配置诊断工具")
    print("=" * 60)
    
    all_ok = True
    
    # 1. 检查纯净版模块
    print("\n📦 检查纯净版模块...")
    try:
        from ai_analyzer_simple import get_ai_analyzer
        print("  ✅ ai_analyzer_simple.py - 可正常导入")
    except ImportError as e:
        print(f"  ❌ ai_analyzer_simple.py - 导入失败: {e}")
        all_ok = False
    
    try:
        from ai_panel_analyzers_simple import get_kpi_analyzer
        print("  ✅ ai_panel_analyzers_simple.py - 可正常导入")
    except ImportError as e:
        print(f"  ❌ ai_panel_analyzers_simple.py - 导入失败: {e}")
        all_ok = False
    
    # 2. 检查dashboard配置
    print("\n⚙️  检查Dashboard配置...")
    try:
        with open('dashboard_v2.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查导入语句
            if 'from ai_analyzer_simple import' in content:
                print("  ✅ 使用纯净版 ai_analyzer_simple")
            elif 'from ai_analyzer import' in content:
                print("  ⚠️  使用旧版 ai_analyzer（会触发检索！）")
                all_ok = False
            else:
                print("  ❓ 未找到AI分析器导入")
                all_ok = False
            
            if 'from ai_panel_analyzers_simple import' in content:
                print("  ✅ 使用纯净版 ai_panel_analyzers_simple")
            elif 'from ai_panel_analyzers import' in content:
                print("  ⚠️  使用旧版 ai_panel_analyzers（会触发检索！）")
                all_ok = False
            
            # 检查是否有向量检索相关代码
            if 'knowledge_retriever' in content:
                print("  ⚠️  Dashboard中仍有向量检索代码残留")
                all_ok = False
            else:
                print("  ✅ 无向量检索代码残留")
                
    except FileNotFoundError:
        print("  ❌ 未找到 dashboard_v2.py 文件")
        all_ok = False
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
        all_ok = False
    
    # 3. 检查旧版模块残留
    print("\n🗑️  检查旧版模块残留...")
    old_modules = {
        'ai_analyzer.py': '旧版AI分析器（会触发检索）',
        'ai_business_context.py': '业务基因库（会被旧版加载）',
        'ai_knowledge_retriever.py': '向量检索引擎（会尝试加载向量库）'
    }
    
    found_old = []
    for module, desc in old_modules.items():
        if os.path.exists(module):
            print(f"  ⚠️  {module} - {desc}")
            found_old.append(module)
        else:
            print(f"  ✅ {module} - 已归档或不存在")
    
    if found_old:
        print(f"\n  💡 建议：将以下文件移到 _archived/ 目录")
        for f in found_old:
            print(f"     - {f}")
        all_ok = False
    
    # 4. 检查向量检索缓存
    print("\n💾 检查向量检索缓存...")
    cache_path = './cache/business_knowledge_vectorstore'
    if os.path.exists(cache_path):
        import shutil
        cache_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, dirnames, filenames in os.walk(cache_path)
            for filename in filenames
        ) / 1024  # KB
        print(f"  ⚠️  向量库缓存存在 ({cache_size:.1f} KB)")
        print(f"     如果不使用向量检索，可删除释放空间")
    else:
        print(f"  ✅ 无向量库缓存（纯净版不需要）")
    
    # 5. 检查Python缓存
    print("\n🔄 检查Python缓存...")
    pycache_dirs = [d for d in os.listdir('.') if d == '__pycache__']
    if pycache_dirs:
        print(f"  ℹ️  发现 __pycache__ 目录")
        print(f"     如遇导入问题，可尝试删除后重启")
    else:
        print(f"  ✅ 无 __pycache__ 目录")
    
    # 6. 测试API配置
    print("\n🔑 检查API配置...")
    api_key = os.getenv('ZHIPU_API_KEY')
    if api_key:
        print(f"  ✅ ZHIPU_API_KEY 已配置 ({api_key[:10]}...)")
    else:
        print(f"  ⚠️  ZHIPU_API_KEY 未配置")
        print(f"     AI分析功能将无法使用")
    
    # 总结
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ 配置正确！不会出现检索问题")
        print("\n可以安全启动:")
        print("  python dashboard_v2.py")
    else:
        print("⚠️  发现配置问题，可能触发检索错误")
        print("\n建议操作:")
        print("  1. 查看上述 ⚠️  标记的问题")
        print("  2. 参考《避免检索问题完全指南.md》")
        print("  3. 运行修复后再次检查")
    print("=" * 60)
    
    return all_ok

def suggest_fixes():
    """建议修复方案"""
    print("\n💡 快速修复建议:\n")
    
    # 检查是否需要修改dashboard
    if os.path.exists('dashboard_v2.py'):
        with open('dashboard_v2.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'from ai_analyzer import' in content:
                print("1️⃣  修改 dashboard_v2.py 导入:")
                print("   找到: from ai_analyzer import get_ai_analyzer")
                print("   改为: from ai_analyzer_simple import get_ai_analyzer")
                print()
    
    # 检查旧版模块
    old_files = [f for f in ['ai_analyzer.py', 'ai_business_context.py'] 
                 if os.path.exists(f)]
    if old_files:
        print("2️⃣  归档旧版模块:")
        print("   mkdir -p _archived/ai_modules_old")
        for f in old_files:
            print(f"   mv {f} _archived/ai_modules_old/")
        print()
    
    # 检查缓存
    if os.path.exists('./cache/business_knowledge_vectorstore'):
        print("3️⃣  清理向量检索缓存（可选）:")
        print("   rm -rf ./cache/business_knowledge_vectorstore")
        print("   # 可释放约420MB空间")
        print()
    
    if os.path.exists('__pycache__'):
        print("4️⃣  清理Python缓存:")
        print("   rm -rf __pycache__")
        print()

if __name__ == '__main__':
    try:
        result = check_modules()
        
        if not result:
            suggest_fixes()
        
        sys.exit(0 if result else 1)
        
    except Exception as e:
        print(f"\n❌ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
