# AgentSymphony OpenClaw 集成指南

## 概述

本文档说明如何将 AgentSymphony（技能交响乐）集成到 OpenClaw 中，使用户可以通过对话方式与交响乐交互。

## 快速开始

### 1. 安装依赖

```bash
# 克隆 AgentSymphony 到 OpenClaw skills 目录
cd ~/.openclaw/workspace/.agents/skills/compound-engineering
git clone https://github.com/YintaTriss/AgentSymphony.git
```

### 2. 启动交响乐

用户输入 `/symphony` 或类似命令触发。

## 集成架构

```
用户消息 (/symphony 开头)
    ↓
OpenClaw 消息处理器
    ↓
识别 /symphony 命令
    ↓
创建 SymphonySession 或路由到现有 session
    ↓
调用 thinking.execute("dialog", {...})
    ↓
返回 response + skill_requests
    ↓
执行 skill_requests (可选)
    ↓
回调 thinking.notify("skill.result", {...}) (可选)
    ↓
继续对话循环直到 done=True
```

## 核心接口

### dialog 动作

thinking skill 的 `dialog` 动作是对话模式的入口：

```python
thinking = ThinkingSkill()
thinking.link_skill("memory", memory_instance)
thinking.link_skill("search", search_instance)

result = thinking.execute("dialog", {
    "message": "用户的消息",
    "answers": {},          # 用户对问题的回答
    "skill_results": {}     # 技能执行结果回调
})
```

### 返回值

```python
{
    "response": "面向用户的回复",
    "skill_requests": [
        {"skill": "memory", "action": "store", "params": {...}}
    ],
    "state": "clarifying|planning|executing|completed",
    "done": False,
    "questions": [...]  # 如果需要澄清
}
```

### skill.result 回调

当其他技能执行完成后，通知 thinking：

```python
thinking.notify("skill.result", {
    "skill": "memory",
    "result": {"success": True, "data": {...}},
    "success": True
})
```

## 会话状态

OpenClaw 需要维护 symphony session 的状态：

```python
class SymphonySession:
    session_key: str           # OpenClaw session key
    thinking: ThinkingSkill    # thinking skill 实例
    memory: MemorySkill         # memory skill 实例
    search: SearchSkill         # search skill 实例
    phase: str                  # clarifying | planning | executing | completed
    done: bool                  # 是否完成
    created_at: float           # 创建时间
```

## 消息路由伪代码

```python
async def handle_symphony_message(message: str, session_key: str):
    # 获取或创建 session
    session = get_or_create_symphony_session(session_key)
    
    # 调用 thinking dialog
    result = session.thinking.execute("dialog", {
        "message": message,
        "answers": {},
        "skill_results": {}
    })
    
    # 发送回复给用户
    await send_to_user(result["response"])
    
    # 处理技能申请
    for req in result.get("skill_requests", []):
        skill = req["skill"]
        action = req["action"]
        params = req["params"]
        
        # 执行技能
        skill_instance = get_skill_instance(skill)
        skill_result = skill_instance.execute(action, params)
        
        # 回调结果给 thinking
        session.thinking.notify("skill.result", {
            "skill": skill,
            "result": skill_result,
            "success": skill_result.get("success", False)
        })
    
    # 检查是否完成
    if result.get("done"):
        # 清理 session 或保持等待
        pass
    else:
        # 等待用户下一条消息
        pass
```

## 命令识别

OpenClaw 需要识别以下命令：

| 命令 | 触发条件 | 说明 |
|------|----------|------|
| `/symphony` | message.startswith("/symphony") | 启动交响乐 |
| `/symphony quit` | message == "/symphony quit" | 退出交响乐 |
| `/symphony restart` | message == "/symphony restart" | 重新开始 |

## 注意事项

1. **上下文维护** - 对话模式需要维护上下文，确保多次调用使用同一个 thinking 实例
2. **skill_requests 处理** - 如果不处理 skill_requests，交响乐仍可工作，只是不会调用其他技能
3. **回调时机** - skill.result 回调应在 skill 执行完成后立即调用
4. **状态清理** - done=True 后应清理 session 或标记为完成

## 测试

```bash
# 测试对话模式
cd ~/.openclaw/workspace/.agents/skills/compound-engineering/AgentSymphony
python agent_symphony_cli.py --test
```

## 示例对话流

```
用户: /symphony
    ↓
OpenClaw: (初始化 session)
    ↓
thinking.dialog({message: ""})
    ↓
返回: "🎵 你好，我是指挥。请告诉我你想要完成的事情吧。"
    ↓
OpenClaw 发送: "你好，我是指挥。请告诉我你想要完成的事情吧。"

用户: "我想搞量化交易"
    ↓
thinking.dialog({message: "我想搞量化交易"})
    ↓
返回: "🎵 让我确认一下：\n\n1. 你目前有编程基础吗？\n2. 有什么具体的时间要求吗？"
    ↓
OpenClaw 发送问题

用户: "完全新手，没时间限制"
    ↓
thinking.dialog({message: "完全新手，没时间限制", answers: {...}})
    ↓
返回: "明白了。需求已清晰，我来制定计划..."
    ↓
OpenClaw 发送计划

... 继续直到完成
```

---

_Last updated: 2026-05-17_