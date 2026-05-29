"""
memory_skill.py - 轻量文件存储

存储结构:
~/.agent-symphony/memory/
├── YYYY-MM-DD.md          # 每日日记
├── preferences.json       # 用户偏好
└── entities.json          # 实体知识
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..config import get_memory_dir


class MemorySkill:
    """轻量记忆存储"""

    def __init__(self):
        self.memory_dir = get_memory_dir()
        self._ensure_files()

    def _ensure_files(self):
        """确保基础文件存在"""
        self.preferences_file = self.memory_dir / "preferences.json"
        self.entities_file = self.memory_dir / "entities.json"
        self.today_file = self.memory_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"

        if not self.preferences_file.exists():
            with open(self.preferences_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
        if not self.entities_file.exists():
            with open(self.entities_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def store(self, type_: str, content: str, tags: list[str] = None) -> dict:
        """存储记忆"""
        tags = tags or []
        timestamp = datetime.now().isoformat()

        if type_ == "preference":
            # 存储偏好到 preferences.json
            prefs = self._load_json(self.preferences_file)
            prefs[content] = {"value": content, "tags": tags, "updated": timestamp}
            self._save_json(self.preferences_file, prefs)
            return {"success": True, "type": "preference", "id": content}

        elif type_ == "fact":
            # 存储实体到 entities.json
            entities = self._load_json(self.entities_file)
            entry = {"content": content, "tags": tags, "created": timestamp}
            entities.append(entry)
            self._save_json(self.entities_file, entities)
            return {"success": True, "type": "fact", "id": len(entities) - 1}

        elif type_ == "plan":
            # 存储计划到今日日记
            self._append_daily(f"**计划** [{timestamp}]: {content}")
            return {"success": True, "type": "plan", "file": str(self.today_file)}

        else:
            # 通用内容存日记
            self._append_daily(f"{content} [{timestamp}]")
            return {"success": True, "type": "context", "file": str(self.today_file)}

    def query(self, query: str, limit: int = 5, type_filter: str | None = None) -> dict:
        """查询记忆"""
        results = []
        query_lower = query.lower()

        # 查 preferences
        if type_filter is None or type_filter == "preference":
            prefs = self._load_json(self.preferences_file)
            for key, val in prefs.items():
                if query_lower in key.lower() or query_lower in val.get("value", "").lower():
                    results.append({
                        "type": "preference",
                        "content": val["value"],
                        "tags": val.get("tags", []),
                        "updated": val.get("updated", ""),
                    })

        # 查 entities
        if type_filter is None or type_filter == "fact":
            entities = self._load_json(self.entities_file)
            for e in entities:
                if query_lower in e.get("content", "").lower():
                    results.append({
                        "type": "fact",
                        "content": e["content"],
                        "tags": e.get("tags", []),
                        "created": e.get("created", ""),
                    })

        # 查日记文件
        if type_filter is None or type_filter == "context":
            for md_file in sorted(self.memory_dir.glob("????-??-??.md"), reverse=True)[:7]:
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if query_lower in content.lower():
                        # 找匹配的行
                        for line in content.split("\n"):
                            if query_lower in line.lower():
                                results.append({
                                    "type": "context",
                                    "content": line.strip(),
                                    "file": str(md_file.name),
                                })
                except Exception:
                    pass

        return {
            "results": results[:limit],
            "total": len(results),
            "query": query,
        }

    def list_entries(self, type_filter: str | None = None, limit: int = 20) -> dict:
        """列出所有记忆"""
        entries = []

        if type_filter is None or type_filter == "preference":
            prefs = self._load_json(self.preferences_file)
            for k, v in prefs.items():
                entries.append({"type": "preference", "content": v["value"], "id": k})

        if type_filter is None or type_filter == "fact":
            entities = self._load_json(self.entities_file)
            for i, e in enumerate(entities):
                entries.append({"type": "fact", "content": e["content"], "id": i})

        if type_filter is None or type_filter == "context":
            for md_file in sorted(self.memory_dir.glob("????-??-??.md"), reverse=True)[:7]:
                try:
                    content = md_file.read_text(encoding="utf-8")
                    for line in content.split("\n"):
                        if line.strip():
                            entries.append({"type": "context", "content": line.strip(), "file": md_file.name})
                except Exception:
                    pass

        return {"entries": entries[:limit], "total": len(entries)}

    def _load_json(self, path: Path) -> dict | list:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {} if path.name == "preferences.json" else []

    def _save_json(self, path: Path, data: dict | list):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _append_daily(self, line: str):
        with open(self.today_file, "a", encoding="utf-8") as f:
            f.write(f"{line}\n")
