# Agent Symphony

> Multi-skill interoperability for AI agents

---

## Overview

Agent Symphony is a multi-skill interconnected Agent framework.

**Core Idea**: 4 skills (thinking/memory/search/team) interoperate at the底层, like a symphony orchestra.

```
User: "Help me analyze this project issue"
    ↓
thinking (Conductor)
    ├──→ memory.store()    # Store context
    ├──→ search.query()    # Search info
    └──→ team.execute()    # Execute task
```

---

## Four Core Skills

| Skill | Repo | Role | Core Function |
|-------|------|------|---------------|
| **thinking** | [Agent-Superthinking](https://github.com/YintaTriss/Agent-Superthinking) | Conductor | Understand, ask, plan, reflect (integrated expert perspectives) |
| **memory** | [MemorySkill](https://github.com/YintaTriss/MemorySkill) | Memory Center | Vector search, hybrid search, smart forgetting |
| **search** | [SearchSkill](https://github.com/YintaTriss/SearchSkill) | Info Retrieval | Multi-engine search, result routing |
| **team** | [AgentTeam](https://github.com/YintaTriss/AgentTeam) | Executor | Task execution, completion check |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Symphony                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐                                            │
│  │   thinking  │ ◄── Conductor                              │
│  └──────┬──────┘                                            │
│         │                                                   │
│    ┌────┴────┬────────────┐                                 │
│    ▼         ▼            ▼                                 │
│ ┌──────┐ ┌──────┐    ┌──────┐                              │
│ │memory│ │search│    │team  │                              │
│ └──┬───┘ └──┬───┘    └──┬───┘                              │
│    │        │           │                                  │
│    ▼        ▼           ▼                                  │
│ ┌──────────────────────────────────────┐                   │
│ │        Shared Context                 │                  │
│ │   • LLM Provider (Plug-in)            │                  │
│ │   • Caller Tracking                  │                  │
│ │   • Result Routing                   │                  │
│ └──────────────────────────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Three Key Features

### 1. Plug-in LLM

Skills auto-detect LLM config from environment variables:

```python
# Auto-detect priority:
# OPENAI_API_KEY → DASHSCOPE_API_KEY → MINIMAX_API_KEY → DEEPSEEK_API_KEY

# Skill gets LLM via SharedContext
context = get_context()
result = context.call_llm("User question...")
embeddings = context.get_embeddings("text")
```

**Works anywhere, with any LLM.**

### 2. Result Routing

Search results are routed based on caller:

| Caller | Output | Format |
|--------|---------|--------|
| User direct call | → User | Full format with meta |
| thinking call | → thinking | Structured data |
| team call | → team | Simplified data |

### 3. Full Skill Interconnection

```
thinking ←→ memory
thinking ←→ search
thinking ←→ team
team ←→ search
```

---

## Related Repos

| Project | URL | Description |
|---------|-----|-------------|
| AgentSymphony | [GitHub](https://github.com/YintaTriss/AgentSymphony) | Main repo (skill symphony) |
| MemorySkill | [GitHub](https://github.com/YintaTriss/MemorySkill) | Standalone memory skill |
| SearchSkill | [GitHub](https://github.com/YintaTriss/SearchSkill) | Standalone search skill |
| AgentTeam | [GitHub](https://github.com/YintaTriss/AgentTeam) | Multi-agent collaboration |
| Agent-Superthinking | [GitHub](https://github.com/YintaTriss/Agent-Superthinking) | Deep thinking (thinking's expert perspectives) |

---

## License

MIT