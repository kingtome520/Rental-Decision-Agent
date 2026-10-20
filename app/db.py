"""存储层 —— SQLite/MySQL 引擎切换 + 业务表 DDL。

对应《后端开发手册》模块 2 / 设计文档 §6.4。
约定：
- SQLAlchemy Core 定义表（不引 ORM），SQLite 与 MySQL 共用 DDL；
- 时间戳统一 UTC ISO 字符串（String(32)），规避 SQLite 无原生 DATETIME 的坑；
- LangGraph checkpoint 由 SqliteSaver 独立文件自管，不与业务表混用。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Float, Integer, MetaData, String, Table, Text, select, insert, delete

from app.config import settings

metadata = MetaData()

# 地理编码缓存（FR-08：目的地无法地理编码 → 提示重输）
geocode_cache = Table(
    "geocode_cache",
    metadata,
    Column("address", String(255), primary_key=True),
    Column("lat", Float, nullable=False),
    Column("lng", Float, nullable=False),
    Column("created_at", String(32), nullable=False),
)

# 通勤缓存，key 口径见 FR-03：{listing_id}|{lat:.4f},{lng:.4f}|{mode}
commute_cache = Table(
    "commute_cache",
    metadata,
    Column("key", String(255), primary_key=True),
    Column("minutes", Float, nullable=False),
    Column("source", String(16), nullable=False),  # api | estimate
    Column("created_at", String(32), nullable=False),
)

# 每节点一条（§7 代码规范 / §4 可观测）
trace = Table(
    "trace",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("thread_id", String(64), index=True, nullable=False),
    Column("node", String(64), nullable=False),
    Column("ts", String(32), nullable=False),
    Column("in_summary", Text, nullable=False),
    Column("out_summary", Text, nullable=False),
    Column("llm_calls", Integer, nullable=False, default=0),
    Column("tokens", Integer, nullable=False, default=0),
    Column("tool_calls", Text, nullable=True),  # JSON 序列化列表
)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_engine = None


def get_engine():
    """按 DATABASE_URL 返回单例引擎；SQLite 开 check_same_thread=False（FastAPI 线程池）。"""
    global _engine
    if _engine is None:
        url = settings.database_url
        kwargs = {}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        _engine = create_engine(url, **kwargs)
    return _engine


def init_db() -> None:
    """幂等建表，应用启动 lifespan 中调用。"""
    metadata.create_all(get_engine())


# ---------- 薄访问函数（供 tools / 节点调用） ----------

def cache_get(table: Table, key_column: str, key: str) -> dict | None:
    with get_engine().connect() as conn:
        row = conn.execute(select(table).where(table.c[key_column] == key)).first()
        return dict(row._mapping) if row else None


def cache_put(table: Table, values: dict) -> None:
    with get_engine().begin() as conn:
        # UPSERT 语义两端 DDL 不统一，简单起见：先删后插
        pk = list(table.primary_key.columns)[0].name
        conn.execute(delete(table).where(table.c[pk] == values[pk]))
        conn.execute(insert(table).values(**values))


def insert_trace(thread_id: str, node: str, in_summary: str, out_summary: str,
                 llm_calls: int = 0, tokens: int = 0, tool_calls: str | None = None) -> None:
    with get_engine().begin() as conn:
        conn.execute(insert(trace).values(
            thread_id=thread_id, node=node, ts=utcnow_iso(),
            in_summary=in_summary, out_summary=out_summary,
            llm_calls=llm_calls, tokens=tokens, tool_calls=tool_calls,
        ))


def get_traces(thread_id: str) -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(select(trace).where(trace.c.thread_id == thread_id).order_by(trace.c.id)).all()
        return [dict(r._mapping) for r in rows]
