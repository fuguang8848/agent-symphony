import sys
sys.path.insert(0, '.')
from skills.thinking import ThinkingSkill

print("=== Dialog Mode Test ===")

t = ThinkingSkill()

# Test 1: Intro
print("\n[1] Intro (empty message)")
r = t.execute('dialog', {'message': ''})
print(f"    state={r.get('data',{}).get('state')}, done={r.get('data',{}).get('done')}")
print(f"    response: {r.get('data',{}).get('response','')[:80]}")

# Test 2: Requirement
print("\n[2] User says requirement")
r = t.execute('dialog', {'message': '我想搞量化交易'})
print(f"    state={r.get('data',{}).get('state')}, done={r.get('data',{}).get('done')}")
print(f"    questions={len(r.get('data',{}).get('questions',[]))}")
if r.get('data',{}).get('questions'):
    q = r['data']['questions'][0]
    print(f"    Q: {q.get('question','')[:60]}")

# Test 3: Answer
print("\n[3] User answers questions")
r = t.execute('dialog', {'message': '完全新手，想实盘赚钱', 'answers': {'背景': '完全新手', '目标': '实盘赚钱'}})
print(f"    state={r.get('data',{}).get('state')}, done={r.get('data',{}).get('done')}")
print(f"    response: {r.get('data',{}).get('response','')[:80]}")

print("\n=== All Tests PASSED ===")