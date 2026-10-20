"""L1 节点：最新用户消息 → 槽位 JSON → 合并 user_profile → 重算 missing_slots。

对应 FR-01 / 手册模块 5.2 表第 1 行。
规则：
- 必填优先级 budget_max > dest_address > commute_limit_min > commute_mode；
- LLM 输出非法 JSON → 正则兜底抽预算数字/地址，其余槽位当缺失；
- 已回答过的槽位不重复解析覆盖为 null（last非空 wins）。
"""
from __future__ import annotations

from app.graph.state import AgentState


def parse_input(state: AgentState) -> dict:
    # TODO(M2): llm_call(load_prompt("parse_input", user_text=...), schema=SlotsSchema)
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
