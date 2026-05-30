---
name: memory
version: 1.0.0
family: agent-symphony
role: memory-center
description: 记忆技能 - 存储、检索、学习、遗忘
---

# memory 记忆技能

> Agent Symphony 技能交响乐的记忆中心

## 角色定位

memory 是技能交响乐的**记忆中心**，负责：
- 存储用户偏好
- 管理上下文
- 智能检索
- 自动遗忘

## 核心能力

| 能力 | 说明 |
|------|------|
| `memory.store` | 存储记忆 |
| `memory.query` | 查询记忆 |
| `memory.learn` | 从交互中学习 |
| `memory.forget` | 主动遗忘 |
| `memory.preference` | 偏好管理 |

## 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `preference` | 用户偏好 | "喜欢简洁回答" |
| `context` | 上下文 | 项目背景、当前任务 |
| `entity` | 实体知识 | 人名、地名、概念 |
| `fact` | 事实 | 用户告诉我的事实 |
| `learned` | 学习来的 | 从交互中推断 |
| `search_result` | 搜索结果 | 搜索到的信息 |

## 智能遗忘

memory 不是所有事都记住，而是：
- **重要性高的优先记住**
- **访问频繁的优先记住**
- **久远的自动归档**

遗忘算法：
```
遗忘得分 = 访问频率(30%) + 重要性(30%) + 时效性(40%)
得分低的记忆会被遗忘
```

## 检索评分

查询记忆时，综合评分：
```
最终得分 = 文本相关(40%) + 时效性(30%) + 重要性(20%) + 访问频率(10%)
```

## 标准接口

```python
from agent_symphony.skills.memory import get_skill_instance

# 获取技能实例
memory = get_skill_instance()

# 存储记忆
memory.execute("store", {
    "type": "preference",
    "content": "用户喜欢分点回答",
    "importance": 0.8,
    "tags": ["回答风格"]
})

# 查询记忆
memory.query("memory.query", {
    "query": "用户的回答习惯",
    "types": ["preference", "learned"],
    "limit": 10
})

# 学习用户偏好
memory.execute("learn", {
    "interaction": "用户说这个方案不错",
    "preference": {"风格": "简洁"}
})

# 主动遗忘
memory.execute("forget", {
    "memory_id": "mem_123"
})

# 获取偏好
memory.query("memory.preference", {"key": "风格"})
```

## 与其他技能的联动

- `thinking` 调用 `memory.store()` 存储用户偏好
- `thinking` 调用 `memory.query()` 查询上下文
- `search` 自动将结果存入 `memory`
- `memory` 利用 `context` 共享上下文

---

_Agent Symphony 技能交响乐_
