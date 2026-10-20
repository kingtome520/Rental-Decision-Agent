"""评估指标公式 —— FR-07 v0.2 修正版（手册模块 8）。

纯函数：输入推荐结果 + 标注，输出指标 dict。run_eval 与单测复用。
"""
from __future__ import annotations


def hit_rate(recommended_ids: list[str], expected_ids: list[str],
             acceptable_ids: list[str]) -> float:
    """候选命中率 = |推荐 ∩ (标注 ∪ acceptable)| / |标注|。"""
    if not expected_ids:
        return 0.0
    allowed = set(expected_ids) | set(acceptable_ids)
    return len(set(recommended_ids) & allowed) / len(expected_ids)


def hard_constraint_compliance(recommendations: list[dict], constraints: dict) -> float:
    """硬约束合规率（主指标）= 满足全部硬约束的条数 / 推荐总数。

    recommendations 每条含 price_monthly / room_type / walk_to_subway_min。
    """
    if not recommendations:
        return 0.0
    ok = 0
    for r in recommendations:
        if r["price_monthly"] > constraints["budget_max"]:
            continue
        room = constraints.get("room_type", "不限")
        if room != "不限" and not r["room_type"].startswith(room):
            continue
        max_walk = constraints.get("max_walk_to_subway_min")
        if max_walk is not None and r.get("walk_to_subway_min", 0) > max_walk:
            continue
        ok += 1
    return ok / len(recommendations)


def commute_accuracy(recommendations: list[dict], ground_truth: dict, tolerance_min: float = 10) -> float:
    """通勤准确率 = 与 API 真值误差 ≤10min 的条目占比。ground_truth: listing_id -> minutes。"""
    checked = [r for r in recommendations if r["listing_id"] in ground_truth]
    if not checked:
        return 0.0
    ok = sum(abs(r["commute_min"] - ground_truth[r["listing_id"]]) <= tolerance_min for r in checked)
    return ok / len(checked)


def whitelist_pass_rate(recommendations: list[dict], validation_failure_ids: set[str]) -> float:
    """白名单通过率 = 通过 FR-06 校验的推荐数 / 总推荐数（目标 100%）。"""
    if not recommendations:
        return 0.0
    return 1 - len(validation_failure_ids & {r["listing_id"] for r in recommendations}) / len(recommendations)


def clarify_effectiveness(clarifications: list[dict]) -> float:
    """澄清有效率 = 人工判定'影响筛选结果'的澄清数 / 总澄清数。
    clarifications: [{slot, affected_result: bool}]（人工标注位）。"""
    if not clarifications:
        return 0.0
    return sum(1 for c in clarifications if c.get("affected_result")) / len(clarifications)


def summarize(profile_results: list[dict]) -> dict:
    """汇总多画像指标均值 + 平均 LLM 调用次数。

    profile_results 每条：{hit, compliance, commute_acc, whitelist, clarify_eff, llm_calls}
    """
    n = len(profile_results)
    if n == 0:
        return {}
    keys = ["hit", "compliance", "commute_acc", "whitelist", "clarify_eff"]
    out = {k: sum(r.get(k, 0.0) for r in profile_results) / n for k in keys}
    out["avg_llm_calls"] = sum(r.get("llm_calls", 0) for r in profile_results) / n
    out["n_profiles"] = n
    return out
