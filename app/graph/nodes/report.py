"""报告节点：L4 批量生成理由 + 风险提示 + L5 摘要，拼 markdown 报告。

对应 FR-05 / 手册模块 5.2。
规则：
- L4 **一次调用**为 Top K（≤5）生成 {listing_id: [理由…, 风险]}，禁止逐套调用（成本控制）；
- 理由中的数值必须来自输入字段；风险由规则触发（低楼层→采光；朝北→阴冷；
  价格 < 池中位数 60% → 实地核验；source=estimate → 标注估算）；
- defaults_used 非空 → 报告顶部标注"以下按默认处理：…"（FR-01）；
- L5 摘要 ≤60 字，失败可省略；
- 输出 final_recommendations + report_text，交 validate 节点校验。
"""
from __future__ import annotations

from app.graph.state import AgentState


def generate_report(state: AgentState) -> dict:
    # TODO(M1 直筒子先做拼接版; M4 接 L4/L5)
    raise NotImplementedError("见 docs/后端开发手册.md 模块 5.2")
