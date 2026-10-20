"""单次 LLM 基线 —— 一条 Prompt 塞 200 条房源 + 用户输入，直出 Top5（手册模块 8 / FR-07）。

作用：与 Agent 版同口径对比，证明"澄清/筛选/精算/回溯"的决策价值。
解析失败按空推荐计（硬约束合规率惩罚进指标，不给基线放水）。
不做多模型对比（v0.2 砍掉）。
"""
from __future__ import annotations

BASELINE_PROMPT = """你是租房推荐器。从以下房源列表中为用户推荐 Top5。
用户输入：{user_text}
房源列表（JSON）：{listings_json}
只输出 JSON：{{"top5": ["listing_id", ...]}}
"""


def run_baseline(user_text: str, listings: list[dict]) -> list[dict]:
    """返回推荐房源 dict 列表（与 Agent final_recommendations 同构）。"""
    # TODO(M5): llm_call(BASELINE_PROMPT.format(...), schema=Top5Schema)
    #   → 按 ID 回查 listings 补全字段；解析失败返回 []
    raise NotImplementedError("M5 里程碑实现（tools/llm.py 就绪后即可写）")
