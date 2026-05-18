import sys, os
INSTALLED_PATH = r"C:\Users\31683\.openclaw\workspace\.agents\skills\compound-engineering\agent-symphony"
sys.path.insert(0, INSTALLED_PATH)
from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

# Test intent check directly
print("=== Intent Check ===")
tests = ["启动交响乐", "交响乐帮我做量化交易", "我听说交响乐不错"]
for msg in tests:
    result = session._check_symphony_intent(msg)
    print(f"  {msg!r} -> {result}")

print()
print("=== Full Handle Test ===")
result = session.handle("启动交响乐")
print(f"State: {result['state']}, Done: {result['done']}")
print(f"Response: {result['response'][:150] if result['response'] else 'None'}")
