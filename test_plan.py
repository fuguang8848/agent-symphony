import sys
sys.path.insert(0, '.')
from agent_symphony_openclaw import SymphonySession

s = SymphonySession()

print("=== 测试 1：只测 thinking + team plan 生成 ===\n")

r = s.handle("")
print(f"[1] state={r['state']}")

r = s.handle("我想做一个chrome扩展程序，用来一键翻译网页")
print(f"\n[2] state={r['state']}")
print(f"    {r['response'][:200]}")

# 第3轮：确认执行（只看 skill_requests，不实际执行）
r = s.handle("好", {})
print(f"\n[3] state={r['state']}")
req_names = [f"{req['skill']}.{req['action']}" for req in r['skill_requests']]
print(f"    skill_requests: {req_names}")
for req in r['skill_requests']:
    plan = req.get('params', {}).get('plan', [])
    if plan:
        print(f"    [{req['skill']}] plan 有 {len(plan)} 个步骤:")
        for step in plan[:3]:
            print(f"      - {step.get('action')}: {str(step.get('params', {}))[:60]}")
    else:
        print(f"    [{req['skill']}] plan: {req.get('params', {})}")

print("\n=== 测试完成 ===")
