"""
team 技能 - AgentTeam 适配层

Agent Symphony 技能交响乐的执行者
"""

from .skill import TeamSkill, TeamSkillConfig, get_skill_instance

__all__ = [
    "TeamSkill",
    "TeamSkillConfig",
    "get_skill_instance",
]
