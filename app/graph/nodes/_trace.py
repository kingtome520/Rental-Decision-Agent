"""节点公共工具 —— trace 记录。

设计 §7 代码规范：每个节点在 trace 追加一条
{node, ts, in_summary, out_summary, llm_calls, tokens, tool_calls}。
注意（手册 §11 预警 2）：interrupt 恢复时节点从头重放，
trace 走 state reducer append + DB 落库放在节点出口，保证幂等。
"""
from __future__ import annotations

from app.db import utcnow_iso


def trace_entry(node: str, in_summary: str, out_summary: str,
                llm_calls: int = 0, tokens: int = 0, tool_calls: list[dict] | None = None) -> dict:
    import json
    return {
        "node": node,
        "ts": utcnow_iso(),
        "in_summary": in_summary,
        "out_summary": out_summary,
        "llm_calls": llm_calls,
        "tokens": tokens,
        "tool_calls": json.dumps(tool_calls or [], ensure_ascii=False),
    }
