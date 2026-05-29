"""
配置管理 - 从 ~/.agent-symphony/config.json 读取
"""
import os
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".agent-symphony" / "config.json"

DEFAULT_CONFIG = {
    "llm": {
        "provider": "minimax",
        "model": "MiniMax-M2.7",
        "api_key": "",  # 用户需要填入
        "base_url": "https://api.minimaxi.com/anthropic",
    },
    "server": {
        "host": "127.0.0.1",
        "port": 18081,
    },
    "memory": {
        "dir": str(Path.home() / ".agent-symphony" / "memory"),
    },
    "search": {
        "script_path": str(Path.home() / ".openclaw" / "workspace" / "tools" / "search-v.py"),
    },
}


def load_config() -> dict:
    """加载配置，不存在则创建默认配置"""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"[agent-symphony] 配置文件已创建: {CONFIG_PATH}")
        print("[agent-symphony] 请填写 ~/.agent-symphony/config.json 中的 api_key")
        return DEFAULT_CONFIG

    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_llm_config() -> dict:
    """获取 LLM 配置"""
    cfg = load_config()
    llm = cfg.get("llm", {})
    if not llm.get("api_key"):
        raise ValueError(
            "[agent-symphony] LLM API key 未配置！\n"
            f"请编辑 {CONFIG_PATH}\n"
            "填入你的 MiniMax API key"
        )
    return llm


def get_server_config() -> dict:
    cfg = load_config()
    return cfg.get("server", {"host": "127.0.0.1", "port": 18081})


def get_memory_dir() -> Path:
    cfg = load_config()
    d = Path(cfg.get("memory", {}).get("dir",
                str(Path.home() / ".agent-symphony" / "memory")))
    d.mkdir(parents=True, exist_ok=True)
    return d
