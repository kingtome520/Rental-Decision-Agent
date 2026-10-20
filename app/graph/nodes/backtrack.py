"""回溯节点：自动放宽约束，≤ BACKTRACK_MAX(2) 次。

对应 FR-04 / 手册模块 5.2 / ADR-002。
策略顺序（v0.2 定案）：
1. 第 1 次：半径 ×1.5（等价 commute_limit ×1.5）；
2. 第 2 次：通勤上限 +10 分钟；
3. 仍无解（backtrack_count 达上限）→ 条件边转 negotiate，禁止无限循环。
规则：
- 新约束组合 json.dumps(sort_keys=True) 入 tried_constraint_sets，重复直接跳过；
- 每次放宽写 relaxation_log（trace 演示点："每次回溯放宽了什么"）。
"""
from __future__ import annotations

from app.graph.state import AgentState


def backtrack(state: AgentState) -> dict:
    # TODO(M3): 策略选择 + 去重 + relaxation_log 追加
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
