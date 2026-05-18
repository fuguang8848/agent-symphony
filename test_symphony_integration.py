"""
Test symphony in webchat style - 模拟用户在 webchat 说"启动交响乐"
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_symphony_openclaw import SymphonySession

session = SymphonySession()

print("=== 用户: 启动交响乐 ===")
result = session.handle("启动交响乐")
print(f"State: {result['state']}")
print(f"Response:\n{result['response']}")
print()

print("=== 用户: 我想做量化交易 ===")
result = session.handle("我想做量化交易")
print(f"State: {result['state']}")
print(f"Response:\n{result['response']}")
print()

print("=== 用户: 完全没有基础，新手一个 ===")
result = session.handle("完全没有基础，新手一个")
print(f"State: {result['state']}")
print(f"Response:\n{result['response']}")
