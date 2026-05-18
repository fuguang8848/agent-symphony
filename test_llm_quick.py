import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, '..\\Agent-Superthinking\\src')
from shared import SharedContext

ctx = SharedContext()
print(f"LLM provider: {ctx.llm._provider}")
print(f"API key available: {bool(ctx.llm.api_key)}")
print(f"Model: {ctx.llm.model}")

print("\n=== Test 1: Simple LLM call ===")
start = time.time()
r = ctx.call_llm("Say 'hello' in exactly one word.")
print(f"Time: {time.time()-start:.1f}s")
print(f"Response: {repr(r[:100])}")

print("\n=== Test 2: JSON LLM call ===")
start = time.time()
r = ctx.call_llm("""Return JSON with fields: name (string), age (number). Nothing else.""")
print(f"Time: {time.time()-start:.1f}s")
print(f"Response: {repr(r[:200])}")
