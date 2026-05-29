# agent-symphony 技能家族生产化架构方案

> 基于 YintaTriss/AgentSymphony + AgentTeam + Agent-superthinking + AgentSearch + AgentMemory
> 目标：新 OpenClaw 一键安装，立即拥有生产级多技能协作能力
> 最后更新：2026-05-29

---

## 一、定位与目标

**一句话：** 让 OpenClaw 具备多技能协作能力（thinking 对话澄清 + memory 记忆 + search 搜索 + team 执行）

**安装后体验：**
```
用户：启动交响乐帮我做一个博客系统
AI（作为指挥者）：
  clarifying → "你更关注前端还是后端？"
  planning → 制定计划：前端 Vue，后端 FastAPI，部署 Docker...
  executing → 调用 team skill 执行
  completed → 交付结果 + 存入记忆
```

---

## 二、整体架构

```
OpenClaw (Node.js)                    Python 后端
┌──────────────────────────┐       ┌─────────────────────────────┐
│ Skill Handler            │ HTTP  │ SymphonyServer (:18081)   │
│ · symphony skill         │──────▶│ · thinking RPC             │
│ · intercepts msg        │◀──────│ · memory RPC              │
│ · routes to backend     │       │ · search RPC              │
│                          │       │ · team RPC                │
│ sessions_spawn (原生)   │       └──────────────┬──────────────┘
│ · spawn sub-agent       │                      │
│                          │       ┌──────────────▼──────────────┐
│ skill-handler.js         │       │ OpenClaw SDK               │
│ · event-bus 集成         │       │ sessions.create/send        │
│ · model-router 集成      │       │ (Gateway RPC)              │
│ · exec-guard 集成        │       └─────────────────────────────┘
└──────────────────────────┘
```

---

## 三、目录结构

```
~/.openclaw/agent-symphony/          ← pip install -e . (Python包)
├── SKILL.md                          ← OpenClaw skill 入口
├── pyproject.toml                     ← Python 包配置
├── README.md
│
├── server/
│   ├── __init__.py
│   ├── symphony_server.py             ← HTTP RPC 服务器 (localhost:18081)
│   │
│   ├── skills/
│   │   ├── thinking_skill.py         ← 对话 + 澄清 + 规划
│   │   ├── memory_skill.py           ← 记忆存储（轻量文件版）
│   │   ├── search_skill.py           ← 复用 search-v.py
│   │   └── team_skill.py            ← 任务执行（sessions_spawn）
│   │
│   └── shared/
│       ├── context.py                ← 移植 AgentSymphony SharedContext
│       ├── registry.py               ← SkillRegistry
│       └── protocol.py               ← 技能互通协议常量
│
└── run_server.sh                     ← 启动脚本

~/.openclaw/plugin-skills/
├── symphony/                         ← OpenClaw Node.js 前端
│   ├── SKILL.md
│   └── handler.js                   ← HTTP RPC 客户端，调用 Python 后端
```

---

## 四、各模块设计

### 4.1 symphony_server.py（HTTP RPC 网关）

端口：18081

| 端点 | 方法 | 说明 |
|------|------|------|
| `/thinking/dialog` | POST | 对话 + 澄清 |
| `/thinking/plan` | POST | 生成执行计划 |
| `/memory/store` | POST | 存储记忆 |
| `/memory/query` | POST | 查询记忆 |
| `/search/execute` | POST | 执行搜索（调 search-v.py）|
| `/team/spawn` | POST | Spawn sub-agent（调 Gateway RPC）|
| `/team/status` | GET | 任务状态 |

### 4.2 thinking_skill.py（核心）

移植自 AgentSymphony thinking skill，改进点：

**输入：**
```json
{
  "message": "用户消息",
  "answers": {"背景": "新手"},
  "state": "clarifying|planning|executing|completed"
}
```

**输出：**
```json
{
  "response": "面向用户的回复",
  "state": "clarifying|planning|executing|completed",
  "questions": ["你更关注前端还是后端？"],
  "skill_requests": [{"skill": "search", "action": "execute", "params": {...}}],
  "done": false
}
```

**关键设计：**
- 状态机：clarifying → planning → executing → completed
- clarifying 阶段：最多 3 轮提问，然后强制进入 planning
- 调用 LLM 用 SharedContext 的 LLMProvider（自动从 OpenClaw 配置读取）
- skill_requests 由 OpenClaw skill handler 执行后回调

### 4.3 memory_skill.py（轻量版）

不做成 AgentMemory 那种四层架构，用简单的文件存储：

```
~/.agent-symphony/memory/
├── YYYY-MM-DD.md          # 每日日记（Markdown）
├── preferences.json       # 用户偏好
├── entities.json          # 实体知识
└── archive/              # 归档
```

**接口：**
```json
// POST /memory/store
{ "type": "preference|fact|plan|context", "content": "...", "tags": [...] }

// POST /memory/query
{ "query": "...", "limit": 5 }
```

### 4.4 team_skill.py

调用 OpenClaw Gateway RPC（sessions.create/send）执行任务：

```python
# 复用 AgentTeam OpenClaw SDK Backend 逻辑
def spawn_task(team_name: str, task: str, agent_type: str):
    # 1. sessions.create 创建 sub-agent session
    # 2. sessions.send 发送任务 + 协作协议（参考 AgentTeam Continuous Run Block）
    # 3. 轮询 session history 直到完成
    # 4. 返回结果
```

**协作协议（从 AgentTeam 移植）：**
- sub-agent 持续运行，不退出
- 每 30 秒检查一次 inbox
- 收到 "shutdown" 才退出
- 任务完成后报告给 leader

### 4.5 search_skill.py

直接复用 `tools/search-v.py`，不重复造轮子：

```python
def search(query: str, max_results: int = 5):
    result = subprocess.run(['python3', SEARCH_V_PATH, query], ...)
    return json.loads(result.stdout)
```

### 4.6 symphony SKILL.md

```markdown
---
name: symphony
version: 1.0.0
family: compound-engineering
role: multi-skill-orchestrator
description: 交响乐技能 — AI 担任指挥者，协调 thinking/memory/search/team 完成复杂任务
triggers:
  - 启动交响乐
  - 交响乐
  - symphony
  - 帮我做一个
  - 帮我开发
---

# 交响乐技能

## 工作流

clarifying → planning → executing → completed

## 触发方式

用户说"启动交响乐"、"交响乐"、"帮我做一个XXX" → AI 立即启动工作流
```

### 4.7 handler.js（Node.js 前端）

```javascript
// 接收 OpenClaw 消息，RPC 到 Python 后端
async function handle(params) {
  const { message, state } = params.data;
  
  // RPC 到 Python
  const response = await fetch('http://localhost:18081/thinking/dialog', {
    method: 'POST',
    body: JSON.stringify({ message, state })
  });
  
  return response.json();
}
```

---

## 五、安装流程（目标）

```bash
# 1. 一键安装
git clone https://ghproxy.net/.../agent-symphony.git ~/.openclaw/agent-symphony
cd ~/.openclaw/agent-symphony && pip install -e .

# 2. 一键启动后端
python -m server.symphony_server &

# 3. OpenClaw 自动加载 symphony skill
# 完成
```

---

## 六、关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| thinking 用 Python | ✅ | LLM 对话 + 状态机 Python 更自然 |
| team 用 OpenClaw SDK | ✅ | sessions_spawn 原生支持 sub-agent |
| memory 轻量文件版 | ✅ | 不过度设计，现有工具够用 |
| 通信协议 | HTTP RPC | 解耦，跨语言简单 |
| 搜索复用 search-v.py | ✅ | 不重复造轮子 |
| Session Keeper 模式 | ✅ | AgentTeam 的持续运行 + inbox 检查 |
| exec-guard 集成 | ✅ | skill-handler 的 exec 命令走白名单检查 |

---

## 七、参考来源

| 来源 | 借鉴内容 |
|------|---------|
| AgentSymphony/shared/context.py | LLMProvider（自动读取 OpenClaw 配置）|
| AgentSymphony/protocol.md | 技能互通协议 + 事件总线 |
| AgentTeam/core.py | CTTeam/CTAgent/CTTask/CTMessage |
| AgentTeam/openclaw_sdk_backend.py | Session Keeper + Continuous Run Block |
| AgentTeam/team/router.py | TaskRouter 四因素负载感知 |
| AgentTeam/alerts.py | AlertSystem 四级告警 |
| AgentTeam/team/mailbox.py | MailboxManager 文件队列 |
| Agent-superthinking | INDEX 路由 + 专家视角 |
| AgentSearch | URL 去重 + 多引擎 fallback + 排序权重 |
| AgentMemory | 四层架构理念（最终未采用重量实现）|
| claude-code-skills | exec 白名单 + memory_bridge 降级 |

---

## 八、里程碑

- [ ] M1: Python 后端框架 + thinking_skill 对话
- [ ] M2: memory_skill 轻量存储
- [ ] M3: team_skill + Session Keeper
- [ ] M4: search_skill 集成
- [ ] M5: symphony SKILL.md + handler.js
- [ ] M6: 安装脚本 + 一键部署
