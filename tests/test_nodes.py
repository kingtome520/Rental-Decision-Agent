"""节点纯函数单测（手册模块 9 / 设计 §9.1）：MOCK_LLM=1 固定输入输出，断言 state 增量。"""
from __future__ import annotations

import pytest


def test_route_after_parse_missing_mode_goes_clarify(base_state):
    """缺 commute_mode → 路由到 clarify（FR-01 验收前置）。"""
    from app.graph.build import route_after_parse
    from app.graph.nodes.parse_input import parse_input

    state = {**base_state, "messages": []}
    # TODO(M2): 用 mock L1 固定返回（缺 mode）填充 state 后断言路由
    pytest.skip("M2 实现 parse_input 后启用")


def test_coarse_filter_radius_boundary():
    """半径边界：d 恰好 = speed×(limit/60)×1.3 的房源保留，超出 1 个身位剔除。"""
    # TODO(M2)
    pytest.skip("M2 实现 coarse_filter 后启用")


def test_validate_rejects_fake_id(base_state):
    """注入不存在的 listing_id → 被剔除且 validation_failures 留痕（FR-06 验收）。"""
    pytest.skip("M4 实现 validate_output 后启用")
    from app.graph.nodes.validate import validate_output

    state = {**base_state,
             "listings_pool": [{"listing_id": "BJ-0001"}],
             "commute_results": {"BJ-0001": {"minutes": 30, "source": "api"}},
             "final_recommendations": [
                 {"listing_id": "BJ-0001", "commute_min": 30},
                 {"listing_id": "BJ-9999", "commute_min": 25},  # 假 ID
             ]}
    delta = validate_output(state)
    assert all(r["listing_id"] != "BJ-9999" for r in delta["final_recommendations"])
    assert any(f["listing_id"] == "BJ-9999" for f in delta["validation_failures"])
