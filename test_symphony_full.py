import sys, os
INSTALLED_PATH = r"C:\Users\31683\.openclaw\workspace\.agents\skills\compound-engineering\agent-symphony"
sys.path.insert(0, INSTALLED_PATH)
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

print("=== Turn 1: 启动交响乐 ===")
r = session.handle("启动交响乐")
print(f"State: {r['state']} | Done: {r['done']}")
print(f"Response: {r['response']}")
print()

print("=== Turn 2: 我想做量化交易 ===")
r = session.handle("我想做量化交易")
print(f"State: {r['state']} | Done: {r['done']}")
print(f"Response: {r['response']}")
print()

print("=== Turn 3: 新手，完全没基础 ===")
r = session.handle("新手，完全没基础，不知道怎么入门")
print(f"State: {r['state']} | Done: {r['done']}")
print(f"Response: {r['response']}")
