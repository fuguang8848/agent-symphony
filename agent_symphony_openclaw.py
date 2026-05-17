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
from typing import Optional

# 添加 AgentSymphony 路径
SYMPHONY_PATH = os.path.dirname(os.path.abspath(__file__))
PARENT_PATH = os.path.dirname(SYMPHONY_PATH)
if PARENT_PATH not in sys.path:
    sys.path.insert(0, PARENT_PATH)
if SYMPHONY_PATH not in sys.path:
    sys.path.insert(0, SYMPHONY_PATH)

from skills.thinking import ThinkingSkill
from skills.memory import MemorySkill
from skills.search import SearchSkill
from shared import SharedContext


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


# === OpenClaw 命令处理器 ===

def is_symphony_command(message: str) -> bool:
    """检查是否是交响乐命令"""
    return message.startswith("/symphony")


def extract_requirement(message: str) -> str:
    """从命令中提取需求"""
    if message.startswith("/symphony"):
        return message[10:].strip()
    return message


def create_session() -> SymphonySession:
    """创建交响乐会话"""
    return SymphonySession()


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
    
    print("\n" + "=" * 50)
    print("* Test Complete")