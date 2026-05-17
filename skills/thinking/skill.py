"""
thinking 技能 - 协调者，带提问流程

Agent Symphony 技能交响乐的核心协调者
负责理解需求、提问澄清、规划、调用技能、反思

集成 Agent-Superthinking 专家视角分析能力
支持调用 memory/search/team 技能
支持区分用户直接调用 vs 技能间调用
"""

import time
import sys
import logging
from typing import Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from shared import (
    Skill,
    SkillCapability,
    SharedContext,
    get_context,
    get_registry,
    SkillRegistry,
)

# === Agent-Superthinking 集成 ===
# 添加 Agent-Superthinking 到 Python 路径
SUPER_THINKING_PATH = Path(__file__).parent.parent.parent.parent / "Agent-superthinking" / "src"
if str(SUPER_THINKING_PATH) not in sys.path:
    sys.path.insert(0, str(SUPER_THINKING_PATH))

try:
    from super_thinking.core.registry import Registry as SuperRegistry
    from super_thinking.core.jury import Jury, JuryResult
    from super_thinking.core.router import Router
    from super_thinking.perspectives._interface import PerspectiveOutput
    SUPERTHINKING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Agent-Superthinking 未安装: {e}")
    SUPERTHINKING_AVAILABLE = False
    SuperRegistry = None
    Jury = None
    JuryResult = None
    Router = None
    PerspectiveOutput = None


# === 预定义的专家视角配置 ===
# 用于需求分析的专家视角组合
DEFAULT_ANALYSIS_PERSPECTIVES = [
    "stakeholder",    # 利益相关者分析
    "meta_thinking",  # 元认知视角
    "risk_detail",    # 风险细节
    "verification",   # 验证视角
    "past_experience", # 过往经验
]


# 专门用于提问生成的专家视角
QUESTION_GENERATION_PERSPECTIVES = [
    "stakeholder",    # 芒格利益相关者 - 识别各方诉求
    "meta_thinking",  # 元认知 - 发现思维盲点
    "risk_detail",    # 风险视角 - 识别隐患问题
    "jobs",           # 乔布斯视角 - 产品/价值追问
    "vcp",            # VCP视角 - 节奏/阶段问题
]


@dataclass
class ThinkingConfig:
    """thinking 技能配置"""
    max_questions: int = 5  # 最大提问次数
    min_clarity_threshold: float = 0.7  # 需求明确度阈值
    
    # 提问相关的提示词
    clarify_prompt: str = """
你是一个需求分析专家。用户提出了一个需求，但可能不够清晰。
请分析用户的需求，识别以下模糊点：
1. 目标不明确 - 用户想达成什么？
2. 范围不清 - 包含什么？不包含什么？
3. 约束缺失 - 有什么限制条件？
4. 优先级不明 - 什么是关键的，什么是可选的？

请生成 1-3 个具体问题来澄清这些模糊点。
只输出问题，不要解释。每个问题单独一行。
"""
    
    # 需求评估提示词
    evaluate_prompt: str = """
评估以下需求是否足够清晰，可以开始执行。

需求：{requirement}

判断标准：
- 目标明确（能说出具体要达成什么）
- 范围清晰（知道包含什么）
- 约束明确（知道有什么限制）
- 可执行（能转化为具体任务）

请给出：
1. 明确度评分（0-1）
2. 是否可以开始执行（是/否）
3. 如果不能，还需要什么？
"""


@dataclass
class Question:
    """问题"""
    question: str
    topic: str  # 属于哪个模糊点
    answered: bool = False
    answer: str = ""


class ThinkingSkill:
    """
    Thinking 技能 - Agent Symphony 的协调者
    
    核心职责：
    1. 理解用户需求
    2. 提问澄清需求（集成 Agent-Superthinking 专家视角）
    3. 制定计划
    4. 调用其他技能（memory, search, team）
    5. 反思结果
    
    调用来源识别：
    - 用户直接调用：返回格式化的完整输出（包含 meta）
    - 技能间调用：返回纯数据结果，不包含包装
    """

    def __init__(self, config: ThinkingConfig | None = None):
        self.config = config or ThinkingConfig()
        self._context: SharedContext = get_context()
        self._registry: SkillRegistry = get_registry()
        self._questions: list[Question] = []
        self._clarity_score: float = 0.0
        self._call_source: str = "user"  # "user" | "skill" | "system"
        self._linked_skills: dict[str, Any] = {}  # 已链接的技能实例
        
        # === Agent-Superthinking Jury 初始化 ===
        if SUPERTHINKING_AVAILABLE:
            self._super_registry = SuperRegistry()
            self._super_registry.discover()
            self._router = Router(self._super_registry)
            self._jury = Jury(registry=self._super_registry, router=self._router)
        else:
            self._super_registry = None
            self._router = None
            self._jury = None

    # ==================== 技能链接 ====================
    
    def link_skill(self, skill_name: str, instance: Any) -> None:
        """
        链接外部技能实例
        
        用于技能间调用，避免通过 registry 绕路
        """
        self._linked_skills[skill_name] = instance
        logging.info(f"[Thinking] Linked skill: {skill_name}")

    def unlink_skill(self, skill_name: str) -> None:
        """取消链接技能"""
        if skill_name in self._linked_skills:
            del self._linked_skills[skill_name]

    def _get_skill_instance(self, skill_name: str) -> Optional[Any]:
        """
        获取技能实例（优先链接的，其次 registry）
        """
        # 1. 优先使用已链接的实例
        if skill_name in self._linked_skills:
            return self._linked_skills[skill_name]
        
        # 2. 通过 registry 获取
        skill = self._registry.get_skill(skill_name)
        if skill and skill.instance:
            return skill.instance
        
        return None

    # ==================== 调用来源识别 ====================

    def set_call_source(self, source: str) -> None:
        """
        设置调用来源
        
        Args:
            source: "user" | "skill" | "system"
        """
        self._call_source = source

    def _detect_call_source(self) -> str:
        """
        检测调用来源（自动检测）
        
        基于调用栈和上下文判断是用户直接调用还是技能间调用
        """
        # 检查是否通过 notify/event 触发（技能间调用特征）
        if hasattr(self._context, 'get'):
            # 通过 SharedContext 的特殊 key 传递调用来源
            source = self._context.get("_call_source", "user")
            if source:
                return source
        
        return self._call_source

    def _should_wrap_for_user(self) -> bool:
        """
        判断是否应该为用户包装输出
        
        用户直接调用：需要包含 meta、格式化消息
        技能间调用：返回纯数据
        """
        source = self._detect_call_source()
        return source == "user"

    # ==================== 标准接口 ====================

    def query(self, capability: str, context: dict | None = None) -> dict:
        """
        查询技能能力
        """
        capability_map = {
            "thinking.analyze": self._analyze,
            "thinking.ask": self._generate_questions,
            "thinking.plan": self._create_plan,
            "thinking.reflect": self._reflect,
            "thinking.evaluate": self._evaluate_clarity,
            "thinking.status": self._get_status,
            # 技能间调用接口
            "thinking.understand": self._understand_requirement,
            "thinking.clarify": self._clarify_with_questions,
            "thinking.execute": self._execute_plan,
        }
        
        if capability not in capability_map:
            return self._error_response(
                "CAPABILITY_NOT_FOUND",
                f"Capability {capability} not found"
            )
        
        # 设置调用来源为技能
        self.set_call_source("skill")
        result = capability_map[capability](context or {})
        
        # 技能间调用直接返回数据
        return result

    def execute(self, action: str, params: dict) -> dict:
        """
        执行动作
        
        Args:
            action: 动作名称
            params: 参数（可能包含 _call_source 字段）
        """
        start_time = time.time()
        
        # 检测调用来源
        if params.get("_call_source"):
            self.set_call_source(params.pop("_call_source"))
        else:
            self.set_call_source("user")
        
        try:
            if action == "understand":
                result = self._understand_requirement(params)
            elif action == "clarify":
                result = self._clarify_with_questions(params)
            elif action == "plan":
                result = self._create_plan(params)
            elif action == "execute":
                result = self._execute_plan(params)
            elif action == "reflect":
                result = self._reflect(params)
            elif action == "analyze":
                result = self._analyze(params)
            elif action == "evaluate":
                result = self._evaluate_clarity(params)
            elif action == "status":
                result = self._get_status(params)
            elif action == "dialog":
                result = self._dialog_mode(params)
            else:
                return self._error_response(
                    "ACTION_NOT_FOUND",
                    f"Action {action} not found",
                    include_meta=True
                )
            
            # 用户调用需要包装
            if self._should_wrap_for_user():
                return {
                    "success": True,
                    "data": result,
                    "meta": {
                        "skill": "thinking",
                        "action": action,
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "call_source": self._call_source
                    }
                }
            
            # 技能间调用直接返回数据
            return result
            
        except Exception as e:
            error = self._error_response(
                "EXECUTION_ERROR",
                str(e),
                include_meta=self._should_wrap_for_user()
            )
            if self._should_wrap_for_user():
                return error
            raise

    def notify(self, event: str, data: dict):
        """
        接收事件通知
        
        技能间通信的主要方式
        """
        # 设置调用来源为技能
        self.set_call_source("skill")
        
        if event == "user.response":
            self._handle_user_response(data)
        elif event == "task.completed":
            self._on_task_completed(data)
        elif event == "task.failed":
            self._on_task_failed(data)
        elif event == "skill.call":
            # 其他技能调用 thinking
            self._handle_skill_call(data)
        elif event == "context.update":
            # 更新上下文
            self._handle_context_update(data)
        elif event == "skill.result":
            # 技能执行结果（用于 dialog 模式回调）
            self._handle_skill_result(data)

    # ==================== 技能间调用处理 ====================

    def _handle_skill_call(self, data: dict) -> dict:
        """
        处理来自其他技能的调用
        
        返回纯数据，不包装
        """
        action = data.get("action")
        params = data.get("params", {})
        params["_call_source"] = "skill"
        
        return self.execute(action, params)

    def _handle_context_update(self, data: dict) -> dict:
        """
        处理上下文更新事件
        """
        key = data.get("key")
        value = data.get("value")
        
        if key and value is not None:
            self._context.set(key, value)
        
        return {"updated": True, "key": key}

    def _handle_skill_result(self, data: dict):
        """
        处理技能执行结果回调
        
        用于 dialog 模式中，接收其他技能执行完成后发回的结果
        """
        skill_name = data.get("skill")
        result = data.get("result", {})
        success = data.get("success", False)
        
        if success:
            logging.info(f"[Thinking] Skill {skill_name} completed successfully")
        else:
            error = data.get("error", "Unknown error")
            logging.warning(f"[Thinking] Skill {skill_name} failed: {error}")
        
        return {"processed": True, "skill": skill_name, "success": success}

    # ==================== 对话模式（指挥家）====================

    def _dialog_mode(self, params: dict) -> dict:
        """
        对话模式 - 指挥家的核心入口
        
        用于与用户进行多轮对话，直到问题解决。
        这是交响乐的"演奏模式"，指挥家引导整个对话流程。
        
        Args:
            params: 包含 message 和可选的 context 更新
            
        Returns:
            {
                "response": "面向用户的回复",
                "skill_requests": [...],  # 可选，需要执行的技能申请
                "skill_results": {...},   # 可选，技能执行结果
                "state": "clarifying|planning|executing|completed",
                "done": false             # 是否完成
            }
        """
        message = params.get("message", "")
        user_answers = params.get("answers", {})  # 用户对问题的回答
        skill_results = params.get("skill_results", {})  # 其他技能的结果
        
        # 处理技能结果回调
        if skill_results:
            self._process_skill_results(skill_results)
        
        # 检查是否是第一次对话（初始化）
        if not self._context.get("symphony_started"):
            return self._symphony_intro()
        
        # 处理用户回答
        if user_answers:
            self._process_user_answers(user_answers)
            # 重新评估需求（回答可能已补充足够信息）
            updated_req = self._context.get("requirement", "")
            result = self._understand_requirement({"requirement": updated_req})
            if result.get("can_proceed"):
                self._context.set("symphony_phase", "planning")
                self._context.set("clarity_score", result.get("clarity_score", 0.7))
                return self._generate_plan()
            # 仍需澄清，返回追问
            questions = result.get("questions", [])
            if questions:
                return {
                    "response": self._format_questions_for_user(questions),
                    "questions": questions,
                    "state": "clarifying",
                    "done": False,
                    "skill_requests": []
                }
            # 没有问题但还不能执行，继续等待
            return {
                "response": "还有什么需要我了解的吗？",
                "state": "clarifying",
                "done": False
            }
        elif message:
            # 新消息 -> 理解需求或继续对话
            return self._handle_user_message(message)
        
        # 根据当前状态决定下一步
        return self._decide_next_step()

    def _symphony_intro(self) -> dict:
        """
        交响乐开场白 - 指挥家自我介绍
        """
        self._context.set("symphony_started", True)
        self._context.set("symphony_phase", "clarifying")  # clarifying | planning | executing | completed
        self._context.set("user_answers", {})
        
        intro = (
            "* 你好，我是指挥。\n\n"
            "请告诉我你想要完成的事情吧。"
        )
        
        return {
            "response": intro,
            "state": "clarifying",
            "done": False,
            "meta": {
                "conductor": "thinking",
                "symphony": "agent-symphony"
            }
        }

    def _handle_user_message(self, message: str) -> dict:
        """
        处理用户消息
        """
        phase = self._context.get("symphony_phase", "clarifying")
        
        if phase == "clarifying":
            # 理解需求，评估明确度
            return self._clarify_requirement(message)
        elif phase == "planning":
            # 制定/确认计划
            return self._handle_plan_confirmation(message)
        elif phase == "executing":
            # 执行中，汇报进度
            return self._handle_execution_progress(message)
        elif phase == "completed":
            # 已完成，等待新需求或结束
            return self._handle_completion(message)
        
        return self._clarify_requirement(message)

    def _select_perspectives_for(self, phase: str, requirement: str) -> list[str]:
        """
        thinking 技能作为指挥家，主动选择需要调用的专家团/方法论
        
        Args:
            phase: 当前阶段 (clarifying | planning | executing)
            requirement: 用户需求
        
        Returns:
            perspective ID 列表
        """
        # 各阶段对应的专家团配置
        PHASE_PERSPECTIVES = {
            "clarifying": [
                "stakeholder",       # 利益相关者 - 理解各方诉求
                "meta_thinking",     # 元认知 - 发现思维盲点
                "risk_detail",       # 风险视角 - 识别隐患
                "magi_debate",       # 辩论 - 权衡利弊
                "doubt",             # 怀疑 - 费曼检验
                "past_experience",    # 过往经验 - 避免重复犯错
            ],
            "planning": [
                "stakeholder",       # 利益相关者 - 确认目标
                "jobs",             # 乔布斯 - 产品思维
                "naval",            # Naval - 决策方法论
                "risk_detail",       # 风险视角 - 评估风险
                "vcp",              # VCP - 节奏把控
                "magi_debate",       # 辩论 - 方案权衡
            ],
            "executing": [
                "verification",      # 验证 - 检查结果
                "stakeholder",      # 利益相关者 - 确认满意度
                "meta_thinking",    # 元认知 - 反思执行
                "risk_detail",      # 风险视角 - 监控风险
            ],
            "completed": [
                "meta_thinking",    # 元认知 - 总结经验
                "verification",     # 验证 - 确认结果
            ],
        }
        
        selected = PHASE_PERSPECTIVES.get(phase, PHASE_PERSPECTIVES["clarifying"])
        
        # 检查这些 perspective 是否在 registry 中可用
        available = [p.id for p in self._super_registry.list_all()] if self._super_registry else []
        if available:
            selected = [p for p in selected if p in available]
        
        return selected
    
    def _analyze_with_jury(self, requirement: str) -> dict:
        """
        使用 Agent-Superthinking Jury 进行多专家分析（thinking 指挥，主动选专家）
        
        Returns:
            dict with keys: clarity_score, can_proceed, needs, jury_result, response
        """
        if not self._jury:
            # Fallback to rule-based if Jury not available
            clarity, can_proceed, needs = self._evaluate_clarity_internal(requirement)
            return {
                "clarity_score": clarity,
                "can_proceed": can_proceed,
                "needs": needs,
                "jury_result": None,
                "response": None
            }
        
        try:
            # thinking 作为指挥家，主动选择需要调用的专家
            phase = self._context.get("symphony_phase", "clarifying")
            selected_perspectives = self._select_perspectives_for(phase, requirement)
            
            # 使用 selective 模式，只调用选中的专家
            result = self._jury.think(
                input=requirement,
                context={
                    "user_answers": self._context.get("user_answers", {}),
                    "phase": phase
                },
                mode="selective",
                selective_ids=selected_perspectives
            )
            
            # 汇总各专家观点
            summary_parts = []
            questions = []
            
            for pid, output in result.outputs.items():
                # 使用 analysis 或 summary 作为专家意见
                analysis_text = getattr(output, 'analysis', None) or getattr(output, 'summary', None) or ''
                if analysis_text:
                    summary_text = analysis_text[:300] if len(analysis_text) > 300 else analysis_text
                    summary_parts.append(f"**[{pid}]**: {summary_text}")
                # key_points 也加入
                key_points = getattr(output, 'key_points', None) or []
                if key_points:
                    for kp in key_points[:2]:
                        summary_parts.append(f"  → {kp[:100]}")
            
            # 判断是否可以继续
            has_expert_opinions = len(summary_parts) > 0
            can_proceed = has_expert_opinions and result.successful >= 2
            clarity_score = result.successful / max(len(selected_perspectives), 1)
            needs = questions[:3] if questions else []
            
            # 如果 Jury 没有产生任何专家意见，降级到规则判断
            if not has_expert_opinions:
                clarity, rule_proceed, rule_needs = self._evaluate_clarity_internal(requirement)
                clarity_score = clarity
                if rule_proceed:
                    can_proceed = True
                else:
                    can_proceed = False
                    needs = rule_needs if rule_needs else ['需求描述太短，请详细说明']
            
            # 生成综合响应
            if summary_parts:
                response_text = f"* 我请了 {len(result.outputs)} 位专家来帮你分析：\n\n" + "\n\n".join(summary_parts[:6])
                if questions:
                    response_text += "\n\n**还需要澄清：**\n"
                    for q in questions[:3]:
                        response_text += f"\n- {q}"
            else:
                response_text = None
            
            return {
                "clarity_score": clarity_score,
                "can_proceed": can_proceed,
                "needs": needs if needs else questions[:3],
                "jury_result": result,
                "response": response_text
            }
            
        except Exception as e:
            logging.warning(f"[Thinking] Jury analysis failed: {e}")
            clarity, can_proceed, needs = self._evaluate_clarity_internal(requirement)
            return {
                "clarity_score": clarity,
                "can_proceed": can_proceed,
                "needs": needs,
                "jury_result": None,
                "response": None
            }

    def _clarify_requirement(self, message: str) -> dict:
        """
        澄清需求阶段
        """
        # 使用 Jury 进行 AI 分析
        jury_result = self._analyze_with_jury(message)
        clarity = jury_result.get("clarity_score", 0)
        can_proceed = jury_result.get("can_proceed", False)
        
        # 存储需求到记忆
        self._store_requirement(message)
        
        if can_proceed:
            # 需求足够清晰，进入计划阶段
            self._context.set("symphony_phase", "planning")
            self._context.set("clarity_score", clarity)
            
            # 生成计划（带上专家分析结果）
            return self._generate_plan(jury_result)
        else:
            # 需要澄清，返回 Jury 生成的响应或默认问题
            needs = jury_result.get("needs", [])
            response = jury_result.get("response")
            
            if not response:
                response = "* 让我确认一下：\n\n"
                for need in needs:
                    response += f"- {need}\n"
            
            return {
                "response": response,
                "questions": [{"question": q} for q in needs],
                "state": "clarifying",
                "done": False,
                "skill_requests": []
            }
        clarity = result.get("clarity_score", 0)
        can_proceed = result.get("can_proceed", False)
        
        # 存储需求到记忆
        self._store_requirement(message)
        
        if can_proceed:
            # 需求足够清晰，进入计划阶段
            self._context.set("symphony_phase", "planning")
            self._context.set("clarity_score", clarity)
            
            # 生成计划
            return self._generate_plan()
        else:
            # 需要澄清，生成问题
            questions = result.get("questions", [])
            if not questions:
                # fallback: 使用简单问题
                questions = self._generate_default_questions(message)
            
            return {
                "response": self._format_questions_for_user(questions),
                "questions": questions,
                "state": "clarifying",
                "done": False,
                "skill_requests": []
            }

    def _format_questions_for_user(self, questions: list) -> str:
        """
        格式化问题，面向用户输出
        """
        if not questions:
            return "请告诉我更多细节吧。"
        
        intro = "* 让我确认一下：\n\n"
        
        q_list = []
        for i, q in enumerate(questions[:5], 1):
            topic = q.get("topic", "")
            text = q.get("question", str(q))
            q_list.append(f"{i}. **{text}**")
        
        return intro + "\n".join(q_list) + "\n\n请告诉我吧。"

    def _generate_default_questions(self, requirement: str) -> list:
        """
        生成默认问题（当专家视角没有生成问题时）
        """
        # 简单规则检测
        vague_words = ["搞", "弄", "优化", "改进", "看看", "研究", "了解"]
        has_vague = any(w in requirement.lower() for w in vague_words)
        
        questions = []
        
        if has_vague:
            questions.append({
                "question": "你能具体说说想达成什么目标吗？",
                "topic": "目标明确",
                "source": "rule_based"
            })
        
        if "等" in requirement or "什么的" in requirement:
            questions.append({
                "question": "具体包含哪些内容呢？",
                "topic": "范围界定",
                "source": "rule_based"
            })
        
        if len(questions) < 2:
            questions.append({
                "question": "有什么具体的时间要求或限制吗？",
                "topic": "约束条件",
                "source": "rule_based"
            })
        
        return questions

    def _process_user_answers(self, answers: dict) -> dict:
        """
        处理用户对问题的回答
        """
        # 存储回答
        existing_answers = self._context.get("user_answers", {})
        existing_answers.update(answers)
        self._context.set("user_answers", existing_answers)
        
        # 更新需求描述
        requirement = self._context.get("requirement", "")
        updated_requirement = self._build_requirement_from_answers(requirement, answers)
        self._context.set("requirement", updated_requirement)
        
        # 存储到记忆
        for key, value in answers.items():
            self._store_preference(key, value)
        
        return None  # 让下一步决定做什么

    def _build_requirement_from_answers(self, original: str, answers: dict) -> str:
        """
        根据回答构建更完整的需求描述
        """
        pieces = [original] if original else []
        for key, value in answers.items():
            if value:
                pieces.append(f"{key}: {value}")
        return "; ".join(pieces)

    def _generate_plan(self, jury_result: dict = None) -> dict:
        """
        生成计划
        """
        requirement = self._context.get("requirement", "")
        
        # 调用 team 技能制定计划（如果可用）
        team_result = self._delegate_to_team([
            {"task": "制定计划", "description": requirement}
        ])
        
        # 包含专家分析（如果有）
        expert_analysis = ""
        if jury_result:
            expert_response = jury_result.get("response", "")
            if expert_response:
                expert_analysis = expert_response + "\n\n"
        
        plan_text = f"* 根据你的需求，我帮你梳理了这样的路径：\n\n"
        
        # 简单计划（后续可以调用 team 的详细规划）
        steps = [
            f"* 需求：{requirement}",
            f"* 明确度：{self._context.get('clarity_score', 0):.0%}",
            "\n* 建议的下一步：",
            "1. 明确具体目标和范围",
            "2. 收集必要信息和资料",
            "3. 分解任务，逐步执行"
        ]
        
        plan_text += "\n".join(steps)
        plan_text = expert_analysis + plan_text
        plan_text += "\n\n这个方向对吗？我们可以继续细化。"
        
        return {
            "response": plan_text,
            "state": "planning",
            "done": False,
            "skill_requests": []
        }

    def _generate_learning_path(self) -> dict:
        """
        为完全新手生成量化交易学习路径（LLM驱动）
        """
        requirement = self._context.get("requirement", "")
        user_answers = self._context.get("user_answers", {})
        
        # 构造 prompt，让 LLM 生成个性化学习路径
        prompt = f"""你是量化交易教育专家。用户是一个完全新手，想要学习量化交易。

用户背景：
{requirement}

详细背景：
"""
        for key, value in user_answers.items():
            prompt += f"- {key}: {value}\n"
        prompt += """

请为这个用户生成一条从零基础到能实战的量化交易学习路径。要求：
1. 分阶段（3个阶段左右）
2. 每个阶段有具体行动项
3. 推荐免费/低成本的资源
4. 强调实操重要性
5. 最后给出选项让用户选择下一步

格式要求：
- 用 **标题** 标记重点
- 用 1️⃣ 2️⃣ 3️⃣ 标记选项
- 总量控制在500字以内
- 语气像一位耐心的导师在带新人
"""
        
        try:
            llm_response = self._context.call_llm(prompt)
            if "[LLM not available" in llm_response:
                # LLM 不可用，返回引导性回复
                return {
                    "response": "* 好，你是新手，我来带你走这条路。\n\n作为你的指挥家，我需要先了解你更多背景，才能给出最合适的路线规划。请告诉我：\n\n1. 你每周能投入多少时间学习？\n2. 你是更偏向动手实践，还是先想搞清楚原理？\n3. 有没有任何编程或金融相关的基础？",
                    "state": "planning",
                    "done": False,
                    "skill_requests": []
                }
        except Exception as e:
            llm_response = f"*[指挥家暂时无法思考，请稍后再试]*"
        
        return {
            "response": f"* 好，你是新手，我来带你走这条路。\n\n{llm_response}",
            "state": "planning",
            "done": False,
            "skill_requests": []
        }

    def _decide_next_step(self) -> dict:
        """
        根据当前状态决定下一步
        """
        phase = self._context.get("symphony_phase", "clarifying")
        
        if phase == "clarifying":
            return {
                "response": "还有什么需要我了解的吗？",
                "state": "clarifying",
                "done": False
            }
        elif phase == "planning":
            return {
                "response": "计划进行得怎么样了？需要调整吗？",
                "state": "planning",
                "done": False
            }
        elif phase == "executing":
            return {
                "response": "执行中...有什么进展我会告诉你。",
                "state": "executing",
                "done": False
            }
        
        return {
            "response": "有什么需要我帮忙的吗？",
            "state": "completed",
            "done": True
        }

    def _handle_plan_confirmation(self, message: str) -> dict:
        """
        处理用户对计划的确认/调整
        """
        msg_lower = message.lower()
        
        # 优先检查：用户表示迷茫 -> 直接给学习路径
        if any(w in msg_lower for w in ["不知道", "迷茫", "不会", "不懂", "怎么开始", "你指导", "你决定", "你安排", "带我", "教我"]):
            return self._generate_learning_path()
        
        # 检查：用户想跳过学习直接开始
        if any(w in msg_lower for w in ["不学习", "不学", "跳过学习", "不用学", "直接开始", "直接用", "不入门"]):
            return self._handle_skip_learning()
        
        if any(w in msg_lower for w in ["不对", "调整", "改", "不是"]):
            return {
                "response": "好的，请告诉我你想怎么调整？",
                "state": "planning",
                "done": False
            }
        
        if any(w in msg_lower for w in ["好", "行", "执行", "对", "没错"]):
            self._context.set("symphony_phase", "executing")
            return {
                "response": "* 明白，开始协调各方成员！\n\n我将调用 memory 记录你的需求，search 搜索相关信息，team 执行具体任务。\n\n稍等，正在启动...",
                "state": "executing",
                "done": False,
                "skill_requests": [
                    {"skill": "memory", "action": "store", "params": {"type": "context", "content": self._context.get("requirement", "")}},
                    {"skill": "search", "action": "search", "params": {"query": self._context.get("requirement", "")}}
                ]
            }
        
        return {
            "response": "请告诉我：可以开始执行吗？或者需要调整？",
            "state": "planning",
            "done": False
        }

    def _handle_skip_learning(self) -> dict:
        """
        处理用户想跳过学习直接开始的情况（LLM驱动）
        """
        requirement = self._context.get("requirement", "")
        user_answers = self._context.get("user_answers", {})
        
        # 构造 prompt
        prompt = f"""用户背景：
{requirement}
"""
        for key, value in user_answers.items():
            prompt += f"- {key}: {value}\n"
        prompt += """

用户说想用机器学习做量化交易，但不想学习基础知识。作为量化交易专家，你需要：
1. 诚实告诉他为什么至少需要理解基本概念（不能完全零基础）
2. 但理解他时间有限，给他一个「最低限度」的学习方案
3. 给出3条路线让他选择
4. 语气要务实、理解，但也要说实话

格式：
- 先说为什么不能完全零基础
- 再给最低限度方案（2-3天速成）
- 给出路线选择 1️⃣ 2️⃣ 3️⃣
- 总量400字以内
"""
        
        try:
            llm_response = self._context.call_llm(prompt)
            if "[LLM not available" in llm_response:
                # LLM 不可用，返回引导性回复
                return {
                    "response": "* 你的想法我理解。\n\n说实话，至少要懂一些基本概念才能做量化交易——不然就像蒙着眼睛开车。\n\n不过我理解你时间有限。请告诉我：\n\n1. 你每周能投入多少时间？\n2. 你更倾向于哪种学习方式？\n   - 先系统学习（2-4周）\n   - 速成+工具（1-2周）\n   - 用现成平台（几天）",
                    "state": "planning",
                    "done": False,
                    "skill_requests": []
                }
        except Exception as e:
            llm_response = f"*[指挥家暂时无法思考，请稍后再试]*"
        
        return {
            "response": f"* 你的想法我理解。{llm_response}",
            "state": "planning",
            "done": False,
            "skill_requests": []
        }

    def _handle_execution_progress(self, message: str) -> dict:
        """
        处理执行中的进度询问或新指令
        """
        return {
            "response": "* 执行中\n\n我在持续协调各方。有新进展会告诉你。\n\n你有什么要补充的吗？",
            "state": "executing",
            "done": False
        }

    def _handle_completion(self, message: str) -> dict:
        """
        处理已完成状态
        """
        # 检查是否有新需求
        if message and len(message) > 3:
            # 新需求，重新开始
            self._context.set("symphony_phase", "clarifying")
            self._context.set("requirement", message)
            return self._clarify_requirement(message)
        
        return {
            "response": "* 有什么需要再找我。交响乐随时待命！",
            "state": "completed",
            "done": True
        }

    def _process_skill_results(self, results: dict):
        """
        处理技能执行结果
        """
        for skill_name, result in results.items():
            if skill_name == "memory" and result.get("success"):
                self._context.set("memory_stored", True)
            elif skill_name == "search" and result.get("success"):
                self._context.set("search_results", result.get("data", {}))

    def _store_requirement(self, requirement: str):
        """
        存储需求到记忆
        """
        self._context.set("requirement", requirement)
        
        # 尝试调用 memory
        try:
            self.call_memory("store", {
                "type": "context",
                "content": requirement,
                "importance": 0.8,
                "tags": ["requirement", "symphony"]
            })
        except Exception as e:
            logging.warning(f"Failed to store requirement: {e}")

    def _store_preference(self, key: str, value: str):
        """
        存储用户偏好
        """
        try:
            self.call_memory("store", {
                "type": "preference",
                "content": value,
                "importance": 0.7,
                "tags": ["preference", key, "symphony"],
                "metadata": {"key": key}
            })
        except Exception as e:
            logging.warning(f"Failed to store preference: {e}")

    # ==================== 调用其他技能 ====================

    def call_memory(self, action: str, params: dict) -> dict:
        """
        调用 memory 技能
        
        技能间调用的标准方式
        """
        memory_skill = self._get_skill_instance("memory")
        
        if memory_skill:
            # 直接调用链接的实例
            params["_call_source"] = "skill"
            return memory_skill.execute(action, params)
        
        # 降级：通过 registry 调用
        result = self._registry.call("memory", "execute", action, params)
        
        if result.get("success"):
            return result.get("data", result)
        return result

    def call_search(self, action: str, params: dict) -> dict:
        """
        调用 search 技能
        """
        search_skill = self._get_skill_instance("search")
        
        if search_skill:
            params["_call_source"] = "skill"
            return search_skill.execute(action, params)
        
        result = self._registry.call("search", "execute", action, params)
        
        if result.get("success"):
            return result.get("data", result)
        return result

    def call_team(self, action: str, params: dict) -> dict:
        """
        调用 team 技能
        """
        team_skill = self._get_skill_instance("team")
        
        if team_skill:
            params["_call_source"] = "skill"
            return team_skill.execute(action, params)
        
        result = self._registry.call("team", "execute", action, params)
        
        if result.get("success"):
            return result.get("data", result)
        return result

    def _search_related_info(self, query: str) -> dict:
        """
        搜索相关信息（调用 search 技能）
        """
        return self.call_search("search", {
            "query": query,
            "max_results": 5
        })

    def _retrieve_memories(self, query: str, memory_type: str = None) -> dict:
        """
        检索相关记忆（调用 memory 技能）
        """
        params = {
            "query": query,
            "limit": 10
        }
        if memory_type:
            params["types"] = [memory_type]
        
        return self.call_memory("retrieve", params)

    def _delegate_to_team(self, plan: list[dict]) -> dict:
        """
        委托任务给 team 技能执行
        """
        return self.call_team("execute_task", {
            "plan": plan,
            "check_completion": True
        })

    # ==================== 核心方法 ====================

    def _understand_requirement(self, params: dict) -> dict:
        """
        理解需求
        """
        requirement = params.get("requirement", "")
        
        # 更新上下文
        self._context.set_thinking_phase("understanding")
        self._context.create_task(description=requirement)
        
        # 评估需求明确度
        clarity, can_proceed, needs = self._evaluate_clarity_internal(requirement)
        self._clarity_score = clarity
        
        return {
            "requirement": requirement,
            "clarity_score": clarity,
            "can_proceed": can_proceed,
            "needs_clarification": needs,
            "message": self._get_understanding_message(clarity, can_proceed, needs)
        }

    def _clarify_with_questions(self, params: dict) -> dict:
        """
        通过提问澄清需求
        """
        requirement = params.get("requirement", "")
        max_q = params.get("max_questions", self.config.max_questions)
        
        # 重置问题列表
        self._questions = []
        
        # 生成问题
        questions = self._generate_clarifying_questions(requirement)
        
        # 限制数量
        questions = questions[:max_q]
        
        # 转换为 Question 对象
        self._questions = [
            Question(question=q["question"], topic=q["topic"])
            for q in questions
        ]
        
        # 更新上下文
        for q in self._questions:
            self._context.add_question(q.question)
        
        return {
            "questions": [
                {"question": q.question, "topic": q.topic, "answered": q.answered}
                for q in self._questions
            ],
            "count": len(self._questions),
            "message": self._format_questions_message()
        }

    def _generate_clarifying_questions(self, requirement: str) -> list[dict]:
        """
        生成澄清问题
        
        优先使用 Agent-Superthinking 的专家视角分析需求，
        综合多个视角的洞见生成更有深度的问题。
        如果 SuperThinking 不可用，则降级到基于规则的简单实现。
        """
        # 尝试使用 Agent-Superthinking 专家视角
        if SUPERTHINKING_AVAILABLE:
            return self._generate_questions_with_superthinking(requirement)
        else:
            return self._generate_questions_rule_based(requirement)

    def _generate_questions_with_superthinking(self, requirement: str) -> list[dict]:
        """
        使用 Agent-Superthinking 专家视角生成问题
        
        流程：
        1. 初始化 Jury 并运行多个专家视角
        2. 收集各视角的 key_points 和 warnings
        3. 基于专家洞见生成针对性问题
        """
        questions = []
        context = {
            "source": "thinking_skill",
            "phase": "question_generation",
            "requirement": requirement,
        }

        try:
            # 创建 Jury 实例
            registry = SuperRegistry()
            registry.discover()
            jury = Jury(registry=registry, timeout_per_perspective=30.0)

            # 运行多个专家视角分析需求
            jury_result: JuryResult = jury.think(
                input=requirement,
                context=context,
                mode="force_all",
            )

            # 收集各视角的洞见
            insights = self._collect_perspective_insights(jury_result)

            # 基于洞见生成问题
            questions = self._derive_questions_from_insights(requirement, insights, jury_result)

            # 如果专家视角生成的问题太少，补充默认问题
            if len(questions) < 2:
                questions.extend(self._generate_default_questions(requirement))

        except Exception as e:
            logging.warning(f"SuperThinking 分析失败，降级到规则方法: {e}")
            return self._generate_questions_rule_based(requirement)

        # 去重并限制数量
        seen = set()
        unique_questions = []
        for q in questions:
            qid = q["question"][:20]
            if qid not in seen:
                seen.add(qid)
                unique_questions.append(q)

        return unique_questions[:self.config.max_questions]

    def _collect_perspective_insights(self, jury_result: JuryResult) -> dict:
        """
        收集各专家视角的洞见
        """
        insights = {
            "key_points": [],
            "warnings": [],
            "stakeholder_asks": [],
            "risk_questions": [],
            "meta_questions": [],
            "all_analysis": [],
        }

        for output in jury_result.get_outputs():
            pid = output.perspective_id

            for kp in output.key_points:
                insights["key_points"].append({
                    "perspective": pid,
                    "point": kp,
                })

            for w in output.warnings:
                insights["warnings"].append({
                    "perspective": pid,
                    "warning": w,
                })

            if pid == "stakeholder":
                insights["stakeholder_asks"] = output.key_points[:3]
            elif pid in ["risk_detail", "risk"]:
                insights["risk_questions"] = output.key_points[:3]
            elif pid == "meta_thinking":
                insights["meta_questions"] = output.key_points[:3]

            if output.analysis:
                insights["all_analysis"].append({
                    "perspective": pid,
                    "name": output.perspective_name,
                    "analysis": output.analysis[:300],
                })

        return insights

    def _derive_questions_from_insights(
        self, requirement: str, insights: dict, jury_result: JuryResult
    ) -> list[dict]:
        """
        基于专家视角洞见派生问题
        """
        questions = []

        # === 利益相关者视角 ===
        if insights["stakeholder_asks"]:
            for ask in insights["stakeholder_asks"][:1]:
                if "激励" in ask or "利益" in ask or "谁在" in ask:
                    questions.append({
                        "question": "这个需求涉及哪些相关方？各方的核心诉求和利益是什么？",
                        "topic": "利益相关者识别",
                        "source": "stakeholder",
                    })
            for ask in insights["stakeholder_asks"]:
                if "博弈" in ask or "竞争" in ask or "零和" in ask:
                    questions.append({
                        "question": "这个场景中存在博弈或竞争关系吗？各方的立场是什么？",
                        "topic": "博弈结构",
                        "source": "stakeholder",
                    })

        # === 风险视角 ===
        if insights["risk_questions"]:
            for rq in insights["risk_questions"][:1]:
                questions.append({
                    "question": "实现这个目标可能遇到哪些风险或障碍？哪个环节最容易出问题？",
                    "topic": "风险识别",
                    "source": "risk_detail",
                })

        # === 元认知视角 ===
        if insights["meta_questions"]:
            for mq in insights["meta_questions"][:1]:
                if "假设" in mq or "盲点" in mq or "偏见" in mq:
                    questions.append({
                        "question": "你这个需求背后有哪些隐含假设？有没有可能被忽视的盲点？",
                        "topic": "假设与盲点",
                        "source": "meta_thinking",
                    })

        # === 从 key_points 提炼问题 ===
        for kp_info in insights["key_points"]:
            kp = kp_info["point"]
            if len(kp) < 10:
                continue
            if "？" in kp or "?" in kp:
                continue
            if "【" in kp and "】" in kp:
                tag_content = kp.split("】")[1].strip() if "】" in kp else kp
                if len(tag_content) > 5 and len(tag_content) < 100:
                    questions.append({
                        "question": f"关于「{tag_content[:30]}」，你有什么具体考虑？",
                        "topic": "细节澄清",
                        "source": kp_info["perspective"],
                    })

        # === 从 warnings 生成问题 ===
        for warn_info in insights["warnings"]:
            w = warn_info["warning"]
            if len(w) > 10 and "？" not in w:
                questions.append({
                    "question": f"关于「{w[:40]}」，你打算如何应对？",
                    "topic": "风险应对",
                    "source": warn_info["perspective"],
                })

        return questions

    def _generate_default_questions(self, requirement: str) -> list[dict]:
        """生成默认问题"""
        questions = []
        req_lower = requirement.lower()

        vague_goals = ["搞", "弄", "弄好", "搞明白", "优化", "改进", "看看"]
        if any(vg in req_lower for vg in vague_goals):
            questions.append({
                "question": "你能具体说说想要达成的目标是什么吗？",
                "topic": "目标明确",
                "source": "rule_based",
            })

        if "等" in requirement or "什么的" in requirement or "相关内容" in requirement:
            questions.append({
                "question": "具体包含哪些内容？有没有明确的范围？",
                "topic": "范围清晰",
                "source": "rule_based",
            })

        if "尽量" in requirement or "可能" in requirement or "最好" in requirement:
            questions.append({
                "question": "有什么具体的限制条件吗？比如时间、成本、质量要求？",
                "topic": "约束明确",
                "source": "rule_based",
            })

        if len(requirement) < 20:
            questions.append({
                "question": "能详细描述一下你的需求吗？包括背景、目标、期望等。",
                "topic": "详细描述",
                "source": "rule_based",
            })

        if not questions:
            questions.append({
                "question": "这个任务有什么截止时间或特殊要求吗？",
                "topic": "约束条件",
                "source": "rule_based",
            })
            questions.append({
                "question": "完成的标准是什么？怎么才算做好了？",
                "topic": "完成标准",
                "source": "rule_based",
            })

        return questions

    def _generate_questions_rule_based(self, requirement: str) -> list[dict]:
        """基于规则的提问生成（降级方案）"""
        return self._generate_default_questions(requirement)

    def _evaluate_clarity_internal(self, requirement: str) -> tuple[float, bool, list[str]]:
        """评估需求明确度"""
        clarity = 0.5
        needs = []
        
        if len(requirement) < 10:
            clarity = 0.2
            needs.append("需求描述太短，请详细说明")
        elif len(requirement) > 500:
            clarity = 0.6
        else:
            clarity = 0.7
        
        clear_verbs = ["创建", "删除", "修改", "实现", "完成", "修复", "测试", "部署", "更新"]
        if any(v in requirement for v in clear_verbs):
            clarity += 0.1
        
        vague_words = ["等等", "什么的", "大概", "可能", "也许"]
        if any(v in requirement for v in vague_words):
            clarity -= 0.2
            needs.append("需求描述有些模糊，请更具体一些")
        
        clarity = max(0.0, min(1.0, clarity))
        can_proceed = clarity >= self.config.min_clarity_threshold
        
        return clarity, can_proceed, needs

    def _evaluate_clarity(self, params: dict) -> dict:
        """评估需求明确度"""
        requirement = params.get("requirement", "")
        clarity, can_proceed, needs = self._evaluate_clarity_internal(requirement)
        
        return {
            "clarity_score": clarity,
            "can_proceed": can_proceed,
            "threshold": self.config.min_clarity_threshold,
            "needs_clarification": needs
        }

    def _handle_user_response(self, data: dict):
        """处理用户回复"""
        answer = data.get("answer", "")
        question_index = data.get("question_index", -1)
        
        if 0 <= question_index < len(self._questions):
            self._questions[question_index].answered = True
            self._questions[question_index].answer = answer
            self._context.add_answer(answer)
            self._clarity_score = min(1.0, self._clarity_score + 0.15)
            
            return {
                "processed": True,
                "new_clarity_score": self._clarity_score,
                "remaining_questions": sum(1 for q in self._questions if not q.answered)
            }
        
        return {"processed": False, "error": "Invalid question index"}

    def _create_plan(self, params: dict) -> dict:
        """创建计划"""
        requirement = params.get("requirement", "")
        
        self._context.set_thinking_phase("planning")
        
        plan = [
            {"action": "analyze", "description": "分析需求", "order": 1},
            {"action": "search", "description": "搜索相关信息", "order": 2},
            {"action": "execute", "description": "执行任务", "order": 3},
            {"action": "review", "description": "检查结果", "order": 4},
        ]
        
        self._context.set_task_plan(plan)
        
        return {
            "plan": plan,
            "task_id": self._context.get_task().id if self._context.get_task() else None,
            "message": f"已创建计划，共 {len(plan)} 个步骤"
        }

    def _execute_plan(self, params: dict) -> dict:
        """执行计划（调用 team 技能）"""
        plan = params.get("plan", self._context.get_task().plan if self._context.get_task() else [])
        
        self._context.set_thinking_phase("executing")
        
        return {
            "status": "executing",
            "plan": plan,
            "message": "计划已提交给 team 技能执行"
        }

    def _reflect(self, params: dict) -> dict:
        """反思"""
        self._context.set_thinking_phase("reflection")
        result = params.get("result", {})
        
        return {
            "reflection": "执行完成，请告诉我还需要做什么调整吗？",
            "result_summary": str(result)[:200],
            "suggestions": self._generate_suggestions(result)
        }

    def _analyze(self, params: dict) -> dict:
        """分析"""
        return {"analysis": "Analysis not yet implemented"}

    def _get_status(self, params: dict) -> dict:
        """获取状态"""
        task = self._context.get_task()
        
        return {
            "phase": self._context.get_thinking_phase(),
            "task_id": task.id if task else None,
            "clarity_score": self._clarity_score,
            "pending_questions": sum(1 for q in self._questions if not q.answered),
            "conversation_history": self._context.get_conversation_history()
        }

    # ==================== 事件处理 ====================

    def _on_task_completed(self, data: dict):
        """任务完成事件"""
        task_id = data.get("task_id")
        result = data.get("result")
        self._context.set_task_result(result)
        self._context.update_task_status("completed")

    def _on_task_failed(self, data: dict):
        """任务失败事件"""
        self._context.update_task_status("failed")

    # ==================== 辅助方法 ====================

    def _error_response(self, code: str, message: str, include_meta: bool = False) -> dict:
        """生成错误响应"""
        if include_meta:
            return {
                "success": False,
                "error": {"code": code, "message": message}
            }
        return {"success": False, "error": {"code": code, "message": message}}

    def _get_understanding_message(self, clarity: float, can_proceed: bool, needs: list[str]) -> str:
        """生成理解反馈消息"""
        if can_proceed:
            return f"需求理解完成，明确度 {clarity:.0%}。可以开始执行。"
        else:
            msg = f"需求还不够明确，明确度 {clarity:.0%}。"
            if needs:
                msg += " 需要澄清：" + " ".join(needs)
            return msg

    def _format_questions_message(self) -> str:
        """格式化问题消息"""
        if not self._questions:
            return "需求已经足够明确，可以开始执行。"
        
        msg = "为了更好地帮助你，我有几个问题想确认：\n\n"
        for i, q in enumerate(self._questions, 1):
            answered = "✅" if q.answered else "❓"
            msg += f"{i}. {q.question} {answered}\n"
        
        return msg

    def _generate_suggestions(self, result: Any) -> list[str]:
        """生成建议"""
        return [
            "检查结果是否符合预期",
            "是否需要调整方向",
            "是否继续深化"
        ]


def get_skill_instance(config: ThinkingConfig | None = None) -> ThinkingSkill:
    """获取 thinking 技能实例"""
    return ThinkingSkill(config=config)
