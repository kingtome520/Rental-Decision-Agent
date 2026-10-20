"""pytest 公共 fixture —— 临时 SQLite + 迷你房源池 + initial_state（手册模块 9）。"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

# 测试环境强制全离线（必须在导入 app 之前设置）
os.environ.update({"MOCK_LLM": "1", "MOCK_MAP": "1", "MAP_FAIL_RATE": "0.0"})

MINI_LISTINGS = [
    {"listing_id": "BJ-0001", "title": "西二旗·主卧", "city": "北京", "district": "海淀区",
     "business_area": "西二旗", "price_monthly": 2600, "area_sqm": 16, "room_type": "合租-主卧",
     "floor": "中楼层", "orientation": "南", "walk_to_subway_min": 8, "subway_line": "13号线",
     "lat": 40.052, "lng": 116.301, "tags": ["近地铁", "朝南"]},
    {"listing_id": "BJ-0002", "title": "西二旗·次卧", "city": "北京", "district": "海淀区",
     "business_area": "西二旗", "price_monthly": 2100, "area_sqm": 12, "room_type": "合租-次卧",
     "floor": "低楼层", "orientation": "北", "walk_to_subway_min": 12, "subway_line": "13号线",
     "lat": 40.057, "lng": 116.306, "tags": []},
    {"listing_id": "BJ-0003", "title": "上地·1室", "city": "北京", "district": "海淀区",
     "business_area": "上地", "price_monthly": 5800, "area_sqm": 45, "room_type": "整租-1室",
     "floor": "高楼层", "orientation": "东南", "walk_to_subway_min": 6, "subway_line": "13号线",
     "lat": 40.041, "lng": 116.326, "tags": ["近地铁", "有电梯"]},
    {"listing_id": "BJ-0004", "title": "回龙观·隔断", "city": "北京", "district": "昌平区",
     "business_area": "回龙观", "price_monthly": 1800, "area_sqm": 10, "room_type": "合租-隔断",
     "floor": "中楼层", "orientation": "西", "walk_to_subway_min": 18, "subway_line": "13号线",
     "lat": 40.071, "lng": 116.336, "tags": []},
    {"listing_id": "BJ-0005", "title": "望京·主卧", "city": "北京", "district": "朝阳区",
     "business_area": "望京", "price_monthly": 3200, "area_sqm": 18, "room_type": "合租-主卧",
     "floor": "低楼层", "orientation": "南", "walk_to_subway_min": 5, "subway_line": "15号线",
     "lat": 40.002, "lng": 116.489, "tags": ["近地铁", "朝南"]},
]


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    """每个测试独立 SQLite 文件，避免缓存/trace 串扰。"""
    from app import config, db

    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setattr(config.settings, "database_url", url)
    db._engine = None  # 重置单例引擎
    db.init_db()
    yield
    db._engine = None


@pytest.fixture
def mini_pool(tmp_path, monkeypatch):
    """迷你房源池替换 200 条全量（节点/工具单测够用）。"""
    from app.tools import listings

    p = tmp_path / "listings.json"
    p.write_text(json.dumps(MINI_LISTINGS, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(listings, "LISTINGS_PATH", p)
    monkeypatch.setattr(listings, "_pool", None)
    yield MINI_LISTINGS
    monkeypatch.setattr(listings, "_pool", None)


@pytest.fixture
def base_state():
    from app.graph.state import initial_state
    return initial_state("t_test")
