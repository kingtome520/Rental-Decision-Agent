"""存储层 —— SQLite/MySQL 引擎切换 + 业务表 DDL + 薄访问函数。

对应《后端开发手册》模块 2 / 设计文档 §6.4。

职责：
    1. 定义 SQLAlchemy Core 表结构（不引 ORM，保持轻量）；
    2. 管理数据库引擎单例（SQLite/MySQL 双模切换）；
    3. 提供薄访问函数（cache_get/put、insert_trace、get_traces），供 tools 和节点调用；
    4. 时间戳统一 UTC ISO 字符串（String(32)），规避 SQLite 无原生 DATETIME 的坑。

技术要点：
    - SQLite 与 MySQL 共用 DDL，通过 settings.database_url 一键切换；
    - LangGraph checkpoint 由 SqliteSaver 独立文件自管（见 settings.checkpoint_db），不与业务表混用；
    - 所有表定义在模块级，应用启动时由 init_db() 幂等建表。

使用场景：
    - 应用启动：lifespan 中调用 init_db() 建表；
    - 业务代码：from app.db import cache_get, cache_put, insert_trace；
    - 测试：通过 monkeypatch 修改 settings.database_url 指向临时 SQLite。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Float, Integer, MetaData, String, Table, Text, select, insert, delete

from app.config import settings

# SQLAlchemy MetaData 实例 —— 所有表定义共享同一个元数据对象，便于批量建表
metadata = MetaData()

# ---- 地理编码缓存表（FR-08：目的地无法地理编码 → 提示重输）----
# 用途：缓存地址 → 坐标的映射，避免重复调用高德 API
# 主键：address（地址原文）
# 结构：{address: str, lat: float, lng: float, created_at: str}
geocode_cache = Table(
    "geocode_cache",
    metadata,
    Column("address", String(255), primary_key=True, comment="地址原文，作为缓存键"),
    Column("lat", Float, nullable=False, comment="纬度"),
    Column("lng", Float, nullable=False, comment="经度"),
    Column("created_at", String(32), nullable=False, comment="缓存创建时间（UTC ISO）"),
)

# ---- 通勤缓存表（FR-03：避免重复调用高德路径规划 API）----
# 用途：缓存 {房源ID, 目的地坐标, 通勤方式} → 通勤分钟数的映射
# 主键：key（格式：{listing_id}|{lat:.4f},{lng:.4f}|{mode}）
# 结构：{key: str, minutes: float, source: str, created_at: str}
# source 取值：'api'（高德返回）| 'estimate'（Haversine 估算降级）
commute_cache = Table(
    "commute_cache",
    metadata,
    Column("key", String(255), primary_key=True, comment="缓存键：{listing_id}|{lat:.4f},{lng:.4f}|{mode}"),
    Column("minutes", Float, nullable=False, comment="通勤时间（分钟）"),
    Column("source", String(16), nullable=False, comment="数据来源：api | estimate"),
    Column("created_at", String(32), nullable=False, comment="缓存创建时间（UTC ISO）"),
)

# ---- 追踪记录表（§7 代码规范 / §4 可观测性）----
# 用途：每个图节点执行后写入一条记录，用于调试、监控、成本统计
# 主键：id（自增）
# 结构：{thread_id, node, ts, in_summary, out_summary, llm_calls, tokens, tool_calls}
# 索引：thread_id（按会话查询）
trace = Table(
    "trace",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, comment="自增主键"),
    Column("thread_id", String(64), index=True, nullable=False, comment="会话 ID，用于关联同一轮对话的所有节点"),
    Column("node", String(64), nullable=False, comment="节点名称（如 parse_input, coarse_filter）"),
    Column("ts", String(32), nullable=False, comment="节点执行时间（UTC ISO）"),
    Column("in_summary", Text, nullable=False, comment="节点输入摘要（JSON 或简述）"),
    Column("out_summary", Text, nullable=False, comment="节点输出摘要（JSON 或简述）"),
    Column("llm_calls", Integer, nullable=False, default=0, comment="本节点 LLM 调用次数"),
    Column("tokens", Integer, nullable=False, default=0, comment="本节点 LLM 消耗 token 数"),
    Column("tool_calls", Text, nullable=True, comment="工具调用记录（JSON 序列化列表）"),
)


def utcnow_iso() -> str:
    """获取当前 UTC 时间的 ISO 8601 格式字符串（精确到秒）。

    Returns:
        str: UTC 时间字符串，格式如 '2026-10-23T12:34:56+00:00'。

    Note:
        - 统一使用 UTC 避免时区混乱；
        - 存入数据库时转为 String(32)，规避 SQLite 无原生 DATETIME 的坑；
        - 所有表的时间戳字段（created_at, ts）均调用此函数。

    Example:
        >>> utcnow_iso()
        '2026-10-23T12:34:56+00:00'
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# 模块级引擎单例 —— 首次调用 get_engine() 时初始化，后续复用
_engine = None


def get_engine():
    """按 DATABASE_URL 返回单例数据库引擎。

    Returns:
        Engine: SQLAlchemy 引擎实例（SQLite 或 MySQL）。

    Note:
        - SQLite 需开启 check_same_thread=False（FastAPI 线程池访问）；
        - SQLite 设置 timeout=30 防止 'database is locked' 偶发错误；
        - 引擎单例由模块级 _engine 变量保证，进程内只初始化一次。

    Example:
        >>> engine = get_engine()
        >>> with engine.connect() as conn:
        ...     result = conn.execute(select(trace).limit(1))
    """
    global _engine
    if _engine is None:
        url = settings.database_url
        kwargs = {}
        # SQLite 特殊配置：允许跨线程访问 + 锁等待超时
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _engine = create_engine(url, **kwargs)
    return _engine


def init_db() -> None:
    """幂等建表 —— 应用启动时在 lifespan 中调用。

    Note:
        - 使用 metadata.create_all() 批量创建所有已定义的表；
        - 幂等性：表已存在时不会报错，也不会覆盖数据；
        - SQLite 与 MySQL 共用 DDL，无需区分数据库类型。

    Example:
        >>> # 在 FastAPI lifespan 中调用
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     init_db()
        ...     yield
    """
    metadata.create_all(get_engine())


# ---------- 薄访问函数（供 tools / 节点调用）----------
# 设计原则：封装 SQL 操作为简单函数，业务代码无需直接写 SQL

def cache_get(table: Table, key_column: str, key: str) -> dict | None:
    """从缓存表查询单条记录。

    Args:
        table: SQLAlchemy Table 对象（geocode_cache 或 commute_cache）。
        key_column: 缓存键列名（如 'address' 或 'key'）。
        key: 缓存键值（如 '西二旗软件园' 或 'BJ-0001|40.0520,116.3010|公交'）。

    Returns:
        dict | None: 命中返回字典（含所有列），未命中返回 None。

    Example:
        >>> hit = cache_get(geocode_cache, 'address', '西二旗软件园')
        >>> if hit:
        ...     print(hit['lat'], hit['lng'])
    """
    with get_engine().connect() as conn:
        row = conn.execute(select(table).where(table.c[key_column] == key)).first()
        return dict(row._mapping) if row else None


def cache_put(table: Table, values: dict) -> None:
    """写入或更新缓存记录（UPSERT 语义）。

    Args:
        table: SQLAlchemy Table 对象（geocode_cache 或 commute_cache）。
        values: 要写入的字段字典，必须包含主键列。

    Note:
        - 由于 SQLAlchemy Core 不直接支持 UPSERT，采用"先删后插"策略；
        - 主键列从 table.primary_key.columns 动态获取（第一个主键）；
        - 适用于缓存场景（数据量小、写入频率低）。

    Example:
        >>> cache_put(geocode_cache, {
        ...     'address': '西二旗软件园',
        ...     'lat': 40.052,
        ...     'lng': 116.301,
        ...     'created_at': utcnow_iso()
        ... })
    """
    with get_engine().begin() as conn:
        # UPSERT 语义两端 DDL 不统一，简单起见：先删后插
        pk = list(table.primary_key.columns)[0].name
        conn.execute(delete(table).where(table.c[pk] == values[pk]))
        conn.execute(insert(table).values(**values))


def insert_trace(thread_id: str, node: str, in_summary: str, out_summary: str,
                 llm_calls: int = 0, tokens: int = 0, tool_calls: str | None = None) -> None:
    """插入一条追踪记录（每个节点执行后调用）。

    Args:
        thread_id: 会话 ID，用于关联同一轮对话的所有节点。
        node: 节点名称（如 'parse_input', 'coarse_filter'）。
        in_summary: 节点输入摘要（JSON 字符串或简述）。
        out_summary: 节点输出摘要（JSON 字符串或简述）。
        llm_calls: 本节点 LLM 调用次数，默认 0。
        tokens: 本节点 LLM 消耗 token 数，默认 0。
        tool_calls: 工具调用记录（JSON 序列化列表），默认 None。

    Note:
        - 时间戳 ts 由 utcnow_iso() 自动生成；
        - 记录写入 trace 表，供 /trace/{thread_id} 端点查询；
        - 用于调试、监控、成本统计（§4 可观测性）。

    Example:
        >>> insert_trace(
        ...     thread_id='t_abc123',
        ...     node='coarse_filter',
        ...     in_summary='pool=200, radius=17.5km',
        ...     out_summary='candidates=20',
        ...     llm_calls=0,
        ...     tokens=0
        ... )
    """
    with get_engine().begin() as conn:
        conn.execute(insert(trace).values(
            thread_id=thread_id, node=node, ts=utcnow_iso(),
            in_summary=in_summary, out_summary=out_summary,
            llm_calls=llm_calls, tokens=tokens, tool_calls=tool_calls,
        ))


def get_traces(thread_id: str) -> list[dict]:
    """按 thread_id 查询该会话的所有追踪记录（按执行顺序升序）。

    Args:
        thread_id: 会话 ID。

    Returns:
        list[dict]: 追踪记录列表，每条为字典（含所有列）；无记录时返回空列表。

    Note:
        - 结果按 id 升序排列（即节点执行顺序）；
        - 供 /trace/{thread_id} 端点返回完整决策链路；
        - 用于调试、监控、成本统计。

    Example:
        >>> traces = get_traces('t_abc123')
        >>> for t in traces:
        ...     print(f"{t['node']}: {t['in_summary']} -> {t['out_summary']}")
    """
    with get_engine().connect() as conn:
        rows = conn.execute(select(trace).where(trace.c.thread_id == thread_id).order_by(trace.c.id)).all()
        return [dict(r._mapping) for r in rows]
