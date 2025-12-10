"""测试Phase 1增强功能"""
import os
os.environ['ZHIPU_API_KEY'] = '9f6f4134b7854fff87297a183a6dd0f9.ntVxfTOqYgmr7dCQ'

print("=" * 60)
print("🧪 Phase 1增强功能测试")
print("=" * 60)

# 1. 测试向量检索器
print("\n1️⃣ 测试向量检索器...")
try:
    from ai_knowledge_retriever import get_knowledge_retriever, VECTOR_SEARCH_AVAILABLE
    
    print(f"向量检索可用性: {'✅ 可用' if VECTOR_SEARCH_AVAILABLE else '⚠️ 降级模式'}")
    
    retriever = get_knowledge_retriever()
    print(f"检索器状态: {'✅ 已初始化' if retriever else '❌ 失败'}")
    
    if retriever:
        # 测试检索
        test_query = "动销率低于60%怎么办?"
        knowledge = retriever.get_contextual_knowledge(test_query)
        print(f"✅ 检索成功: {len(knowledge)} 字符")
        print(f"示例: {knowledge[:200]}...")
    
except Exception as e:
    print(f"❌ 向量检索器测试失败: {e}")
    import traceback
    traceback.print_exc()

# 2. 测试AI分析器集成
print("\n2️⃣ 测试AI分析器集成...")
try:
    from ai_analyzer import get_ai_analyzer, VECTOR_RETRIEVAL_ENABLED
    
    print(f"向量检索集成: {'✅ 已集成' if VECTOR_RETRIEVAL_ENABLED else '⚠️ 未集成'}")
    
    analyzer = get_ai_analyzer()
    print(f"AI分析器状态: {'✅ 就绪' if analyzer.is_ready() else '❌ 未就绪'}")
    
    if analyzer.is_ready():
        print(f"向量检索器: {'✅ 已加载' if analyzer.knowledge_retriever else '⚠️ 未加载'}")
    
except Exception as e:
    print(f"❌ AI分析器测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ 测试完成!")
print("=" * 60)
