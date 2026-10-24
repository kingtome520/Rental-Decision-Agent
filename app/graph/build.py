
"""图装配 —— StateGraph 节点注册 + 条件边路由 + checkpointer 注入。

对应设计 §5.2 状态图 / 手册模块 5.3。

职责：
    1. 注册 10 个节点到 StateGraph；
    2. 定义条件边路由函数（纯函数，state → 下一节点名/END）；
    3. 编译图并注入 checkpointer（SqliteSaver，支持会话恢复）。

边拓扑（设计 §5.2）：
    START → parse_input →(route_after_parse)→ clarify | fetch_and_filter
    fetch_and_filter →(route_after_filter)→ backtrack | coarse_filter
    coarse_filter →(route_after_coarse)→ backtrack | compute_commute
    compute_commute → evaluate_candidates →(route_after_evaluate)→ generate_report | backtrack
    backtrack →(route_after_backtrack)→ fetch_and_filter | negotiate
    negotiate → validate_output            # 协商只出方案文本，白名单校验后出口
    generate_report → validate_output →(route_after_validate)→ END | generate_report(regen≤1)

技术要点：
    - 条件边路由函数是纯函数（state → 节点名/END），可脱离图单测；
    - clarify / negotiate 内部使用 interrupt()，恢复由 Command(resume=...) 驱动；
    - compile(checkpointer=SqliteSaver)，thread_id 在 invoke config 传入；
    - 图实例缓存为模块级单例，避免重复编译。

开发顺序（手册 §11）：
    M2: 先实现 route_after_parse/route_after_filter/route_after_evaluate + get_graph（不含 backtrack/negotiate）
    M3: 补充 route_after_backtrack + negotiate 节点
    M4: 补充 route_after_validate + validate 节点
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.config import settings
from app.graph.nodes.backtrack import backtrack
from app.graph.nodes.clarify import clarify
from app.graph.nodes.coarse_filter import coarse_filter
from app.graph.nodes.commute import compute_commute
from app.graph.nodes.evaluate import evaluate_candidates
from app.graph.nodes.fetch_filter import fetch_and_filter
from app.graph.nodes.negotiate import negotiate
from app.graph.nodes.parse_input import parse_input
from app.graph.nodes.report import generate_report
from app.graph.nodes.validate import validate_output
from app.graph.state import AgentState


def route_after_parse(state: AgentState) -> str:
    """parse_input 节点后的路由 —— 缺必填槽位 → clarify，齐全 → fetch_and_filter。

    Args:
        state: 当前状态字典。

    Returns:
        str: 下一节点名称（'clarify' 或 'fetch_and_filter'）。

    Note:
        - 纯函数，不修改 state；
        - 判断逻辑：state['missing_slots'] 非空 → 'clarify'，否则 → 'fetch_and_filter'；
        - 可脱离图单测（直接传 state 字典断言返回值）。
    """

    if state.get("missing_slots"):
        return "clarify"
    else:
        return "fetch_and_filter"



def route_after_filter(state: AgentState) -> str:
    """fetch_and_filter 节点后的路由 —— 房源池空 → backtrack(回溯)，否则 → coarse_filter (`粗筛`)。

    Args:
        state: 当前状态字典。

    Returns:
        str: 下一节点名称（'backtrack' 或 'coarse_filter'）。

    Note:
        - 判断逻辑：state['listings_pool'] 为空 → 'backtrack'，否则 → 'coarse_filter'；
        - 池空说明硬约束过严，需要回溯放宽。

    Raises:
        NotImplementedError: M2 待实现。
    """
    ...  # TODO(M2): 池空 → backtrack

    if state.get("listings_pool"):
        return "coarse_filter"
    else:
        return "backtrack"


def route_after_coarse(state: AgentState) -> str:
    """coarse_filter 节点后的路由 —— 粗筛结果空 → backtrack，否则 → compute_commute。

    Args:
        state: 当前状态字典。

    Returns:
        str: 下一节点名称（'compute_commute' 或 'backtrack'）。

    Note:
        - 判断逻辑：state['candidates'] 为空 → 'backtrack'，否则 → 'compute_commute'；
        - 半径内一套房都没有，继续精算没有意义，直接回溯放宽。
    """

    if state.get("candidates"):
        return "compute_commute"
    return "backtrack"


def route_after_evaluate(state: AgentState) -> str:
    """evaluate_candidates 节点后的路由 —— 合格候选 <2 → backtrack，否则 → generate_report。

    Args:
        state: 当前状态字典。

    Returns:
        str: 下一节点名称（'backtrack' 或 'generate_report'）。

    Note:
        - 判断逻辑：state['final_recommendations'] 长度 <2 → 'backtrack'，否则 → 'generate_report'；
        - 合格候选不足 2 套说明约束仍过严，需要回溯放宽。

    Raises:
        NotImplementedError: M2 待实现。
    """
    ...  # TODO(M2): 合格 <2 → backtrack
    if len(state.get("final_recommendations")) < 2:
        return "backtrack"
    else:
        return "generate_report"




def route_after_backtrack(state: AgentState) -> str:
    """backtrack 节点后的路由 —— 未超限 → fetch_and_filter，超限 → negotiate。

    Args:
        state: 当前状态字典。

    Returns:
        str: 下一节点名称（'fetch_and_filter' 或 'negotiate'）。

    Note:
        - 判断逻辑：state['backtrack_count'] < settings.backtrack_max → 'fetch_and_filter'，
          否则 → 'negotiate'（进入协商模式，让用户选择放宽方案）；
        - 防止无限回溯（上限默认 2 次）。

    Raises:
        NotImplementedError: M3 待实现。
    """
    ...  # TODO(M3): 超限 → negotiate
    if state.get("backtrack_count") < settings.backtrack_max:
        return "fetch_and_filter"
    else:
        return "negotiate"



def route_after_validate(state: AgentState) -> str:
    """validate_output 节点后的路由 —— 校验失败且重试用尽 → END，否则 → generate_report 重生成。

    Args:
        state: 当前状态字典。

    Returns:
        str: 下一节点名称（'END' 或 'generate_report'）。

    Note:
        - 判断逻辑：state['validation_failures'] 非空 且 state['regen_count'] < 1 → 'generate_report'（重生成一次），
          否则 → 'END'（输出已通过部分 + 失败说明）；
        - 防止无限重生成（上限 1 次）。

    Raises:
        NotImplementedError: M4 待实现。
    """
    ...  # TODO(M4): 未通过 & regen<1 → generate_report，否则 END
    if state.get("validation_failures") and state.get("regen_count", 0) < 1:
        return "generate_report"
    else:
        return END



# 模块级单例缓存 —— 默认 checkpointer 的图只编译一次
_graph: CompiledStateGraph | None = None


def _make_sqlite_saver() -> SqliteSaver:
    """创建进程级长连接 SqliteSaver（供默认图使用）。

    Returns:
        SqliteSaver: 绑定 settings.checkpoint_db 的检查点存储实例。

    Note:
        - 不用 SqliteSaver.from_conn_string()：它是 @contextmanager，with 退出即关连接，
          无法作为长生命周期单例使用；这里手工建连接；
        - check_same_thread=False：FastAPI 把同步 endpoint 丢线程池，连接会跨线程使用；
          SqliteSaver 内部有 threading.Lock 保证串行；
        - timeout=30：缓解偶发 database is locked（手册 §11 预警 3）；
        - 建表由 SqliteSaver.cursor() 首次访问时惰性调用 setup() 完成，无需手动建表。
    """
    db_path = Path(settings.checkpoint_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=30)
    return SqliteSaver(conn)


def _build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """按设计 §5.2 边拓扑装配并编译图。

    Args:
        checkpointer: 检查点存储（SqliteSaver 或测试用 InMemorySaver）。

    Returns:
        CompiledStateGraph: 可 invoke / resume 的编译图。

    Note:
        - 节点注册名与路由函数返回值必须逐字一致（开发实时文件 §2.2）；
        - 条件边第三参数列出全部可能去向，LangGraph 会静态校验；
        - clarfy → parse_input 回边：用户回答后必须重新解析槽位、重算 missing_slots。
    """
    builder = StateGraph(AgentState)

    # 1) 注册 10 个节点（名字即路由函数返回值）
    builder.add_node("parse_input", parse_input)
    builder.add_node("clarify", clarify)
    builder.add_node("fetch_and_filter", fetch_and_filter)
    builder.add_node("coarse_filter", coarse_filter)
    builder.add_node("compute_commute", compute_commute)
    builder.add_node("evaluate_candidates", evaluate_candidates)
    builder.add_node("backtrack", backtrack)
    builder.add_node("negotiate", negotiate)
    builder.add_node("generate_report", generate_report)
    builder.add_node("validate_output", validate_output)

    # 2) 普通边
    builder.add_edge(START, "parse_input")
    builder.add_edge("clarify", "parse_input")          # 追问后回到槽位解析
    builder.add_edge("compute_commute", "evaluate_candidates")
    builder.add_edge("generate_report", "validate_output")
    builder.add_edge("negotiate", "validate_output")     # 协商只出方案文本，校验后出口

    # 3) 条件边（路由函数均为纯函数）
    builder.add_conditional_edges(
        "parse_input", route_after_parse, ["clarify", "fetch_and_filter"])
    builder.add_conditional_edges(
        "fetch_and_filter", route_after_filter, ["backtrack", "coarse_filter", END])
    builder.add_conditional_edges(
        "coarse_filter", route_after_coarse, ["compute_commute", "backtrack"])
    builder.add_conditional_edges(
        "evaluate_candidates", route_after_evaluate, ["backtrack", "generate_report"])
    builder.add_conditional_edges(
        "backtrack", route_after_backtrack, ["fetch_and_filter", "negotiate"])
    builder.add_conditional_edges(
        "validate_output", route_after_validate, ["generate_report", END])

    return builder.compile(checkpointer=checkpointer)


def get_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """编译并缓存单例图 —— 应用启动时在 lifespan 中调用一次。

    Args:
        checkpointer: 可选的检查点存储；测试注入 InMemorySaver 时使用。
                      传 None 时用 settings.checkpoint_db 的 SqliteSaver 单例。

    Returns:
        CompiledStateGraph: 编译后的 LangGraph 图实例，可直接 invoke。

    Note:
        - 使用 StateGraph(AgentState) 注册所有节点和边；
        - 注入 SqliteSaver checkpointer（独立文件 settings.checkpoint_db）；
        - 图实例缓存为模块级单例，避免重复编译；
        - 显式传入 checkpointer 时不写缓存，避免测试内存库被生产单例污染；
        - thread_id 在 invoke 时通过 config={"configurable": {"thread_id": ...}} 传入。

    Example:
        >>> # 生产：main.py lifespan 中预热
        >>> graph = get_graph()
        >>> result = graph.invoke(state, config={"configurable": {"thread_id": "t_abc123"}})
        >>> # 测试：注入内存 checkpointer
        >>> graph = get_graph(checkpointer=InMemorySaver())
    """
    global _graph

    if checkpointer is not None:
        return _build_graph(checkpointer)

    if _graph is None:
        _graph = _build_graph(_make_sqlite_saver())
    return _graph
