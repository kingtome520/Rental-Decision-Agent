"""AgentState 定义 —— 设计文档 §5.3 原样落地。

对应《后端开发手册》模块 5.1。
reducer 约定：
- trace 每节点 append 而非覆盖 → Annotated[list, operator.add]；
- messages 用 langgraph add_messages；
- 其余字段 last-write-wins。
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # 会话输入
    messages: Annotated[list[BaseMessage], add_messages]  # LangChain 消息列表（多轮）
    thread_id: str                                        # 会话 ID，checkpointer 用它恢复

    # 槽位与澄清
    user_profile: dict
    missing_slots: list[str]
    asked_slots: list[str]
    clarify_question: str | None
    defaults_used: list[str]                              # 追问超限后回退默认值的槽位（FR-01）

    # 约束（含已放宽记录）
    constraints: dict

    # 目的地坐标（geocode 一次写入，全流程复用）
    dest_coord: dict | None                               # {lat, lng}

    # 筛选与通勤
    listings_pool: list[dict]
    candidates: list[dict]                                # Top20（含粗筛距离 d_km）
    commute_results: dict                                 # listing_id -> {minutes, source}

    # 回溯与协商
    backtrack_count: int
    tried_constraint_sets: list[str]                      # 稳定序列化 key（FR-04 去重）
    relaxation_log: list[dict]
    negotiation_options: list[dict]                       # 待用户选的放宽方案
    negotiation_choice: str | None                        # 用户选完回填

    # 输出与观测
    final_recommendations: list[dict]
    report_text: str | None                               # 协商出口时放方案对比文本
    validation_failures: list[dict]
    regen_count: int                                      # report↔validate 重生成计数（上限 1）
    status: str                                           # clarifying/searching/negotiating/done/failed
    llm_calls: int
    trace: Annotated[list[dict], operator.add]            # 每节点 append


def initial_state(thread_id: str) -> AgentState:
    """空状态工厂，eval 与测试复用（手册模块 5.1）。"""
    return AgentState(
        messages=[], thread_id=thread_id,
        user_profile={}, missing_slots=[], asked_slots=[], clarify_question=None, defaults_used=[],
        constraints={}, dest_coord=None,
        listings_pool=[], candidates=[], commute_results={},
        backtrack_count=0, tried_constraint_sets=[], relaxation_log=[],
        negotiation_options=[], negotiation_choice=None,
        final_recommendations=[], report_text=None, validation_failures=[], regen_count=0,
        status="searching", llm_calls=0, trace=[],
    )
