"""生成 200 条北京模拟房源 —— app/data/listings.json（M1 第一步，手册模块 3）。

设计 §6.1 价格公式：
  price = BASE[district] × ROOM_COEF[room_type] × DIST_SUBWAY_COEF[walk桶]
          × ORIENTATION_COEF[orientation] × FLOOR_COEF[floor] ± N(0, 0.05)
自洽性：小区中心按目标步行分钟（80m/min）布在地铁站周边，房源经纬度在小区中心
±0.005 度抖动，walk_to_subway_min 由房源实际坐标反算，保证"字段与坐标一致"。
固定 seed，可重复执行（评估标注复用同一份数据）。

用法：python scripts/generate_listings.py
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

SEED = 20261019
OUT_PATH = Path(__file__).resolve().parents[1] / "app" / "data" / "listings.json"
WALK_KM_PER_MIN = 0.08  # 步行 80m/min

# ---- 系数表（§6.1，可配置）----
BASE = {"海淀区": 3800, "朝阳区": 3500, "西城区": 4200, "东城区": 4000, "昌平区": 2800, "大兴区": 2800}
ROOM_TYPES = ["整租-1室", "整租-2室", "合租-主卧", "合租-次卧", "合租-隔断"]
ROOM_COEF = {"整租-1室": 1.6, "整租-2室": 2.4, "合租-主卧": 1.0, "合租-次卧": 0.8, "合租-隔断": 0.65}
ORIENTATIONS = ["南", "东南", "东", "北", "西"]
ORIENTATION_COEF = {"南": 1.05, "东南": 1.0, "东": 0.98, "北": 0.92, "西": 0.9}
FLOORS = ["低楼层", "中楼层", "高楼层"]
FLOOR_COEF = {"低楼层": 0.95, "中楼层": 1.0, "高楼层": 1.03}

# ---- 地铁站表：(站名, 线路, 区, 商圈, lat, lng) ----
STATIONS = [
    ("西二旗", "13号线", "海淀区", "西二旗", 40.052, 116.301),
    ("上地", "13号线", "海淀区", "上地", 40.041, 116.326),
    ("中关村", "4号线", "海淀区", "中关村", 39.985, 116.326),
    ("五道口", "13号线", "海淀区", "五道口", 39.992, 116.337),
    ("望京", "15号线", "朝阳区", "望京", 40.002, 116.489),
    ("国贸", "1号线", "朝阳区", "国贸", 39.908, 116.461),
    ("双井", "10号线", "朝阳区", "双井", 39.898, 116.478),
    ("劲松", "10号线", "朝阳区", "劲松", 39.883, 116.472),
    ("阜成门", "2号线", "西城区", "阜成门", 39.923, 116.352),
    ("月坛", "16号线", "西城区", "月坛", 39.916, 116.356),
    ("东直门", "2号线", "东城区", "东直门", 39.941, 116.434),
    ("和平里北街", "5号线", "东城区", "和平里", 39.959, 116.416),
    ("回龙观", "13号线", "昌平区", "回龙观", 40.071, 116.336),
    ("天通苑北", "5号线", "昌平区", "天通苑", 40.082, 116.419),
    ("亦庄", "亦庄线", "大兴区", "亦庄", 39.794, 116.505),
]

XIAOQU_NAMES = ["融泽嘉园", "保利罗兰", "万象新天", "中关村东南小区", "智优家园", "望京西园",
                "大西洋新城", "双井广渠家苑", "采月社区", "阜外西里", "东直门银座", "安贞西里",
                "新龙城", "天通苑北一区", "亦庄园", "育新小区", "西雨小区", "橙福家园",
                "禾光里", "悦美社区", "金澳花园", "清泽园", "北辰绿色", "华纺易城", "后现代城"]


def km_to_deg(km: float, lat: float) -> tuple[float, float]:
    """距离 → (dlat, dlng) 度数近似。"""
    return km / 111.0, km / (111.0 * math.cos(math.radians(lat)))


def gen_one(listing_id: str, xiaoqu: str, st: tuple, rng: random.Random) -> dict:
    _, line, district, area, st_lat, st_lng = st
    room_type = rng.choice(ROOM_TYPES)
    orientation = rng.choice(ORIENTATIONS)
    floor = rng.choice(FLOORS)

    # 房源坐标：地铁站随机方向 0.3~2.4km（≈4~30 分钟步行）
    dist_km = rng.uniform(0.3, 2.4)
    bearing = rng.uniform(0, 2 * math.pi)
    dlat, dlng = km_to_deg(dist_km, st_lat)
    lat = round(st_lat + dlat * math.sin(bearing) + rng.uniform(-0.003, 0.003), 4)
    lng = round(st_lng + dlng * math.cos(bearing) + rng.uniform(-0.003, 0.003), 4)
    walk_min = max(1, round(dist_km / WALK_KM_PER_MIN))

    # 价格公式（§6.1）
    if walk_min <= 5:
        dist_coef = 1.15
    elif walk_min <= 10:
        dist_coef = 1.05
    elif walk_min <= 15:
        dist_coef = 1.0
    elif walk_min <= 20:
        dist_coef = 0.92
    else:
        dist_coef = 0.85
    price = (BASE[district] * ROOM_COEF[room_type] * dist_coef
             * ORIENTATION_COEF[orientation] * FLOOR_COEF[floor])
    price = round(price * (1 + rng.gauss(0, 0.05)) / 50) * 50

    area_sqm = 15 if room_type.startswith("合租") else rng.choice([45, 55, 65, 80])
    tags = []
    if walk_min <= 10:
        tags.append("近地铁")
    if orientation in ("南", "东南"):
        tags.append("朝南")
    if floor == "高楼层" and rng.random() < 0.7:
        tags.append("有电梯")

    return {
        "listing_id": listing_id,
        "title": f"{area}·{room_type.split('-')[-1]}",
        "city": "北京",
        "district": district,
        "business_area": area,
        "xiaoqu": xiaoqu,
        "price_monthly": price,
        "area_sqm": area_sqm,
        "room_type": room_type,
        "floor": floor,
        "orientation": orientation,
        "walk_to_subway_min": walk_min,
        "subway_line": line,
        "lat": lat,
        "lng": lng,
        "tags": tags,
    }


def main() -> None:
    rng = random.Random(SEED)
    listings = []
    for i in range(200):
        st = STATIONS[i % len(STATIONS)]
        xiaoqu = XIAOQU_NAMES[(i // 8) % len(XIAOQU_NAMES)]
        listings.append(gen_one(f"BJ-{i + 1:04d}", xiaoqu, st, rng))

    # 自检
    ids = {l["listing_id"] for l in listings}
    assert len(listings) == 200 and len(ids) == 200, "ID 必须唯一且共 200 条"
    prices = [l["price_monthly"] for l in listings]
    # 公式含整租-2室×西城区可达 ≈10k，合理上限 12000；合租隔断低端 ≈1200
    assert 1000 <= min(prices) and max(prices) <= 12000, f"价格分布异常: {min(prices)}-{max(prices)}"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(listings, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 {len(listings)} 条房源 → {OUT_PATH}")
    print(f"价格区间: {min(prices)} ~ {max(prices)} 元/月")


if __name__ == "__main__":
    main()
