"""图节点包 —— 10 个决策节点实现。

统一约定：
    所有节点函数签名：def node(state: AgentState) -> dict
    - 输入：当前状态字典（AgentState）
    - 输出：状态增量字典（只返回要更新的字段，不原地修改 state）
    - 每个节点出口追加 trace 记录（通过 nodes/_trace.py 的 trace_entry）

节点列表（按执行顺序）：
    1. parse_input: L1 自然语言 → 槽位 JSON → 合并 user_profile → 重算 missing_slots
    2. clarify: interrupt 暂停问一个缺失槽位（一次只问一个）
    3. fetch_filter: geocode 目的地 + 硬约束过滤房源池
    4. coarse_filter: Haversine 直线距离保留 Top K（默认 20）
    5. commute: 对 Top K 调高德路径规划精算通勤
    6. evaluate: 合格候选过滤 + 综合排序
    7. backtrack: 自动放宽约束（≤ BACKTRACK_MAX 次）
    8. negotiate: interrupt 协商（生成放宽方案，等用户选择）
    9. report: L4 批量生成理由 + 风险提示 + L5 摘要
    10. validate: ID 白名单 + 通勤数值溯源（输出侧防幻觉）

开发状态：
    - M2: parse_input, clarify, fetch_filter, coarse_filter, commute, evaluate, report
    - M3: backtrack, negotiate
    - M4: validate
"""
