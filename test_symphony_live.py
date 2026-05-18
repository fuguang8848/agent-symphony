"""
Symphony Live Test
"""
import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, '..\\Agent-Superthinking\\src')
sys.path.insert(0, '..\\AgentTeam')

from agent_symphony_openclaw import SymphonySession

print("=" * 60)
print("SYMPHONY LIVE TEST")
print("=" * 60)

s = SymphonySession()

# === Round 1: Start ===
print("\n[Round 1] Start Symphony")
r = s.handle("")
print(f"  state: {r['state']}")
print(f"  response: {r['response'][:150]}")

# === Round 2: Present requirement ===
print("\n[Round 2] Present requirement")
r = s.handle("I want to build a Chrome extension that translates web pages with one click")
print(f"  state: {r['state']}")
print(f"  response preview: {r['response'][:300]}")

# === Round 3: Confirm execution ===
print("\n[Round 3] Confirm execution")
r = s.handle("ok")
print(f"  state: {r['state']}")
req_names = [f"{req['skill']}.{req['action']}" for req in r['skill_requests']]
print(f"  skill requests: {req_names}")

for req in r['skill_requests']:
    if req['skill'] == 'team':
        plan = req.get('params', {}).get('plan', [])
        print(f"  team plan ({len(plan)} steps):")
        for step in plan:
            print(f"    - {step.get('action')}: {str(step.get('params', {}))[:60]}")

# === Round 4: Execute skills (memory + search only) ===
print("\n[Round 4] Execute skills (memory + search)")
all_results = {}
for req in r['skill_requests']:
    if req['skill'] == 'team':
        print(f"  SKIP team (requires OpenClaw Session, too slow)")
        continue
    print(f"  Execute {req['skill']}.{req['action']}...")
    result = s.execute_skill(req["skill"], req["action"], req["params"])
    print(f"    success={result.get('success')}")
    if req['skill'] == 'search':
        data = result.get('data', {})
        print(f"    search results: {len(data.get('results', []))}")
    all_results[req['skill']] = result
    s.notify_skill_result(req["skill"], result)

# === Round 5: Callback ===
print("\n[Round 5] Callback with results")
r = s.handle("continue", {}, skill_results=all_results)
print(f"  state={r['state']}, done={r['done']}")
print(f"  response: {r['response'][:200]}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
