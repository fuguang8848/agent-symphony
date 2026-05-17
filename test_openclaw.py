import sys
sys.path.insert(0, '.')

print("Step 1: import SymphonySession")
from agent_symphony_openclaw import SymphonySession

print("Step 2: create session")
s = SymphonySession()

print("Step 3: handle('')")
r = s.handle("")
print(f"  state={r['state']}, done={r['done']}")

print("Step 4: handle('我想搞量化')")
r = s.handle("我想搞量化")
print(f"  state={r['state']}, questions={len(r['questions'])}")

print("=== DONE ===")