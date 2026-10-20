"""配置中心 —— 全项目唯一的魔法数字与开关来源。

对应《后端开发手册》模块 1 / 设计文档 §7 环境变量约定。
所有值可被 .env 或环境变量覆盖（大小写不敏感），代码内禁止散落常量。
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM ----
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout_s: float = 30.0
    llm_max_retries: int = 1  # JSON 校验失败重试次数（§5.8）

    # ---- 地图（高德）----
    amap_key: str = ""
    map_timeout_ms: int = 3000
    map_call_warn_threshold: int = 50  # FR-03：单次运行累计告警

    # ---- 图执行参数 ----
    backtrack_max: int = 2             # FR-04：自动回溯上限
    coarse_topk: int = 20              # FR-03：粗筛保留数
    coarse_margin: float = 1.3         # FR-03：直线距离余量系数
    commute_llm_call_cap: int = 8      # §4：单次查询 LLM 调用上限

    # ---- 槽位默认值（FR-01）----
    default_commute_mode: str = "公交"
    default_room_type: str = "不限"
    default_max_walk_to_subway_min: int = 15

    # ---- Mock / 测试注入（§7）----
    mock_llm: bool = False
    mock_map: bool = False
    map_fail_rate: float = 0.0         # 脏输入测试：模拟地图超时概率

    # ---- 存储 ----
    database_url: str = "sqlite:///./app/data/rent_agent.db"
    checkpoint_db: str = "./app/data/checkpoints.db"  # SqliteSaver 独立文件（手册模块 2）

    # ---- 粗筛速度表（km/h，FR-03，北京城区合理值）----
    speed_kmh: dict[str, float] = {
        "驾车": 25.0,
        "公交": 18.0,
        "骑行": 15.0,
        "步行": 5.0,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
