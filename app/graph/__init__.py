"""LangGraph 状态图包 —— 决策流程编排核心。

本包实现《设计文档》§5.2 状态图，包含：
    - state.py: AgentState 定义（TypedDict，含 reducer 约定）
    - schemas.py: LLM 结构化输出 Pydantic 模型（SlotsSchema, NegotiateSchema, ReasonsSchema）
    - build.py: 图装配（StateGraph + 条件边 + checkpointer）
    - nodes/: 10 个图节点（parse_input, clarify, fetch_filter, coarse_filter, commute, evaluate, backtrack, negotiate, report, validate）

技术要点：
    - 使用 LangGraph StateGraph 实现有状态决策图（支持条件边、interrupt、checkpointer）；
    - 节点统一签名：def node(state: AgentState) -> dict，返回 state 增量（不原地修改）；
    - 条件边路由函数为纯函数：state -> 下一节点名/END，可脱离图单测；
    - checkpointer 使用 SqliteSaver（独立文件），支持会话恢复。

开发顺序（手册 §11）：
    M2: 先跑通单节点 interrupt + SqliteSaver 最小 demo → 逐个实现节点 → 装配图 → 接入 main.py
    M3: backtrack/negotiate 节点 + 条件边 + 协商续跑
    M4: validate 节点 + trace 落 DB + /trace 端点
"""
