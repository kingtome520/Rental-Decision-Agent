"""粗筛节点：Haversine 直线距离保留 Top K（默认 20）。

对应 FR-03 阶段一 / 手册模块 5.2。
规则：
- 半径(km) = speed_kmh[mode] × (commute_limit_min / 60) × coarse_margin(1.3)；
- 保留 d ≤ 半径的房源，按 d 升序取 COARSE_TOPK；
- 候选为空 → 条件边转 backtrack；
- 本节点输出 candidates（每条附 d_km，供报告与排序）。
"""
from __future__ import annotations

from app.config import settings
from app.graph.nodes._trace import trace_entry
from app.graph.state import AgentState
from app.tools.map import haversine


def coarse_filter(state: AgentState) -> dict:
    """
    粗筛节点：Haversine 直线距离保留 Top K（默认 20）。
    :param state: 状态
    :return: 粗筛结果
    """
    # TODO(M1 可先直筒子实现): haversine 逐条计算 + 排序截断

    #获取基础计算数据 1) 从 state 取输入,使用get防止取不到时的崩溃
    dest = state.get("dest_coord")          # {"lat":.., "lng":..} 或 None
    pool = state.get("listings_pool", [])   # 房源列表
    constraints = state["constraints"]
    if not dest:  # 防御：没有目的地坐标，直接空候选
        return {"candidates": [], "trace": [trace_entry("coarse_filter", "缺 dest_coord", "candidates=0")]}

    # 计算直线距离并筛选
    km = settings.speed_kmh[constraints["mode"]] * (constraints["commute_limit_min"] / 60) * settings.coarse_margin

    d_km = haversine(dest, pool[0]["coord"])
