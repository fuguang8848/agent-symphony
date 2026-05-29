"""
symphony_server.py - HTTP RPC 网关服务器

端口: 18081
端点:
  POST /thinking/dialog     - 对话 + 澄清
  POST /thinking/plan       - 生成执行计划
  POST /thinking/complete   - 标记执行完成
  POST /thinking/reset      - 重置会话
  GET  /thinking/state      - 获取状态
  POST /memory/store        - 存储记忆
  POST /memory/query        - 查询记忆
  GET  /memory/list         - 列出记忆
  GET  /health              - 健康检查
"""
import asyncio
import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .config import load_config, get_server_config
from .skills.thinking_skill import ThinkingSkill, State
from .skills.search_skill import SearchSkill
from .skills.memory_skill import MemorySkill
from .skills.team_skill import TeamSkill

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("symphony")

app = FastAPI(title="agent-symphony", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:18789", "http://127.0.0.1:18789"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局技能实例
thinking_skill = ThinkingSkill()
search_skill = SearchSkill()
memory_skill = MemorySkill()
team_skill = TeamSkill()


# ── 请求模型 ────────────────────────────────────────────────────────

class DialogRequest(BaseModel):
    message: str
    answers: dict | None = None
    session_id: str = "default"


class PlanRequest(BaseModel):
    user_message: str
    answers: dict | None = None
    session_id: str = "default"


class CompleteRequest(BaseModel):
    result: str = ""
    session_id: str = "default"


class ResetRequest(BaseModel):
    session_id: str = "default"


class MemoryStoreRequest(BaseModel):
    type: str = "context"  # preference | fact | plan | context
    content: str
    tags: list[str] = []


class MemoryQueryRequest(BaseModel):
    query: str = ""
    limit: int = 5
    type_filter: str | None = None


# ── 路由 ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-symphony"}


# ── Thinking 路由 ─────────────────────────────────────────────────────

async def _execute_skills(skill_requests: list[dict]) -> str:
    """执行技能请求，返回结果摘要"""
    results = []
    for req in skill_requests:
        skill = req.get("skill", "")
        params = req.get("params", {})

        if skill == "search":
            query = params.get("query", "")
            r = search_skill.execute(query=query, max_results=5)
            if "error" in r:
                results.append(f"搜索失败: {r['error']}")
            else:
                count = len(r.get("results", []))
                results.append(f"搜索完成，获得 {count} 条结果")

        elif skill == "team":
            task = params.get("task", "")
            r = team_skill.spawn(task=task)
            if "error" in r:
                results.append(f"任务执行失败: {r['error']}")
            else:
                results.append(f"任务已启动: {r.get('message', '')}")

        elif skill == "memory":
            content = params.get("content", "")
            r = memory_skill.store(type_="context", content=content)
            if "error" in r:
                results.append(f"记忆存储失败: {r['error']}")
            else:
                results.append("已记住")

        else:
            results.append(f"未知技能: {skill}")

    return "；".join(results) if results else "技能执行完成"


@app.post("/thinking/dialog")
async def dialog(req: DialogRequest):
    """
    对话 + 澄清 + 状态推进

    自动执行 skill_requests（search/team/memory），
    不需要外部回调 complete。
    """
    try:
        result = await thinking_skill.think(
            user_message=req.message,
            answers=req.answers,
            session_id=req.session_id,
        )

        # 如果是 executing 状态且有技能请求，自动执行
        if result.get("state") == "executing" and result.get("skill_requests"):
            skill_results = await _execute_skills(result["skill_requests"])
            # 执行完成后进入 completed
            result = await thinking_skill.complete(
                session_id=req.session_id,
                result=skill_results,
            )

        return result
    except Exception as e:
        logger.exception("thinking/dialog error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/thinking/complete")
async def complete(req: CompleteRequest):
    """标记执行完成，进入 completed 状态"""
    try:
        result = await thinking_skill.complete(
            session_id=req.session_id,
            result=req.result,
        )
        return result
    except Exception as e:
        logger.exception("thinking/complete error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/thinking/reset")
async def reset(req: ResetRequest):
    """重置会话"""
    return await thinking_skill.reset(session_id=req.session_id)


@app.get("/thinking/state")
async def state(session_id: str = "default"):
    """获取当前会话状态"""
    return thinking_skill.get_state(session_id=session_id)


# ── Memory 路由 ───────────────────────────────────────────────────────

from .skills.memory_skill import MemorySkill

memory_skill = MemorySkill()


@app.post("/memory/store")
async def memory_store(req: MemoryStoreRequest):
    """存储记忆"""
    try:
        return memory_skill.store(
            type_=req.type,
            content=req.content,
            tags=req.tags,
        )
    except Exception as e:
        logger.exception("memory/store error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/query")
async def memory_query(req: MemoryQueryRequest):
    """查询记忆"""
    try:
        return memory_skill.query(
            query=req.query,
            limit=req.limit,
            type_filter=req.type_filter,
        )
    except Exception as e:
        logger.exception("memory/query error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/list")
async def memory_list(type_filter: str | None = None, limit: int = 20):
    """列出记忆"""
    try:
        return memory_skill.list_entries(type_filter=type_filter, limit=limit)
    except Exception as e:
        logger.exception("memory/list error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Team 路由 ──────────────────────────────────────────────────────

from .skills.team_skill import TeamSkill
from pydantic import BaseModel

team_skill = TeamSkill()

class TeamSpawnRequest(BaseModel):
    task: str
    agent_type: str = "general"


@app.post("/team/spawn")
async def team_spawn(req: TeamSpawnRequest):
    """Spawn sub-agent 执行任务"""
    try:
        return team_skill.spawn(task=req.task, agent_type=req.agent_type)
    except Exception as e:
        logger.exception("team/spawn error")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/team/status")
async def team_status(session_id: str):
    """查询任务状态"""
    try:
        return team_skill.status(session_id=session_id)
    except Exception as e:
        logger.exception("team/status error")
        raise HTTPException(status_code=500, detail=str(e))


class TeamWaitRequest(BaseModel):
    session_id: str
    timeout: int = 300


@app.post("/team/wait")
async def team_wait(req: TeamWaitRequest):
    """等待任务完成"""
    try:
        return team_skill.wait_complete(session_id=req.session_id, timeout=req.timeout)
    except Exception as e:
        logger.exception("team/wait error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/team/shutdown")
async def team_shutdown(session_id: str):
    """通知 sub-agent 关闭"""
    try:
        return team_skill.shutdown(session_id=session_id)
    except Exception as e:
        logger.exception("team/shutdown error")
        raise HTTPException(status_code=500, detail=str(e))


# ── Search 路由 ───────────────────────────────────────────────────────

from .skills.search_skill import SearchSkill

search_skill = SearchSkill()

class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


@app.post("/search/execute")
async def search_execute(req: SearchRequest):
    """执行搜索"""
    try:
        return search_skill.execute(query=req.query, max_results=req.max_results)
    except Exception as e:
        logger.exception("search/execute error")
        raise HTTPException(status_code=500, detail=str(e))


# ── 启动 ─────────────────────────────────────────────────────────────

def main():
    cfg = get_server_config()
    host = cfg.get("host", "127.0.0.1")
    port = cfg.get("port", 18081)

    # 检查 LLM 配置
    try:
        from .config import get_llm_config
        get_llm_config()
        logger.info("LLM 配置检查通过")
    except ValueError as e:
        logger.warning(f"LLM 配置不完整: {e}")

    logger.info(f"启动 agent-symphony 服务: {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
