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

## 核心原则

**工作流分阶段，每个阶段有明确的职责。**

- **clarifying 阶段**：调用 thinking 技能进行需求分析、提问澄清
- **planning 阶段**：AI助手（指挥者）直接制定执行计划
- **executing 阶段**：AI助手（指挥者）协调 AgentTeam 执行

AI助手在 clarifying 阶段不能跳过 thinking 技能，但在 planning 和 executing 阶段由 AI助手自行主导。

---

## 工作流（clarifying → planning → executing）

```
用户描述需求
    ↓
[clarifying] thinking 技能 ← AI助手主导：提问、澄清、分析
    ↓
memory 技能 ← 需求明确后存入记忆
    ↓
[planning] AI助手制定执行计划
    ↓
memory 技能 ← 计划存入记忆
    ↓
[executing] AI助手调用 team 技能
    ↓
AgentTeam ← 实际执行任务
    ↓
AI助手反思结果，评估目标达成
```

---

## 状态机

```
clarifying（澄清）→ planning（计划）→ executing（执行）→ completed（完成）
```

- **clarifying**：调用 thinking 技能，分析需求，向用户提问澄清
- **planning**：AI助手（指挥者）直接制定执行计划
- **executing**：调用 AgentTeam 执行，监控进度
- **completed**：反思总结，输出结果

---

## AI 助手路由说明

**交响乐有两种启动方式，互补：**

### 被动触发（优先级最高）
用户明确说"启动交响乐"、"交响乐"时，AI 助手**立即启动**，不做任何判断。

### 主动判断（LLM 决定）
当用户描述的需求具有以下特征时，AI 助手应启动交响乐工作流：

1. **需要多轮澄清** — 目标不明确，需要提问才能搞清楚
2. **需要多技能协作** — 涉及 memory、search、team 等多个技能的配合
3. **需要规划执行** — 要分解任务、制定步骤、协调执行
4. **复杂/模糊任务** — 用户自己也不确定怎么做，需要分析讨论

**不需要启动交响乐的情况：**
- 用户问题非常明确，不需要澄清
- 是简单的知识问答或直接操作
- 只需要单次回答，不需要多轮对话

---

## API

```python
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

# 启动
result = session.handle("启动交响乐")

# clarifying 阶段：thinking 分析用户需求
result = session.handle("我想做量化交易")

# result:
{
    "response": "* 根据你的需求...",      # thinking 分析后的回复
    "skill_requests": [],                   # 技能申请
    "state": "clarifying",                # 当前状态
    "done": False,
    "questions": [],                       # thinking 生成的问题
    "success": True
}
```

---

## 注意事项

1. **clarifying 阶段必须调用 thinking** - 这是唯一必须调用 thinking 的阶段
2. **AI 助手是指挥者** - planning 和 executing 由 AI助手直接主导
3. **会话隔离** - 每个用户有独立的 SymphonySession

---

_AgentSymphony OpenClaw Integration v2.1.0_
