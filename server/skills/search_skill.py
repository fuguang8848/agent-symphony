"""
search_skill.py - 搜索技能（复用 search-v.py）

参考 AgentSearch 多引擎架构
"""
import os
import subprocess
import json
from pathlib import Path


SEARCH_V_PATH = str(Path.home() / ".openclaw" / "workspace" / "tools" / "search-v.py")


class SearchSkill:
    """
    调用 search-v.py 执行搜索

    功能：
    - 直接 Bing HTML 搜索
    - no_proxy 绕过系统代理
    - 国内结果优先 (mkt=zh-CN)
    """

    def execute(self, query: str, max_results: int = 5) -> dict:
        """
        执行搜索

        Returns:
            {
                "results": [{"url", "title", "snippet"}, ...],
                "answer": str | null,
            }
        """
        try:
            result = subprocess.run(
                ["python3", SEARCH_V_PATH, query, "--max-results", str(max_results)],
                capture_output=True,
                text=True,
                timeout=30,
                env={"no_proxy": "*", **os.environ},
            )

            if result.returncode != 0:
                return {
                    "results": [],
                    "error": result.stderr or "搜索失败",
                }

            # search-v.py 输出是 JSON 格式
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "results": [],
                    "error": "搜索结果解析失败",
                    "raw": result.stdout[:200],
                }

        except subprocess.TimeoutExpired:
            return {"results": [], "error": "搜索超时"}
        except FileNotFoundError:
            return {"results": [], "error": f"search-v.py 未找到: {SEARCH_V_PATH}"}
        except Exception as e:
            return {"results": [], "error": str(e)}
