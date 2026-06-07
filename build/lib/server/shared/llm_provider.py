"""
LLM Provider - OpenAI 兼容接口调用 MiniMax
"""
import httpx
from typing import AsyncIterator

from ..config import get_llm_config


class LLMProvider:
    """LLM 调用封装，支持流式和非流式"""

    def __init__(self):
        self.cfg = get_llm_config()
        self.model = self.cfg.get("model", "MiniMax-M2.7")
        self.base_url = self.cfg.get("base_url", "https://api.minimaxi.com/anthropic")
        self.api_key = self.cfg.get("api_key", "")
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        发送对话请求，返回文本或流式迭代器

        messages: [{"role": "user", "content": "..."}]
        """
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        client = self._get_client()

        if stream:
            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()
            return self._stream_response(response)

        response = await client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        content = data.get("content", [])
        if not content:
            return ""
        first = content[0]
        raw_text = ""
        if first.get("type") == "text":
            raw_text = first.get("text", "")
        elif first.get("type") == "thinking":
            raw_text = first.get("thinking", "")
        else:
            raw_text = str(first)

        # 后处理：从思考过程中提取最终回答
        # MiniMax 推理模型的 thinking 块包含"最终答案"或"回答："之后的内容
        return self._extract_answer(raw_text)

    def _extract_answer(self, thinking_text: str) -> str:
        """从推理文本中提取最终回答"""
        if not thinking_text:
            return ""
        lines = thinking_text.strip().split("\n")
        # 策略：取最后几行非推理标注的内容
        # 过滤掉明显的推理步骤行
        answer_lines = []
        skip_patterns = [
            "The user asks", "The user says", "We should respond",
            "Check policy", "So we", "I think", "Let me",
            "But ", "However,", "Actually ",
            "用户问", "用户说", "我们应该", "我要",
            "首先", "其次", "然后", "最后", "所以",
            "问题：", "答案：", "回答：",
        ]
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            # 跳过包含推理关键词的行
            if any(p.lower() in line.lower()[:30] for p in skip_patterns if len(p) > 3):
                continue
            answer_lines.append(line)
            if len(answer_lines) >= 3:
                break
        if answer_lines:
            return "\n".join(reversed(answer_lines))
        # fallback：返回原文最后200字符
        return thinking_text[-200:].strip()

    async def _stream_response(self, response: httpx.Response) -> AsyncIterator[str]:
        """解析 SSE 流式响应"""
        async for line in response.aiter_lines():
            if not line or line.startswith(":"):
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                import json
                try:
                    chunk = json.loads(data)
                    if chunk.get("type") == "content_block_delta":
                        delta = chunk.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
                except Exception:
                    pass


# 全局单例
_llm: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _llm
    if _llm is None:
        _llm = LLMProvider()
    return _llm
