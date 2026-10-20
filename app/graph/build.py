"""图装配 —— StateGraph 节点 + 条件边 + checkpointer。

对应设计 §5.2 状态图 / 手册模块 5.3。
边拓扑：
  START → parse_input →(route_slots)→ clarify | fetch_and_filter
  fetch_and_filter →(池空?)→ backtrack | coarse_filter
  coarse_filter →(Top20 空?)→ backtrack | compute_commute
  compute_commute → evaluate_candidates →(合格≥2?)→ generate_report | backtrack
  backtrack →(未超限?)→ fetch_and_filter | negotiate
  negotiate → validate_output            # 协商只出方案文本，白名单校验后出口
  generate_report → validate_output →(通过/重试用尽?)→ END | generate_report(regen≤1)
要点：
- 条件边路由函数是纯函数（state → 节点名/END），可脱离图单测；
- clarify / negotiate 内部使用 interrupt()，恢复由 Command(resume=...) 驱动；
- compile(checkpointer=SqliteSaver)，thread_id 在 invoke config 传入。
"""
from __future__ import annotations

from app.graph.state import AgentState


def route_after_parse(state: AgentState) -> str:
    """缺必填 → clarify；齐全 → fetch_and_filter。纯函数，单测覆盖。"""
    # TODO(M2)
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.3")


def route_after_filter(state: AgentState) -> str:
    ...  # TODO(M2): 池空 → backtrack


def route_after_evaluate(state: AgentState) -> str:
    ...  # TODO(M2): 合格 <2 → backtrack


def route_after_backtrack(state: AgentState) -> str:
    ...  # TODO(M3): 超限 → negotiate


def route_after_validate(state: AgentState) -> str:
    ...  # TODO(M4): 未通过 & regen<1 → generate_report，否则 END


def get_graph():
    """编译并缓存单例图（lifespan 调用一次）。"""
    # TODO(M2):
    # from langgraph.checkpoint.sqlite import SqliteSaver
    # builder = StateGraph(AgentState) ... builder.compile(checkpointer=...)
    raise NotImplementedError("M2 里程碑实现（先跑通单节点 interrupt + SqliteSaver 最小 demo）")
