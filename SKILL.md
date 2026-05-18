---
name: agent-symphony-integration
version: 2.0.0
family: compound-engineering
description: "AgentSymphony 交响乐技能。提供多轮对话式任务编排，自动协调 thinking/memory/search/team 技能。适用于复杂任务的需求澄清、多技能协作和规划执行。"
argument-hint: "[需求描述]"
triggers:
  - 启动交响乐
  - 交响乐
  - symphony
---

# AgentSymphony OpenClaw 集成

## ⚠️ AI 助手路由说明（重要）

**交响乐有两种启动方式，互补：**

### 被动触发（优先级最高）
用户明确说"启动交响乐"、"交响乐"时，AI 助手**立即启动**，不做任何判断。

### 主动判断（LLM 决定）
当用户描述的需求具有以下特征时，AI 助手应启动交响乐工作流：

1. **需要多轮澄清** — 目标不明确，需要提问才能搞清楚
2. **需要多技能协作** — 涉及 memory、search、team 等多个技能的配合
3. **需要规划执行** — 要分解任务、制定步骤、协调执行
4. **复杂/模糊任务** — 用户自己也不确定怎么做，需要分析讨论

**典型场景：**
- "我想做XXX但不知道怎么入手"
- "我需要规划一下这个项目"
- "这个东西怎么实现，你能帮我分析吗"
- "我想搞一个XX系统，帮我看看方案"

**不需要启动交响乐的情况：**
- 用户问题非常明确，不需要澄清
- 是简单的知识问答或直接操作
- 只需要单次回答，不需要多轮对话

**AI 助手（楚灵）在交响乐中的角色：**
- 作为协调者，整合 thinking/memory/search/team 的结果
- 和用户直接对话，辩证分析需求
- 最终把执行计划交给 team leader

---

## 概述

交响乐是一个**多技能协作工作流**，不是独立程序。AI 助手（楚灵）就是这个工作流的**指挥者**，没有额外的"指挥家"角色。

**工作流：**
```
用户描述需求
    ↓
thinking 技能 ← AI助手（楚灵）主导：提问、澄清、分析
    ↓
memory 技能 ← 需求/计划明确后存入记忆
    ↓
planning（计划阶段）← AI助手制定执行计划
    ↓
memory 技能 ← 计划存入记忆
    ↓
AgentTeam ← AI助手调用 team 技能执行
```

**自然调用：** 过程中需要搜索时，AI助手自然调用 search 技能；需要记忆时调用 memory 技能。不需要手动管理。

**AI 助手（楚灵）的职责：**
- 判断何时启动交响乐
- 通过 thinking 技能与用户对话澄清需求
- 协调所有技能的调用时机
- 整合结果，回应用户
- 调用 AgentTeam 执行计划

---

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

_AgentSymphony OpenClaw Integration v2.0.0_
