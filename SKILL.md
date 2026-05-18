---
name: agent-symphony-integration
version: 2.1.0
family: compound-engineering
description: "AgentSymphony 交响乐技能。提供多轮对话式任务编排，自动协调 thinking/memory/search/team 技能。适用于复杂任务的需求澄清、多技能协作和规划执行。"
argument-hint: "[需求描述]"
triggers:
  - 启动交响乐
  - 交响乐
  - symphony
---

# AgentSymphony OpenClaw 集成

## 核心原则（必须遵循）

**工作流的每个节点都必须调用 thinking 技能。**

交响乐是一个严格的工作流，不是自由发挥的对话。AI 助手不能自己判断如何回应——每一条用户消息都必须经过 thinking 技能分析，thinking 返回结果后才能回应用户。

```
用户消息
    ↓
[必须] thinking 技能分析 ← AI助手不得跳过
    ↓
thinking 返回结构化结果
    ↓
AI助手整合结果，回应用户
```

**违反这条原则就不是交响乐。**

---

## AI 助手路由说明（重要）

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

**AI 助手在交响乐中的职责：**
- 判断何时启动交响乐
- **每一句话都必须调用 thinking 技能分析**
- 通过 thinking 技能的返回结果与用户对话
- 协调所有技能的调用时机
- 整合 thinking 结果，回应用户

---

## 工作流（强制执行）

```
用户描述需求
    ↓
[必须] thinking 技能 ← 分析用户需求、提问澄清
    ↓
memory 技能 ← 需求/计划明确后存入记忆
    ↓
[必须] thinking 技能 ← 制定执行计划
    ↓
memory 技能 ← 计划存入记忆
    ↓
[必须] thinking 技能 ← 协调 AgentTeam 执行
    ↓
AgentTeam ← team 技能调用执行
    ↓
[必须] thinking 技能 ← 反思结果，评估是否达成目标
```

**每个箭头都代表一次 thinking 技能调用。AI 助手不能跳过 thinking 直接回应用户。**

---

## 状态机

```
clarifying（澄清）→ planning（计划）→ executing（执行）→ completed（完成）
```

- **clarifying**：thinking 分析需求，向用户提问澄清
- **planning**：thinking 生成执行计划
- **executing**：thinking 协调 team/memory/search 技能执行
- **completed**：thinking 反思总结，输出结果

## API

### Python 调用

```python
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

# 启动
result = session.handle("启动交响乐")

# 每一句话都必须通过 handle 传递给 thinking 技能
result = session.handle("我想做量化交易")

# result:
{
    "response": "* 根据你的需求...",      # thinking 分析后的回复
    "skill_requests": [],                   # 技能申请
    "state": "clarifying",                # 当前状态
    "done": False,                        # 是否完成
    "questions": [],                       # thinking 生成的问题
    "success": True
}
```

---

## 注意事项

1. **thinking 技能是核心** - 每条用户消息都必须经过 thinking 分析
2. **AI 助手不能跳过 thinking** - 直接回应用户等于破坏工作流
3. **会话隔离** - 每个用户有独立的 SymphonySession
4. **WebChat 限制** - slash command 在 WebChat 不触发技能，需通过自然语言触发

---

_AgentSymphony OpenClaw Integration v2.1.0_
