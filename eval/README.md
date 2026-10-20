# 评估标注规范（eval/README.md）

对应设计文档 §6.2。**标准冻结前只标 10 组；冻结后改标准必须全部重标。**

## 标注口径

- `expected_listing_ids` = 满足全部硬约束（预算 / room_type 前缀 / max_walk）**且通勤 ≤ 上限** 的房源，
  按综合分升序取 **前 5**：

  ```
  score = 价格分位 × 0.4 + 通勤分位 × 0.4 + 地铁步行分位 × 0.2
  ```

- `acceptable_alternatives` = 同一排序下的 **6–10 名**（命中率公式的"可接受范围"，避免"全合规但不重合"的伪失败）。
- 通勤真值：`commute_cache` 中的 `source=api` 记录；缓存缺失时用 Haversine 估算值标注（在 notes 注明 `estimate-labeled`）。

## 流程（半自动）

1. `python scripts/annotate_profiles.py` → 脚本按口径生成两个 ID 列表草稿；
2. 人工"剔不合理 + 补漏"（重点检查：商住公寓、明显数据噪声、同小区重复度过高）；
3. 迭代两版后 **冻结**：给 `profiles.json` 打 git tag，之后指标对比才有意义；
4. 冻结后扩到 20 组（新增画像覆盖更多边界：极端预算、多约束叠加）。

## 指标公式口径

见 `metrics.py`（FR-07 v0.2 修正版）：主指标为 **硬约束合规率**；候选命中率含 acceptable_alternatives；白名单通过率目标 100%。

## 失败案例记录

每轮跑批后在 `results/analysis.md` 记录 ≥2 条失败案例：现象 → trace 定位 → 根因（槽位漏解析 / 粗筛半径不足 / LLM 理由数值幻觉等）→ 改进项。
