"""AgentSymphony skills package - lazy loading."""

__all__ = [
    "ThinkingSkill",
    "MemorySkill",
    "TeamSkill",
    "SearchSkill",
]


def __getattr__(name: str):
    if name == "ThinkingSkill":
        from .thinking import ThinkingSkill
        return ThinkingSkill
    if name == "MemorySkill":
        from .memory import MemorySkill
        return MemorySkill
    if name == "TeamSkill":
        from .team import TeamSkill
        return TeamSkill
    if name == "SearchSkill":
        from .search import SearchSkill
        return SearchSkill
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
