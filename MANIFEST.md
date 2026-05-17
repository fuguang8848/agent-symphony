# Agent Symphony 技能交响乐 - 家族清单

> 多技能底层互通，1+1 > 2 的质变效果

## 版本
- **版本**: 1.0.0
- **更新**: 2026-05-17

---

## 家族成员

| 技能 | 版本 | 仓库 | 角色 | 核心能力 |
|------|------|------|------|----------|
| **thinking** | 2.3+ | [Agent-Superthinking](https://github.com/YintaTriss/Agent-Superthinking) | 协调者 | 理解需求、深度分析、规划、反思、提问 |
| **memory** | 1.0+ | [MemorySkill](https://github.com/YintaTriss/MemorySkill) | 记忆中心 | 偏好、上下文、学习定位、智能遗忘 |
| **search** | 1.0+ | [SearchSkill](https://github.com/YintaTriss/SearchSkill) | 信息获取 | Web搜索、本地检索、爬虫、过滤、排序 |
| **team** | 0.7.6+ | [AgentTeam](https://github.com/YintaTriss/AgentTeam) | 执行者 | 任务执行、完成度检查 |

---

## 工作流

```
用户需求
    ↓
┌─────────────────────────────────────┐
│  阶段一：思考（Thinking）             │
│  - 向用户提问，澄清需求              │
│  - 动用 search 获取信息              │
│  - 动用 memory 记录偏好               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  阶段二：规划（Planning）            │
│  - 制定行动计划                      │
│  - 任务分解                          │
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

## 技能联动

```
thinking (协调者)
    ├──→ memory.store()    # 存储偏好/上下文
    ├──→ memory.query()   # 查询记忆
    ├──→ search.query()    # 搜索信息
    └──→ team.execute()   # 执行任务

search (被调用)
    └──→ memory.store()    # 存储有价值的信息

team (被调用)
    └──→ thinking.notify() # 执行完成通知
```

---

## 核心设计原则

1. **thinking 是协调者**，其他技能被动响应
2. **标准化接口**：query / execute / notify
3. **共享上下文**：技能间通过 context 传递信息
4. **主动学习**：memory 从交互中学习用户偏好
5. **智能过滤**：search 不只是搜索，还过滤噪音

---

## 目录结构

```
agent-family/
├── MANIFEST.md          # 本文件 - 家族清单
├── PROTOCOL.md          # 技能互通协议
├── README.md            # 家族介绍
│
├── shared/              # 共享模块
│   ├── registry.py      # 技能注册表
│   └── context.py      # 共享上下文
│
└── skills/             # 子技能
    ├── thinking/        # 思考技能
    ├── memory/          # 记忆技能
    ├── search/          # 搜索技能
    └── team/            # 团队技能
```

---

## 标准化接口

每个技能必须实现以下接口：

```python
class BaseSkill:
    def query(self, capability: str, context: dict) -> dict:
        """查询技能能力"""
        pass
    
    def execute(self, action: str, params: dict) -> dict:
        """执行动作"""
        pass
    
    def notify(self, event: str, data: dict):
        """接收事件通知"""
        pass
```

---

## 事件流

| 事件 | 发送方 | 接收方 | 说明 |
|------|--------|--------|------|
| `memory.store` | thinking/search | memory | 存储记忆 |
| `memory.query` | thinking | memory | 查询记忆 |
| `search.query` | thinking | search | 执行搜索 |
| `team.execute` | thinking | team | 执行任务 |
| `task.completed` | team | thinking | 任务完成 |
| `task.failed` | team | thinking | 任务失败 |

---

_技能交响乐 · Agent Symphony_
