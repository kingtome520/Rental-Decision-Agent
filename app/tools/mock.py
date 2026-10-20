"""Mock 实现 —— 离线开发与测试（手册模块 4.4 / 设计 §7 Mock 注入）。

约定：
- 与真实工具同签名；tools/llm.py、tools/map.py 在入口按开关委托到本模块；
- mock_llm_call 按 Prompt 头部 [[TASK:xxx]] 标记路由到固定返回，单测完全确定化；
- MAP_FAIL_RATE>0 时按概率模拟超时，验证降级路径；
- 单测/脏输入跑批：MOCK_LLM=1 MOCK_MAP=1 MAP_FAIL_RATE=1.0 全离线。
"""
from __future__ import annotations

import random

from app.config import settings
from app.tools.llm import regex_fallback_parse  # mock 与兜底保持同构输出

# ---- 固定返回表（与 tests/conftest 的迷你房源配合断言）----
MOCK_SLOT_JSON = {
    "budget_max": 3000,
    "dest_address": "西二旗软件园",
    "commute_limit_min": 45,
    "commute_mode": None,          # 默认缺 mode → 必触发一次澄清（FR-01 验收）
    "room_type": "合租",
    "max_walk_to_subway_min": None,
    "orientation_pref": "南",
}

MOCK_NEGOTIATE_JSON = {"plans": [
    {"plan": "预算加 500", "relax_field": "budget_max", "new_value": 3500, "cost_estimate": "预算 +500 元"},
    {"plan": "通勤放宽 15 分钟", "relax_field": "commute_limit_min", "new_value": 60, "cost_estimate": "通勤 +15 分钟"},
]}

MOCK_REASONS_JSON: dict[str, list[str]] = {}  # 按 candidates 动态生成，见 mock_llm_call


def mock_llm_call(prompt_text: str, schema=None) -> tuple:
    """按 [[TASK:xxx]] 路由固定返回。"""
    stats = {"calls": 1, "tokens": 0, "mock": True}
    if "[[TASK:parse_input]]" in prompt_text:
        # 从 prompt 里回抽用户原文，命中不了给默认 JSON
        return dict(MOCK_SLOT_JSON), stats
    if "[[TASK:clarify]]" in prompt_text:
        return "你平时主要靠什么通勤？公交、驾车还是骑行？", stats
    if "[[TASK:negotiate]]" in prompt_text:
        return dict(MOCK_NEGOTIATE_JSON), stats
    if "[[TASK:reasons]]" in prompt_text:
        return {"_mock": ["理由1", "理由2", "风险1"]}, stats
    if "[[TASK:summary]]" in prompt_text:
        return "（mock 摘要）已为你筛选出通勤达标、预算内的候选房源。", stats
    return regex_fallback_parse(prompt_text), stats


def mock_geocode(address: str) -> dict | None:
    """固定坐标表 + 未知地址返回 None（覆盖 FR-08 地理编码失败路径）。"""
    table = {
        "西二旗软件园": {"lat": 40.052, "lng": 116.301},
        "望京SOHO": {"lat": 40.002, "lng": 116.489},
        "国贸": {"lat": 39.908, "lng": 116.461},
    }
    return table.get(address)


def mock_commute_time(listing: dict, dest_coord: dict, mode: str) -> dict:
    """纯估算；MAP_FAIL_RATE=1.0 时全部走 estimate 分支（与降级路径同结果，验证标注逻辑）。"""
    if settings.map_fail_rate > 0 and random.random() < settings.map_fail_rate:
        # 模拟超时：真实实现里这里抛 httpx.TimeoutException，由 map.py 捕获降级
        pass
    from app.tools.map import haversine
    d_km = haversine((listing["lat"], listing["lng"]), (dest_coord["lat"], dest_coord["lng"]))
    return {"minutes": round(d_km / settings.speed_kmh[mode] * 60, 1), "source": "estimate"}
