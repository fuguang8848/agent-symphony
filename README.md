# Agent Symphony 技能交响乐

> 多技能协作工作流，让 AI 担任指挥，用户只管说需求

[English](README_en.md) · 简体中文

---

## 核心定位

**交响乐是一个多技能协作工作流，不是独立程序。**

安装后，AI 助手自动理解自己的角色：担任指挥者，协调 thinking/memory/search/AgentTeam 技能完成复杂任务。

用户不需要理解交响乐是什么——只需要说需求，AI 就会启动工作流。

这个工作流本质上，是ai担任指挥家，协调各个插件协作工作来规范完成复杂任务，用户则是“观众”，只需要欣赏，沟通，验收结果。
---

## 工作流

```
用户描述需求
    ↓
thinking 技能 ← AI助手（指挥者）主导：提问、澄清、分析
    ↓
memory 技能 ← 需求/计划明确后存入记忆
    ↓
planning（计划阶段）← AI助手制定执行计划
    ↓
memory 技能 ← 计划存入记忆
    ↓
AgentTeam ← AI助手调用 team 技能执行
```

**自然调用：** 过程中需要搜索时，AI助手自然调用 search 技能；需要记忆时调用 memory 技能。

---

## 触发方式

| 触发方式 | 说明 |
|---------|------|
| **被动触发** | 用户说"启动交响乐"、"交响乐" → AI立即启动 |
| **主动判断** | AI根据任务性质判断是否启动（需要多轮澄清/多技能协作/规划执行） |

用户说"交响乐是什么"只是询问，不会启动工作流。LLM会判断用户的真实意图。

---

## 四大核心技能

| 技能 | 职责 | 说明 |
|------|------|------|
| **thinking** | 对话 + 分析 | 主导需求探讨、提问澄清、制定计划 |
| **memory** | 记忆存储 | 需求/计划明确后存入，供后续参考 |
| **search** | 信息获取 | 需要时自然调用，获取实时信息 |
| **team** | 任务执行 | 调用 AgentTeam 执行具体任务 |

---

## AI 助手的角色

**我就是指挥家。** 

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
- **planning**：已理解需求，制定执行计划
- **executing**：调用 AgentTeam 执行
- **completed**：完成，输出结果

---

## 跨平台支持

| 平台 | 状态 |
|------|------|
| Windows | ✅ |
| macOS | ✅ |
| Linux | ✅ |

Python 3.10+，依赖 `subprocess`、`pathlib`，无平台特定代码。

---

## 安装

```bash
# 1. 克隆仓库
cd ~/.openclaw/workspace
git clone https://github.com/YintaTriss/AgentSymphony

# 2. 移动到正确位置
# 根据你的 OpenClaw skills 路径配置，选择以下之一：
mv AgentSymphony ~/.openclaw/workspace/.agents/skills/compound-engineering/agent-symphony

# 3. 重启 OpenClaw
openclaw gateway restart
```

---

## 快速开始

```python
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

# 启动
result = session.handle("我想做量化交易系统")
print(result["response"])
# → "你好，我是指挥。请告诉我你想要完成的事情吧。"

# 继续对话
result = session.handle("完全新手，不知道怎么入手")
print(result["response"])
# → "你最想了解哪个方面？"
```

---

## 工作流示例

```
用户: "我想做量化交易"
    ↓
thinking: "你最想了解哪个方面？"
    ↓
用户: "我想了解怎么入门"
    ↓
thinking: "好的，根据你的情况，我来制定一个学习计划..."
    ↓
memory: 存储学习计划
    ↓
planning: 生成执行计划
    ↓
AgentTeam: 开始执行学习任务
```

---

## 架构

```
用户消息（自然语言）
    ↓
OpenClaw 消息处理器
    ↓
Skill Matching（检测到交响乐需求）
    ↓
SymphonySession（AI助手指挥者在内部协调）
    ↓
thinking / memory / search / AgentTeam 技能
    ↓
返回 response 给用户
```

---

## 相关项目

- [AgentTeam](https://github.com/YintaTriss/AgentTeam) - 多 agent 协作框架
- [Agent-Superthinking](https://github.com/YintaTriss/Agent-Superthinking) - 超级思考能力（专家视角分析）
- [AgentSymphony](https://github.com/YintaTriss/AgentSymphony) - 本仓库

---

## 版本历史

### v2.0 (2026-05-18)
- **我就是指挥者**：删除伪需求"指挥家"角色，AI助手直接担任指挥
- 更新工作流描述：thinking探讨 → memory存储 → planning制定计划 → memory存储 → AgentTeam执行
- 双重触发机制：被动（用户说启动）+ 主动（LLM判断任务性质）
- 跨平台兼容：Windows/macOS/Linux

### v0.8 (2026-05-18)
- thinking 接入真实 LLM（MiniMax）
- thinking 在 planning 阶段用 LLM 生成执行计划
- 完整流程：clarifying → planning → executing → completed

### v0.7 (2026-05-17)
- 交响乐状态机完善
- 初始版本

---

_v2.0.0_
