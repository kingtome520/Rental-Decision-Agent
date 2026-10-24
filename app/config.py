"""配置中心 —— 全项目唯一的魔法数字与开关来源。

对应《后端开发手册》模块 1 / 设计文档 §7 环境变量约定。
所有值可被 .env 或环境变量覆盖（大小写不敏感），代码内禁止散落常量。
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置类 —— 项目所有魔法数字与开关的唯一来源。

    职责：
        集中管理 LLM、地图、图执行参数、槽位默认值、Mock 开关、存储路径等配置项，
        避免常量散落在业务代码中。所有字段均可通过 .env 文件或环境变量覆盖（大小写不敏感）。

    使用场景：
        1. 在应用启动时通过 get_settings() 获取单例实例；
        2. 业务代码中直接 import settings 使用（已实例化）；
        3. 测试时可通过 monkeypatch 修改 settings 字段值。

    技术要点：
        - 继承 pydantic_settings.BaseSettings，自动从 .env 和环境变量加载配置；
        - model_config 指定 .env 文件路径、编码、忽略额外字段；
        - 所有字段都有类型注解和默认值，便于 IDE 提示和静态检查。

    Attributes:
        model_config: Pydantic 模型配置字典，控制 .env 加载行为。
    """

    # Pydantic 配置：从 .env 文件读取，UTF-8 编码，忽略未定义字段（防止 .env 多余键报错）
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- LLM 配置（DeepSeek 兼容接口）----
    llm_api_key: str = ""                              # API 密钥，生产环境必填
    llm_base_url: str = "https://api.deepseek.com"     # API 基础地址（OpenAI 兼容格式）
    llm_model: str = "deepseek-chat"                   # 模型名称，对应 DeepSeek 的 chat 模型
    llm_timeout_s: float = 30.0                        # 单次请求超时时间（秒），防止 LLM 卡死
    llm_max_retries: int = 1                           # JSON 校验失败后的重试次数（§5.8 成本约束）

    # ---- 地图配置（高德 Web 服务 API）----
    amap_key: str = ""                                 # 高德 API 密钥，生产环境必填
    map_timeout_ms: int = 3000                         # 地图请求超时时间（毫秒），超时走降级估算
    map_call_warn_threshold: int = 50                  # 单次运行累计调用次数告警阈值（FR-03 成本控制）

    # ---- 图执行参数（LangGraph 状态图控制）----
    backtrack_max: int = 2                             # 自动回溯上限（FR-04），超限转协商节点
    coarse_topk: int = 20                              # 粗筛保留候选数（FR-03），Top K 进入精算
    coarse_margin: float = 1.3                         # 直线距离余量系数（FR-03），半径 = 速度×时间×余量
    commute_llm_call_cap: int = 8                      # 单次查询 LLM 调用上限（§4 成本约束），防止死循环

    # ---- 槽位默认值（FR-01 必填槽位缺失时的回退值）----
    default_commute_mode: str = "公交"                 # 默认通勤方式，用户未指定时使用
    default_room_type: str = "不限"                    # 默认房型偏好，"不限"表示不过滤
    default_max_walk_to_subway_min: int = 15           # 默认步行到地铁上限（分钟），超过则剔除

    # ---- Mock / 测试注入（§7 离线开发开关）----
    mock_llm: bool = False                             # True 时 LLM 调用走 mock 固定返回，零成本
    mock_map: bool = False                             # True 时地图调用走 mock 估算，无网络
    map_fail_rate: float = 0.0                         # 模拟地图超时概率（0.0~1.0），用于脏输入测试

    # ---- 存储配置（SQLAlchemy 引擎）----
    database_url: str = "sqlite:///./app/data/rent_agent.db"   # 业务数据库 URL，SQLite 默认，可切 MySQL
    checkpoint_db: str = "./app/data/checkpoints.db"           # LangGraph 检查点文件（SqliteSaver 独立管理）

    # ---- 粗筛速度表（km/h，FR-03 北京城区合理值）----
    # 用途：coarse_filter 节点根据通勤方式查表计算直线距离半径
    # 结构：{通勤方式中文: 速度 km/h}，键必须与 constraints.commute_mode 一致
    speed_kmh: dict[str, float] = {
        "驾车": 25.0,    # 城区平均车速（含红绿灯）
        "公交": 18.0,    # 公交 + 地铁混合，含等车时间
        "骑行": 15.0,    # 共享单车/电动车
        "步行": 5.0,     # 正常步行速度
    }


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例（带 LRU 缓存，进程内只初始化一次）。

    Returns:
        Settings: 配置实例，所有字段已从 .env / 环境变量加载完毕。

    Example:
        >>> from app.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.llm_model)
        'deepseek-chat'

    Note:
        - 使用 @lru_cache 装饰器确保多次调用返回同一实例；
        - 测试时如需重置，可调用 get_settings.cache_clear() 清除缓存。
    """
    return Settings()


# 模块级配置实例 —— 应用启动时自动初始化，业务代码直接 import 使用
settings = get_settings()
