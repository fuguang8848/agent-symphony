import sys
sys.path.insert(0, '.')
from skills.thinking import ThinkingSkill
import json

t = ThinkingSkill()

print("=== 多轮对话测试 ===")

# 第1轮：提需求
r = t.execute("dialog", {"message": "我想做一个博客网站"})
d = r["data"]
print(f"[1] state={d.get('state')}, done={d.get('done')}")
print(f"    response: {d.get('response', '')[:150]}")
print(f"    questions: {len(d.get('questions', []))}")
print(f"    keys: {list(d.keys())}")

# 第2轮：提需求（跳过intro）
r2 = t.execute("dialog", {"message": "博客网站：个人技术博客，面向开发者，用Python"})
d2 = r2["data"]
print(f"\n[2] state={d2.get('state')}, done={d2.get('done')}")
print(f"    response: {d2.get('response', '')[:200]}")
print(f"    questions: {len(d2.get('questions', []))}")
for q in d2.get("questions", [])[:2]:
    print(f"    Q: {q.get('question', '')[:80]}")

# 第3轮：回答
r3 = t.execute("dialog", {
    "message": "想快速上线，没限制",
    "answers": {}
})
d3 = r3["data"]
print(f"\n[3] state={d3.get('state')}, done={d3.get('done')}")
print(f"    response: {d3.get('response', '')[:300]}")
print(f"    questions: {len(d3.get('questions', []))}")

print("\n=== 测试完成 ===")
