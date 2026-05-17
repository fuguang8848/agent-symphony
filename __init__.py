"""
AgentSymphony - 技能交响乐

多技能底层互通的 Agent 框架

使用方式：
  python -m agent_symphony "你的需求"

示例：
  python -m agent_symphony "帮我分析石榴籽项目"
"""

from agent_symphony.skills.thinking import ThinkingSkill
from agent_symphony.skills.memory import MemorySkill
from agent_symphony.skills.search import SearchSkill
from agent_symphony.shared import SharedContext

__all__ = [
    "ThinkingSkill",
    "MemorySkill",
    "SearchSkill",
    "SharedContext",
]