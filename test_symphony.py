import sys
sys.path.insert(0, '.')
from agent_symphony_openclaw import SymphonySession

s = SymphonySession()

print("=== Symphony 集成测试 ===\n")

# 测试1: 启动交响乐
r = s.handle("")
print(f"[1] 启动")
print(f"    state={r['state']}, done={r['done']}")
print(f"    response: {r['response'][:100]}")

# 测试2: 提需求
r = s.handle("我想做一个chrome扩展程序")
print(f"\n[2] 提需求")
print(f"    state={r['state']}, done={r['done']}")
print(f"    skill_requests: {len(r['skill_requests'])}")
print(f"    response: {r['response'][:150]}")

# 测试3: 执行技能申请（如果有）
for req in r.get("skill_requests", []):
    print(f"\n    技能申请: {req['skill']}.{req['action']}")
    result = s.execute_skill(req["skill"], req["action"], req["params"])
    print(f"    结果: success={result.get('success')}")
    s.notify_skill_result(req["skill"], result)

# 测试4: 继续对话
r = s.handle("用JavaScript，不需要复杂功能", {})
print(f"\n[4] 回答问题后")
print(f"    state={r['state']}, done={r['done']}")
print(f"    response: {r['response'][:200]}")

print("\n=== 交响乐测试完成 ===")
