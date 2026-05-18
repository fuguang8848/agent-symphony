"""
Jury 分析脚本 - 由子代理调用
运行专家评审，结果写入 JSON 文件
"""
import sys
import json
import os

# Setup paths
workspace = os.path.dirname(os.path.abspath(__file__))
symphony_path = os.path.dirname(workspace)
superthinking_path = os.path.join(symphony_path, "Agent-Superthinking", "src")
agentteam_path = os.path.join(symphony_path, "AgentTeam")

for p in [symphony_path, superthinking_path, agentteam_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

from shared import get_context


def main():
    if len(sys.argv) < 3:
        print("Usage: python run_jury_analysis.py <requirement> <output_json>")
        sys.exit(1)

    requirement = sys.argv[1]
    output_file = sys.argv[2]

    try:
        ctx = get_context()

        # 动态导入（避免循环依赖）
        from skills.thinking.skill import ThinkingSkill

        # 正确初始化 ThinkingSkill
        thinking = ThinkingSkill()

        # 直接调用内部分析方法
        print(f"[Jury] Starting analysis for: {requirement[:50]}...")
        result = thinking._analyze_with_jury(requirement)
        print(f"[Jury] Analysis complete. can_proceed={result.get('can_proceed')}")

        # 转换 JuryResult 为可序列化 dict
        def _to_serializable(obj):
            if hasattr(obj, '__dict__'):
                return {k: _to_serializable(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, dict):
                return {k: _to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_to_serializable(i) for i in obj]
            elif isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            else:
                return str(obj)

        result_serializable = _to_serializable(result)

        # 写入结果
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_serializable, f, ensure_ascii=False, indent=2)

        print(f"[Jury] Results written to {output_file}")

    except Exception as e:
        import traceback
        error_result = {
            "clarity_score": 0,
            "can_proceed": False,
            "needs": [f"分析失败: {str(e)}"],
            "jury_result": None,
            "response": None,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        print(f"[Jury] Error: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
