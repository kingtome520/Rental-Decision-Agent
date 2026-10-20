"""地图工具 —— geocode / commute_time / haversine / 缓存（手册模块 4.2 / FR-03 / §5.5）。

约定：
- httpx 同步调用（节点同步，图跑在 FastAPI 线程池——见手册模块 7 取舍说明）；
- 异常就地降级不向上抛：地图失败 → Haversine × 速度表估算，source=estimate；
- 缓存 key 唯一口径（FR-03 v0.2）：f"{listing_id}|{dest_lat:.4f},{dest_lng:.4f}|{mode}"；
- MOCK_MAP=1 或 MAP_FAIL_RATE>0 → 委托 tools.mock；
- 高德 duration 单位是秒，写入前统一转分钟（手册 §11 预警 4）。
"""
from __future__ import annotations

import math

from app.config import settings
from app.db import cache_get, cache_put, commute_cache, geocode_cache, utcnow_iso

AMAP_BASE = "https://restapi.amap.com"

# 进程内累计调用计数（单次运行超 MAP_CALL_WARN_THRESHOLD 告警）
_map_call_count = 0


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两点直线距离（km）。a/b 为 (lat, lng)。"""
    lat1, lng1, lat2, lng2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _warn_if_over_budget() -> None:
    global _map_call_count
    _map_call_count += 1
    if _map_call_count > settings.map_call_warn_threshold:
        import logging
        logging.getLogger(__name__).warning(
            "单次运行地图调用 %d 次，超过阈值 %d", _map_call_count, settings.map_call_warn_threshold)


def reset_map_call_count() -> None:
    """每次图执行开始时重置（供节点/评测调用）。"""
    global _map_call_count
    _map_call_count = 0


def estimate_minutes(listing: dict, dest: dict, mode: str) -> float:
    """降级估算：直线距离 ÷ 速度表（FR-03，source=estimate）。"""
    d_km = haversine((listing["lat"], listing["lng"]), (dest["lat"], dest["lng"]))
    return d_km / settings.speed_kmh[mode] * 60


def geocode(address: str) -> dict | None:
    """地理编码，DB 缓存优先；失败返回 None（上游走"提示重输"，FR-08）。"""
    if settings.mock_map:
        from app.tools import mock
        return mock.mock_geocode(address)

    hit = cache_get(geocode_cache, "address", address)
    if hit:
        return {"lat": hit["lat"], "lng": hit["lng"]}

    # TODO(M1): httpx GET {AMAP_BASE}/v3/geocode/geo?address=..&key=AMAP_KEY
    #   解析 geocodes[0].location("lng,lat" 顺序注意) → 写缓存 → 返回
    raise NotImplementedError("M1: 跑通高德 geocode + 缓存（手册模块 4.2）")


def commute_time(listing: dict, dest_coord: dict, mode: str) -> dict:
    """路径规划精算单套通勤分钟数。返回 {minutes, source: api|estimate}。"""
    if settings.mock_map:
        from app.tools import mock
        return mock.mock_commute_time(listing, dest_coord, mode)

    key = f"{listing['listing_id']}|{dest_coord['lat']:.4f},{dest_coord['lng']:.4f}|{mode}"
    hit = cache_get(commute_cache, "key", key)
    if hit:
        return {"minutes": hit["minutes"], "source": hit["source"]}

    # TODO(M1): 驾车 /v3/direction/driving；其余 /v3/direction/transit/integrated
    #   成功 → minutes = duration秒/60, source=api
    #   失败/超时(MAP_TIMEOUT_MS) → minutes = estimate_listing(...), source=estimate
    #   两种结果都写缓存（防重试风暴）；_warn_if_over_budget()
    raise NotImplementedError("M1: 跑通高德路径规划 + 缓存 + 降级（手册模块 4.2）")
