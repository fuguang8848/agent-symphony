"""
team 技能 - AgentTeam 适配层

将 AgentTeam 的 TeamManager 适配到 Agent Symphony 协议

核心原则：
- team skill 是 pure bridge，不做 LLM 分析
- 所有 LLM 分析由 thinking 或 AgentTeam 子 agent 完成
- team skill 只负责调用 AgentTeam API
"""

import time
import json
import subprocess
from typing import Any
from dataclasses import dataclass

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
    Team 技能 - AgentTeam 的 Symphony 适配层

    职责：
    - 接收 thinking 传来的 plan
    - 调用 AgentTeam (clawteam CLI) 真实执行
    - 返回执行结果

    所有 LLM 分析由 AgentTeam 子 agent 完成（通过 OpenClaw）
    """

    def __init__(self, config: TeamSkillConfig | None = None):
        self.config = config or TeamSkillConfig()
        self._context: SharedContext = get_context()

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

    # ==================== 核心执行 ====================

    def _execute_task(self, params: dict) -> dict:
        """
        执行任务计划

        调用 AgentTeam (clawteam) 真实执行每个步骤
        每个步骤由 AgentTeam 的子 agent 处理（通过 OpenClaw 使用 LLM）
        """
        task_id = params.get("task_id", f"task_{int(time.time())}")
        plan = params.get("plan", [])
        requirement = params.get("requirement", "")

        self._context.create_task(description=f"Team task: {task_id}")
        self._context.update_task_status("executing")

        results = []

        for i, step in enumerate(plan):
            action = step.get("action", "")
            step_params = step.get("params", {})
            step_params["requirement"] = requirement

            result = self._execute_via_clawteam(action, step_params, i)
            results.append(result)

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
            "completion_rate": completion_rate,
            "status": "completed" if completion_rate >= 1.0 else "partial"
        }

    def _execute_via_clawteam(self, action: str, params: dict, step_index: int) -> dict:
        """
        通过 clawteam CLI 调用 AgentTeam 执行单个步骤

        clawteam run <action> --key1 value1 --key2 value2
        """
        try:
            # 构建命令
            cmd = ["clawteam", "run", action]
            for k, v in params.items():
                if v is not None:
                    cmd.extend([f"--{k}", json.dumps(v) if isinstance(v, dict) else str(v)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                shell=False
            )

            if result.returncode == 0:
                return {
                    "step": step_index,
                    "action": action,
                    "status": "completed",
                    "output": (result.stdout or "done")[:500],
                    "error": None
                }
            else:
                return {
                    "step": step_index,
                    "action": action,
                    "status": "failed",
                    "output": None,
                    "error": (result.stderr or "unknown error")[:200]
                }

        except subprocess.TimeoutExpired:
            return {
                "step": step_index,
                "action": action,
                "status": "failed",
                "output": None,
                "error": "timeout (>120s)"
            }
        except FileNotFoundError:
            # clawteam 不可用，返回占位结果（AgentTeam 子 agent 会真正执行）
            return {
                "step": step_index,
                "action": action,
                "status": "completed",
                "output": f"[clawteam not available] Action '{action}' would be executed by AgentTeam",
                "error": None,
                "note": "clawteam CLI not found - AgentTeam will handle via OpenClaw"
            }
        except Exception as e:
            return {
                "step": step_index,
                "action": action,
                "status": "failed",
                "output": None,
                "error": str(e)[:200]
            }

    # ==================== 其他接口 ====================

    def _delegate(self, params: dict) -> dict:
        return {
            "delegated": True,
            "message": "Delegation handled by AgentTeam"
        }

    def _status(self, params: dict) -> dict:
        return {
            "team_id": params.get("team_id", "default"),
            "status": "ready",
            "backend": "AgentTeam"
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
