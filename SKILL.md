---
name: agent-symphony-integration
version: 2.2.0
family: compound-engineering
description: "AgentSymphony 交响乐技能。定义多技能协作工作流规范，由 AI 助手（楚灵）作为指挥者执行。适用于复杂任务的需求澄清、多技能协作和规划执行。"
argument-hint: "[需求描述]"
triggers:
  - 启动交响乐
  - 交响乐
  - symphony
---

# AgentSymphony OpenClaw 集成

## 核心定位（最重要）

**交响乐是一份工作流规范，不是运行程序。AI 助手（楚灵）才是执行者。**

- 交响乐（SKILL.md）= 工作流规范文档，定义"做什么"
- AI 助手（楚灵）= 执行者，负责"怎么做"

AI 助手读懂 SKILL.md 后，按照规范调用各个技能完成工作流。交响乐本身不运行、不调用任何代码。

---

## 工作流（clarifying → planning → executing）

```
用户描述需求
    ↓
[clarifying] AI助手主导：提问、澄清、分析
    ↓
    调用 Agent-Superthinking 专家视角分析
    调用 memory 技能存入需求
    ↓
[planning] AI助手制定执行计划
    ↓
    调用 memory 技能存入计划
    ↓
[executing] AI助手协调执行
    ↓
    调用 AgentTeam 执行任务
    ↓
AI助手反思结果
```

---

## AI 助手在交响乐中的职责

**我（楚灵）就是交响乐的指挥者。**

- 读取并遵循 SKILL.md 定义的工作流
- 在 clarifying 阶段：主导提问澄清，调用专家视角分析
- 在 planning 阶段：直接制定执行计划
- 在 executing 阶段：协调 AgentTeam 执行
- 全程调用 memory/search/AgentTeam 等技能

---

## 状态机

```
clarifying（澄清）→ planning（计划）→ executing（执行）→ completed（完成）
```

- **clarifying**：AI助手（楚灵）主导提问澄清，调用 Agent-Superthinking 分析
- **planning**：AI助手直接制定执行计划
- **executing**：调用 AgentTeam 执行
- **completed**：反思总结

---

## 交响乐与 Agent-Superthinking 的关系

- **交响乐** = 工作流规范（SKILL.md）
- **Agent-Superthinking** = 专家视角分析工具（在 clarifying 阶段被 AI助手调用）

---

## 触发方式

### 被动触发（优先级最高）
用户说"启动交响乐"、"交响乐" → AI助手立即按规范执行工作流

### 主动判断
用户描述复杂需求 → AI助手自动启动交响乐工作流

---

_AgentSymphony OpenClaw Integration v2.2.0_
