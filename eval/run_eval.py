"""评估跑批 CLI —— run_eval.py --limit N --baseline（手册模块 8 / FR-07 / §9.2）。

流程：
1. 读 eval/profiles.json（--limit 截断）；每画像独立一次性 thread_id（防 checkpoint 膨胀）；
2. 直接 invoke 编译图（不经 HTTP，少一层依赖）；interrupt 场景按画像预设答案自动续跑；
3. 收集 final_recommendations → eval/metrics.py 算指标；
4. --baseline 时同口径跑 baseline.py（单次 LLM 直出 Top5）；
5. 落 eval/results/{timestamp}.json（含 trace 摘要）+ 终端汇总表。

成本护栏：日常调试 --limit 5；真实全量跑批前先 MOCK_LLM=1 验证流程。
"""
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--baseline", action="store_true")
    args = parser.parse_args()
    # TODO(M5): 见模块 docstring 步骤 1-5
    raise NotImplementedError("M5 里程碑实现（依赖 M2-M4 图与 validate 节点）")


if __name__ == "__main__":
    main()
