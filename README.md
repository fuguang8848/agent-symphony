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
thinking (协调者)
    ├──→ memory.store()    # 存储上下文
    ├──→ search.query()    # 搜索信息
    └──→ team.execute()    # 执行任务
```

---

## 四大核心技能

| 技能 | 仓库 | 角色 | 核心功能 |
|------|------|------|----------|
| **thinking** | [AgentSymphony](https://github.com/YintaTriss/AgentSymphony) | 协调者 | 理解需求、提问、规划、反思 |
| **memory** | [MemorySkill](https://github.com/YintaTriss/MemorySkill) | 记忆中心 | 向量检索、混合搜索、智能遗忘 |
| **search** | [SearchSkill](https://github.com/YintaTriss/SearchSkill) | 信息获取 | 多引擎搜索、结果路由 |
| **team** | [AgentTeam](https://github.com/YintaTriss/AgentTeam) | 执行者 | 任务执行、完成度检查 |

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Symphony                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐                                            │
│  │   thinking  │ ◄── 协调者（Conductor）                     │
│  └──────┬──────┘                                            │
│         │                                                   │
│    ┌────┴────┬────────────┐                                 │
│    ▼         ▼            ▼                                 │
│ ┌──────┐ ┌──────┐    ┌──────┐                                │
│ │memory│ │search│    │team  │                                │
│ └──┬───┘ └──┬───┘    └──┬───┘                                │
│    │        │           │                                   │
│    ▼        ▼           ▼                                   │
│ ┌──────────────────────────────┐                            │
│ │        Shared Context        │  ←── 共享上下文            │
│ │   • LLM Provider（插入式）    │                            │
│ │   • Caller 追踪               │                            │
│ │   • 结果路由                  │                            │
│ └──────────────────────────────┘                            │
│                                                             │
│ ┌──────────────────────────────┐                            │
│ │       Skill Registry         │  ←── 技能注册表           │
│ └──────────────────────────────┘                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 三大特性

### 1. 插入式 LLM

技能不硬编码 API Key，自动从环境变量读取用户配置：

```python
# 环境变量自动检测优先级
# OPENAI_API_KEY → DASHSCOPE_API_KEY → MINIMAX_API_KEY → DEEPSEEK_API_KEY

# skill 通过 SharedContext 获取 LLM
context = get_context()
result = context.call_llm("用户的问题是...")
embeddings = context.get_embeddings("文本")
```

**不管装在哪里，用的是什么大模型，都能自动适应。**

### 2. 结果路由

search 结果根据调用者决定输出方向：

| 调用者 | 输出方向 | 格式 |
|--------|----------|------|
| 用户直接调用 | → 用户 | 完整格式，含 meta |
| thinking 调用 | → thinking | 结构化数据 |
| team 调用 | → team | 简化数据 |

### 3. 技能全连通

```
thinking ←→ memory
thinking ←→ search
thinking ←→ team
team ←→ search
```

---

## 工作流程

```
用户需求
    ↓
┌─────────────────────────────────────┐
│  阶段一：思考（Thinking）             │
│  - 向用户提问，澄清需求              │
│  - 调用 search 获取信息              │
│  - 调用 memory 记录偏好              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  阶段二：规划（Planning）            │
│  - 制定行动计划                      │
│  - 向用户确认计划                    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  阶段三：执行（Team）                │
│  - 执行任务                          │
│  - 自我检查完成度                    │
│  - 如有问题自行调整重试              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  阶段四：反思（Thinking）             │
│  - 与用户讨论结果                    │
│  - 决定是否需要继续                  │
└─────────────────────────────────────┘
```

---

## 目录结构

```
agent-symphony/
├── MANIFEST.md          # 技能清单
├── PROTOCOL.md          # 技能互通协议
├── README.md            # 本文件
├── README_en.md         # English version
├── SKILL.md             # OpenClaw 技能入口
│
├── shared/              # 共享模块
│   ├── __init__.py      # 导出接口
│   ├── context.py       # 共享上下文（LLM插入式、调用者追踪）
│   └── registry.py      # 技能注册中心
│
├── skills/              # 核心技能
│   ├── thinking/        # 思考技能
│   │   ├── skill.py     # 协调者实现
│   │   └── SKILL.md     # OpenClaw 入口
│   ├── memory/          # 记忆技能
│   │   ├── skill.py     # 向量检索实现
│   │   └── SKILL.md     # OpenClaw 入口
│   ├── search/          # 搜索技能
│   │   ├── skill.py     # 多引擎搜索实现
│   │   └── SKILL.md     # OpenClaw 入口
│   └── team/            # 团队技能
│       ├── skill.py     # 任务执行实现
│       └── SKILL.md     # OpenClaw 入口
│
└── tests/               # 测试
    └── test_integration.py  # 集成测试
```

---

## 快速开始

### 1. 安装

```bash
# 克隆主仓库
git clone https://github.com/YintaTriss/AgentSymphony.git
cd AgentSymphony

# 安装依赖
pip install -e .
```

### 2. 基本使用

```python
from agent_symphony.skills.thinking import ThinkingSkill
from agent_symphony.shared import SharedContext

# 创建上下文（自动读取用户的 LLM 配置）
context = SharedContext()

# 创建 thinking 技能
thinking = ThinkingSkill()

# 执行理解流程
result = thinking.execute("understand", {
    "requirement": "帮我分析这个项目的问题"
})
```

### 3. 技能联动示例

```python
# thinking 调用 memory 存储偏好
thinking.call_memory("store", {
    "type": "preference",
    "content": "用户喜欢简洁的回复",
    "importance": 0.8
})

# thinking 调用 search 搜索信息
results = thinking.call_search("search", {
    "query": "OpenClaw skills documentation",
    "max_results": 5
})

# thinking 调用 team 执行任务
thinking.call_team("execute_task", {
    "plan": [{"task": "写代码", "agent": "coder"}]
})
```

---

## 标准接口

所有技能实现统一接口：

```python
class Skill:
    def query(self, capability: str, context: dict) -> dict:
        """查询技能能力"""
        
    def execute(self, action: str, params: dict) -> dict:
        """执行动作"""
        
    def notify(self, event: str, data: dict):
        """接收事件通知"""
```

---

## 设计原则

1. **thinking 是协调者** - 其他技能不直接与用户交互
2. **被动响应，主动学习** - 技能等待调用，但调用时会提供额外价值
3. **标准化接口** - 所有技能实现统一的 query/execute/notify 接口
4. **共享上下文** - 技能间通过 context 传递信息
5. **智能遗忘** - memory 自动管理记忆，过滤不再相关的信息

---

## 相关项目

| 项目 | 仓库 | 说明 |
|------|------|------|
| AgentSymphony | [GitHub](https://github.com/YintaTriss/AgentSymphony) | 主仓库（技能交响乐） |
| MemorySkill | [GitHub](https://github.com/YintaTriss/MemorySkill) | 独立记忆技能 |
| SearchSkill | [GitHub](https://github.com/YintaTriss/SearchSkill) | 独立搜索技能 |
| AgentTeam | [GitHub](https://github.com/YintaTriss/AgentTeam) | 多智能体协作框架 |
| Agent-Superthinking | [GitHub](https://github.com/YintaTriss/Agent-Superthinking) | 深度思考框架（thinking 的专家视角） |

---

## License

MIT

---

_技能交响乐 · Agent Symphony_
_让 AI 技能像交响乐一样和谐共鸣_