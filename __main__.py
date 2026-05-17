"""
AgentSymphony 入口脚本

用法：
  python -m agent_symphony "你的需求"

示例：
  python -m agent_symphony "帮我分析石榴籽项目的情况"
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_symphony.skills.thinking import ThinkingSkill
from agent_symphony.skills.memory import MemorySkill
from agent_symphony.skills.search import SearchSkill
from agent_symphony.shared import SharedContext


def main():
    if len(sys.argv) < 2:
        print("用法: python -m agent_symphony \"你的需求\"")
        print("示例: python -m agent_symphony \"帮我分析石榴籽项目\"")
        sys.exit(1)
    
    requirement = sys.argv[1]
    print(f"\n🎵 AgentSymphony 交响乐启动...")
    print(f"📝 需求: {requirement}\n")
    print("-" * 50)
    
    # 初始化共享上下文
    context = SharedContext()
    
    # 初始化技能
    thinking = ThinkingSkill()
    memory = MemorySkill()
    search = SearchSkill()
    
    # 链接技能到上下文
    context.register_skill("thinking", thinking)
    context.register_skill("memory", memory)
    context.register_skill("search", search)
    
    # 理解需求
    print("🔄 理解需求...\n")
    result = thinking.execute("understand", {"requirement": requirement})
    
    clarity = result.get("clarity_score", 0)
    can_proceed = result.get("can_proceed", False)
    
    print(f"📊 需求明确度: {clarity:.0%}")
    print(f"▶️  可执行: {'是' if can_proceed else '否'}")
    
    if not can_proceed:
        # 需要澄清
        questions = result.get("questions", [])
        if questions:
            print(f"\n❓ 需要澄清 ({len(questions)} 个问题):\n")
            for i, q in enumerate(questions[:5], 1):
                print(f"  {i}. {q.get('question', '')}")
            print("\n请回答这些问题后重试。")
        return
    
    # 生成计划
    print("\n📋 制定计划...\n")
    plan_result = thinking.execute("plan", {"requirement": requirement})
    
    plan = plan_result.get("plan", [])
    if plan:
        for i, step in enumerate(plan[:5], 1):
            desc = step.get("description", step.get("task", ""))
            print(f"  {i}. {desc}")
    
    # 存储到记忆
    print("\n💾 存储到记忆...")
    memory.execute("store", {
        "type": "context",
        "content": f"用户需求: {requirement}",
        "importance": 0.8,
        "tags": ["requirement"]
    })
    
    print("\n✅ 分析完成！")
    print("-" * 50)


if __name__ == "__main__":
    main()