"""
OpenClaw AgentSymphony 集成

提供 /symphony 命令的接入点

使用方式：
  from agent_symphony_openclaw import SymphonySession

  session = SymphonySession()
  result = session.handle("我想搞量化交易")
  print(result["response"])

  # 继续对话
  result = session.handle("完全新手")
  print(result["response"])
"""

import sys
import os
import json
import time
from typing import Optional, Callable

# 添加 AgentSymphony 路径
SYMPHONY_PATH = os.path.dirname(os.path.abspath(__file__))
PARENT_PATH = os.path.dirname(SYMPHONY_PATH)
if PARENT_PATH not in sys.path:
    sys.path.insert(0, PARENT_PATH)
if SYMPHONY_PATH not in sys.path:
    sys.path.insert(0, SYMPHONY_PATH)

from skills.thinking import ThinkingSkill
from skills.memory import MemorySkill, MemoryType
from skills.search import SearchSkill
from shared import SharedContext


def call_openclaw_gateway_rpc(method: str, params: dict = None) -> dict:
    """
    调用 OpenClaw Gateway RPC

    Args:
        method: RPC 方法名 (如 "memory.recall")
        params: 参数字典

    Returns:
        RPC 响应结果
    """
    import urllib.request
    import urllib.error

    # Gateway 地址（RPC 端点）
    gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")

    # 获取 token
    config_path = os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")
    token = "未设置"
    try:
        with open(config_path) as f:
            config = json.load(f)
            token = config.get("gateway", {}).get("auth", {}).get("token", "未设置")
    except:
        pass

    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params or {}
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if token and token != "未设置":
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        gateway_url + "/rpc",
        data=data,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            # 支持标准 RPC 和 AgentProtocol
            if "result" in result:
                return result["result"]
            return result
    except urllib.error.URLError as e:
        return {"error": str(e), "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def is_symphony_command(message: str) -> bool:
    """检查是否是交响乐命令"""
    return message.startswith("/symphony")


def extract_requirement(message: str) -> str:
    """从命令中提取需求"""
    if message.startswith("/symphony"):
        return message[10:].strip()
    return message


class SymphonySession:
    """
    交响乐会话 - 用于 OpenClaw 集成

    管理 thinking/memory/search 技能的完整生命周期
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"symphony_{id(self)}"
        self.context = SharedContext()
        self.thinking = ThinkingSkill()
        self.memory = MemorySkill()
        self.search = SearchSkill()

        # 链接技能
        self.thinking.link_skill("memory", self.memory)
        self.thinking.link_skill("search", self.search)

        # 标记来源
        self.context.set_caller("user", "openclaw")

        self._done = False

    def inject_user_memory(self, query: str, max_results: int = 5) -> dict:
        """
        主动从 OpenClaw 个人记忆中检索并注入到当前会话

        Args:
            query: 检索查询
            max_results: 最大注入条数

        Returns:
            {
                "injected_count": int,
                "memories": [...],
                "success": bool
            }
        """
        # 调用 OpenClaw Gateway RPC
        rpc_result = call_openclaw_gateway_rpc("memory.recall", {
            "query": query,
            "limit": max_results,
            "scope": "user"  # 只检索用户个人记忆
        })

        if rpc_result.get("error"):
            return {
                "injected_count": 0,
                "success": False,
                "error": rpc_result["error"]
            }

        # 解析返回的记忆
        items = rpc_result.get("result", [])
        if not items:
            items = rpc_result.get("items", [])
        if not items:
            items = rpc_result.get("memories", [])

        injected_count = 0
        for item in items:
            # 提取记忆内容
            content = item.get("content", "") or item.get("text", "")
            if not content:
                continue

            # 判断类型
            mem_type = MemoryType.CONTEXT.value
            if "偏好" in query or "喜欢" in query or "preference" in query.lower():
                mem_type = MemoryType.PREFERENCE.value
            elif "知识" in query or "fact" in query.lower():
                mem_type = MemoryType.FACT.value

            # 注入到 MemorySkill
            self.memory._store({
                "type": mem_type,
                "content": content,
                "importance": item.get("score", 0.5),
                "tags": ["openclaw_injected", "active"],
                "source": "openclaw",
                "metadata": {
                    "openclaw_id": item.get("id", ""),
                    "injected_at": time.time()
                }
            })
            injected_count += 1

        return {
            "injected_count": injected_count,
            "memories": items,
            "success": True
        }

    def handle(self, message: str, answers: dict = None, skill_results: dict = None) -> dict:
        """
        处理用户消息

        Args:
            message: 用户的消息
            answers: 用户对问题的回答（可选）
            skill_results: 技能执行结果回调（可选）

        Returns:
            {
                "response": "面向用户的回复",
                "skill_requests": [...],
                "state": "clarifying|planning|executing|completed",
                "done": bool
            }
        """
        if self._done and message:
            # 重置会话
            self.reset()

        # 如果消息中提到"交响乐"，先 LLM 判断用户是否想启动工作流
        if message and "交响乐" in message:
            intent = self._check_symphony_intent(message)
            if not intent:
                # 用户只是提到交响乐，不是想启动，正常回应
                return {
                    "response": f"交响乐是一个多技能协作工作流，如果你有复杂任务需要分析和规划，可以告诉我你的需求。",
                    "skill_requests": [],
                    "state": "completed",
                    "done": True,
                    "questions": [],
                    "success": True
                }

        # 检查是否需要主动检索记忆
        if message and not answers:
            # 从消息中提取可能的检索词
            memory_query = self._extract_memory_query(message)
            if memory_query:
                self.inject_user_memory(memory_query, max_results=3)

        result = self.thinking.execute("dialog", {
            "message": message or "",
            "answers": answers or {},
            "skill_results": skill_results or {}
        })

        data = result.get("data", {})
        self._done = data.get("done", False)

        return {
            "response": data.get("response", ""),
            "skill_requests": data.get("skill_requests", []),
            "state": data.get("state", "clarifying"),
            "done": self._done,
            "questions": data.get("questions", []),
            "success": result.get("success", False)
        }

    def _extract_memory_query(self, message: str) -> str:
        """
        从消息中提取记忆检索词

        简单实现：检查是否提到人、项目、偏好等
        """
        # 如果用户提到具体事物，尝试检索
        if len(message) > 10:
            # 返回消息前 50 字符作为检索词
            return message[:50]
        return ""

    def _check_symphony_intent(self, message: str) -> bool:
        """
        当消息中提到"交响乐"时，LLM 判断用户是否真的想启动工作流
        """
        prompt = f"User said: {message}\nDoes the user want to START the symphony workflow (not just mention it)? Answer only 'yes' or 'no'."

        try:
            response = self.context.llm.complete(prompt, None, max_tokens=32)
            response = response.strip().lower()
            return 'yes' in response and 'no' not in response[:5]
        except Exception:
            return False

    def execute_skill(self, skill: str, action: str, params: dict) -> dict:
        """
        执行技能（用于处理 skill_requests）

        Args:
            skill: 技能名 (memory/search/team)
            action: 动作名
            params: 参数

        Returns:
            技能执行结果
        """
        skill_instance = None
        if skill == "memory":
            skill_instance = self.memory
        elif skill == "search":
            skill_instance = self.search
        elif skill == "team":
            # team 技能需要额外初始化
            from skills.team import TeamSkill
            skill_instance = TeamSkill()

        if skill_instance:
            return skill_instance.execute(action, params)

        return {"success": False, "error": f"Unknown skill: {skill}"}

    def notify_skill_result(self, skill: str, result: dict, success: bool = True):
        """
        通知技能执行结果（回调给 thinking）
        """
        self.thinking.notify("skill.result", {
            "skill": skill,
            "result": result,
            "success": success
        })

    def reset(self):
        """重置会话"""
        self.context = SharedContext()
        self.thinking = ThinkingSkill()
        self.thinking.link_skill("memory", self.memory)
        self.thinking.link_skill("search", self.search)
        self.context.set_caller("user", "openclaw")
        self._done = False

    @property
    def is_done(self) -> bool:
        return self._done


# === 主入口（用于测试） ===

if __name__ == "__main__":
    print("=" * 50)
    print("* AgentSymphony OpenClaw Integration Test")
    print("=" * 50)

    session = SymphonySession()

    # 开场
    print("\n[1] 开场")
    r = session.handle("")
    print(f">>> {r['response']}")
    print(f">>> state={r['state']}, done={r['done']}")

    # 用户需求
    print("\n[2] 用户需求")
    r = session.handle("我想搞量化交易")
    print(f">>> {r['response'][:100]}")
    print(f">>> questions={len(r['questions'])}")

    # 回答问题
    print("\n[3] 回答问题")
    r = session.handle("完全新手，想学", {"背景": "完全新手", "目标": "实盘赚钱"})
    print(f">>> {r['response'][:100]}")

    # 测试主动记忆注入
    print("\n[4] 主动记忆注入测试")
    inj = session.inject_user_memory("石榴籽项目")
    print(f">>> injected={inj['injected_count']}, success={inj['success']}")

    print("\n" + "=" * 50)
    print("* Test Complete")