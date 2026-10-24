"""房源检索工具 —— search_listings（手册模块 4.1 / FR-02）。

职责：
    从本地 JSON 文件加载房源池，按硬约束过滤，返回符合条件的房源列表。

设计原则：
    - 纯函数，无副作用；
    - 数据层与决策层解耦的 seam（ADR-004）：将来接真实数据源只改 _load_pool()；
    - 进程内缓存房源池（首次加载后复用，避免重复读文件）。

使用场景：
    - fetch_filter 节点调用 search_listings(constraints) 获取初始房源池；
    - 测试时可通过 monkeypatch 替换 LISTINGS_PATH 指向迷你房源文件。

技术要点：
    - 房源文件格式：app/data/listings.json（200 条模拟房源，由 scripts/generate_listings.py 生成）；
    - 硬约束：budget_max（必填）、room_type（前缀匹配）、max_walk_to_subway_min（可选）；
    - 软约束（朝向/tags）不在此过滤，交 evaluate 节点排序；
    - 返回结果按价格升序、listing_id 升序排列（保证可复现）。
"""
from __future__ import annotations

import json
from pathlib import Path

# 房源文件路径（app/data/listings.json）
LISTINGS_PATH = Path(__file__).resolve().parents[1] / "data" / "listings.json"

# 进程内缓存的房源池（首次加载后复用，避免重复读文件）
_pool: list[dict] | None = None


def _load_pool() -> list[dict]:
    """加载房源池（进程内缓存，首次调用时从 JSON 文件读取）。

    Returns:
        list[dict]: 房源列表，每条为字典（含完整房源字段）。

    Note:
        - 使用模块级 _pool 变量缓存，避免每次调用都读文件；
        - 测试时可通过 monkeypatch 替换 _pool 或 LISTINGS_PATH。
    """
    global _pool
    if _pool is None:
        _pool = json.loads(LISTINGS_PATH.read_text(encoding="utf-8"))
    return _pool


def search_listings(constraints: dict) -> list[dict]:
    """硬约束过滤 —— 返回满足全部硬约束的房源（价格升序，稳定可复现）。

    Args:
        constraints: 约束字典，可含以下键：
            - budget_max: int（必填），月租上限；
            - room_type: str（可选），房型偏好（"整租"|"合租"|"不限"），前缀匹配；
            - max_walk_to_subway_min: int（可选），步行到地铁上限（分钟），房源该字段存在时才约束。

    Returns:
        list[dict]: 符合条件的房源列表，按 (price_monthly, listing_id) 升序排列。

    Note:
        - 软约束（朝向/tags）不在此过滤，交 evaluate 节点排序；
        - 空结果返回 []（不报错），判定交给上游条件边 → backtrack；
        - room_type 前缀匹配："合租" 匹配 "合租-主卧/次卧/隔断"；
        - max_walk_to_subway_min 只在房源该字段存在时约束（缺失则跳过）。

    Example:
        >>> pool = search_listings({"budget_max": 3000, "room_type": "合租", "max_walk_to_subway_min": 15})
        >>> print(len(pool), pool[0]["listing_id"])
    """
    result = []
    for l in _load_pool():
        # 硬约束 1：价格不超过预算
        if l["price_monthly"] > constraints["budget_max"]:
            continue
        # 硬约束 2：房型前缀匹配（"不限" 全过）
        room = constraints.get("room_type", "不限")
        if room != "不限" and not l["room_type"].startswith(room):
            continue
        # 硬约束 3：步行到地铁上限（房源字段存在时才约束）
        max_walk = constraints.get("max_walk_to_subway_min")
        if max_walk is not None and l.get("walk_to_subway_min") is not None:
            if l["walk_to_subway_min"] > max_walk:
                continue
        result.append(l)
    # 按价格升序、listing_id 升序排列（保证可复现）
    return sorted(result, key=lambda x: (x["price_monthly"], x["listing_id"]))
