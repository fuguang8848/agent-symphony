# Agent Symphony

> Multi-skill collaborative workflow — the AI is the conductor, users just describe their needs

---

## Core Concept

**Symphony is a multi-skill collaborative workflow, not a standalone program.**

After installation, the AI assistant automatically understands its role: acting as the conductor, coordinating thinking/memory/search/AgentTeam skills to complete complex tasks.

Users don't need to understand what Symphony is — just describe their needs and the AI starts the workflow.

---

## Workflow

```
User describes a need
    ↓
thinking skill ← AI (conductor): ask, clarify, analyze
    ↓
memory skill ← store confirmed requirements/plans
    ↓
planning (plan stage) ← AI creates execution plan
    ↓
memory skill ← store the plan
    ↓
AgentTeam ← AI calls team skill to execute
```

**Natural invocation:** When search is needed, AI naturally calls search skill; when memory is needed, AI calls memory skill.

---

## How It Starts

| Trigger | Description |
|---------|-------------|
| **Passive** | User says "启动交响乐", "交响乐" → AI starts immediately |
| **Active** | AI judges by task nature (needs multi-round clarification / multi-skill collaboration / planning) |

If user says "交响乐是什么" just to ask, that won't trigger the workflow — the AI judges the true intent.

---

## Four Core Skills

| Skill | Responsibility | Description |
|-------|---------------|-------------|
| **thinking** | Dialogue + Analysis | Lead requirement discussion, clarify, create plans |
| **memory** | Memory Storage | Store requirements/plans for future reference |
| **search** | Information Retrieval | Called naturally when needed |
| **team** | Task Execution | Call AgentTeam to execute specific tasks |

---

## The AI's Role

**I am the conductor.** No separate "conductor" role exists.

- Judge when to start Symphony
- Discuss and clarify requirements with user through thinking skill
- Coordinate all skill invocations
- Integrate results, respond to user
- Call AgentTeam to execute plans

---

## State Machine

```
clarifying → planning → executing → completed
```

- **clarifying**: Requirements unclear, ask user questions
- **planning**: Requirements understood, create execution plan
- **executing**: Call AgentTeam to execute
- **completed**: Done, output results

---

## Cross-Platform

| Platform | Status |
|----------|--------|
| Windows | ✅ |
| macOS | ✅ |
| Linux | ✅ |

Python 3.10+. Uses `subprocess`, `pathlib` — no platform-specific code.

---

## Installation

```bash
# 1. Clone the repo
cd ~/.openclaw/workspace
git clone https://github.com/YintaTriss/AgentSymphony

# 2. Move to correct location
mv AgentSymphony ~/.openclaw/workspace/.agents/skills/compound-engineering/agent-symphony

# 3. Restart OpenClaw
openclaw gateway restart
```

---

## Quick Start

```python
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

# Start
result = session.handle("I want to build a quantitative trading system")
print(result["response"])
# → "Hello, I'm the conductor. Please tell me what you want to accomplish."

# Continue
result = session.handle("I'm a complete beginner, don't know where to start")
print(result["response"])
# → "What aspect would you most like to understand?"
```

---

## Related Projects

- [AgentTeam](https://github.com/YintaTriss/AgentTeam) - Multi-agent collaboration framework
- [Agent-Superthinking](https://github.com/YintaTriss/Agent-Superthinking) - Super thinking capability (expert perspective analysis)
- [AgentSymphony](https://github.com/YintaTriss/AgentSymphony) - This repo

---

## Changelog

### v2.0 (2026-05-18)
- **I am the conductor**: Removed fake "conductor" role, AI assistant directly acts as conductor
- Updated workflow: thinking discuss → memory store → planning create plan → memory store → AgentTeam execute
- Dual trigger: passive (user says "启动交响乐") + active (LLM judges task nature)
- Cross-platform: Windows/macOS/Linux

---

_楚灵 ⚔️ 2026-05-18 v2.0_
