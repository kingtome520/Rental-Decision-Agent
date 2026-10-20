"""协商节点（interrupt）：生成放宽方案，等用户选择后续跑。

对应 FR-04 / 设计 §5.7 / 手册模块 5.2 / ADR-005。
流程：
1. L3 生成 2–3 个 {plan, relax_field, new_value, cost_estimate}（LLM 失败→模板拼接 relaxation_log）；
2. interrupt({"type": "negotiate", "options": [...]}) 暂停；
3. 用户选择回填 negotiation_choice → 按方案改写 constraints；
4. 返回 {"backtrack_count": 0, "constraints": 新约束, ...}，条件边导回 fetch_and_filter。
规则：协商模式不生成推荐房源，只生成方案对比。
"""
from __future__ import annotations

from app.graph.state import AgentState


def negotiate(state: AgentState) -> dict:
    # TODO(M3): L3 + interrupt + 选择回填
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
