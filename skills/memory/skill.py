"""
memory 技能 - 智能记忆系统（插入式 LLM 版）

Agent Symphony 技能交响乐的记忆中心
基于 Mem0, Letta, Zep 等框架的设计理念

增强特性：
- 插入式 LLM（使用 SharedContext 的 LLMProvider）
- 向量嵌入语义检索
- 混合搜索（语义 + 关键词 + 重要性）
- 技能间互联
"""

import time
import json
import os
import numpy as np
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from agent_symphony.shared import (
    SharedContext,
    get_context,
    CallerInfo,
)


class MemoryType(Enum):
    """记忆类型"""
    PREFERENCE = "preference"      # 用户偏好
    CONTEXT = "context"           # 上下文
    ENTITY = "entity"             # 实体知识
    FACT = "fact"                # 事实
    LEARNED = "learned"          # 学习来的
    SEARCH_RESULT = "search_result"  # 搜索结果


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    type: str
    content: str
    importance: float = 0.5  # 0-1 重要性
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    source: str = "unknown"  # explicit | learned | search
    metadata: dict = field(default_factory=dict)
    # 向量增强字段
    embedding: Optional[np.ndarray] = field(default=None, repr=False)
    content_hash: str = ""  # 用于去重


@dataclass
class MemoryConfig:
    """memory 技能配置"""
    max_memories: int = 1000      # 最大记忆数量
    retention_threshold: float = 0.2  # 遗忘阈值
    recency_weight: float = 0.3    # 时效性权重
    importance_weight: float = 0.4   # 重要性权重
    access_weight: float = 0.3     # 访问频率权重
    default_importance: float = 0.5  # 默认重要性
    # 向量配置
    embedding_dim: int = 384  # 默认维度
    vector_store_path: str = ""  # 向量存储路径（空则用内存）
    top_k: int = 10  # 默认返回数量
    similarity_threshold: float = 0.3  # 相似度阈值
    hybrid_alpha: float = 0.7  # 语义搜索权重（1-关键词权重）


class VectorStore:
    """
    轻量级向量存储
    使用 SQLite + numpy 存储向量，支持余弦相似度搜索
    """
    
    def __init__(self, db_path: str = "", dim: int = 384):
        self.dim = dim
        self.db_path = db_path
        self._memory_store: dict[str, np.ndarray] = {}  # 内存存储
        
        if db_path and os.path.exists(db_path):
            self._load_index()
    
    def _load_index(self):
        """从磁盘加载索引"""
        index_file = self.db_path + ".vec.npz"
        if os.path.exists(index_file):
            data = np.load(index_file, allow_pickle=True)
            self._memory_store = dict(data.items())
    
    def _save_index(self):
        """保存索引到磁盘"""
        if not self.db_path:
            return
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        index_file = self.db_path + ".vec.npz"
        np.savez(index_file, **self._memory_store)
    
    def add(self, id: str, embedding: np.ndarray):
        """添加向量"""
        self._memory_store[id] = embedding.astype(np.float32)
    
    def remove(self, id: str):
        """删除向量"""
        self._memory_store.pop(id, None)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 10, 
               exclude_ids: set = None) -> list[tuple[str, float]]:
        """
        余弦相似度搜索
        返回 [(id, similarity_score), ...]
        """
        if not self._memory_store:
            return []
        
        exclude_ids = exclude_ids or set()
        
        # 批量计算余弦相似度
        ids = []
        vectors = []
        for id_, vec in self._memory_store.items():
            if id_ not in exclude_ids:
                ids.append(id_)
                vectors.append(vec)
        
        if not vectors:
            return []
        
        vectors = np.array(vectors)
        query = query_embedding.astype(np.float32).reshape(1, -1)
        
        # 余弦相似度 = normalize 后点积
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8
        vectors_norm = vectors / norms
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        
        similarities = (vectors_norm @ query_norm.T).flatten()
        
        # 取 top_k
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        return [(ids[i], float(similarities[i])) for i in top_indices]
    
    def save(self):
        """保存到磁盘"""
        self._save_index()

    def clear(self):
        """清空"""
        self._memory_store.clear()
        if self.db_path:
            index_file = self.db_path + ".vec.npz"
            if os.path.exists(index_file):
                os.remove(index_file)


class MemorySkill:
    """
    Memory 技能 - Agent Symphony 的记忆中心（插入式 LLM 版）
    
    核心职责：
    1. 存储记忆（store）- 自动生成并存储向量
    2. 检索记忆（retrieve/query）- 语义相似度搜索
    3. 学习用户偏好（learn）
    4. 智能遗忘（forget）
    5. 上下文管理（context）
    
    插入式 LLM：
    - 使用 SharedContext 的 LLMProvider
    - 自动从环境变量/OpenClaw 配置读取用户的大模型设置
    - skill 不硬编码 API Key
    """

    def __init__(self, config: MemoryConfig | None = None):
        self.config = config or MemoryConfig()
        self._context: SharedContext = get_context()
        self._memories: dict[str, MemoryEntry] = {}  # id -> MemoryEntry
        
        # 初始化向量存储（使用 context.llm 生成嵌入）
        self._vector_store = VectorStore(
            db_path=self.config.vector_store_path,
            dim=self.config.embedding_dim
        )
        
        # 实体索引
        self._entity_index: dict[str, dict] = {}     # entity_type -> entity_id -> MemoryEntry

    # ==================== 标准接口 ====================

    def query(self, capability: str, context: dict | None = None) -> dict:
        """
        查询技能能力
        """
        capability_map = {
            "memory.store": self._store,
            "memory.query": self._query,
            "memory.learn": self._learn,
            "memory.forget": self._forget,
            "memory.preference": self._get_preference,
            "memory.context": self._get_context_memory,
            "memory.semantic_search": self._semantic_search,
        }
        
        if capability not in capability_map:
            return {
                "success": False,
                "error": {
                    "code": "CAPABILITY_NOT_FOUND",
                    "message": f"Capability {capability} not found"
                }
            }
        
        return capability_map[capability](context or {})

    def execute(self, action: str, params: dict) -> dict:
        """
        执行动作
        """
        start_time = time.time()
        
        # 获取调用者信息
        caller: CallerInfo = self._context.get_caller()
        
        try:
            if action == "store":
                result = self._store(params)
            elif action == "retrieve":
                result = self._retrieve(params)
            elif action == "learn":
                result = self._learn(params)
            elif action == "forget":
                result = self._forget(params)
            elif action == "get_preference":
                result = self._get_preference(params)
            elif action == "semantic_search":
                result = self._semantic_search(params)
            elif action == "llm_enhance":
                # LLM 增强的记忆分析
                result = self._llm_enhance(params)
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "ACTION_NOT_FOUND",
                        "message": f"Action {action} not found"
                    }
                }
            
            # 结果路由：如果是技能间调用，返回结构化结果；否则返回完整结果
            if self._context.is_skill_call():
                # 技能间调用：返回给调用者，不输出给用户
                return {
                    "success": True,
                    "data": result,
                    "meta": {
                        "skill": "memory",
                        "action": action,
                        "caller": caller.caller_id,
                        "route_to": caller.caller_id,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                }
            else:
                # 用户直接调用：返回完整结果
                return {
                    "success": True,
                    "data": result,
                    "meta": {
                        "skill": "memory",
                        "action": action,
                        "route_to": "user",
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(e)
                }
            }

    def notify(self, event: str, data: dict):
        """
        接收事件通知
        """
        if event == "search.result":
            self._store_search_result(data)
        elif event == "user.feedback":
            self._learn_from_feedback(data)
        elif event == "team.member.update":
            # team 成员更新了某些内容
            pass

    # ==================== 核心方法 ====================

    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        生成文本向量 - 使用 context 的 LLM Provider
        
        插入式设计：通过 SharedContext 获取用户的大模型配置
        不硬编码 API Key，不管装在哪里都能用
        """
        # 使用 context 的 LLMProvider（自动从环境变量读取）
        embeddings = self._context.get_embeddings(text)
        if isinstance(embeddings, list) and len(embeddings) > 0:
            if isinstance(embeddings[0], list):
                return np.array(embeddings[0], dtype=np.float32)
            return np.array(embeddings, dtype=np.float32)
        # 降级：生成随机向量
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(self.config.embedding_dim).astype(np.float32)
    
    def _generate_content_hash(self, content: str) -> str:
        """生成内容哈希（用于去重）"""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()

    def _store(self, params: dict) -> dict:
        """
        存储记忆（自动生成向量）
        """
        memory_type = params.get("type", MemoryType.CONTEXT.value)
        content = params.get("content", "")
        importance = params.get("importance", self.config.default_importance)
        tags = params.get("tags", [])
        source = params.get("source", "explicit")
        metadata = params.get("metadata", {})
        
        # 内容哈希去重检查
        content_hash = self._generate_content_hash(content)
        existing = [m for m in self._memories.values() if m.content_hash == content_hash]
        if existing:
            # 更新访问时间
            existing[0].accessed_at = time.time()
            existing[0].access_count += 1
            return {
                "stored": False,
                "reason": "duplicate",
                "memory_id": existing[0].id,
                "total_memories": len(self._memories)
            }
        
        # 生成 ID
        memory_id = f"mem_{int(time.time() * 1000)}"
        
        # 生成向量嵌入（使用插入式 LLM）
        embedding = self._generate_embedding(content)
        
        # 创建记忆条目
        entry = MemoryEntry(
            id=memory_id,
            type=memory_type,
            content=content,
            importance=importance,
            tags=tags,
            source=source,
            metadata=metadata,
            embedding=embedding,
            content_hash=content_hash
        )
        
        # 存储
        self._memories[memory_id] = entry
        
        # 添加到向量索引
        self._vector_store.add(memory_id, embedding)
        
        # 如果是实体，更新索引
        if memory_type == MemoryType.ENTITY.value:
            entity_type = metadata.get("entity_type", "unknown")
            entity_id = metadata.get("entity_id", memory_id)
            if entity_type not in self._entity_index:
                self._entity_index[entity_type] = {}
            self._entity_index[entity_type][entity_id] = entry
        
        # 更新上下文引用
        self._context.add_memory(memory_type, content, tags)
        
        # 如果是偏好，更新上下文
        if memory_type == MemoryType.PREFERENCE.value:
            self._context.set_preference(metadata.get("key", memory_id), content)
        
        # 检查是否需要遗忘
        self._maybe_forget()
        
        return {
            "stored": True,
            "memory_id": memory_id,
            "type": memory_type,
            "total_memories": len(self._memories)
        }

    def _query(self, params: dict) -> dict:
        """
        查询记忆 - 混合搜索（语义 + 关键词 + 重要性）
        """
        query_text = params.get("query", "")
        types = params.get("types", None)  # 过滤类型
        limit = params.get("limit", self.config.top_k)
        tags = params.get("tags", None)    # 过滤标签
        alpha = params.get("alpha", self.config.hybrid_alpha)  # 语义权重
        
        if not query_text:
            return {"results": [], "count": 0, "query": ""}
        
        # 获取查询向量
        query_embedding = self._generate_embedding(query_text)
        
        # 向量搜索
        vector_results = self._vector_store.search(
            query_embedding, 
            top_k=limit * 2,  # 多取一些，后面过滤
            exclude_ids=set()
        )
        
        # 构建候选集
        candidate_ids = set(id_ for id_, _ in vector_results)
        
        # 将 vector_results 转为 dict 以便快速查找
        vector_dict = dict(vector_results)
        
        # 过滤类型和标签
        candidates = []
        for id_ in candidate_ids:
            if id_ in self._memories:
                mem = self._memories[id_]
                if types and mem.type not in types:
                    continue
                if tags and not any(t in mem.tags for t in tags):
                    continue
                candidates.append(mem)
        
        # 混合评分
        scored = []
        for mem in candidates:
            # 向量相似度
            vector_score = vector_dict.get(mem.id, 0.0)
            
            # 关键词得分
            keyword_score = self._calculate_keyword_score(mem, query_text)
            
            # 重要性得分
            importance_score = mem.importance
            
            # 综合得分 = alpha * 向量 + (1-alpha) * 关键词 + 重要性
            hybrid_score = (
                alpha * vector_score +
                (1 - alpha) * keyword_score +
                importance_score * 0.2
            )
            
            scored.append((hybrid_score, mem))
        
        # 排序
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # 限制数量
        results = scored[:limit]
        
        # 更新访问信息
        for score, mem in results:
            mem.accessed_at = time.time()
            mem.access_count += 1
        
        return {
            "results": [
                {
                    "id": mem.id,
                    "type": mem.type,
                    "content": mem.content,
                    "importance": mem.importance,
                    "tags": mem.tags,
                    "score": score,
                    "vector_score": vector_results.get(mem.id, 0.0),
                    "created_at": mem.created_at
                }
                for score, mem in results
            ],
            "count": len(results),
            "query": query_text,
            "search_mode": "hybrid"
        }

    def _semantic_search(self, params: dict) -> dict:
        """
        纯语义搜索（不使用关键词）
        """
        query_text = params.get("query", "")
        limit = params.get("limit", self.config.top_k)
        threshold = params.get("threshold", self.config.similarity_threshold)
        
        if not query_text:
            return {"results": [], "count": 0, "query": ""}
        
        # 获取查询向量
        query_embedding = self._generate_embedding(query_text)
        
        # 向量搜索
        vector_results = self._vector_store.search(
            query_embedding,
            top_k=limit * 2,
            exclude_ids=set()
        )
        
        # 过滤阈值
        results = []
        for id_, score in vector_results:
            if score >= threshold and id_ in self._memories:
                mem = self._memories[id_]
                results.append({
                    "id": mem.id,
                    "type": mem.type,
                    "content": mem.content,
                    "importance": mem.importance,
                    "tags": mem.tags,
                    "score": score,
                    "created_at": mem.created_at
                })
                if len(results) >= limit:
                    break
        
        return {
            "results": results,
            "count": len(results),
            "query": query_text,
            "search_mode": "semantic"
        }

    def _retrieve(self, params: dict) -> dict:
        """
        检索记忆（简化版查询）
        """
        return self._query(params)

    def _learn(self, params: dict) -> dict:
        """
        从交互中学习用户偏好
        """
        interaction = params.get("interaction", "")
        inferred_preference = params.get("preference", {})
        
        learned_count = 0
        
        # 从交互中学习
        if "喜欢" in interaction or "不喜欢" in interaction:
            learned_count += 1
        
        # 存储学习到的偏好
        for key, value in inferred_preference.items():
            self._store({
                "type": MemoryType.PREFERENCE.value,
                "content": str(value),
                "importance": 0.7,
                "tags": ["learned", key],
                "source": "learned",
                "metadata": {"key": key}
            })
            learned_count += 1
        
        # 如果启用了 LLM，用 LLM 分析交互提取偏好
        if interaction and self._context.llm.api_key:
            preference_text = self._call_llm_analyze(interaction)
            if preference_text:
                self._store({
                    "type": MemoryType.LEARNED.value,
                    "content": preference_text,
                    "importance": 0.6,
                    "tags": ["llm_learned"],
                    "source": "learned"
                })
                learned_count += 1
        
        return {
            "learned": True,
            "learned_count": learned_count,
            "total_memories": len(self._memories)
        }

    def _llm_enhance(self, params: dict) -> dict:
        """
        使用 LLM 增强记忆分析
        """
        memory_ids = params.get("memory_ids", [])
        task = params.get("task", "analyze")  # analyze | summarize | extract_entities
        
        if not self._context.llm.api_key:
            return {"success": False, "error": "LLM not available"}
        
        memories = []
        for mid in memory_ids:
            if mid in self._memories:
                memories.append(self._memories[mid])
        
        if not memories:
            return {"success": False, "error": "No memories found"}
        
        # 构造 prompt
        memory_text = "\n".join([f"- [{m.type}] {m.content}" for m in memories])
        
        if task == "analyze":
            prompt = f"""分析以下记忆，识别：
1. 共同主题
2. 用户偏好
3. 潜在意图

记忆：
{memory_text}

输出 JSON 格式：
{{"themes": [...], "preferences": [...], "intentions": [...]}}
"""
        elif task == "summarize":
            prompt = f"""总结以下记忆的核心内容：

{memory_text}

输出简洁的总结（不超过 100 字）：
"""
        else:
            prompt = f"""从以下记忆中提取实体和关系：

{memory_text}

输出 JSON 格式：
{{"entities": [...], "relations": [...]}}
"""
        
        result = self._context.call_llm(prompt)
        
        return {
            "success": True,
            "task": task,
            "memories_analyzed": len(memories),
            "result": result
        }

    def _call_llm_analyze(self, text: str) -> str:
        """调用 LLM 分析文本"""
        prompt = f"""从以下文本中提取用户偏好：

{text}

只输出偏好内容，不要解释。如果无法提取，输出空字符串。
"""
        return self._context.call_llm(prompt)

    def _forget(self, params: dict) -> dict:
        """
        主动遗忘
        """
        memory_id = params.get("memory_id")
        
        if memory_id and memory_id in self._memories:
            # 从向量索引删除
            self._vector_store.remove(memory_id)
            # 从记忆字典删除
            del self._memories[memory_id]
            return {
                "forgotten": True,
                "memory_id": memory_id,
                "total_memories": len(self._memories)
            }
        
        return {
            "forgotten": False,
            "reason": "Memory not found"
        }

    def _get_preference(self, params: dict) -> dict:
        """
        获取用户偏好
        """
        key = params.get("key")
        
        if key:
            # 获取特定偏好
            value = self._context.get_preference(key)
            return {
                "key": key,
                "value": value
            }
        
        # 获取所有偏好
        preferences = self._context.memory.preferences
        return {
            "preferences": preferences,
            "count": len(preferences)
        }

    def _get_context_memory(self, params: dict) -> dict:
        """
        获取上下文相关记忆
        """
        limit = params.get("limit", 10)
        memory_type = params.get("type")
        
        memories = self._context.get_recent_memories(
            limit=limit,
            memory_type=memory_type
        )
        
        return {
            "memories": memories,
            "count": len(memories)
        }

    def _store_search_result(self, data: dict):
        """
        存储搜索结果（被 search 技能调用）
        """
        query = data.get("query", "")
        results = data.get("results", [])
        
        # 存储查询
        self._store({
            "type": MemoryType.SEARCH_RESULT.value,
            "content": f"搜索: {query}",
            "importance": 0.4,
            "tags": ["search", query],
            "source": "search",
            "metadata": {
                "query": query,
                "result_count": len(results)
            }
        })
        
        # 存储有价值的搜索结果
        for i, result in enumerate(results[:3]):  # 只存储前3个
            self._store({
                "type": MemoryType.FACT.value,
                "content": result.get("content", str(result)),
                "importance": 0.5,
                "tags": ["search_result", query],
                "source": "search",
                "metadata": {
                    "query": query,
                    "url": result.get("url", ""),
                    "title": result.get("title", "")
                }
            })

    def _learn_from_feedback(self, data: dict):
        """
        从用户反馈中学习
        """
        feedback = data.get("feedback", "")
        task_result = data.get("task_result", {})
        
        # 如果用户纠正了什么，学习它
        if "不对" in feedback or "错了" in feedback:
            self._store({
                "type": MemoryType.LEARNED.value,
                "content": f"纠正: {feedback}",
                "importance": 0.8,
                "tags": ["correction"],
                "source": "learned"
            })

    # ==================== 辅助方法 ====================

    def _calculate_keyword_score(self, memory: MemoryEntry, query: str) -> float:
        """
        计算关键词匹配得分
        """
        query_words = set(query.lower().split())
        content_words = set(memory.content.lower().split())
        
        if not query_words:
            return 0.0
        
        overlap = query_words & content_words
        return len(overlap) / max(len(query_words), 1)

    def _maybe_forget(self):
        """
        检查是否需要遗忘（当记忆过多时）
        """
        if len(self._memories) <= self.config.max_memories:
            return
        
        # 计算每个记忆的遗忘得分
        scored = []
        for mem in self._memories.values():
            score = self._calculate_forget_score(mem)
            scored.append((score, mem.id))
        
        # 排序
        scored.sort(key=lambda x: x[0])
        
        # 删除最低分的记忆（删除 10%）
        delete_count = len(scored) // 10
        for _, mem_id in scored[:delete_count]:
            self._vector_store.remove(mem_id)
            del self._memories[mem_id]

    def _calculate_forget_score(self, memory: MemoryEntry) -> float:
        """
        计算遗忘得分（越低越容易被遗忘）
        """
        # 低访问频率
        access_score = min(1.0, memory.access_count / 5)
        
        # 低重要性
        importance_score = memory.importance
        
        # 久远
        age_days = (time.time() - memory.created_at) / (24 * 3600)
        age_score = max(0.0, 1.0 - age_days / 30)  # 30天完全衰减
        
        # 综合（越低越容易被遗忘）
        return access_score * 0.3 + importance_score * 0.3 + age_score * 0.4

    def _update_access(self, memory_id: str):
        """更新访问信息"""
        if memory_id in self._memories:
            mem = self._memories[memory_id]
            mem.accessed_at = time.time()
            mem.access_count += 1

    # ==================== 生命周期方法 ====================

    def save_index(self):
        """保存向量索引到磁盘"""
        self._vector_store.save()

    def clear_all(self):
        """清空所有记忆"""
        self._memories.clear()
        self._vector_store.clear()
        self._entity_index.clear()


def get_skill_instance(config: MemoryConfig | None = None) -> MemorySkill:
    """获取 memory 技能实例"""
    return MemorySkill(config=config)