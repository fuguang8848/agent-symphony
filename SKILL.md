---
name: agent-symphony
version: 1.1.0
family: compound-engineering
description: 多技能底层互通的Agent框架 - 协调thinking/memory/search/team四大技能，提供理解需求、深度分析、规划、反思、记忆存储、信息检索、任务执行等综合能力
argument-hint: "[需求描述或任务说明]"
examples:
  - "我想搞量化交易"
  - "帮我分析石榴籽项目"
  - "给我制定一个Python学习计划"
---

# Agent Symphony 技能交响乐

> 多技能底层互通，1+1 > 2 的质变效果

## 一键使用

```
/symphony 我想搞量化交易
```

## 核心技能

| 技能 | 角色 | 说明 |
|------|------|------|
| **thinking** | 协调者 | 理解需求、提问、分析、规划、反思 |
| **memory** | 记忆中心 | 向量检索、混合搜索、智能遗忘 |
| **search** | 信息获取 | 多引擎搜索、结果路由 |
| **team** | 执行者 | 任务执行、完成度检查 |

## 工作流程

```
用户需求 → 理解 → 提问澄清 → 制定计划 → 执行 → 反思
```

## 使用方式

### 方式一：CLI 快速使用

```bash
# 直接运行
python agent_symphony_cli.py "我想搞量化交易"

# 交互模式
python agent_symphony_cli.py -i
```

### 方式二：模块调用

```python
from agent_symphony import ThinkingSkill, MemorySkill, SearchSkill
from agent_symphony.shared import SharedContext

# 初始化
context = SharedContext()
thinking = ThinkingSkill()
memory = MemorySkill()

# 理解需求
result = thinking.execute("understand", {
    "requirement": "我想搞量化交易"
})
```

## CLI 功能

- ✅ 需求理解 + 明确度评估
- ✅ 澄清问题生成
- ✅ 行动计划制定
- ✅ 记忆存储
- ✅ 交互模式（输入问题持续对话）
- ✅ 内置命令（memory / search）

## 插入式 LLM

自动从环境变量检测：
- OPENAI_API_KEY
- DASHSCOPE_API_KEY  
- MINIMAX_API_KEY
- DEEPSEEK_API_KEY

## 交互模式（指挥家对话）

通过 `dialog` 动作启动交互式对话：

```bash
python agent_symphony_cli.py -i
```

或通过 execute 调用：

```python
thinking = ThinkingSkill()
result = thinking.execute("dialog", {
    "message": "你好",
    "answers": {},
    "skill_results": {}
})
# result["response"] - 面向用户的回复
# result["skill_requests"] - 需要执行的技能申请
# result["state"] - clarifying|planning|executing|completed
# result["done"] - 是否完成
```

### 对话流程

```
用户启动交响乐
    ↓
指挥家自我介绍
    ↓
用户说出需求
    ↓
如果需求不明确 → 提问澄清
    ↓
如果明确 → 制定计划
    ↓
用户确认计划
    ↓
执行（调用 memory/search/team）
    ↓
完成/继续
```

### 技能申请（skill_requests）

当 thinking 需要调用其他技能时，返回 `skill_requests`：

```python
{
    "response": "正在搜索...",
    "skill_requests": [
        {"skill": "memory", "action": "store", "params": {...}},
        {"skill": "search", "action": "search", "params": {...}}
    ]
}
```

OpenClaw 执行这些技能后，通过 `notify("skill.result", {...})` 回调结果。

---

_技能交响乐 · Agent Symphony_