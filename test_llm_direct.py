"""
Test direct LLM call from SharedContext
"""
import sys, os
sys.path.insert(0, 'C:/Users/31683/.openclaw/workspace/AgentSymphony')
sys.path.insert(0, 'C:/Users/31683/.openclaw/workspace/Agent-Superthinking/src')
from shared.context import SharedContext

ctx = SharedContext()
print(f"LLM: {ctx.llm._provider}, API key: {bool(ctx.llm.api_key)}")

# Test the complete method directly
prompt = 'Return JSON array of 3 expert IDs: ["jobs","elon","turing"]'
result = ctx.llm.complete(prompt, None, max_tokens=512)
print(f"Result: {repr(result)}")
