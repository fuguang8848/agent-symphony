import sys, time, json
sys.path.insert(0, '.')
sys.path.insert(0, '..\\Agent-Superthinking\\src')
from shared import SharedContext

ctx = SharedContext()
print(f"Model: {ctx.llm.model}, provider: {ctx.llm._provider}")

# 测试 plan 生成
start = time.time()
prompt = """用户需求：
我想做一个chrome扩展，用来一键翻译网页

你是一个任务规划专家。分解为 3 个具体步骤。

返回 JSON：
{
  "plan": [
    {"action": "步骤动作", "params": {"参数": "值"}}
  ]
}
只返回 JSON。"""

r = ctx.call_llm(prompt)
elapsed = time.time() - start
print(f"Time: {elapsed:.1f}s")
print(f"Response: {repr(r[:300])}")

start_idx = r.find('{')
end_idx = r.rfind('}')
if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
    data = json.loads(r[start_idx:end_idx+1])
    print(f"Plan steps: {len(data.get('plan', []))}")
    for step in data.get('plan', []):
        print(f"  - {step.get('action')}")
else:
    print("JSON parse failed")
