# AgentSymphony OpenClaw 集成指南

## 概述

本文档说明 AgentSymphony（技能交响乐）如何集成到 OpenClaw 中。

**重要说明：** OpenClaw 的 WebChat 频道不支持 slash command 路由。用户无法通过 `/symphony` 触发技能。正确的方式是通过**自然语言描述需求**触发 OpenClaw 的 skill matching。

## 触发方式

OpenClaw 根据 SKILL.md 中的 description + examples 进行 skill matching：

| 用户输入 | 说明 |
|----------|------|
| `我想用交响乐` | 启动交响乐 |
| `交响乐帮我规划项目` | 带需求启动 |
| `我需要一个完整的量化交易系统` | 直接带需求 |

OpenClaw 识别到交响乐需求后，调用本技能的 Python 代码。

## 集成架构

```
用户消息（自然语言）
    ↓
OpenClaw 消息处理器
    ↓
Skill Matching（根据 description/examples）
    ↓
agent_symphony_openclaw.SymphonySession
    ↓
thinking.execute("dialog", {...})
    ↓
返回 response + skill_requests
    ↓
（可选）执行 skill_requests
    ↓
继续对话直到 done=True
```

## LLM 自动接入

交响乐的 LLM 智力来自 OpenClaw 运行时。技能不携带 API Key，通过 OpenClaw 上下文调用 LLM：

- OpenClaw 配置的模型（MiniMax、DeepSeek 等）
- 自动检测，无需额外配置

## 核心接口

### handle(message)

```python
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()
result = session.handle("我想做一个量化交易系统")

# result:
{
    "response": "* 根据你的需求...",      # 面向用户的回复
    "skill_requests": [],                   # 技能申请
    "state": "planning",                   # clarifying|planning|executing|completed
    "done": False,                         # 是否完成
    "questions": [],                       # 澄清问题
    "success": True
}
```

### execute_skill(skill, action, params)

处理技能申请（可选，不处理时交响乐降级为纯对话）：

```python
skill_map = {
    "thinking": ThinkingSkillInstance,
    "memory": MemorySkillInstance,
    "search": SearchSkillInstance,
    "team": TeamSkillInstance,
}

for req in result.get("skill_requests", []):
    skill = req["skill"]
    action = req["action"]
    params = req["params"]

    skill_result = skill_map[skill].execute(action, params)
    session.notify_skill_result(skill, skill_result)
```

### notify_skill_result(skill, result)

技能执行完成后回调：

```python
session.notify_skill_result("memory", {
    "success": True,
    "data": {...}
})
```

## 会话状态

每个用户维护独立的 SymphonySession：

```python
class SymphonySession:
    session_id: str            # 会话 ID
    thinking: ThinkingSkill     # thinking 技能实例
    memory: MemorySkill        # memory 技能实例
    search: SearchSkill        # search 技能实例
    phase: str                 # clarifying | planning | executing | completed
    done: bool                 # 是否完成
    created_at: float          # 创建时间
```

## 示例对话流

```
用户: "我想用交响乐"
    ↓
SymphonySession.handle("")
    ↓
返回: "你好，我是指挥。请告诉我你想要完成的事情吧。"

用户: "我想搞量化交易"
    ↓
SymphonySession.handle("我想搞量化交易")
    ↓
返回: "让我确认一下...\n\n1. 你目前有编程基础吗？\n2. 有具体时间要求吗？"

用户: "完全新手，没时间限制"
    ↓
SymphonySession.handle("完全新手，没时间限制", answers={...})
    ↓
返回: "明白了。需求已清晰，我来制定计划..."
    ↓
... 继续直到完成
```

## WebChat 限制

| 功能 | 状态 | 说明 |
|------|------|------|
| slash command (`/symphony`) | ❌ 不生效 | WebChat 不路由 slash command |
| 自然语言触发 | ✅ 生效 | 通过 skill matching 识别需求 |
| OpenClaw skill matching | ✅ 生效 | description + examples 匹配 |

## 测试

```bash
cd ~/.openclaw/workspace/.agents/skills/compound-engineering/agent-symphony
python agent_symphony_cli.py --test
```

---

_Last updated: 2026-05-17 v1.1.0_
