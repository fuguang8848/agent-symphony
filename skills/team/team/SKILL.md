---
name: team
version: 0.7.6
family: agent-symphony
role: executor
description: 团队技能 - 任务执行、完成度检查（基于 AgentTeam）
---

# team 团队技能

> Agent Symphony 技能交响乐的执行者

## 角色定位

team 是技能交响乐的**执行者**，负责：
- 执行任务计划
- 协调子任务
- 检查完成度
- 自动重试

## 核心能力

| 能力 | 说明 |
|------|------|
| `team.execute` | 执行任务计划 |
| `team.delegate` | 委托子任务 |
| `team.check` | 完成度检查 |
| `team.status` | 获取团队状态 |

## 适配说明

本技能基于 AgentTeam 的 TeamManager 适配，桥接到 Agent Symphony 协议。

## 标准接口

```python
from agent_symphony.skills.team import get_skill_instance

# 获取技能实例
team = get_skill_instance()

# 查询能力
result = team.query("team.execute", {"task_id": "xxx", "plan": [...]})

# 执行动作
result = team.execute("execute_task", {
    "task_id": "task_001",
    "plan": [
        {"action": "clone_repo", "params": {...}},
        {"action": "run_tests", "params": {...}}
    ],
    "check_completion": True,
    "max_retries": 3
})

# 接收通知
team.notify("task.completed", {"task_id": "xxx", "result": {...}})
```

## 执行流程

```
thinking 调用 team.execute()
    ↓
[解析计划] 理解任务分解
    ↓
[执行子任务] 按顺序/并行执行
    ↓
[完成度检查] 自动验证结果
    ↓
[如有失败] 自动重试 (最多3次)
    ↓
[通知 thinking] 任务完成/失败
```

## 完成度检查

team 执行完任务后会自动检查：

1. **数量检查** - 是否完成了所有子任务
2. **质量检查** - 输出是否符合预期
3. **一致性检查** - 结果是否与计划匹配

## 与其他技能的联动

- `thinking` 调用 `team.execute()` 执行任务
- `team` 执行完成后通过 `notify()` 通知 `thinking`
- `team` 使用 `SharedContext` 存储执行上下文

---

_Agent Symphony 技能交响乐_
