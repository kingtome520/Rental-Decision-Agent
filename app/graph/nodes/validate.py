"""校验节点：ID 白名单 + 通勤数值溯源（输出侧防幻觉）。

对应 FR-06 / 手册模块 5.2 / ADR-003。
规则：
- 每条推荐 listing_id ∈ listings_pool 且 commute_min ∈ commute_results[id]
  （或该 ID 存在 estimated=true 记录）；
- 不通过 → 剔除 + 追加 validation_failures（trace 可见）；
- 剔除后 <2 且 regen_count < 1 → 条件边回 report 重生成一次；
- 重试用尽仍失败 → 输出已通过部分 + 失败说明，status=done。
"""
from __future__ import annotations

from app.graph.state import AgentState


def validate_output(state: AgentState) -> dict:
    # TODO(M4): 白名单校验 + validation_failures
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
