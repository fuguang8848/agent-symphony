"""
技能注册表 - 实现技能发现和调用

Agent Symphony 技能交响乐的核心组件
负责管理所有技能的注册、查询和调用
"""

import time
import uuid
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    """事件类型"""
    SKILL_REGISTER = "skill.register"
    SKILL_UNREGISTER = "skill.unregister"
    MEMORY_STORE = "memory.store"
    MEMORY_QUERY = "memory.query"
    SEARCH_EXECUTE = "search.execute"
    TASK_EXECUTE = "task.execute"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"


@dataclass
class SkillCapability:
    """技能能力定义"""
    name: str                           # 能力名称
    description: str                    # 能力描述
    params: dict                        # 参数 schema
    result_schema: dict                 # 返回 schema
    handler: Callable = None            # 处理函数


@dataclass
class Skill:
    """技能定义"""
    name: str                           # 技能名称
    version: str                        # 版本
    description: str                    # 描述
    capabilities: list[SkillCapability] # 能力列表
    instance: Any = None                # 技能实例
    metadata: dict = field(default_factory=dict)  # 元数据


@dataclass
class Event:
    """事件"""
    event: str
    source: str
    target: str | None
    timestamp: float
    data: dict

    @classmethod
    def create(cls, event: str, source: str, target: str | None = None, **data):
        return cls(
            event=event,
            source=source,
            target=target,
            timestamp=time.time(),
            data=data
        )


class SkillRegistry:
    """
    技能注册表
    
    管理 Agent Symphony 中所有技能的注册、查询和调用
    """

    def __init__(self):
        self.skills: dict[str, Skill] = {}
        self.capability_index: dict[str, list[str]] = {}  # capability -> [skill_names]
        self.event_handlers: dict[str, list[Callable]] = {}
        self._context: dict = {}

    def register(self, skill: Skill) -> bool:
        """
        注册技能
        
        Args:
            skill: Skill 对象
            
        Returns:
            是否注册成功
        """
        if skill.name in self.skills:
            print(f"[Registry] Skill {skill.name} already registered, updating...")
            
        # 注册技能
        self.skills[skill.name] = skill
        
        # 更新能力索引
        for cap in skill.capabilities:
            if cap.name not in self.capability_index:
                self.capability_index[cap.name] = []
            if skill.name not in self.capability_index[cap.name]:
                self.capability_index[cap.name].append(skill.name)
        
        # 发送注册事件
        self._emit_event(Event.create(
            EventType.SKILL_REGISTER.value,
            source="registry",
            skill_name=skill.name,
            capabilities=[cap.name for cap in skill.capabilities]
        ))
        
        print(f"[Registry] Registered skill: {skill.name} v{skill.version}")
        return True

    def unregister(self, skill_name: str) -> bool:
        """
        注销技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            是否注销成功
        """
        if skill_name not in self.skills:
            print(f"[Registry] Skill {skill_name} not found")
            return False
        
        skill = self.skills[skill_name]
        
        # 从能力索引中移除
        for cap in skill.capabilities:
            if cap.name in self.capability_index:
                self.capability_index[cap.name].remove(skill_name)
                if not self.capability_index[cap.name]:
                    del self.capability_index[cap.name]
        
        # 删除技能
        del self.skills[skill_name]
        
        # 发送注销事件
        self._emit_event(Event.create(
            EventType.SKILL_UNREGISTER.value,
            source="registry",
            skill_name=skill_name
        ))
        
        print(f"[Registry] Unregistered skill: {skill_name}")
        return True

    def query(self, capability: str) -> list[str]:
        """
        查询具有特定能力的技能
        
        Args:
            capability: 能力名称
            
        Returns:
            技能名称列表
        """
        return self.capability_index.get(capability, [])

    def get_skill(self, skill_name: str) -> Skill | None:
        """
        获取技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            Skill 对象或 None
        """
        return self.skills.get(skill_name)

    def call(self, skill_name: str, method: str, *args, **kwargs) -> dict:
        """
        调用技能方法
        
        Args:
            skill_name: 技能名称
            method: 方法名
            *args, **kwargs: 方法参数
            
        Returns:
            标准响应格式
        """
        start_time = time.time()
        
        skill = self.skills.get(skill_name)
        if not skill:
            return {
                "success": False,
                "error": {
                    "code": "SKILL_NOT_FOUND",
                    "message": f"Skill {skill_name} not found"
                }
            }
        
        if not skill.instance:
            return {
                "success": False,
                "error": {
                    "code": "SKILL_NOT_INITIALIZED",
                    "message": f"Skill {skill_name} not initialized"
                }
            }
        
        # 调用方法
        try:
            handler = getattr(skill.instance, method, None)
            if not handler:
                return {
                    "success": False,
                    "error": {
                        "code": "METHOD_NOT_FOUND",
                        "message": f"Method {method} not found in {skill_name}"
                    }
                }
            
            result = handler(*args, **kwargs)
            
            return {
                "success": True,
                "data": result,
                "meta": {
                    "skill": skill_name,
                    "method": method,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(e)
                },
                "meta": {
                    "skill": skill_name,
                    "method": method,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }

    def on_event(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 处理函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    def _emit_event(self, event: Event):
        """触发事件"""
        handlers = self.event_handlers.get(event.event, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[Registry] Event handler error: {e}")

    def set_context(self, key: str, value: Any):
        """设置上下文"""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文"""
        return self._context.get(key, default)

    def clear_context(self):
        """清空上下文"""
        self._context = {}

    def list_skills(self) -> list[dict]:
        """列出所有已注册技能"""
        return [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "capabilities": [cap.name for cap in s.capabilities]
            }
            for s in self.skills.values()
        ]

    def get_capability_map(self) -> dict[str, list[str]]:
        """获取能力地图"""
        return self.capability_index.copy()


# 全局注册表实例
_global_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    """获取全局注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry


def register_skill(skill: Skill):
    """快捷注册函数"""
    return get_registry().register(skill)


def query_skills(capability: str) -> list[str]:
    """快捷查询函数"""
    return get_registry().query(capability)


def call_skill(skill_name: str, method: str, *args, **kwargs) -> dict:
    """快捷调用函数"""
    return get_registry().call(skill_name, method, *args, **kwargs)
