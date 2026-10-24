"""LLM 结构化输出契约 —— 字段与 app/prompts/*.md 输出块、tools/mock.py 固定返回严格对齐。

llm_call(prompt, schema=...) 接收这些模型类本身（type[BaseModel]），
用于校验并规整 LLM 的 JSON 输出；下游节点据字段名安全取值。
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel, field_validator


class SlotsSchema(BaseModel):
    """L1：自然语言 → 槽位（prompts/parse_input.md）。缺字段一律 None，parse_input 据此算 missing_slots。"""
    #防止 LLM 多返回一个字段就校验失败（llm.py 里失败会重试 1 次再抛 LLMJsonError，能容错就别浪费重试）
    model_config = ConfigDict(extra="ignore")

    budget_max: int | None = None            # 预算上限（元/月），用于粗筛与比价
    dest_address: str | None = None          # 目的地地址（通勤终点，如公司）
    commute_limit_min: int | None = None     # 可接受的单程通勤时长上限（分钟）
    commute_mode: str | None = None          # 通勤方式：驾车/公交/步行/骑行（中文，与 config.speed_kmh 对齐）
    room_type: str | None = None             # 房型偏好：整租/合租/不限
    max_walk_to_subway_min: int | None = None  # 步行到地铁站的最长时间（分钟）
    orientation_pref: str | None = None      # 朝向偏好（如 朝南/东南）


class NegotiationPlan(BaseModel):
    """单个放宽方案（negotiate.md 的 plans[] 元素；对应 MOCK_NEGOTIATE_JSON 的每条）。"""
    model_config = ConfigDict(extra="ignore")

    plan: str                  # 方案名，一句话，如"预算加 500"
    relax_field: str           # 放宽的字段名：budget_max | commute_limit_min | room_type | max_walk_to_subway_min
    new_value: int | float | str  # 放宽后的新值（数值或字符串；mock 里给的是 int）
    cost_estimate: str         # 预计代价描述，如"通勤 +15 分钟"


class NegotiateSchema(BaseModel):
    """L3 协商：无解时生成的 2–3 个放宽方案集合，供 clarify/negotiate 的 interrupt 展示给用户选。"""
    model_config = ConfigDict(extra="ignore")

    plans: list[NegotiationPlan]  # 2–3 个方案；对应 mock 的 {"plans": [...]}

class ReasonsSchema(RootModel[dict[str, list[str]]]):
    """L4 推荐理由结构：动态 key（listing_id）→ 理由/风险字符串列表。

    来源：prompts/reasons.md
    典型输出：{"BJ-0001": ["理由1", "理由2", "风险1"], ...}
    mock 兼容：{"_mock": ["理由1", "理由2", "风险1"]}

    因为 listing_id 不固定，普通 BaseModel 定义不了固定字段，
    必须用 RootModel 包裹 dict[str, list[str]]。
    """

    @field_validator("root")
    @classmethod
    def _check_entries(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        for listing_id, reasons in v.items():
            if not listing_id or not listing_id.strip():
                raise ValueError("listing_id 不能为空")
            if not isinstance(reasons, list) or not reasons:
                raise ValueError(f"{listing_id!r} 的理由列表不能为空")
            for i, reason in enumerate(reasons):
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError(
                        f"{listing_id!r} 第 {i} 条理由必须是非空字符串"
                    )
        return v


