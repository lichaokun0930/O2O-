"""
AI业务知识向量检索模块
Phase 1: 增强现有方案 - 向量检索集成

功能:
1. 将2500行业务知识库向量化
2. 根据用户问题自动检索相关知识
3. 智能注入到提示词中

作者: AI Assistant
日期: 2024年10月27日
版本: v1.0
"""

import os
import pickle
from typing import List, Dict, Optional
from pathlib import Path

# 向量检索相关 - 延迟导入避免启动阻塞
VECTOR_SEARCH_AVAILABLE = False
_langchain_modules = None

def _lazy_load_langchain():
    """延迟加载langchain模块"""
    global VECTOR_SEARCH_AVAILABLE, _langchain_modules
    if _langchain_modules is not None:
        return _langchain_modules
    
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import FAISS
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        _langchain_modules = {
            'RecursiveCharacterTextSplitter': RecursiveCharacterTextSplitter,
            'FAISS': FAISS,
            'HuggingFaceEmbeddings': HuggingFaceEmbeddings
        }
        VECTOR_SEARCH_AVAILABLE = True
        print("✅ 向量检索模块已加载")
        return _langchain_modules
    except ImportError as e:
        VECTOR_SEARCH_AVAILABLE = False
        print(f"⚠️ 向量检索依赖未安装,使用基础模式: {e}")
        return None


class BusinessKnowledgeRetriever:
    """业务知识向量检索器"""
    
    def __init__(self, cache_dir: str = "./cache"):
        """
        初始化检索器
        
        Args:
            cache_dir: 向量库缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.vectorstore = None
        self.embeddings = None
        
        if VECTOR_SEARCH_AVAILABLE:
            self._init_embeddings()
            self._load_or_build_vectorstore()
        else:
            print("⚠️ 向量检索不可用,将使用全量业务知识")
    
    def _init_embeddings(self):
        """初始化中文向量模型"""
        print("🔧 初始化中文向量模型...")
        
        # 使用轻量级中文向量模型
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        print("✅ 向量模型加载完成")
    
    def _load_or_build_vectorstore(self):
        """加载或构建向量库"""
        vectorstore_path = self.cache_dir / "business_knowledge_vectorstore"
        
        # 检查缓存是否存在
        if vectorstore_path.exists():
            try:
                print("📦 加载已缓存的向量库...")
                self.vectorstore = FAISS.load_local(
                    str(vectorstore_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print("✅ 向量库加载成功")
                return
            except Exception as e:
                print(f"⚠️ 加载向量库失败: {e}")
                print("🔄 重新构建向量库...")
        
        # 构建新的向量库
        self._build_vectorstore()
        
        # 保存向量库
        if self.vectorstore:
            try:
                self.vectorstore.save_local(str(vectorstore_path))
                print(f"💾 向量库已保存到: {vectorstore_path}")
            except Exception as e:
                print(f"⚠️ 保存向量库失败: {e}")
    
    def _build_vectorstore(self):
        """构建向量库"""
        print("🏗️ 构建业务知识向量库...")
        
        # 加载业务知识
        from ai_business_context import BUSINESS_CONTEXT
        
        # 文本分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # 每块500字符
            chunk_overlap=50,  # 重叠50字符
            separators=["\n\n", "\n", "。", "!", "?", ";", "；", "!", "?", ",", "、", " "],
            keep_separator=True
        )
        
        chunks = text_splitter.split_text(BUSINESS_CONTEXT)
        print(f"📄 业务知识已分块: {len(chunks)} 个片段")
        
        # 构建向量库
        self.vectorstore = FAISS.from_texts(
            texts=chunks,
            embedding=self.embeddings,
            metadatas=[{"source": f"chunk_{i}"} for i in range(len(chunks))]
        )
        print("✅ 向量库构建完成")
    
    def retrieve_relevant_knowledge(
        self, 
        query: str, 
        top_k: int = 5,
        score_threshold: float = 0.3
    ) -> List[str]:
        """
        检索相关业务知识
        
        Args:
            query: 用户查询
            top_k: 返回最相关的K个片段
            score_threshold: 相似度阈值(0-1)
        
        Returns:
            相关知识片段列表
        """
        if not VECTOR_SEARCH_AVAILABLE or not self.vectorstore:
            # 降级到全量知识
            from ai_business_context import BUSINESS_CONTEXT
            return [BUSINESS_CONTEXT[:3000]]  # 返回前3000字符
        
        try:
            # 相似度搜索
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query, 
                k=top_k
            )
            
            # 过滤低相关度结果
            relevant_docs = [
                doc.page_content 
                for doc, score in docs_with_scores 
                if score < (1 - score_threshold)  # FAISS距离越小越相似
            ]
            
            if not relevant_docs:
                print(f"⚠️ 未找到相关知识(阈值={score_threshold}),使用默认知识")
                from ai_business_context import BUSINESS_CONTEXT
                return [BUSINESS_CONTEXT[:3000]]
            
            print(f"✅ 检索到 {len(relevant_docs)} 个相关知识片段")
            return relevant_docs
            
        except Exception as e:
            print(f"❌ 向量检索失败: {e}")
            # 降级到全量知识
            from ai_business_context import BUSINESS_CONTEXT
            return [BUSINESS_CONTEXT[:3000]]
    
    def get_contextual_knowledge(
        self,
        query: str,
        analysis_type: Optional[str] = None
    ) -> str:
        """
        获取上下文相关的业务知识
        
        Args:
            query: 用户查询或分析任务
            analysis_type: 分析类型(如"健康度诊断"、"商品角色识别"等)
        
        Returns:
            组合后的业务知识文本
        """
        # 构建增强查询
        enhanced_query = query
        if analysis_type:
            enhanced_query = f"{analysis_type}: {query}"
        
        # 检索相关知识
        relevant_chunks = self.retrieve_relevant_knowledge(
            enhanced_query, 
            top_k=5,
            score_threshold=0.3
        )
        
        # 组合知识片段
        combined_knowledge = "\n\n---\n\n".join(relevant_chunks)
        
        return combined_knowledge
    
    def rebuild_vectorstore(self):
        """强制重建向量库(当业务知识更新时调用)"""
        print("🔄 强制重建向量库...")
        
        # 删除旧缓存
        vectorstore_path = self.cache_dir / "business_knowledge_vectorstore"
        if vectorstore_path.exists():
            import shutil
            shutil.rmtree(vectorstore_path)
            print("🗑️ 已删除旧向量库")
        
        # 重新构建
        if VECTOR_SEARCH_AVAILABLE:
            self._build_vectorstore()
            
            # 保存新向量库
            if self.vectorstore:
                self.vectorstore.save_local(str(vectorstore_path))
                print("✅ 新向量库已构建并保存")
        else:
            print("⚠️ 向量检索不可用")


# 全局单例
_retriever_instance = None

def get_knowledge_retriever() -> BusinessKnowledgeRetriever:
    """获取业务知识检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = BusinessKnowledgeRetriever()
    return _retriever_instance


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 测试业务知识向量检索")
    print("=" * 60)
    
    # 初始化检索器
    retriever = get_knowledge_retriever()
    
    # 测试查询
    test_queries = [
        "什么是流量品?如何定价?",
        "动销率低于60%怎么办?",
        "如何计算促销强度?",
        "商品成本占比超过70%是否健康?",
        "爆品集中度过高有什么风险?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"📝 测试查询 {i}: {query}")
        print(f"{'='*60}")
        
        knowledge = retriever.get_contextual_knowledge(query)
        print(f"\n检索结果 ({len(knowledge)} 字符):")
        print("-" * 60)
        print(knowledge[:500] + "..." if len(knowledge) > 500 else knowledge)
        print("-" * 60)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
