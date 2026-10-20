"""粗筛节点：Haversine 直线距离保留 Top K（默认 20）。

对应 FR-03 阶段一 / 手册模块 5.2。
规则：
- 半径(km) = speed_kmh[mode] × (commute_limit_min / 60) × coarse_margin(1.3)；
- 保留 d ≤ 半径的房源，按 d 升序取 COARSE_TOPK；
- 候选为空 → 条件边转 backtrack；
- 本节点输出 candidates（每条附 d_km，供报告与排序）。
"""
from __future__ import annotations

from app.graph.state import AgentState


def coarse_filter(state: AgentState) -> dict:
    # TODO(M1 可先直筒子实现): haversine 逐条计算 + 排序截断
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
