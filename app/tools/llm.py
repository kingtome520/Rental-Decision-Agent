"""LLM 统一封装 —— llm_call / load_prompt（手册模块 4.3 / §5.6 / §5.8）。

约定：
- httpx 直调 DeepSeek 兼容接口（不引 langchain-openai，token 统计自掌控）；
- schema 非空 → response_format=json_object + Pydantic 校验，失败重试 1 次，
  仍失败抛 LLMJsonError，由调用点走规则兜底（如 L1 正则抽取）；
- 进程内累计 LLM_CALL_COUNT / LLM_TOKEN_COUNT，供 §4 成本约束核对；
- MOCK_LLM=1 → 委托 tools.mock；
- load_prompt 用正则只替换 {var} 占位符（Prompt 里含 JSON 字面花括号，禁 str.format）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.config import settings

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

llm_call_count = 0
llm_token_count = 0

_prompt_cache: dict[str, tuple[str, str]] = {}  # name -> (version, text)


class LLMJsonError(RuntimeError):
    """JSON 输出校验重试后仍失败。"""


def load_prompt(name: str, **vars_) -> tuple[str, str]:
    """读 app/prompts/{name}.md，返回 (version, 填充后文本)。

    头部 `<!-- version: vX -->` 解析为版本号，随 trace 落库（§5.8）。
    """
    if name not in _prompt_cache:
        raw = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
        m = re.match(r"<!--\s*version:\s*(\S+)\s*\|", raw)
        _prompt_cache[name] = (m.group(1) if m else "unknown", raw)
    version, text = _prompt_cache[name]
    for k, v in vars_.items():
        text = text.replace("{" + k + "}", str(v))
    return version, text


def llm_call(prompt_text: str, schema: type[BaseModel] | None = None) -> tuple[str | dict, dict]:
    """调用 LLM。返回 (输出, stats{calls, tokens, prompt_version?})。

    stats 由调用节点并入 trace。
    """
    global llm_call_count, llm_token_count
    if settings.mock_llm:
        from app.tools import mock
        return mock.mock_llm_call(prompt_text, schema)

    last_err: Exception | None = None
    for attempt in range(settings.llm_max_retries + 1):
        # TODO(M1): httpx POST {LLM_BASE_URL}/chat/completions
        #   json={"model": settings.llm_model,
        #         "messages": [{"role": "user", "content": prompt_text}],
        #         "response_format": {"type": "json_object"} if schema else None}
        #   header: Authorization: Bearer {LLM_API_KEY}；timeout=settings.llm_timeout_s
        #   usage.total_tokens 累加进 llm_token_count；llm_call_count += 1
        #   schema 路径：剥 ```json 围栏 → json.loads → schema.model_validate，
        #   ValidationError 时把报错拼进追问重试一次（attempt+1）
        raise NotImplementedError("M1: 封装 DeepSeek 调用 + JSON 重试（手册模块 4.3）")
    raise LLMJsonError(str(last_err))


def regex_fallback_parse(user_text: str) -> dict:
    """L1 规则兜底（§5.6）：正则抽预算数字/通勤分钟，地址当剩余文本。"""
    profile: dict = {}
    m = re.search(r"(?:预算|不超过|最多)\D*(\d{3,5})", user_text)
    if m:
        profile["budget_max"] = int(m.group(1))
    m = re.search(r"(\d{2,3})\s*(?:分钟)?(?:内|以内|通勤)", user_text)
    if m:
        profile["commute_limit_min"] = int(m.group(1))
    return profile
