"""
Test what LLM actually returns
"""
import sys, os
sys.path.insert(0, 'C:/Users/31683/.openclaw/workspace/AgentSymphony')
from shared.context import SharedContext

ctx = SharedContext()

# Test with more tokens
prompt = 'Return JSON array of 3 expert IDs: ["jobs","elon","turing"]'
print("Testing with max_tokens=1024...")
result = ctx.llm.complete(prompt, None, max_tokens=1024)
print(f"Result: {repr(result)}")

# Test with thinking disabled
print("\nTesting without thinking...")
result2 = ctx.llm.complete(
    "Return exactly: [\"jobs\",\"elon\",\"turing\"]",
    "Only return JSON array, no explanation.",
    max_tokens=256
)
print(f"Result2: {repr(result2)}")
