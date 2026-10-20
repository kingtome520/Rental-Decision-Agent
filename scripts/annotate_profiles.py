"""半自动评估标注 —— 脚本生成 → 人工删改（手册模块 8 / 设计 §6.2）。

标注口径（冻结标准）：
- expected_listing_ids = 满足全部硬约束 且 通勤 ≤ 上限 的房源，
  按 价格分位×0.4 + 通勤分位×0.4 + 地铁距离分位×0.2 综合排序取前 5；
- acceptable_alternatives = 同一排序下的 6–10 名。
先 10 组，标准冻结后扩到 20；冻结后改标准必须全部重标。

用法：python scripts/annotate_profiles.py [--commute-source mock|cache]
"""
from __future__ import annotations


def main() -> None:
    # TODO(M5): 读 eval/profiles.json 的 input/expected_slots →
    #   用 tools（listings + map/mock 通勤）跑筛选排序 → 回填两个 ID 列表
    raise NotImplementedError("M5 里程碑实现（见 docs/后端开发手册.md 模块 8）")


if __name__ == "__main__":
    main()
