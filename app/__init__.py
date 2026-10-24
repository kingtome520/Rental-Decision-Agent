"""Rental Decision Agent — 后端应用包。

本包是项目的核心业务逻辑层，包含：
    - config.py: 全局配置中心（所有魔法数字和开关的唯一来源）
    - db.py: 存储层（SQLite/MySQL 双模，业务表 + 缓存表 + 追踪表）
    - main.py: FastAPI 入口（HTTP 接口层，提供 /chat /trace /health 端点）
    - graph/: LangGraph 状态图（决策流程编排，含 10 个节点）
    - tools/: 工具层（LLM 调用、地图 API、房源检索、Mock 实现）

技术栈：
    - Python 3.12
    - FastAPI 0.115 + Uvicorn 0.34
    - LangGraph 0.4 + LangChain Core 0.3
    - SQLAlchemy 2.0（Core 模式，无 ORM）
    - Pydantic 2.11（数据校验 + 配置管理）
    - httpx 0.28（HTTP 客户端，同步调用）

启动方式：
    uvicorn app.main:app --reload --port 8000
"""
