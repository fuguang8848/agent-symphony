"""
Test jury via subagent
"""
import sys, time, os, json
sys.path.insert(0, '.')
sys.path.insert(0, '..\\Agent-Superthinking\\src')
sys.path.insert(0, '..\\AgentTeam')

from agent_symphony_openclaw import SymphonySession

s = SymphonySession()

# Turn 1: state requirement
print("[1] User says requirement...")
t0 = time.time()
r = s.handle("I want to build a Chrome extension that translates web pages")
elapsed = time.time() - t0
print(f"    Time: {elapsed:.1f}s")
print(f"    state: {r['state']}")
print(f"    jury_status: {r.get('jury_status', 'N/A')}")
print(f"    Response: {r['response'][:150]}")

# Check if jury process is running
result_file = os.path.expanduser("~/.openclaw/symphony/jury_result.json")
print(f"\n    Result file exists: {os.path.exists(result_file)}")

# Wait a bit for subprocess to start
time.sleep(2)

# Turn 2: User answers the follow-up question
print("\n[2] User answers follow-up...")
t0 = time.time()
r = s.handle("For general tourists visiting foreign websites")
elapsed = time.time() - t0
print(f"    Time: {elapsed:.1f}s")
print(f"    state: {r['state']}")
print(f"    Response: {r['response'][:200]}")

# Check result file
print(f"\n    Result file exists: {os.path.exists(result_file)}")
if os.path.exists(result_file):
    with open(result_file) as f:
        data = json.load(f)
    print(f"    Jury result: can_proceed={data.get('can_proceed')}, clarity={data.get('clarity_score')}")

print("\nDONE")
