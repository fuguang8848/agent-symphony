"""
Symphony Quick Test - just the plan generation
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..\\Agent-Superthinking\\src')
sys.path.insert(0, '..\\AgentTeam')

from agent_symphony_openclaw import SymphonySession

print("=== SYMPHONY QUICK TEST ===")
s = SymphonySession()

# Round 1: Start
r = s.handle("")
print(f"[1] state={r['state']}")

# Round 2: Present requirement
r = s.handle("I want to build a Chrome extension that translates web pages with one click")
print(f"[2] state={r['state']}")
print(f"    response: {r['response'][:200]}")

# Round 3: Confirm - just see the skill_requests
r = s.handle("ok")
print(f"[3] state={r['state']}")
req_names = [f"{req['skill']}.{req['action']}" for req in r['skill_requests']]
print(f"    skill_requests: {req_names}")
for req in r['skill_requests']:
    if req['skill'] == 'team':
        plan = req.get('params', {}).get('plan', [])
        print(f"    team plan ({len(plan)} steps)")
        for step in plan:
            print(f"      - {step.get('action')}")

print("=== DONE ===")
