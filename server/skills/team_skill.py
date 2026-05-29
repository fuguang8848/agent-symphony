"""
team_skill.py - 任务执行（复用 sessions_spawn）

参考 AgentTeam OpenClaw SDK Backend
"""
import subprocess
import json
from pathlib import Path


class TeamSkill:
    """
    通过 OpenClaw sessions_spawn 执行多任务

    工作流程：
    1. spawn() 创建 sub-agent session
    2. 通过 sessions.send 发送任务
    3. 轮询 session history 直到完成
    """

    def __init__(self):
        self.gateway_url = "ws://127.0.0.1:18789"

    def spawn(self, task: str, agent_type: str = "general") -> dict:
        """
        Spawn 一个 sub-agent 执行任务

        注意：这里用 subprocess 调用 openclaw CLI
        后续改用 Gateway RPC
        """
        # TODO: 实现完整的 Session Keeper 模式
        # 参考 AgentTeam openclaw_sdk_backend.py
        return {
            "status": "stub",
            "task": task,
            "message": "team_skill 仍在开发中",
            "note": "请使用 sessions_spawn 替代",
        }

    def status(self, session_id: str) -> dict:
        """查询任务状态"""
        return {
            "session_id": session_id,
            "status": "unknown",
        }
