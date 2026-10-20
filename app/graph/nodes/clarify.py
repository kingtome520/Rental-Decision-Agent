"""澄清节点（interrupt）：一次只问一个缺失槽位。

对应 FR-01 / 设计 §5.7 / 手册模块 5.2。
关键：interrupt() 恢复时本节点从头重放——interrupt 之前只允许纯计算（L2 生成问句可重放，
但会重复消耗一次 LLM 调用，M2 决策：接受重放成本 or 用 asked_slots 幂等短路）。
每个必填槽位最多问 1 次；仍无有效回答 → config 默认值 + defaults_used 标记。
"""
from __future__ import annotations

from app.graph.state import AgentState


def clarify(state: AgentState) -> dict:
    # TODO(M2):
    # from langgraph.types import interrupt
    # question = state["clarify_question"]
    # user_answer = interrupt({"type": "clarify", "question": question,
    #                          "missing_slot": state["missing_slots"][0]})
    # return {"messages": [HumanMessage(content=user_answer)],
    #         "asked_slots": state["asked_slots"] + [state["missing_slots"][0]], ...}
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
