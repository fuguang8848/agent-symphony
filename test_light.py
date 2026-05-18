"""
Test full lightweight flow: clarify -> plan -> execute
"""
import sys, time
sys.path.insert(0, '.')
sys.path.insert(0, '..\\Agent-Superthinking\\src')
sys.path.insert(0, '..\\AgentTeam')

from agent_symphony_openclaw import SymphonySession

s = SymphonySession()

# Round 1: Start
r = s.handle("")
print(f"[1] state={r['state']}")

# Round 2: Requirement
print("\n[2] Requirement...")
t0 = time.time()
r = s.handle("I want to build a Chrome extension that translates web pages with one click")
print(f"    Time: {time.time()-t0:.1f}s, state={r['state']}")
print(f"    {r['response'][:150]}")

# Round 3: Confirm execution
print("\n[3] Confirm 'ok'...")
t0 = time.time()
r = s.handle("好")
print(f"    Time: {time.time()-t0:.1f}s, state={r['state']}")
reqs = [f"{req['skill']}.{req['action']}" for req in r['skill_requests']]
print(f"    skill_requests: {reqs}")
for req in r['skill_requests']:
    if req['skill'] == 'team':
        plan = req.get('params', {}).get('plan', [])
        print(f"    team plan ({len(plan)} steps):")
        for step in plan[:5]:
            print(f"      - {step.get('action')}")

# Round 4: Execute memory + search (skip team)
print("\n[4] Execute memory + search...")
all_results = {}
for req in r['skill_requests']:
    if req['skill'] == 'team':
        print(f"    SKIP team")
        continue
    t0 = time.time()
    result = s.execute_skill(req["skill"], req["action"], req["params"])
    print(f"    {req['skill']}: {time.time()-t0:.1f}s, success={result.get('success')}")
    all_results[req['skill']] = result
    s.notify_skill_result(req["skill"], result)

# Round 5: Callback
print("\n[5] Callback...")
r = s.handle("continue", {}, skill_results=all_results)
print(f"    state={r['state']}, done={r['done']}")
print(f"    {r['response'][:150]}")

print("\nDONE")
