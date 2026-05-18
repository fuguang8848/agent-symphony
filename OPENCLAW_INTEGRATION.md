# AgentSymphony OpenClaw 集成指南

## 安装说明

### 新用户安装步骤

1. **克隆仓库**
   ```bash
   cd ~/.openclaw/workspace
   git clone https://github.com/YintaTriss/AgentSymphony
   ```

2. **移动到正确位置**
   ```bash
   # 如果 OpenClaw 的 skills 目录在 .agents/skills/compound-engineering/
   mv AgentSymphony ~/.openclaw/workspace/.agents/skills/compound-engineering/agent-symphony
   ```
   或者，把 `AgentSymphony/` 里的 `agent-symphony/` 目录（即 skills/ 和相关文件）放到你的 `.agents/skills/` 下。

3. **重启 OpenClaw**
   ```bash
   openclaw gateway restart
   ```

---

## 概述

AgentSymphony（技能交响乐）是一个多技能协作**工作流**，不是独立程序。AI 助手（楚灵）就是这个工作流的**指挥者**，没有额外的"指挥家"角色。

**AI 助手（楚灵）在交响乐中的职责：**
- 判断何时启动交响乐（被动触发 + 主动判断）
- 通过 thinking 技能与用户对话澄清需求
- 协调所有技能的调用时机（memory、search、AgentTeam）
- 整合结果，回应用户
- 调用 AgentTeam 执行计划

## 触发方式（重要）

**被动触发：** 用户说"启动交响乐"、"交响乐"、"symphony" → AI助手立即启动

**主动判断：** 用户描述复杂需求（需要多轮澄清、多技能协作、规划执行）→ AI助手自动判断启动

## 触发判断示例

| 用户输入 | 是否启动交响乐 |
|----------|--------------|
| `启动交响乐` | ✅ 立即启动 |
| `交响乐帮我做量化交易` | ✅ 立即启动 |
| `交响乐是什么` | ❌ 只是询问，不是启动 |
| `我想做量化交易但不知道怎么做` | ✅ AI判断后启动 |
| `1+1等于几` | ❌ 简单问答，不启动 |

## 工作流

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

## 架构

```
用户消息（自然语言）
    ↓
OpenClaw 消息处理器
    ↓
Skill Matching（检测到交响乐需求）
    ↓
SymphonySession（AI助手楚灵在内部协调）
    ↓
thinking / memory / search / AgentTeam 技能
    ↓
返回 response 给用户
```

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

## 会话状态

```
clarifying（澄清）→ planning（计划）→ executing（执行）→ completed（完成）
```

- **clarifying**：需求不明确，向用户提问
- **planning**：已理解需求，规划执行步骤
- **executing**：执行中，调用 AgentTeam 做事
- **completed**：完成，输出结果

## WebChat 限制

| 功能 | 状态 | 说明 |
|------|------|------|
| slash command (`/symphony`) | ❌ 不生效 | WebChat 不路由 slash command |
| 自然语言触发 | ✅ 生效 | 通过 skill matching 识别需求 |
| OpenClaw skill matching | ✅ 生效 | description + triggers 匹配 |

## 测试

```bash
cd ~/.openclaw/workspace/.agents/skills/compound-engineering/agent-symphony
python test_symphony_integration.py
```

---

_Last updated: 2026-05-18 v2.0.0_
