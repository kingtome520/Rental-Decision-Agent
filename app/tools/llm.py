"""LLM 统一封装 —— llm_call / load_prompt（手册模块 4.3 / §5.6 / §5.8）。

职责：
    1. 封装 DeepSeek 兼容接口调用（httpx 直调，不引 langchain-openai）；
    2. 管理 Prompt 模板加载与变量替换；
    3. JSON 输出校验与重试逻辑；
    4. 进程内累计 LLM 调用次数与 token 消耗（成本监控）。

技术要点：
    - httpx 直调 DeepSeek 兼容接口（OpenAI 格式），token 统计自掌控；
    - schema 非空 → response_format=json_object + Pydantic 校验，失败重试 1 次；
    - 仍失败抛 LLMJsonError，由调用点走规则兜底（如 L1 正则抽取）；
    - 进程内累计 llm_call_count / llm_token_count，供 §4 成本约束核对；
    - MOCK_LLM=1 → 委托 tools.mock；
    - load_prompt 用正则只替换 {var} 占位符（Prompt 里含 JSON 字面花括号，禁 str.format）。

使用场景：
    - 节点调用：version, prompt = load_prompt("parse_input", user_text=...)
    - LLM 调用：result, stats = llm_call(prompt, schema=SlotsSchema)
    - Mock 模式：settings.mock_llm=True 时自动走 mock 固定返回

开发状态：
    - M1: 实现 httpx 真实调用（需 LLM_API_KEY）
    - 当前：Mock 模式可用（MOCK_LLM=1）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ValidationError

from app.config import settings

# Prompt 模板目录（app/prompts/*.md）
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

# 进程内 LLM 调用计数器（用于成本监控，§4 约束）
llm_call_count = 0
# 进程内 LLM token 消耗计数器（用于成本监控，§4 约束）
llm_token_count = 0

# Prompt 模板缓存（name -> (version, text)），避免重复读文件
_prompt_cache: dict[str, tuple[str, str]] = {}


class LLMJsonError(RuntimeError):
    """LLM JSON 输出校验失败异常 —— 重试后仍无法通过 Pydantic 校验时抛出。

    Attributes:
        message: 错误描述（包含校验失败详情）。

    Note:
        调用点应捕获此异常并走规则兜底（如 L1 正则抽取）。
    """


def load_prompt(name: str, **vars_) -> tuple[str, str]:
    """加载 Prompt 模板并替换变量。

    Args:
        name: Prompt 文件名（不含 .md 后缀），如 'parse_input', 'clarify'。
        **vars_: 模板变量字典，用于替换 {var} 占位符。

    Returns:
        tuple[str, str]: (版本号, 填充后文本)。
            - 版本号从 Prompt 头部 <!-- version: vX --> 解析，随 trace 落库（§5.8）；
            - 填充后文本为替换变量后的完整 Prompt。

    Note:
        - 使用正则替换 {var}（而非 str.format），因为 Prompt 里含 JSON 字面花括号；
        - 首次加载后缓存到 _prompt_cache，后续调用直接复用；
        - 版本号解析失败时默认为 'unknown'。

    Example:
        >>> version, prompt = load_prompt('parse_input', user_text='预算3000，公司在西二旗')
        >>> print(version, prompt[:50])
        'v1' '[[TASK:parse_input]]\n\n你是租房需求解析器...'
    """
    if name not in _prompt_cache:
        raw = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
        # 解析头部版本号：<!-- version: vX | ... -->
        m = re.match(r"<!--\s*version:\s*(\S+)\s*\|", raw)
        _prompt_cache[name] = (m.group(1) if m else "unknown", raw)
    version, text = _prompt_cache[name]
    # 替换 {var} 占位符（不用 str.format，避免 JSON 花括号冲突）
    for k, v in vars_.items():
        text = text.replace("{" + k + "}", str(v))
    return version, text


def llm_call(prompt_text: str, schema: type[BaseModel] | None = None) -> tuple[str | dict, dict]:
    """调用 LLM（DeepSeek 兼容接口）。

    Args:
        prompt_text: 完整 Prompt 文本（已填充变量）。
        schema: Pydantic 模型类（可选），非空时启用 JSON mode 并校验输出。

    Returns:
        tuple[str | dict, dict]: (LLM 输出, 统计信息)。
            - 输出：schema 非空时为 dict（校验后的 JSON），否则为 str（纯文本）；
            - 统计：{calls: int, tokens: int, prompt_version: str}，由调用节点并入 trace。

    Raises:
        LLMJsonError: JSON 校验失败且重试用尽时抛出。

    Note:
        - MOCK_LLM=1 时委托 tools.mock.mock_llm_call（固定返回，零成本）；
        - schema 非空时启用 response_format=json_object，并用 Pydantic 校验；
        - 校验失败重试 1 次（settings.llm_max_retries），仍失败抛 LLMJsonError；
        - 每次调用累加 llm_call_count / llm_token_count（进程内计数器）。

    Example:
        >>> # Mock 模式
        >>> result, stats = llm_call(prompt, schema=SlotsSchema)
        >>> print(result['budget_max'], stats['calls'])
        3000 1
    """
    global llm_call_count, llm_token_count
    # Mock 模式：委托 tools.mock
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
    """L1 规则兜底（§5.6）—— 正则抽取预算数字/通勤分钟，地址当剩余文本。

    Args:
        user_text: 用户输入原文。

    Returns:
        dict: 抽取结果，可能含 budget_max（int）、commute_limit_min（int）。

    Note:
        - 当 LLM 返回非法 JSON 且重试失败时，调用点用此函数兜底；
        - 正则匹配规则：
          * 预算：匹配 "预算/不超过/最多" 后的 3-5 位数字；
          * 通勤：匹配 "XX分钟/XX内/XX以内/XX通勤" 中的 2-3 位数字；
        - 未匹配到的字段不写入字典（由调用点判断缺失）。

    Example:
        >>> profile = regex_fallback_parse('预算3000，通勤45分钟内')
        >>> print(profile)
        {'budget_max': 3000, 'commute_limit_min': 45}
    """
    profile: dict = {}
    # 正则抽取预算（3-5 位数字）
    m = re.search(r"(?:预算|不超过|最多)\D*(\d{3,5})", user_text)
    if m:
        profile["budget_max"] = int(m.group(1))
    # 正则抽取通勤分钟（2-3 位数字）
    m = re.search(r"(\d{2,3})\s*(?:分钟)?(?:内|以内|通勤)", user_text)
    if m:
        profile["commute_limit_min"] = int(m.group(1))
    return profile
