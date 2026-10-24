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
    """LangGraph 状态字典 —— 图执行过程中的完整数据结构。

    所有节点共享此状态，通过返回增量字典更新（不原地修改）。
    字段按功能分组，便于理解和维护。

    Note:
        - TypedDict 提供类型提示，运行时仍为普通字典；
        - Annotated 用于指定 reducer（状态合并策略）；
        - 可选字段用 | None 标注，默认值在 initial_state 中设置。
    """

    # ---- 会话输入 ----
    # messages: LangChain 消息列表（多轮对话），使用 add_messages reducer 自动合并
    messages: Annotated[list[BaseMessage], add_messages]
    # thread_id: 会话唯一标识，checkpointer 用它恢复状态（格式：t_ + 12位十六进制）
    thread_id: str

    # ---- 槽位与澄清（FR-01 必填槽位管理）----
    # user_profile: 用户画像字典，从 parse_input 节点解析并合并（如 {budget_max: 3000, dest_address: "西二旗"}）
    user_profile: dict
    # missing_slots: 缺失的必填槽位列表（如 ["commute_mode", "commute_limit_min"]），按优先级排序
    missing_slots: list[str]
    # asked_slots: 已追问过的槽位列表（防止重复追问同一槽位）
    asked_slots: list[str]
    # clarify_question: 当前澄清问句（由 clarify 节点生成，interrupt 展示给用户）
    clarify_question: str | None
    # defaults_used: 追问超限后回退默认值的槽位列表（FR-01，用于报告顶部标注"以下按默认处理"）
    defaults_used: list[str]

    # ---- 约束（含已放宽记录）----
    # constraints: 约束字典（如 {budget_max: 3000, commute_limit_min: 45, commute_mode: "公交", room_type: "合租"}）
    # 由 fetch_filter 节点从 user_profile 生成，backtrack/negotiate 节点可能修改
    constraints: dict

    # ---- 目的地坐标（geocode 一次写入，全流程复用）----
    # dest_coord: 目的地坐标字典 {lat: float, lng: float}，由 fetch_filter 节点调用 geocode 获取
    dest_coord: dict | None

    # ---- 筛选与通勤（FR-02/FR-03）----
    # listings_pool: 硬约束过滤后的房源池（list[dict]，每条含完整房源字段）
    listings_pool: list[dict]
    # candidates: 粗筛后的 Top K 候选（list[dict]，每条附 d_km 直线距离字段）
    candidates: list[dict]
    # commute_results: 通勤精算结果字典 {listing_id: {minutes: float, source: str}}
    # source 取值：'api'（高德返回）| 'estimate'（Haversine 估算降级）
    commute_results: dict

    # ---- 回溯与协商（FR-04）----
    # backtrack_count: 已回溯次数（上限 settings.backtrack_max，默认 2）
    backtrack_count: int
    # tried_constraint_sets: 已尝试的约束组合列表（稳定序列化 key，用于去重防止死循环）
    # 格式：json.dumps(constraints, sort_keys=True)
    tried_constraint_sets: list[str]
    # relaxation_log: 放宽记录列表（每次回溯追加一条，如 {field: "budget_max", old: 3000, new: 3500}）
    relaxation_log: list[dict]
    # negotiation_options: 待用户选的放宽方案列表（由 negotiate 节点 L3 生成，interrupt 展示）
    negotiation_options: list[dict]
    # negotiation_choice: 用户选完回填的方案标识（如 "预算加 500"）
    negotiation_choice: str | None

    # ---- 输出与观测（§4 可观测性）----
    # final_recommendations: 最终推荐房源列表（list[dict]，每条含 listing_id, commute_min, reasons, risks）
    final_recommendations: list[dict]
    # report_text: 协商出口时放方案对比文本（markdown 格式），或最终报告文本
    report_text: str | None
    # validation_failures: 校验失败记录列表（validate 节点剔除不合格推荐时追加）
    validation_failures: list[dict]
    # regen_count: report↔validate 重生成计数（上限 1，防止死循环）
    regen_count: int
    # status: 图执行状态，取值：'clarifying' | 'searching' | 'negotiating' | 'done' | 'failed'
    status: str
    # llm_calls: 本次会话累计 LLM 调用次数（用于成本监控，上限 settings.commute_llm_call_cap）
    llm_calls: int
    # trace: 追踪记录列表（每节点执行后追加一条，使用 operator.add reducer 自动合并）
    # 每条格式：{node, ts, in_summary, out_summary, llm_calls, tokens, tool_calls}
    trace: Annotated[list[dict], operator.add]


def initial_state(thread_id: str) -> AgentState:
    """空状态工厂 —— 创建初始 AgentState 实例。

    Args:
        thread_id: 会话唯一标识（格式：t_ + 12位十六进制）。

    Returns:
        AgentState: 所有字段初始化的空状态字典。

    Note:
        - 列表字段初始化为空列表 []（避免可变默认值陷阱）；
        - 字典字段初始化为空字典 {}；
        - 数值字段初始化为 0；
        - 可选字段初始化为 None；
        - status 初始为 'searching'（进入图后由节点更新）。

    Example:
        >>> state = initial_state('t_abc123')
        >>> print(state['thread_id'], state['status'])
        't_abc123' 'searching'
    """
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
