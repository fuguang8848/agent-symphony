"""
Agent Symphony 技能交响乐 - 共享模块

提供技能注册表和共享上下文
"""

from .registry import (
    SkillRegistry,
    Skill,
    SkillCapability,
    Event,
    EventType,
    get_registry,
    register_skill,
    query_skills,
    call_skill,
)

from .context import (
    SharedContext,
    Task,
    ThinkingState,
    MemoryRef,
    SearchState,
    CallerInfo,
    LLMProvider,
    get_context,
    reset_context,
    new_context,
    get_llm_provider,
)

__all__ = [
    # Registry
    "SkillRegistry",
    "Skill",
    "SkillCapability",
    "Event",
    "EventType",
    "get_registry",
    "register_skill",
    "query_skills",
    "call_skill",
    # Context
    "SharedContext",
    "Task",
    "ThinkingState",
    "MemoryRef",
    "SearchState",
    "CallerInfo",
    "LLMProvider",
    "get_context",
    "reset_context",
    "new_context",
    "get_llm_provider",
]
