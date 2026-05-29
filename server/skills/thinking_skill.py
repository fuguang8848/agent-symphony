"""
thinking_skill.py - 对话 + 澄清 + 规划 状态机

工作流: clarifying → planning → executing → completed
参考: AgentSymphony thinking skill + AgentTeam TaskRouter
"""
import re
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator

from ..shared.llm_provider import get_llm


class State(Enum):
    CLARIFYING = "clarifying"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"


# 交响乐触发词（明确要启动 symphony）
SYMPHONY_TRIGGERS = [
    "启动交响乐", "交响乐模式", "symphony",
]

# 技能触发词（symphony 内部执行阶段使用）
SKILL_TRIGGERS = {
    "search": ["搜索", "帮我搜", "查一下", "找一下"],
    "team": ["执行", "开始做"],
    "memory": ["记住", "存一下", "记录"],
}


@dataclass
class ThinkingContext:
    """对话上下文"""
    user_message: str
    state: State = State.CLARIFYING
    clarifying_round: int = 0
    max_clarifying_rounds: int = 3
    answers: dict[str, str] = field(default_factory=dict)
    plan: str = ""
    skill_requests: list[dict] = field(default_factory=list)
    last_user_message: str = ""
    done: bool = False


SYSTEM_PROMPT = """你是一位AI助手，担任"思考者"角色。

你的职责是根据用户的需求，引导用户澄清关键信息，然后制定执行计划。

工作流程：
1. **clarifying（澄清）**：向用户提问，澄清需求（最多3轮）
2. **planning（规划）**：基于已知信息，制定详细计划
3. **executing（执行）**：调用技能执行计划
4. **completed（完成）**：交付结果

回复规则：
- clarifying 阶段：用中文提问，一次只问1个最关键的问题
- planning 阶段：给出清晰的分步计划
- 每次回复都要说明当前状态（clarifying/planning/executing/completed）

用户偏好：
- 简洁直接，不废话
- 不要重复用户说过的话
- 直接给结论，再解释"""


CLARIFYING_PROMPT = """当前状态: clarifying（需求澄清）

用户说：{user_message}

已知信息：{answers}

请用中文问用户1个最关键的问题来澄清需求。
只问1个问题，要具体、明确。
如果信息已经足够明确，直接回答"好的，我明白了"并进入 planning。

格式：
问题：..."""


PLANNING_PROMPT = """当前状态: planning（制定计划）

用户原始需求：{user_message}
已澄清的信息：{answers}

请制定详细的执行计划。
计划要：
- 分步骤，每步有明确目标
- 标注可能用到的技能（search/team/memory）
- 考虑用户偏好（简洁直接）

格式：
计划：
1. ...
2. ...
3. ...

技能需求：
- search: [需要搜索什么]
- team: [需要执行什么任务]
- memory: [需要记住什么]"""


EXECUTING_PROMPT = """当前状态: executing（执行中）

用户需求：{user_message}
已制定计划：{plan}
正在执行技能：{skill}

执行结果：{result}

请给用户一个简洁的阶段性汇报。
如果所有技能都已执行完毕，回复"完成"并进入 completed 状态。"""


COMPLETED_PROMPT = """当前状态: completed（完成）

用户需求：{user_message}
执行结果：{result}

请给用户一个简洁的最终总结。
包含：做了什么 + 关键结果 + 后续建议（如有）。"""


class ThinkingSkill:
    """思考技能 - 状态机驱动"""

    def __init__(self):
        self.llm = get_llm()
        self.contexts: dict[str, ThinkingContext] = {}
        self._sessions: dict[str, asyncio.Task] = {}

    def _get_session_id(self, user_id: str = "default") -> str:
        return user_id

    def _get_or_create_context(self, session_id: str, user_message: str) -> ThinkingContext:
        """获取或创建上下文"""
        ctx = self.contexts.get(session_id)
        if ctx is None:
            ctx = ThinkingContext(user_message=user_message)
            self.contexts[session_id] = ctx
        else:
            # 新消息，更新用户输入
            ctx.last_user_message = ctx.user_message
            ctx.user_message = user_message
            # 如果之前完成了，重置
            if ctx.state == State.COMPLETED:
                ctx.state = State.CLARIFYING
                ctx.clarifying_round = 0
                ctx.answers = {}
                ctx.plan = ""
                ctx.skill_requests = []
                ctx.done = False
        return ctx

    async def think(self, user_message: str, answers: dict | None = None, session_id: str = "default") -> dict:
        """
        主入口 - 处理用户消息，返回思考结果

        Returns:
            {
                "response": str,           # 面向用户的回复
                "state": State,            # 当前状态
                "questions": [str],        # 澄清问题列表
                "skill_requests": [dict],  # 需要执行的技能
                "done": bool,
                "plan": str,               # 计划（planning 阶段）
            }
        """
        ctx = self._get_or_create_context(session_id, user_message)

        # 更新 answers
        if answers:
            ctx.answers.update(answers)

        # 检查是否是交响乐任务
        is_symphony = self._is_symphony_task(user_message)

        # 如果不是 symphony 任务，先走澄清流程
        if not is_symphony:
            # 非 symphony 消息，检查是否需要触发技能（单技能执行）
            if self._check_skill_trigger(user_message):
                ctx.state = State.EXECUTING

        if ctx.state == State.CLARIFYING:
            return await self._do_clarifying(ctx)
        elif ctx.state == State.PLANNING:
            return await self._do_planning(ctx)
        elif ctx.state == State.EXECUTING:
            return await self._do_executing(ctx)
        else:
            return await self._do_completed(ctx)

    def _is_symphony_task(self, message: str) -> bool:
        """检查是否是交响乐任务（需要完整工作流）"""
        msg_lower = message.lower()
        for t in SYMPHONY_TRIGGERS:
            if t.lower() in msg_lower:
                return True
        return False

    def _check_skill_trigger(self, message: str) -> bool:
        """检查是否触发了技能（仅在 symphony 内部执行阶段）"""
        for skill, triggers in SKILL_TRIGGERS.items():
            for t in triggers:
                if t in message:
                    return True
        return False

    async def _do_clarifying(self, ctx: ThinkingContext) -> dict:
        """澄清阶段"""
        ctx.clarifying_round += 1

        # 格式化已知信息
        answers_str = "\n".join(f"- {k}: {v}" for k, v in ctx.answers.items()) or "（暂无）"

        # 检查是否超过最大轮次
        if ctx.clarifying_round > ctx.max_clarifying_rounds:
            ctx.state = State.PLANNING
            return await self._do_planning(ctx)

        # 调用 LLM 判断是否还需要澄清
        prompt = CLARIFYING_PROMPT.format(
            user_message=ctx.user_message,
            answers=answers_str,
        )

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            max_tokens=512,
            temperature=0.7,
        )

        response = response.strip()

        # 判断是否进入 planning
        if "好的，我明白了" in response or ctx.clarifying_round >= ctx.max_clarifying_rounds:
            ctx.state = State.PLANNING
            # 如果还需要问问题但轮次到了，先问最后一个
            if "问题：" in response or "？" in response:
                return {
                    "response": response,
                    "state": State.CLARIFYING,
                    "questions": [response],
                    "skill_requests": [],
                    "done": False,
                    "plan": "",
                }
            return await self._do_planning(ctx)

        return {
            "response": response,
            "state": State.CLARIFYING,
            "questions": [response],
            "skill_requests": [],
            "done": False,
            "plan": "",
        }

    async def _do_planning(self, ctx: ThinkingContext) -> dict:
        """规划阶段"""
        answers_str = "\n".join(f"- {k}: {v}" for k, v in ctx.answers.items()) or "（无额外澄清）"

        prompt = PLANNING_PROMPT.format(
            user_message=ctx.user_message,
            answers=answers_str,
        )

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            max_tokens=1024,
            temperature=0.5,
        )

        ctx.plan = response
        ctx.state = State.EXECUTING

        # 解析技能需求
        skill_requests = self._parse_skill_requests(response)

        return {
            "response": response,
            "state": State.EXECUTING,
            "questions": [],
            "skill_requests": skill_requests,
            "done": False,
            "plan": ctx.plan,
        }

    def _parse_skill_requests(self, plan_text: str) -> list[dict]:
        """从计划文本中解析技能需求"""
        requests = []
        for skill, triggers in SKILL_TRIGGERS.items():
            for t in triggers:
                if t in plan_text.lower():
                    requests.append({
                        "skill": skill,
                        "action": "execute",
                        "params": {"query": plan_text},
                    })
                    break
        return requests

    async def _do_executing(self, ctx: ThinkingContext) -> dict:
        """执行阶段"""
        # 这里 skill_requests 会被外部执行
        # 执行完成后调用 complete(result) 进入 completed
        return {
            "response": "正在执行计划...",
            "state": State.EXECUTING,
            "questions": [],
            "skill_requests": ctx.skill_requests,
            "done": False,
            "plan": ctx.plan,
        }

    async def _do_completed(self, ctx: ThinkingContext, result: str = "") -> dict:
        """完成阶段"""
        prompt = COMPLETED_PROMPT.format(
            user_message=ctx.user_message,
            result=result or "任务已完成",
        )

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
            max_tokens=512,
            temperature=0.5,
        )

        ctx.done = True

        return {
            "response": response,
            "state": State.COMPLETED,
            "questions": [],
            "skill_requests": [],
            "done": True,
            "plan": ctx.plan,
        }

    async def complete(self, session_id: str = "default", result: str = "") -> dict:
        """标记执行完成，进入 completed"""
        ctx = self.contexts.get(session_id)
        if not ctx:
            return {"error": "session not found"}
        ctx.state = State.COMPLETED
        return await self._do_completed(ctx, result)

    async def reset(self, session_id: str = "default") -> dict:
        """重置会话"""
        if session_id in self.contexts:
            del self.contexts[session_id]
        return {"success": True}

    def get_state(self, session_id: str = "default") -> dict:
        """获取当前状态"""
        ctx = self.contexts.get(session_id)
        if not ctx:
            return {"state": "no_session"}
        return {
            "state": ctx.state.value,
            "clarifying_round": ctx.clarifying_round,
            "answers": ctx.answers,
            "plan": ctx.plan,
            "done": ctx.done,
        }
