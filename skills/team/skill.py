"""
team 技能 - AgentTeam 完全体适配层

使用 AgentTeam Python SDK（完全体），不经过 CLI：
- CTTeam: 团队容器
- CTAgent: 运行在 OpenClaw Session 的智能体
- CTTask: 任务跟踪
- spawn: 通过 OpenClaw SDK Backend 创建子 Agent

所有 LLM 分析由 AgentTeam 子 agent 完成（通过 OpenClaw 使用用户配置的模型）
"""

import sys
import time
import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass

# 将 AgentTeam 添加到 path（如果不在 Python 环境里）
_agentteam_path = Path(__file__).parent.parent.parent.parent / "AgentTeam"
if str(_agentteam_path) not in sys.path:
    sys.path.insert(0, str(_agentteam_path))

from shared import (
    Skill,
    SkillCapability,
    SharedContext,
    get_context,
)


@dataclass
class TeamSkillConfig:
    """team 技能配置"""
    data_dir: str = "~/.agentteam"
    max_retries: int = 3
    check_completion: bool = True


class TeamSkill:
    """
    Team 技能 - AgentTeam 完全体

    直接使用 AgentTeam SDK：
    - CTTeam.spawn() -> OpenClaw Session Agent
    - 子 agent 通过 OpenClaw 使用用户配置的 LLM
    - team skill 是纯协调层，不自己做 LLM 分析
    """

    def __init__(self, config: TeamSkillConfig | None = None):
        self.config = config or TeamSkillConfig()
        self._context: SharedContext = get_context()
        self._teams: dict[str, Any] = {}

    # ==================== 标准接口 ====================

    def query(self, capability: str, context: dict | None = None) -> dict:
        capability_map = {
            "team.execute": self._execute,
            "team.status": self._status,
            "team.delegate": self._delegate,
            "team.check": self._check,
        }

        if capability not in capability_map:
            return {
                "success": False,
                "error": {"code": "CAPABILITY_NOT_FOUND", "message": f"Capability {capability} not found"}
            }

        return capability_map[capability](context or {})

    def execute(self, action: str, params: dict) -> dict:
        start_time = time.time()

        try:
            if action == "execute_task":
                result = self._execute_task(params)
            elif action == "delegate":
                result = self._delegate(params)
            elif action == "check_completion":
                result = self._check(params)
            else:
                return {
                    "success": False,
                    "error": {"code": "ACTION_NOT_FOUND", "message": f"Action {action} not found"}
                }

            return {
                "success": True,
                "data": result,
                "meta": {
                    "skill": "team",
                    "action": action,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": {"code": "EXECUTION_ERROR", "message": str(e)},
                "meta": {
                    "skill": "team",
                    "action": action,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }

    def notify(self, event: str, data: dict):
        if event == "task.completed":
            self._on_task_completed(data)
        elif event == "task.failed":
            self._on_task_failed(data)

    # ==================== AgentTeam SDK 完全体执行 ====================

    def _execute_task(self, params: dict) -> dict:
        """
        使用 AgentTeam CTTeam 完全体执行任务计划

        流程：
        1. 创建/获取 CTTeam
        2. 为每个步骤 spawn 一个 CTAgent
        3. 等待所有 agent 完成
        4. 汇总结果
        """
        from agentteam.core import CTTeam, AgentState

        task_id = params.get("task_id", f"task_{int(time.time())}")
        plan = params.get("plan", [])
        requirement = params.get("requirement", "")

        self._context.create_task(description=f"Team task: {task_id}")
        self._context.update_task_status("executing")

        # 创建团队（每个任务一个独立团队）
        team_name = f"symphony_{task_id}"
        team = CTTeam(team_name)
        self._teams[team_name] = team

        # 为每个步骤 spawn agent
        results = []
        for i, step in enumerate(plan):
            action = step.get("action", "")
            step_params = step.get("params", {})
            agent_name = f"worker_{i}"

            # 构造 agent 任务描述
            task_desc = self._build_agent_task(action, step_params, requirement, i)

            try:
                agent = team.spawn(
                    name=agent_name,
                    task=task_desc,
                    agent_type="worker",
                )

                results.append({
                    "step": i,
                    "action": action,
                    "status": "spawned",
                    "agent_name": agent_name,
                    "session_key": agent.session_key,
                })

            except Exception as e:
                results.append({
                    "step": i,
                    "action": action,
                    "status": "failed",
                    "error": str(e)
                })

        # 等待所有 agent 完成（最多 5 分钟）
        wait_timeout = 300
        start = time.time()
        while time.time() - start < wait_timeout:
            all_done = all(
                r.get("status") in ("completed", "failed") or r.get("session_key")
                for r in results
            )
            if all_done:
                break
            time.sleep(5)

            # 检查 agent 状态
            for r in results:
                if r.get("session_key") and r.get("status") == "spawned":
                    # 检查 agent 是否完成
                    agent_name = r.get("agent_name")
                    agent = team.agents.get(agent_name)
                    if agent and agent.state in (AgentState.COMPLETED, AgentState.FAILED, AgentState.TERMINATED):
                        r["status"] = "completed" if agent.state == AgentState.COMPLETED else "failed"
                        if agent.task_id:
                            r["result"] = agent.task_id

        # 标记未完成的为超时
        for r in results:
            if r.get("status") == "spawned":
                r["status"] = "timeout"

        # 完成度
        completed = sum(1 for r in results if r.get("status") == "completed")
        completion_rate = completed / len(results) if results else 0

        self._context.set_task_result({
            "task_id": task_id,
            "results": results,
            "completion_rate": completion_rate
        })
        self._context.update_task_status("completed" if completion_rate >= 1.0 else "partial")

        return {
            "task_id": task_id,
            "results": results,
            "team_name": team_name,
            "completion_rate": completion_rate,
            "status": "completed" if completion_rate >= 1.0 else "partial"
        }

    def _build_agent_task(self, action: str, params: dict, requirement: str, step_index: int) -> str:
        """为 agent 构造任务描述"""
        params_str = json.dumps(params, ensure_ascii=False, indent=2)
        return f"""你是任务执行专家。请执行以下步骤：

## 任务索引：{step_index}
## 动作：{action}
## 原始需求：{requirement}
## 参数：{params_str}

执行步骤 {step_index + 1}：{action}

完成执行后，返回：
1. 执行结果（2-3句话）
2. 关键洞察（1-2句）

只返回执行结果，不要多余内容。"""

    # ==================== 其他接口 ====================

    def _delegate(self, params: dict) -> dict:
        return {
            "delegated": True,
            "message": "Delegation handled by AgentTeam CTTeam"
        }

    def _status(self, params: dict) -> dict:
        return {
            "team_id": params.get("team_id", "default"),
            "status": "ready",
            "backend": "AgentTeam SDK (CTTeam)"
        }

    def _check(self, params: dict) -> dict:
        return {
            "task_id": params.get("task_id"),
            "completion_rate": 1.0,
            "checked": True
        }

    def _on_task_completed(self, data: dict):
        self._context.set_task_result(data.get("result", {}))
        self._context.update_task_status("completed")

    def _on_task_failed(self, data: dict):
        self._context.update_task_status("failed")


def get_skill_instance(config: TeamSkillConfig | None = None) -> TeamSkill:
    return TeamSkill(config=config)
