"""判定节点：合格候选过滤 + 综合排序。

对应 FR-04 触发条件 / 手册模块 5.2。
规则：
- 合格 = commute_results[id].minutes ≤ constraints.commute_limit_min；
- 排序口径与 §6.2 标注一致：价格分位×0.4 + 通勤分位×0.4 + 地铁距离分位×0.2（升序优）；
- 软约束（朝向偏好、tags）参与排序加分，不做硬过滤；
- 合格数 < 2 → 条件边转 backtrack；≥2 → report；
- 输出按排序截断后的 Top 3–5（推荐条数写进 state 供 report 用）。
"""
from __future__ import annotations

from app.graph.state import AgentState


def evaluate_candidates(state: AgentState) -> dict:
    # TODO(M2): 过滤 + 分位数排序
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
