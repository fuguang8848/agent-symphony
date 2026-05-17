"""
共享上下文 - 技能间传递信息

Agent Symphony 技能交响乐的核心组件
提供跨技能的上下文共享能力
支持插入式 LLM、结果路由、技能互联
"""

import os
import time
import uuid
from typing import Any, Literal, Callable
from dataclasses import dataclass, field
from datetime import datetime


# ==================== LLM Provider ====================

class LLMProvider:
    """
    插入式 LLM 提供者
    
    自动从环境变量/OpenClaw 配置读取用户的大模型设置
    skill 不硬编码 API Key，从这里获取
    """
    
    # 支持的提供商
    PROVIDERS = {
        "openai": {
            "env_keys": ["OPENAI_API_KEY", "OPENAI_BASE_URL"],
            "default_model": "gpt-4o-mini",
            "embed_model": "text-embedding-3-small"
        },
        "bailian": {
            "env_keys": ["DASHSCOPE_API_KEY", "OPENAI_BASE_URL"],
            "default_model": "qwen-plus",
            "embed_model": "text-embedding-v2"
        },
        "minimax": {
            "env_keys": ["MINIMAX_API_KEY", "MINIMAX_BASE_URL"],
            "default_model": "MiniMax-M2.7",
            "embed_model": "emb Model"
        },
        "deepseek": {
            "env_keys": ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL"],
            "default_model": "deepseek-chat",
            "embed_model": "text-embedding-3"
        },
        "local": {
            "env_keys": ["LOCAL_LLM_BASE_URL", "LOCAL_LLM_API_KEY"],
            "default_model": "local-model",
            "embed_model": "local-embed"
        }
    }
    
    def __init__(self, provider: str | None = None):
        self._provider = provider or self._detect_provider()
        self._client = None
        self._embedding_client = None
    
    def _detect_provider(self) -> str:
        """自动检测提供商"""
        # 检查环境变量
        for provider, config in self.PROVIDERS.items():
            for env_key in config["env_keys"]:
                if os.environ.get(env_key):
                    return provider
        return "openai"  # 默认
    
    def _get_provider_config(self) -> dict:
        """获取提供商配置"""
        return self.PROVIDERS.get(self._provider, self.PROVIDERS["openai"])
    
    @property
    def api_key(self) -> str:
        """获取 API Key"""
        config = self._get_provider_config()
        for env_key in config["env_keys"]:
            if key := os.environ.get(env_key):
                return key
        # 尝试通用的
        return os.environ.get("OPENAI_API_KEY", os.environ.get("API_KEY", ""))
    
    @property
    def base_url(self) -> str:
        """获取 Base URL"""
        config = self._get_provider_config()
        for env_key in config["env_keys"]:
            if key := os.environ.get(env_key.replace("_KEY", "_BASE_URL")):
                return key
        # 默认 OpenAI
        return os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    @property
    def model(self) -> str:
        """获取默认模型"""
        config = self._get_provider_config()
        return os.environ.get("LLM_MODEL", config["default_model"])
    
    @property
    def embed_model(self) -> str:
        """获取嵌入模型"""
        config = self._get_provider_config()
        return os.environ.get("EMBED_MODEL", config["embed_model"])
    
    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """
        调用 LLM 完成文本
        
        Args:
            prompt: 用户提示
            system: 系统提示
            **kwargs: 其他参数 (temperature, max_tokens 等)
        
        Returns:
            LLM 生成的文本
        """
        # 延迟导入避免循环
        try:
            from openai import OpenAI
        except ImportError:
            return "[LLM not available - openai not installed]"
        
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[LLM Error: {str(e)}]"
    
    def embed(self, texts: str | list[str]) -> list[float] | list[list[float]]:
        """
        获取文本嵌入
        
        Args:
            texts: 单个文本或文本列表
        
        Returns:
            嵌入向量
        """
        try:
            from openai import OpenAI
        except ImportError:
            # 返回假的嵌入
            if isinstance(texts, str):
                return [0.0] * 384
            return [[0.0] * 384 for _ in texts]
        
        if self._embedding_client is None:
            self._embedding_client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        try:
            response = self._embedding_client.embeddings.create(
                model=self.embed_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if isinstance(texts, str):
                return [0.0] * 384
            return [[0.0] * 384 for _ in texts]
    
    def __repr__(self):
        return f"LLMProvider(provider={self._provider}, model={self.model})"


# ==================== 调用者信息 ====================

@dataclass
class CallerInfo:
    """调用者信息"""
    caller_id: str = "user"           # user | thinking | search | memory | team | member_xxx
    caller_type: str = "external"      # external | skill | member
    intent: str = ""                   # 调用意图
    callback: Any = None               # 回调函数（用于返回结果给调用者）


# ==================== 任务定义 ====================

@dataclass
class Task:
    """任务定义"""
    id: str
    status: str  # pending / planning / executing / completed / failed
    description: str
    plan: list[dict] | None = None
    result: Any = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


# ==================== 思考状态 ====================

@dataclass
class ThinkingState:
    """思考状态"""
    phase: str  # understanding / planning / executing / reflection
    questions: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    plan_confirmed: bool = False


# ==================== 记忆引用 ====================

@dataclass
class MemoryRef:
    """记忆引用"""
    recent: list[dict] = field(default_factory=list)
    preferences: dict = field(default_factory=dict)
    entities: dict = field(default_factory=dict)
    learned_count: int = 0


# ==================== 搜索状态 ====================

@dataclass
class SearchState:
    """搜索状态"""
    query: str = ""
    results: list[dict] = field(default_factory=list)
    cached: bool = False
    last_search: float = 0


# ==================== 技能注册 ====================

class SkillRegistry:
    """技能注册表 - 用于技能间调用"""
    
    def __init__(self):
        self._skills: dict[str, Any] = {}
        self._callbacks: dict[str, Callable] = {}
    
    def register(self, skill_name: str, skill_instance: Any):
        """注册技能实例"""
        self._skills[skill_name] = skill_instance
    
    def get(self, skill_name: str) -> Any | None:
        """获取技能实例"""
        return self._skills.get(skill_name)
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        self._callbacks[event] = callback
    
    def trigger_callback(self, event: str, data: dict):
        """触发回调"""
        if callback := self._callbacks.get(event):
            callback(data)


# ==================== 共享上下文 ====================

class SharedContext:
    """
    跨技能共享上下文
    
    用于在技能间传递信息，支持以下场景：
    - thinking 调用 memory 时传递上下文
    - thinking 调用 search 时传递上下文
    - team 执行完成后传递结果
    
    新增功能：
    - 插入式 LLM Provider
    - 调用者追踪
    - 结果路由
    - 技能互联
    """

    def __init__(self, session_id: str | None = None, user_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id or "default"
        self.created_at = time.time()
        
        # 核心状态
        self.task: Task | None = None
        self.thinking: ThinkingState = ThinkingState(phase="understanding")
        self.memory: MemoryRef = MemoryRef()
        self.search: SearchState = SearchState()
        
        # 插入式 LLM Provider
        self.llm: LLMProvider = LLMProvider()
        
        # 技能注册表
        self.skills: SkillRegistry = SkillRegistry()
        
        # 当前调用者信息
        self._current_caller: CallerInfo = CallerInfo()
        
        # 自定义数据
        self._data: dict = {}
        
        # 历史记录
        self._history: list[dict] = []

    # ==================== 调用者追踪 ====================
    
    def set_caller(self, caller_id: str, caller_type: str = "external", intent: str = ""):
        """设置当前调用者"""
        self._current_caller = CallerInfo(
            caller_id=caller_id,
            caller_type=caller_type,
            intent=intent
        )
    
    def get_caller(self) -> CallerInfo:
        """获取当前调用者"""
        return self._current_caller
    
    def is_skill_call(self) -> bool:
        """是否是技能间调用"""
        return self._current_caller.caller_type == "skill"
    
    def is_user_call(self) -> bool:
        """是否是用户直接调用"""
        return self._current_caller.caller_id == "user" or self._current_caller.caller_type == "external"
    
    # ==================== LLM 调用 ====================
    
    def call_llm(self, prompt: str, system: str | None = None, **kwargs) -> str:
        """调用 LLM（通过 provider）"""
        return self.llm.complete(prompt, system, **kwargs)
    
    def get_embeddings(self, texts: str | list[str]) -> list[float] | list[list[float]]:
        """获取嵌入向量"""
        return self.llm.embed(texts)
    
    # ==================== 技能注册 ====================
    
    def register_skill(self, skill_name: str, skill_instance: Any):
        """注册技能"""
        self.skills.register(skill_name, skill_instance)
    
    def get_skill(self, skill_name: str) -> Any | None:
        """获取技能"""
        return self.skills.get(skill_name)
    
    def call_skill(self, skill_name: str, action: str, params: dict) -> dict:
        """
        调用技能
        
        自动追踪调用者，结果根据调用者类型路由
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return {"success": False, "error": f"Skill {skill_name} not found"}
        
        # 设置调用者信息（被调用的技能可以通过 context 获取）
        original_caller = self._current_caller
        if "caller_id" not in params:
            params["caller_id"] = self._current_caller.caller_id
        
        # 调用技能
        if hasattr(skill, "execute"):
            result = skill.execute(action, params)
        elif hasattr(skill, "query"):
            result = skill.query(action, params)
        else:
            result = {"success": False, "error": "Skill has no execute or query method"}
        
        # 恢复原始调用者
        self._current_caller = original_caller
        
        return result

    # ==================== 结果路由 ====================
    
    def should_output_to_user(self) -> bool:
        """是否应该输出给用户"""
        # 如果是用户直接调用，结果应该给用户
        # 如果是技能间调用，结果不应该直接给用户
        return self.is_user_call()
    
    def get_result_routing(self) -> dict:
        """获取结果路由信息"""
        caller = self._current_caller
        
        if caller.caller_id == "user":
            return {"route": "user", "format": "full"}
        elif caller.caller_id in ["thinking", "team"]:
            return {"route": "skill", "format": "structured"}
        else:
            return {"route": "member", "format": "simplified"}

    # ==================== 任务管理 ====================

    def create_task(self, description: str) -> Task:
        """创建新任务"""
        self.task = Task(
            id=str(uuid.uuid4())[:8],
            status="pending",
            description=description
        )
        return self.task

    def update_task_status(self, status: str):
        """更新任务状态"""
        if self.task:
            self.task.status = status
            self.task.updated_at = time.time()

    def set_task_plan(self, plan: list[dict]):
        """设置任务计划"""
        if self.task:
            self.task.plan = plan
            self.task.updated_at = time.time()

    def set_task_result(self, result: Any):
        """设置任务结果"""
        if self.task:
            self.task.result = result
            self.task.updated_at = time.time()

    def get_task(self) -> Task | None:
        """获取当前任务"""
        return self.task

    # ==================== 思考状态 ====================

    def set_thinking_phase(self, phase: str):
        """设置思考阶段"""
        valid_phases = ["understanding", "planning", "executing", "reflection"]
        if phase not in valid_phases:
            raise ValueError(f"Invalid phase: {phase}. Must be one of {valid_phases}")
        self.thinking.phase = phase

    def add_question(self, question: str):
        """添加问题"""
        self.thinking.questions.append(question)

    def add_answer(self, answer: str):
        """添加回答"""
        self.thinking.answers.append(answer)

    def set_thinking_context(self, key: str, value: Any):
        """设置思考上下文"""
        self.thinking.context[key] = value

    def get_thinking_context(self, key: str, default: Any = None) -> Any:
        """获取思考上下文"""
        return self.thinking.context.get(key, default)

    def confirm_plan(self):
        """确认计划"""
        self.thinking.plan_confirmed = True

    def is_plan_confirmed(self) -> bool:
        """计划是否已确认"""
        return self.thinking.plan_confirmed

    def get_thinking_phase(self) -> str:
        """获取当前思考阶段"""
        return self.thinking.phase

    def get_conversation_history(self) -> list[dict]:
        """获取对话历史"""
        return [
            {"q": q, "a": a}
            for q, a in zip(self.thinking.questions, self.thinking.answers)
        ]

    # ==================== 记忆引用 ====================

    def add_memory(self, memory_type: str, content: Any, tags: list[str] | None = None):
        """添加记忆引用"""
        memory_entry = {
            "type": memory_type,
            "content": content,
            "tags": tags or [],
            "timestamp": time.time()
        }
        self.memory.recent.insert(0, memory_entry)
        
        # 保持最近记忆数量限制
        if len(self.memory.recent) > 100:
            self.memory.recent = self.memory.recent[:100]

    def set_preference(self, key: str, value: Any):
        """设置用户偏好"""
        self.memory.preferences[key] = value
        self.memory.learned_count += 1

    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好"""
        return self.memory.preferences.get(key, default)

    def add_entity(self, entity_type: str, entity_id: str, data: dict):
        """添加实体知识"""
        if entity_type not in self.memory.entities:
            self.memory.entities[entity_type] = {}
        self.memory.entities[entity_type][entity_id] = data

    def get_entity(self, entity_type: str, entity_id: str) -> dict | None:
        """获取实体知识"""
        return self.memory.entities.get(entity_type, {}).get(entity_id)

    def get_recent_memories(self, limit: int = 10, memory_type: str | None = None) -> list[dict]:
        """获取最近记忆"""
        memories = self.memory.recent
        if memory_type:
            memories = [m for m in memories if m.get("type") == memory_type]
        return memories[:limit]

    def get_learned_count(self) -> int:
        """获取学习次数"""
        return self.memory.learned_count

    # ==================== 搜索状态 ====================

    def set_search_query(self, query: str):
        """设置搜索查询"""
        self.search.query = query
        self.search.cached = False

    def set_search_results(self, results: list[dict]):
        """设置搜索结果"""
        self.search.results = results
        self.search.last_search = time.time()

    def get_search_results(self) -> list[dict]:
        """获取搜索结果"""
        return self.search.results

    def mark_search_cached(self):
        """标记搜索结果已缓存"""
        self.search.cached = True

    def is_search_cached(self) -> bool:
        """搜索结果是否已缓存"""
        return self.search.cached

    def get_last_search_time(self) -> float:
        """获取最近搜索时间"""
        return self.search.last_search

    # ==================== 通用数据 ====================

    def set(self, key: str, value: Any):
        """设置值"""
        self._data[key] = value
        self._add_history("set", key=key)

    def get(self, key: str, default: Any = None) -> Any:
        """获取值"""
        return self._data.get(key, default)

    def delete(self, key: str):
        """删除值"""
        if key in self._data:
            del self._data[key]
            self._add_history("delete", key=key)

    def clear(self):
        """清空自定义数据"""
        self._data = {}
        self._add_history("clear")

    def keys(self) -> list[str]:
        """获取所有键"""
        return list(self._data.keys())

    def items(self):
        """获取所有键值对"""
        return self._data.items()

    # ==================== 历史 ====================

    def _add_history(self, action: str, **kwargs):
        """添加历史记录"""
        self._history.append({
            "action": action,
            "timestamp": time.time(),
            **kwargs
        })

    def get_history(self, limit: int = 50) -> list[dict]:
        """获取历史记录"""
        return self._history[-limit:]

    def clear_history(self):
        """清空历史"""
        self._history = []

    # ==================== 序列化 ====================

    def to_dict(self) -> dict:
        """导出为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "task": {
                "id": self.task.id,
                "status": self.task.status,
                "description": self.task.description,
                "plan": self.task.plan,
                "created_at": self.task.created_at,
                "updated_at": self.task.updated_at
            } if self.task else None,
            "thinking": {
                "phase": self.thinking.phase,
                "questions": self.thinking.questions,
                "answers": self.thinking.answers,
                "context": self.thinking.context,
                "plan_confirmed": self.thinking.plan_confirmed
            },
            "memory": {
                "recent": self.memory.recent,
                "preferences": self.memory.preferences,
                "entities": self.memory.entities,
                "learned_count": self.memory.learned_count
            },
            "search": {
                "query": self.search.query,
                "cached": self.search.cached,
                "last_search": self.search.last_search
            },
            "llm_provider": str(self.llm),
            "data": self._data,
            "history": self._history[-100:]  # 限制历史长度
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SharedContext":
        """从字典恢复"""
        ctx = cls(session_id=data.get("session_id"), user_id=data.get("user_id"))
        
        if "task" in data and data["task"]:
            ctx.task = Task(**data["task"])
        
        if "thinking" in data:
            ctx.thinking = ThinkingState(**data["thinking"])
        
        if "memory" in data:
            ctx.memory = MemoryRef(**data["memory"])
        
        if "search" in data:
            ctx.search = SearchState(**data["search"])
        
        if "data" in data:
            ctx._data = data["data"]
        
        if "history" in data:
            ctx._history = data["history"]
        
        return ctx

    def copy(self) -> "SharedContext":
        """创建副本"""
        return SharedContext.from_dict(self.to_dict())


# ==================== 全局上下文 ====================

_global_context: SharedContext | None = None


def get_context() -> SharedContext:
    """获取全局上下文"""
    global _global_context
    if _global_context is None:
        _global_context = SharedContext()
    return _global_context


def reset_context():
    """重置全局上下文"""
    global _global_context
    _global_context = None


def new_context(session_id: str | None = None, user_id: str | None = None) -> SharedContext:
    """创建新上下文"""
    global _global_context
    _global_context = SharedContext(session_id=session_id, user_id=user_id)
    return _global_context


def get_llm_provider() -> LLMProvider:
    """获取全局 LLM Provider"""
    ctx = get_context()
    return ctx.llm