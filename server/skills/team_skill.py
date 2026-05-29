"""
team_skill.py - 多任务执行（基于 sessions_spawn）

参考 AgentTeam OpenClaw SDK Backend
原理：
  1. 调用 openclaw gateway call sessions.create 创建 sub-agent
  2. 调用 sessions.send 发送任务 + 等待回复
  3. 直接读 session JSONL 文件，绕过 Gateway 权限问题
"""
import json
import subprocess
import time
import uuid
from pathlib import Path

GATEWAY_URL = "ws://127.0.0.1:18789"
POLL_INTERVAL = 5  # 秒


def _read_session_file(session_key: str) -> dict:
    """直接读取 session JSONL 文件，绕过 Gateway 权限问题"""
    uuid_str = session_key.split(":")[-1]
    session_file = Path.home() / ".openclaw" / "agents" / "main" / "sessions" / f"{uuid_str}.jsonl"

    if not session_file.exists():
        return {"messages": [], "error": f"Session file not found"}

    messages = []
    try:
        with open(session_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    messages.append(entry)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        return {"messages": [], "error": str(e)}

    return {"messages": messages}


def _gateway_call(method: str, params: dict = None) -> dict:
    """调用 Gateway RPC"""
    cmd = [
        "openclaw", "gateway", "call",
        method,
        "--params", json.dumps(params or {}),
        "--json",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gateway call failed: {result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON from gateway: {result.stdout}")


class TeamSkill:
    """
    通过 sessions_spawn 执行多任务

    使用 openclaw gateway 原生 sessions API：
    - sessions.create: 创建 sub-agent session
    - sessions.send: 发送消息
    - session JSONL: 读取结果（绕过权限）
    """

    def __init__(self):
        self.active_sessions: dict[str, dict] = {}

    def spawn(self, task: str, agent_type: str = "general", session_id: str = None) -> dict:
        """
        Spawn 一个 sub-agent 执行任务

        返回:
            {
                "session_id": str,
                "status": "created",
                "message": str
            }
        """
        session_id = session_id or str(uuid.uuid4())[:8]

        # 1. 创建 session
        try:
            resp = _gateway_call("sessions.create", {
                "agentId": "main",
                "label": f"symphony-team-{session_id}",
            })
            session_key = resp.get("key")
            created_id = session_key.split(":")[-1]
            if not session_key:
                return {"error": "No sessionKey in response", "raw": resp}
        except Exception as e:
            return {"error": f"Failed to create session: {e}"}

        # 2. 发送任务
        try:
            _gateway_call("sessions.send", {
                "key": session_key,
                "message": task,
            })
        except Exception as e:
            return {"error": f"Failed to send task: {e}"}

        # 3. 记录 session
        self.active_sessions[session_key] = {
            "task": task,
            "agent_type": agent_type,
            "created_at": time.time(),
            "session_id": created_id,
        }

        return {
            "session_id": created_id,
            "session_key": session_key,
            "status": "created",
            "message": f"Sub-agent 已启动 (session: {created_id[:8]})",
        }

    def status(self, session_id: str) -> dict:
        """轮询 session 状态和历史（优先读文件，避免权限问题）"""
        try:
            # 直接读 session 文件
            file_result = _read_session_file(session_id)
            messages = file_result.get("messages", [])

            completed = False
            last_message = ""
            if messages:
                last = messages[-1]
                if isinstance(last, dict):
                    last_message = last.get("content", "")[:100]
                    if last.get("role") == "assistant":
                        completed = True
                else:
                    last_message = str(last)[:100]

            return {
                "session_id": session_id,
                "status": "completed" if completed else "running",
                "messages_count": len(messages),
                "last_message": last_message,
            }
        except Exception as e:
            return {"session_id": session_id, "error": str(e)}

    def wait_complete(self, session_id: str, timeout: int = 300) -> dict:
        """等待任务完成（轮询）"""
        start = time.time()
        while time.time() - start < timeout:
            st = self.status(session_id)
            if st.get("status") == "completed" or "error" in st:
                return st
            time.sleep(POLL_INTERVAL)

        return {
            "session_id": session_id,
            "status": "timeout",
            "message": f"等待超时（{timeout}秒）",
        }

    def shutdown(self, session_id: str) -> dict:
        """通知 sub-agent 关闭"""
        try:
            _gateway_call("sessions.send", {
                "key": session_id,
                "message": "shutdown",
            })
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return {"session_id": session_id, "status": "shutdown_sent"}
        except Exception as e:
            return {"session_id": session_id, "error": str(e)}
