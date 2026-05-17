---
name: agent-symphony-integration
version: 1.1.0
family: compound-engineering
description: "AgentSymphony 交响乐技能。提供多轮对话式任务编排，自动协调 thinking/memory/search/team 技能。当用户想要交响乐辅助完成任务、或描述需要多轮澄清的需求时触发。"
argument-hint: "[需求描述]"
examples:
  - "我想用交响乐"
  - "交响乐帮我规划项目"
  - "我想搞量化交易"
  - "我需要做一个完整的项目规划"
---

# AgentSymphony OpenClaw 集成

## 概述

AgentSymphony（技能交响乐）是一个多技能协作框架，通过「指挥家 + 技能」模式完成复杂任务。

**架构：**
```
用户消息 → OpenClaw（检测到交响乐需求）→ SymphonySession（指挥家）
                                                ↓
                        thinking 技能 → LLM（分析、规划）
                        memory 技能  → LLM（记忆检索）
                        search 技能  → LLM（搜索、总结）
                        team 技能    → LLM（任务拆分）
```

**LLM 接入：** 交响乐本身不携带 LLM，智力来自 OpenClaw 运行时注入的 LLM 配置。技能通过 OpenClaw 上下文调用 LLM，无需额外配置。

## 触发方式

**用户不需要记忆命令。** 只需描述需求：

| 用户输入 | 说明 |
|----------|------|
| `我想用交响乐` | 启动交响乐 |
| `交响乐帮我规划项目` | 带需求启动 |
| `我需要一个能实盘的量化交易系统` | 直接带需求 |

OpenClaw 的 skill matching 会根据 description + examples 识别交响乐需求并触发本技能。

## 状态机

```
clarifying（澄清）→ planning（计划）→ executing（执行）→ completed（完成）
```

- **clarifying**：需求不明确，向用户提问
- **planning**：已理解需求，规划执行步骤
- **executing**：执行中，处理技能申请
- **completed**：完成，输出结果

## API

### Python 调用

```python
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()
result = session.handle("我想做一个量化交易系统")

# result:
{
    "response": "* 根据你的需求...",      # 面向用户的回复
    "skill_requests": [],                   # 技能申请列表
    "state": "planning",                   # 当前状态
    "done": False,                         # 是否完成
    "questions": [],                       # 澄清问题
    "success": True
}
```

### 处理技能申请（可选）

```python
for req in result.get("skill_requests", []):
    skill = req["skill"]           # "thinking" | "memory" | "search" | "team"
    action = req["action"]         # 技能动作
    params = req["params"]         # 动作参数

    # 执行技能（通过 OpenClaw 的 tools 或直接调用）
    skill_result = execute_skill(skill, action, params)

    # 回调结果
    session.notify_skill_result(skill, skill_result)
```

## 注意事项

1. **LLM 智力和 OpenClaw 共享** - 技能不携带 LLM，通过 OpenClaw 上下文调用
2. **skill_requests 可选** - 不处理技能申请时，交响乐仍可工作（降级为纯对话模式）
3. **会话隔离** - 每个用户有独立的 SymphonySession
4. **WebChat 限制** - slash command 在 WebChat 不触发技能，需通过自然语言触发

---

_AgentSymphony OpenClaw Integration v1.1.0_
