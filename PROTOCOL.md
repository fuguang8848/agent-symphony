# 技能互通协议

> Agent Symphony 技能交响乐的核心协议

## 1. 核心原则

### 1.1 thinking 是协调者
- thinking 负责理解用户需求
- thinking 决定何时调用哪个技能
- 其他技能不直接与用户交互

### 1.2 被动响应，主动学习
- 技能等待 thinking 调用
- 被调用时提供额外价值
- 主动将有价值的信息存入 memory

### 1.3 标准化接口
- 所有技能实现统一接口
- 通过事件总线通信
- 共享上下文传递信息

---

## 2. 接口标准

### 2.1 标准方法

```python
# 查询能力
result = skill.query(capability: str, context: dict) -> dict

# 执行动作
result = skill.execute(action: str, params: dict) -> dict

# 接收通知
skill.notify(event: str, data: dict)
```

### 2.2 返回格式标准

```python
{
    "success": bool,           # 是否成功
    "data": any,              # 返回数据
    "error": str | None,      # 错误信息
    "meta": {                 # 元信息
        "skill": str,         # 技能名
        "capability": str,    # 能力名
        "duration_ms": int    # 耗时
    }
}
```

---

## 3. 事件总线

### 3.1 事件类型

| 事件 | 说明 | 携带数据 |
|------|------|----------|
| `skill.register` | 技能注册 | `{skill_name, capabilities}` |
| `skill.unregister` | 技能注销 | `{skill_name}` |
| `memory.store` | 存储记忆 | `{type, content, tags}` |
| `memory.query` | 查询记忆 | `{query, limit}` |
| `search.execute` | 执行搜索 | `{query, engines, filters}` |
| `task.execute` | 执行任务 | `{task_id, plan}` |
| `task.completed` | 任务完成 | `{task_id, result}` |
| `task.failed` | 任务失败 | `{task_id, error}` |

### 3.2 事件格式

```python
{
    "event": str,             # 事件名
    "source": str,            # 发送方
    "target": str | None,     # 接收方（None 表示广播）
    "timestamp": float,       # 时间戳
    "data": dict             # 事件数据
}
```

---

## 4. 共享上下文

### 4.1 上下文结构

```python
{
    "session_id": str,                    # 会话 ID
    "user_id": str,                       # 用户 ID
    "task": {                             # 当前任务
        "id": str,
        "status": str,                    # pending/planning/executing/completed/failed
        "description": str,
        "plan": list[dict] | None,
        "result": any
    },
    "thinking": {                         # 思考状态
        "phase": str,                     # understanding/planning/executing/reflection
        "questions": list[str],           # 已提出的问题
        "answers": list[str],             # 用户回答
        "context": dict                   # 思考过程中的上下文
    },
    "memory": {                           # 记忆引用
        "recent": list[dict],             # 最近记忆
        "preferences": dict,              # 用户偏好
        "entities": dict                   # 实体知识
    },
    "search": {                           # 搜索状态
        "query": str,
        "results": list[dict],
        "cached": bool
    }
}
```

### 4.2 上下文传递

```python
# thinking 调用 memory
ctx = shared_context.get("thinking.context")
memory.store({
    "type": "preference",
    "content": ctx["user_preference"],
    "tags": ["learned"]
})

# memory 返回给 thinking
result = memory.query({
    "query": "用户对这个项目的偏好",
    "limit": 5
})
```

---

## 5. 技能调用规则

### 5.1 thinking 调用 memory

```python
# 存储用户偏好
thinking → memory.store({
    "type": "preference",
    "content": "用户喜欢简洁的回答",
    "source": "explicit"  # explicit | learned
})

# 查询上下文
thinking → memory.query({
    "query": "用户之前提过类似的问题吗",
    "types": ["task", "question"],
    "limit": 10
})
```

### 5.2 thinking 调用 search

```python
# 执行搜索
thinking → search.execute({
    "query": "最新的 AI Agent 框架",
    "engines": ["tavily", "exa"],  # 可选引擎
    "filters": {
        "relevance": 0.7,
        "freshness": "30d"
    }
})

# search 自动将结果存入 memory
search → memory.store({
    "type": "search_result",
    "content": result,
    "query": original_query
})
```

### 5.3 thinking 调用 team

```python
# 执行任务
thinking → team.execute({
    "task_id": "task_001",
    "plan": [
        {"action": "clone_repo", "params": {...}},
        {"action": "run_tests", "params": {...}}
    ],
    "check_completion": True
})

# team 完成后通知
team → thinking.notify("task.completed", {
    "task_id": "task_001",
    "result": {...},
    "completion_rate": 0.95
})
```

---

## 6. 错误处理

### 6.1 技能级别错误

```python
{
    "success": False,
    "error": {
        "code": "MEMORY_QUERY_FAILED",
        "message": "无法查询记忆",
        "details": "向量数据库连接超时"
    },
    "meta": {
        "skill": "memory",
        "retryable": True
    }
}
```

### 6.2 重试策略

| 错误类型 | 重试次数 | 间隔 |
|----------|----------|------|
| 网络超时 | 3 | 1s, 2s, 5s |
| Rate Limit | 5 | 1s, 2s, 5s, 10s, 30s |
| 服务不可用 | 3 | 5s, 10s, 30s |

---

## 7. 性能要求

| 指标 | 要求 |
|------|------|
| 接口响应时间 | < 500ms |
| 事件传递延迟 | < 100ms |
| 上下文传递 | < 50ms |
| 技能查询 | < 200ms |

---

_技能交响乐 · Agent Symphony_
