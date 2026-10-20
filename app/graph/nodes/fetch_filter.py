"""筛选节点：geocode 目的地 + 硬约束过滤房源池。

对应 FR-02 / FR-08 / 手册模块 5.2。
规则：
- dest_coord 为空 → tools.map.geocode；返回 None → status=failed（提示重输，不进筛选）；
- 由 user_profile 生成 constraints（含默认值：room_type 不限 / max_walk 15）；
- search_listings(constraints) 写 listings_pool；池空由条件边路由到 backtrack；
- 预算低于全池最低价 → 直接转协商提示（FR-08）。
"""
from __future__ import annotations

from app.graph.state import AgentState


def fetch_and_filter(state: AgentState) -> dict:
    # TODO(M2): geocode + constraints 组装 + search_listings
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
