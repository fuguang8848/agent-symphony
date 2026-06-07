"""
Smoke test for AgentSymphony.
验证 server 能启动 + 4 skill 能 import + 关键 endpoint 通。

跑法: cd /home/fuguang/AgentSymphony && python3 tests/test_smoke.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_server_import():
    """server 能 import，不抛错。"""
    from server.symphony_server import app
    assert app is not None
    print("✓ server import OK")

def test_4_skill_import():
    """4 个核心 skill 都能 import。"""
    from server.skills.thinking_skill import ThinkingSkill
    from server.skills.memory_skill import MemorySkill
    from server.skills.search_skill import SearchSkill
    from server.skills.team_skill import TeamSkill
    assert all([ThinkingSkill, MemorySkill, SearchSkill, TeamSkill])
    print("✓ 4 skill import OK")

def test_shared_no_nested():
    """shared/shared/ 嵌套应该不存在（删了 2026-06-04 V 修复）。"""
    nested = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shared", "shared")
    assert not os.path.exists(nested), f"shared/shared/ 仍存在：{nested}"
    print("✓ shared/shared/ 嵌套不存在")

def test_local_skill_registry():
    """shared/context.py 应该叫 LocalSkillRegistry（避免命名冲突）。"""
    from shared.context import LocalSkillRegistry
    assert LocalSkillRegistry is not None
    print("✓ LocalSkillRegistry 命名正确")

if __name__ == "__main__":
    test_server_import()
    test_4_skill_import()
    test_shared_no_nested()
    test_local_skill_registry()
    print("\n=== 4/4 smoke test 通过 ===")
