import sys
sys.path.insert(0, '.')
from agent_symphony_openclaw import SymphonySession

s = SymphonySession()

print("=== 交响乐完整流程测试（team + memory 全部 LLM） ===\n")

# 第1轮：启动
r = s.handle("")
print(f"[1] state={r['state']}")

# 第2轮：提需求
r = s.handle("我想做一个chrome扩展程序，用来一键翻译网页")
print(f"\n[2] state={r['state']}")
print(f"    {r['response'][:200]}")

# 第3轮：确认执行
r = s.handle("好", {})
print(f"\n[3] state={r['state']}")
req_names = [f"{req['skill']}.{req['action']}" for req in r['skill_requests']]
print(f"    skill_requests: {req_names}")
for req in r['skill_requests']:
    plan = req.get('params', {}).get('plan', [])
    if plan:
        print(f"      plan [{req['skill']}]: {plan[:2]}")

# 第4轮：执行技能
all_results = {}
for req in r['skill_requests']:
    print(f"\n    执行 {req['skill']}.{req['action']}...")
    result = s.execute_skill(req["skill"], req["action"], req["params"])
    print(f"    结果: success={result.get('success')}")
    if req['skill'] == 'team':
        data = result.get('data', {})
        results = data.get('results', [])
        summary = data.get('summary', {})
        print(f"    team: {len(results)} steps, status={data.get('status')}")
        print(f"    summary: {summary.get('summary', 'N/A')}")
    all_results[req['skill']] = result
    s.notify_skill_result(req["skill"], result)

# 第5轮：结果回调
r = s.handle("继续", {}, skill_results=all_results)
print(f"\n[5] state={r['state']}, done={r['done']}")
print(f"    {r['response'][:200]}")

print("\n=== 测试完成 ===")
