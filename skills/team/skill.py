"""
team 技能 - AgentTeam 适配层

将 AgentTeam 的 TeamManager 适配到 Agent Symphony 协议
"""

import time
from typing import Any
from dataclasses import dataclass, field

from agentteam.team import TeamManager

from agent_symphony.shared import (
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
    
    桥接 AgentTeam 的 TeamManager 和 Agent Symphony 协议
    """

    def __init__(self, config: TeamSkillConfig | None = None):
        self.config = config or TeamSkillConfig()
        self._manager: TeamManager | None = None
        self._context: SharedContext = get_context()

    def _ensure_manager(self):
        """延迟初始化 TeamManager"""
        if self._manager is None:
            self._manager = TeamManager(data_dir=self.config.data_dir)

    # ==================== 标准接口 ====================

    def query(self, capability: str, context: dict | None = None) -> dict:
        """
        查询技能能力
        
        Args:
            capability: 能力名称
            context: 可选的上下文
            
        Returns:
            标准响应格式
        """
        capability_map = {
            "team.execute": self._execute,
            "team.status": self._status,
            "team.delegate": self._delegate,
            "team.check": self._check,
            "team.notify": self._notify,
        }
        
        if capability not in capability_map:
            return {
                "success": False,
                "error": {
                    "code": "CAPABILITY_NOT_FOUND",
                    "message": f"Capability {capability} not found"
                }
            }
        
        return capability_map[capability](context or {})

    def execute(self, action: str, params: dict) -> dict:
        """
        执行动作
        
        Args:
            action: 动作名称
            params: 参数
            
        Returns:
            标准响应格式
        """
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
                    "error": {
                        "code": "ACTION_NOT_FOUND",
                        "message": f"Action {action} not found"
                    }
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
                "error": {
                    "code": "EXECUTION_ERROR",
                    "message": str(e)
                },
                "meta": {
                    "skill": "team",
                    "action": action,
                    "duration_ms": int((time.time() - start_time) * 1000)
                }
            }

    def notify(self, event: str, data: dict):
        """
        接收事件通知
        
        Args:
            event: 事件类型
            data: 事件数据
        """
        if event == "task.completed":
            self._on_task_completed(data)
        elif event == "task.failed":
            self._on_task_failed(data)
        elif event == "thinking.phase_changed":
            self._on_phase_changed(data)

    # ==================== 内部实现 ====================

    def _execute(self, params: dict) -> dict:
        """执行任务"""
        return self._execute_task(params)

    def _execute_task(self, params: dict) -> dict:
        """执行单个任务"""
        self._ensure_manager()
        
        task_id = params.get("task_id", f"task_{int(time.time())}")
        plan = params.get("plan", [])
        check_completion = params.get("check_completion", self.config.check_completion)
        max_retries = params.get("max_retries", self.config.max_retries)
        
        # 更新上下文
        self._context.create_task(description=f"Team task: {task_id}")
        self._context.update_task_status("executing")
        
        results = []
        for i, step in enumerate(plan):
            action = step.get("action")
            step_params = step.get("params", {})
            
            retry_count = 0
            success = False
            
            while retry_count <= max_retries and not success:
                try:
                    # TODO: 调用 AgentTeam 的实际执行逻辑
                    # 目前是占位实现
                    result = {
                        "step": i,
                        "action": action,
                        "status": "completed",
                        "output": f"Executed {action}"
                    }
                    results.append(result)
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        results.append({
                            "step": i,
                            "action": action,
                            "status": "failed",
                            "error": str(e)
                        })
        
        # 完成度检查
        completion_rate = 1.0
        if check_completion:
            completed = sum(1 for r in results if r.get("status") == "completed")
            completion_rate = completed / len(results) if results else 0
        
        # 更新上下文
        self._context.set_task_result({
            "task_id": task_id,
            "results": results,
            "completion_rate": completion_rate
        })
        self._context.update_task_status("completed" if completion_rate >= 1.0 else "failed")
        
        return {
            "task_id": task_id,
            "results": results,
            "completion_rate": completion_rate,
            "status": "completed" if completion_rate >= 1.0 else "partial"
        }

    def _delegate(self, params: dict) -> dict:
        """委托子任务"""
        self._ensure_manager()
        
        # TODO: 实现委托逻辑
        return {
            "delegated": True,
            "message": "Delegation not yet implemented"
        }

    def _status(self, params: dict) -> dict:
        """获取团队状态"""
        self._ensure_manager()
        
        # TODO: 返回实际的团队状态
        return {
            "team_id": params.get("team_id", "default"),
            "members": [],
            "active_tasks": 0,
            "status": "idle"
        }

    def _check(self, params: dict) -> dict:
        """完成度检查"""
        task_id = params.get("task_id")
        
        # TODO: 实现完成度检查逻辑
        return {
            "task_id": task_id,
            "completion_rate": 1.0,
            "checked": True
        }

    def _notify(self, params: dict) -> dict:
        """发送通知"""
        # 向 thinking 发送任务完成通知
        return {
            "notified": True,
            "recipient": "thinking"
        }

    # ==================== 事件处理 ====================

    def _on_task_completed(self, data: dict):
        """任务完成事件"""
        task_id = data.get("task_id")
        result = data.get("result")
        
        # 更新上下文
        self._context.set_task_result(result)
        self._context.update_task_status("completed")
        
        # TODO: 通知 thinking

    def _on_task_failed(self, data: dict):
        """任务失败事件"""
        task_id = data.get("task_id")
        error = data.get("error")
        
        # 更新上下文
        self._context.update_task_status("failed")
        
        # TODO: 通知 thinking

    def _on_phase_changed(self, data: dict):
        """阶段变化事件"""
        old_phase = data.get("old_phase")
        new_phase = data.get("new_phase")
        
        # 根据 thinking 阶段调整团队行为
        if new_phase == "executing":
            # 开始执行
            pass
        elif new_phase == "reflection":
            # 执行后反思
            pass


def get_skill_instance(config: TeamSkillConfig | None = None) -> TeamSkill:
    """获取 team 技能实例"""
    return TeamSkill(config=config)
