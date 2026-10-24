"""tools 层单测（手册模块 9 / 设计 §9.1）。离线运行由 conftest 保证。"""
from __future__ import annotations

from app.tools.map import estimate_minutes, haversine


def test_haversine_known_pair():
    """已知坐标对（西二旗 40.052,116.301 → 望京 40.002,116.489）误差 <1%。
    高德直线距离参考值 ≈ 16.95 km。"""
    d = haversine((40.052, 116.301), (40.002, 116.489))
    assert abs(d - 16.30) / 16.95 < 0.01


def test_estimate_minutes_uses_speed_table(mini_pool):
    """公交 18km/h：16.3km 直线 ≈54.3 分钟（含速度表口径）。"""
    m = estimate_minutes(mini_pool[0], {"lat": 40.002, "lng": 116.489}, "公交")
    assert m > 0


def test_search_listings_hard_constraints(mini_pool):
    from app.tools.listings import search_listings

    pool = search_listings({"budget_max": 3000, "room_type": "合租", "max_walk_to_subway_min": 15})
    assert [x["listing_id"] for x in pool] == ["BJ-0002", "BJ-0001"]  # 价格升序稳定
    assert all(x["price_monthly"] <= 3000 for x in pool)
    assert all(x["room_type"].startswith("合租") for x in pool)


def test_search_listings_empty_not_error(mini_pool):
    from app.tools.listings import search_listings
    assert search_listings({"budget_max": 100, "room_type": "整租"}) == []


def test_commute_cache_hit_no_request(mini_pool, monkeypatch):
    """缓存命中后不再调外部（mock 计数断言，M1 补全 commute_time 后启用）。"""
    # TODO(M1): cache_put 一条 key → commute_time → 断言 httpx/mock 调用计数为 0
    ...


def test_map_fail_rate_full_degrades_to_estimate(monkeypatch):
    """MAP_FAIL_RATE=1.0 时返回 source=estimate（依赖 M1 commute_time 实现）。"""
    # TODO(M1)
    ...
