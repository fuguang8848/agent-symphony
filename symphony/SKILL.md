---
name: symphony
version: 0.1.0
family: agent-symphony
role: multi-skill-orchestrator
description: 交响乐技能 — AI 担任指挥者，协调 thinking/memory/search/team 完成复杂任务
triggers:
  - 启动交响乐
  - 交响乐模式
  - symphony
---

# 交响乐技能

> 参考 AgentSymphony + AgentTeam + Agent-superthinking 设计

## 工作流

```
clarifying（需求澄清）→ planning（制定计划）→ executing（执行）→ completed（完成）
```

## 状态说明

| 状态 | 说明 |
|------|------|
| clarifying | 向用户提问，澄清需求（最多3轮） |
| planning | 制定执行计划 |
| executing | 调用技能执行计划 |
| completed | 交付结果 |

## 触发方式

用户说"启动交响乐"、"交响乐模式"、"symphony"时，AI 启动交响乐工作流。

## 内部技能

- **thinking**: 状态机驱动的对话 + 澄清 + 规划
- **memory**: 记忆存储（偏好/事实/计划/上下文）
- **search**: 信息检索（复用 search-v.py）
- **team**: 多任务执行（通过 sessions_spawn）

## 技术架构

```
OpenClaw (Node.js skill handler)
    ↓ HTTP RPC
Python 后端 (:18081)
    ├── thinking_skill.py   ← LLM 对话 + 状态机
    ├── memory_skill.py     ← 文件存储
    ├── search_skill.py     → search-v.py
    └── team_skill.py       → sessions_spawn
```
