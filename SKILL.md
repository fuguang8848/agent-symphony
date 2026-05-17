---
name: agent-symphony-integration
version: 1.0.0
family: compound-engineering
description: "OpenClaw integration for AgentSymphony. Provides /symphony command routing, multi-turn dialog management, and skill orchestration (thinking/memory/search/team). Use when user triggers /symphony or wants interactive task coordination."
argument-hint: "[需求描述或 /symphony 启动]"
examples:
  - "/symphony"
  - "/symphony 我想搞量化交易"
  - "交响乐"
---

# AgentSymphony OpenClaw 集成

## 功能

提供 `/symphony` 命令的完整集成，让 OpenClaw 支持交响乐的多轮对话模式。

## 使用方式

### 触发交响乐

```
/symphony
/symphony 我想搞量化交易
```

### 在 Python 代码中调用

```python
from agent_symphony_openclaw import SymphonySession, is_symphony_command, extract_requirement

# 检查命令
if is_symphony_command(message):
    requirement = extract_requirement(message)
    
    # 创建或获取 session
    session = get_symphony_session(user_id)
    
    # 处理消息
    result = session.handle(requirement)
    
    # 发送回复
    send_to_user(result["response"])
    
    # 处理技能申请
    for req in result.get("skill_requests", []):
        skill_result = session.execute_skill(req["skill"], req["action"], req["params"])
        session.notify_skill_result(req["skill"], skill_result)
```

## 核心组件

### SymphonySession

管理交响乐会话的完整生命周期。

**方法：**
- `handle(message, answers, skill_results)` - 处理用户消息
- `execute_skill(skill, action, params)` - 执行技能申请
- `notify_skill_result(skill, result, success)` - 回调技能结果
- `reset()` - 重置会话

**返回：**
```python
{
    "response": "面向用户的回复",
    "skill_requests": [...],  # 需要执行的技能
    "state": "clarifying|planning|executing|completed",
    "done": bool,
    "questions": [...],        # 如果需要澄清
    "success": bool
}
```

### 状态机

```
clarifying（澄清）→ planning（计划）→ executing（执行）→ completed（完成）
```

## OpenClaw 接入伪代码

```python
# 在消息处理器中

async def handle_message(message: str, user_id: str):
    # 检查是否是交响乐命令
    if is_symphony_command(message):
        requirement = extract_requirement(message)
        
        # 获取或创建 session
        session = symphony_sessions.get(user_id)
        if not session:
            session = SymphonySession(user_id)
            symphony_sessions[user_id] = session
        
        # 处理消息
        result = session.handle(requirement)
        
        # 发送回复
        await send_message(result["response"])
        
        # 处理技能申请
        for req in result.get("skill_requests", []):
            skill_result = session.execute_skill(req["skill"], req["action"], req["params"])
            session.notify_skill_result(req["skill"], skill_result)
        
        # 如果 done，清理 session
        if result.get("done"):
            del symphony_sessions[user_id]
        
        return
    
    # 正常消息处理...
```

## 注意事项

1. **会话管理** - 需要为每个用户维护独立的 SymphonySession
2. **skill_requests** - 如果不处理，交响乐仍可工作但不会调用其他技能
3. **回调时机** - skill_result 应在技能执行完成后立即回调

---

_AgentSymphony OpenClaw Integration v1.0.0_