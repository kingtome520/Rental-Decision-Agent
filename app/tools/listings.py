"""房源检索工具 —— search_listings（手册模块 4.1 / FR-02）。

本地 JSON 查询，纯函数；数据层与决策层解耦的 seam（ADR-004）：
将来接真实数据源只改本文件的 _load_pool()。
"""
from __future__ import annotations

import json
from pathlib import Path

LISTINGS_PATH = Path(__file__).resolve().parents[1] / "data" / "listings.json"

_pool: list[dict] | None = None


def _load_pool() -> list[dict]:
    """进程内缓存加载 listings.json。"""
    global _pool
    if _pool is None:
        _pool = json.loads(LISTINGS_PATH.read_text(encoding="utf-8"))
    return _pool


def search_listings(constraints: dict) -> list[dict]:
    """硬约束过滤，返回满足全部硬约束的房源（价格升序，稳定可复现）。

    constraints 键：
      budget_max: int（必填）
      room_type: "整租"|"合租"|"不限" —— 前缀匹配（合租 → 合租-主卧/次卧/隔断）
      max_walk_to_subway_min: int —— 房源该字段存在时才约束
    软约束（朝向/tags）不在此过滤，交 evaluate 排序。
    空结果返回 []（判定交给上游条件边 → backtrack），不报错。
    """
    result = []
    for l in _load_pool():
        if l["price_monthly"] > constraints["budget_max"]:
            continue
        room = constraints.get("room_type", "不限")
        if room != "不限" and not l["room_type"].startswith(room):
            continue
        max_walk = constraints.get("max_walk_to_subway_min")
        if max_walk is not None and l.get("walk_to_subway_min") is not None:
            if l["walk_to_subway_min"] > max_walk:
                continue
        result.append(l)
    return sorted(result, key=lambda x: (x["price_monthly"], x["listing_id"]))
