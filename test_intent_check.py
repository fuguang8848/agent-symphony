"""
Test symphony intent check - standalone
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))

# Fresh import
from shared.context import SharedContext

# Test directly
ctx = SharedContext()
tests = [
    "启动交响乐",
    "交响乐帮我做量化交易",
    "我听说交响乐不错",
    "交响乐是什么",
]

for msg in tests:
    prompt = f'User said: {msg}. Does the user want to START the symphony workflow? Answer only yes or no.'
    r = ctx.llm.complete(prompt, None, max_tokens=128)
    print(f"用户说：{msg}")
    print(f"→ 想启动: {'yes' in r.strip().lower() and 'no' not in r.strip().lower()[:5]}\n")
