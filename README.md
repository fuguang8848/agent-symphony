# Agent Symphony 技能交响乐

> 多技能底层互通，1+1 > 2 的质变效果

[English](README_en.md) · 简体中文

---

## 概述

Agent Symphony（技能交响乐）是一个多技能互通的 Agent 框架。

**核心思想**：4 个技能（thinking/memory/search/team）底层互通，像交响乐团一样各司其职又协调一致。

```
用户: "帮我分析这个项目的问题"
    ↓
thinking (协调者/指挥家)
    ├──→ memory.store()    # 存储上下文，学习用户偏好
    ├──→ search.query()    # 搜索信息，实时获取知识
    └──→ team.execute()    # 协调 AgentTeam 执行任务
```

---

## 四大核心技能

| 技能 | 角色 | 核心功能 | LLM 接入 |
|------|------|----------|----------|
| **thinking** | 协调者（指挥家） | 理解需求、提问澄清、规划、用 LLM 生成执行计划 | ✅ 真实 LLM |
| **memory** | 记忆中心 | 存储上下文、学习用户偏好、向量检索 | ✅ 真实 LLM |
| **search** | 信息获取 | 搜索实时信息、补充知识 | ❌ 纯搜索 |
| **team** | 执行中心 | 接收 plan，调用 AgentTeam 真实执行任务 | ❌ Pure bridge |

---

## 交响乐流程

### 4 阶段状态机

```
clarifying  →  理解需求，评估明确度
    ↓
planning    →  LLM 生成执行计划，专家视角分析
              thinking 调用 LLMRouter 选择专家（87个）
              并行驱动各专家视角，给出建议
    ↓
executing   →  thinking 申请技能执行
              skill_requests = [
                  {skill: "memory", action: "store", ...},
                  {skill: "search", action: "search", ...},
                  {skill: "team", action: "execute_task", plan: [...]}
              ]
    ↓
completed   →  汇总结果，LLM 反思，done=True
```

### 技能调用顺序

1. **thinking** 收到需求 → 用 LLM 分析 → 问用户确认
2. 用户确认"好" → thinking 进入 executing
3. thinking 用 LLM 生成 plan → 申请 memory + search + team
4. **team** 收到 plan → 调用 AgentTeam (clawteam CLI)
5. **AgentTeam** spawn 子 agent → 通过 OpenClaw 使用 LLM
6. thinking 收到结果 → LLM 汇总 → 进入 completed

---

##thinking 技能详解

thinking 是交响乐的核心协调者（指挥家）。

**核心能力：**
- 真实调用 LLM（MiniMax 等）进行需求理解和规划
- LLMRouter 智能选择专家（87个专家：Python 类 + SKILL.md）
- Jury 并行驱动多专家视角分析
- 生成结构化的 skill_requests

**专家池：**
- Python 类定义的专家（18个）
- SKILL.md 声明的专家（69个）
- 包括：jobs、elon、turing、naval、darwin、乔布斯、毛泽东等

---

## team 技能详解

team 是纯桥接层，不做 LLM 分析。

**职责：**
- 接收 thinking 传来的 plan
- 调用 AgentTeam (clawteam CLI) 执行每个步骤
- 所有 LLM 分析由 AgentTeam 子 agent 完成

**执行流程：**
```
team._execute_task(plan)
    ↓
for each step in plan:
    clawteam run <action> --key1 value1 ...
    ↓
AgentTeam spawn 子 agent（通过 OpenClaw 使用 LLM）
```

---

## memory 技能详解

memory 是智能记忆系统。

**核心功能：**
- 插入式 LLM：使用 SharedContext 的 LLMProvider
- 记忆存储：上下文、偏好、模式
- 向量检索：语义相似度搜索
- LLM 增强：自动从交互中学习用户偏好

---

## search 技能

search 负责信息获取。

**核心功能：**
- 实时搜索：web_search 工具
- 不依赖 LLM（纯搜索）
- 为 thinking 和 team 提供实时信息

---

## 架构图

```
                    用户
                      │
                      ▼
               ┌─────────────┐
               │  thinking   │ ◄──── 真实 LLM (MiniMax)
               │  (协调者)    │
               └──────┬──────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ memory  │ │ search  │ │  team   │
    │(记忆)   │ │(搜索)   │ │(执行)   │
    └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │
         │           │           ▼
         │           │    ┌─────────────┐
         │           │    │  AgentTeam  │
         │           │    │ (clawteam)  │
         │           │    └──────┬──────┘
         │           │           │
         │           │           ▼
         │           │    ┌─────────────┐
         │           │    │ 子 agent    │ ◄──── OpenClaw LLM
         │           │    └─────────────┘
         ▼           ▼
      存储到 L3   返回搜索结果
      向量库
```

---

## 接入 OpenClaw

Agent Symphony 作为 OpenClaw 技能接入：

```python
from agent_symphony_openclaw import SymphonySession

s = SymphonySession()

# 第1轮：启动
r = s.handle("")

# 第2轮：提需求
r = s.handle("我想做一个chrome扩展程序，用来一键翻译网页")

# 第3轮：确认执行
r = s.handle("好", {})
# r['skill_requests'] 包含 memory + search + team

# 第4轮：执行技能
for req in r['skill_requests']:
    result = s.execute_skill(req["skill"], req["action"], req["params"])
    s.notify_skill_result(req["skill"], result)

# 第5轮：结果回调
r = s.handle("继续", {}, skill_results=all_results)
```

---

## 相关项目

- [AgentTeam](https://github.com/YintaTriss/AgentTeam) - 多 agent 协作框架
- [Agent-Superthinking](https://github.com/YintaTriss/Agent-Superthinking) - 超级思考能力（专家视角分析）
- [AgentSymphony](https://github.com/YintaTriss/AgentSymphony) - 本仓库

---

## 版本历史

### v0.8 (2026-05-18)
- thinking 接入真实 LLM（MiniMax）
- thinking 在 planning 阶段用 LLM 生成执行计划
- thinking 申请 team skill 执行（plan 包含 team.execute_task）
- team skill 还原为 pure bridge，调用 AgentTeam
- memory 已有 LLM 增强分析
- 完整流程：clarifying → planning → executing → completed

### v0.7 (2026-05-17)
- 交响乐状态机完善
- done 状态正确转换
- 初始版本

---

_楚灵 ⚔️ 2026-05-18_
