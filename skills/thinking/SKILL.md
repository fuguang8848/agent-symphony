---
name: thinking
version: 2.3.0
family: agent-symphony
role: coordinator
description: 思考技能 - 协调者，负责理解需求、提问、分析、规划、反思
---

# thinking 思考技能

> Agent Symphony 技能交响乐的协调者（Conductor）

## 角色定位

thinking 是技能交响乐的**协调者**，类似于交响乐中的指挥家。

核心职责：
1. **理解需求** - 分析用户说的话，评估明确度
2. **提问澄清** - 识别模糊点，向用户提问
3. **制定计划** - 分解任务，制定执行方案
4. **调用技能** - 协调 memory、search、team 执行任务
5. **反思结果** - 评估结果，与用户讨论

## 核心能力

| 能力 | 说明 |
|------|------|
| `thinking.analyze` | 深度分析 |
| `thinking.ask` | 生成澄清问题 |
| `thinking.evaluate` | 评估需求明确度 |
| `thinking.plan` | 制定行动计划 |
| `thinking.reflect` | 反思总结 |

## 工作流程

```
用户需求
    ↓
[理解阶段] 分析需求，评估明确度
    ↓
[提问阶段] 如不明确，向用户提问 ← 【新增】
    ↓
[规划阶段] 制定行动计划
    ↓
[执行阶段] 调用 team 执行
    ↓
[反思阶段] 评估结果，与用户讨论
```

## 提问流程

当需求不够明确时，thinking 会自动生成澄清问题：

```
需求: "帮我优化一下这个项目"
    ↓
识别模糊点：
- 目标不明确：优化什么？
- 范围不清：包含什么？
- 约束缺失：有什么限制？
    ↓
生成问题：
1. 你想优化哪个方面？（性能/可维护性/功能）
2. 有什么具体的指标要求吗？
3. 项目的技术栈是什么？
    ↓
等待用户回答 → 更新上下文 → 继续
```

## 判定标准

| 明确度 | 状态 | 行动 |
|--------|------|------|
| ≥ 0.7 | 明确 | 可直接执行 |
| 0.4-0.7 | 模糊 | 需要提问 |
| < 0.4 | 不明确 | 需要多次提问 |

## 标准接口

```python
from agent_symphony.skills.thinking import get_skill_instance

# 获取技能实例
thinking = get_skill_instance()

# 理解需求
result = thinking.execute("understand", {
    "requirement": "帮我优化这个项目"
})

# 评估明确度
result = thinking.query("thinking.evaluate", {
    "requirement": "帮我优化这个项目"
})

# 生成澄清问题
result = thinking.execute("clarify", {
    "requirement": "帮我优化这个项目",
    "max_questions": 3
})

# 处理用户回答
thinking.notify("user.response", {
    "question_index": 0,
    "answer": "我想优化性能，主要关注加载速度"
})

# 创建计划
result = thinking.execute("plan", {
    "requirement": "优化项目性能"
})

# 反思
result = thinking.execute("reflect", {
    "result": {"completed": True, "output": "..."}
})
```

## 与其他技能的联动

```
thinking (协调者)
    ├──→ memory.store()    # 存储用户偏好
    ├──→ memory.query()   # 查询上下文
    ├──→ search.execute()  # 搜索信息
    └──→ team.execute()   # 执行任务
```

---

_Agent Symphony 技能交响乐_
