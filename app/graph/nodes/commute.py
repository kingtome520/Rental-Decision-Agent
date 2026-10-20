"""精算节点：对 Top K 调高德路径规划（经 tools.map，含缓存与降级）。

对应 FR-03 阶段二 / 手册模块 5.2。
规则：
- 逐个 commute_time(listing_id, dest_coord, mode)，写 commute_results；
- 回溯重跑时排除已在 commute_results 中的 listing（去重省配额）；
- API 失败 → tools.map 内部降级 source=estimate，节点不感知异常；
- 缓存 key 唯一口径见 FR-03（tools/map.py 组装，节点不拼 key）。
"""
from __future__ import annotations

from app.graph.state import AgentState


def compute_commute(state: AgentState) -> dict:
    # TODO(M1): 遍历 candidates 调 commute_time，聚合 commute_results
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
