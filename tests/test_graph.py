"""端到端 + 脏输入 + interrupt 恢复测试（手册模块 9 / 设计 §9.1）。

特别要求：clarify 抛出后带同 thread_id Command(resume=...) 能续跑。
全部依赖 M2 图实现，先以 skip 占位保证 CI 语义清晰。
"""
from __future__ import annotations

import pytest


@pytest.fixture
def graph(mini_pool):
    """编译测试图（独立内存 SQLite checkpointer）。"""
    # TODO(M2): from app.graph.build import get_graph; yield get_graph(checkpointer=InMemorySaver())
    pytest.skip("M2 里程碑后启用")


def test_clean_input_full_report(graph):
    """干净输入端到端出报告，含 ID / commute_min / 理由（成功标准 §1.4-1）。"""
    pytest.skip("M2")


def test_clarify_interrupt_and_resume(graph):
    """缺 commute_mode：第一次 invoke 返回 interrupt → resume("公交") 续跑出报告，
    且同一槽位不出现第二次澄清（FR-01 验收）。"""
    pytest.skip("M2")


def test_negotiate_resume(graph):
    """极端画像 2 次回溯后进入 negotiate；用户选方案后回到 fetch_and_filter 续跑（FR-04 验收）。"""
    pytest.skip("M3")


def test_dirty_inputs_no_crash(graph):
    """eval/dirty_inputs.json 5 条逐一执行，期望行为匹配 expect 字段（FR-08）。"""
    pytest.skip("M3")


def test_fake_id_blocked_in_trace(graph):
    """假 ID 注入 → 拦截且 trace 可见 validation_failures（M4 验收）。"""
    pytest.skip("M4")
