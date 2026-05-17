#!/usr/bin/env python
"""
AgentSymphony CLI 入口

用法：
  python agent_symphony_cli.py "你的需求"
  
或者交互模式：
  python agent_symphony_cli.py -i

示例：
  python agent_symphony_cli.py "我想搞量化交易"
"""

import sys
import os
import json

# 添加父目录到路径
SYMPHONY_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SYMPHONY_PATH)

from agent_symphony.skills.thinking import ThinkingSkill
from agent_symphony.skills.memory import MemorySkill
from agent_symphony.skills.search import SearchSkill
from agent_symphony.shared import SharedContext


def print_banner():
    print("=" * 50)
    print("🎵 AgentSymphony 技能交响乐")
    print("=" * 50)


def print_result(label, data, indent=2):
    """格式化打印结果"""
    prefix = " " * indent
    if isinstance(data, dict):
        print(f"{prefix}{label}:")
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                print_result(k, v, indent + 2)
            else:
                print(f"{prefix}  {k}: {v}")
    elif isinstance(data, list):
        print(f"{prefix}{label}:")
        for i, item in enumerate(data[:10], 1):
            print(f"{prefix}  {i}. {item}")
    else:
        print(f"{prefix}{label}: {data}")


def run_analysis(requirement: str, interactive: bool = False):
    """运行分析"""
    print(f"\n🎵 启动交响乐...")
    print(f"📝 需求: {requirement}\n")
    
    # 初始化
    context = SharedContext()
    thinking = ThinkingSkill()
    memory = MemorySkill()
    search = SearchSkill()
    
    # 注册技能
    context.register_skill("thinking", thinking)
    context.register_skill("memory", memory)
    context.register_skill("search", search)
    
    # 设置为用户直接调用
    context.set_caller("user", "cli")
    
    print("🔄 理解需求...\n")
    
    try:
        # 理解需求
        result = thinking.execute("understand", {"requirement": requirement})
        
        clarity = result.get("clarity_score", 0)
        can_proceed = result.get("can_proceed", False)
        message = result.get("message", "")
        
        print(f"📊 需求明确度: {clarity:.0%}")
        print(f"📝 分析: {message}\n")
        
        if not can_proceed:
            questions = result.get("questions", [])
            if questions:
                print(f"❓ 需要澄清 ({len(questions)} 个问题):\n")
                for i, q in enumerate(questions[:5], 1):
                    topic = q.get("topic", "")
                    q_text = q.get("question", "")
                    print(f"  {i}. [{topic}] {q_text}")
                
                if interactive:
                    print("\n请回答以上问题（输入 'q' 退出）:\n")
                    answers = []
                    for i, q in enumerate(questions[:5], 1):
                        answer = input(f"Q{i}: ").strip()
                        if answer.lower() == 'q':
                            print("\n👋 退出")
                            return
                        answers.append({"question": q.get("question"), "answer": answer})
                    
                    # 带答案继续
                    print("\n🔄 继续分析...\n")
                    result = thinking.execute("clarify", {
                        "requirement": requirement,
                        "answers": answers
                    })
        
        # 创建计划
        print("📋 制定计划...\n")
        plan_result = thinking.execute("plan", {"requirement": requirement})
        
        plan = plan_result.get("plan", [])
        if plan:
            for i, step in enumerate(plan[:5], 1):
                desc = step.get("description", step.get("task", ""))
                agent = step.get("agent", "")
                print(f"  {i}. {desc}")
                if agent:
                    print(f"     → 执行者: {agent}")
        else:
            message = plan_result.get("message", "暂无计划")
            print(f"  {message}")
        
        # 存储到记忆
        print("\n💾 存储到记忆...")
        store_result = memory.execute("store", {
            "type": "context",
            "content": f"用户需求: {requirement}",
            "importance": 0.8,
            "tags": ["requirement", "cli"]
        })
        
        if store_result.get("success"):
            print("  ✅ 已存储")
        
        print("\n" + "=" * 50)
        print("✅ 分析完成！")
        print("=" * 50)
        
        # 如果是交互模式，给出建议的下一步
        if interactive:
            print("\n💡 建议的下一步:")
            print("  - 输入 'memory' 查看记忆")
            print("  - 输入 'search XXX' 搜索信息")
            print("  - 输入 'plan' 查看完整计划")
            print("  - 输入 'q' 退出")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def interactive_mode():
    """交互模式"""
    print_banner()
    print("\n🎯 交互模式 - 随时输入 'q' 退出\n")
    
    context = SharedContext()
    memory = MemorySkill()
    search = SearchSkill()
    
    # 注册技能
    context.register_skill("memory", memory)
    context.register_skill("search", search)
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                print("\n👋 再见！")
                break
            
            if user_input.lower() == 'memory':
                # 查看记忆
                print("\n📚 记忆内容:")
                result = memory.execute("semantic_search", {"query": "", "limit": 10})
                for r in result.get("results", []):
                    print(f"  - [{r.get('type')}] {r.get('content', '')[:50]}...")
                continue
            
            if user_input.lower().startswith('search '):
                # 搜索
                query = user_input[7:].strip()
                print(f"\n🔍 搜索: {query}")
                result = search.execute("search", {"query": query, "max_results": 3})
                for r in result.get("data", {}).get("results", [])[:3]:
                    print(f"  - {r.get('title', 'Untitled')}")
                    print(f"    {r.get('url', '')}")
                continue
            
            # 其他当作需求处理
            run_analysis(user_input, interactive=True)
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break


def main():
    args = sys.argv[1:]
    
    if "-i" in args or "--interactive" in args:
        interactive_mode()
    elif len(args) == 0:
        print_banner()
        print("\n用法:")
        print("  python agent_symphony_cli.py \"你的需求\"")
        print("  python agent_symphony_cli.py -i")
        print("\n示例:")
        print('  python agent_symphony_cli.py "我想搞量化交易"')
    else:
        requirement = " ".join(args)
        run_analysis(requirement)


if __name__ == "__main__":
    main()