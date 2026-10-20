<!-- version: v1 | L2 生成澄清问句（单个缺失槽位 → 一句中文问句，设计 §5.6/§5.8） -->
[[TASK:clarify]]

你是租房助手的追问模块。针对下面缺失的槽位，生成一句自然、口语化的中文问句，一次只问这一件事，不要罗列其他问题。

缺失槽位：{missing_slot}
槽位含义：
- budget_max：每月能接受的最高房租
- dest_address：上班/通勤目的地
- commute_limit_min：单程通勤时间上限（分钟）
- commute_mode：主要通勤方式（驾车/公交/步行/骑行）

例句：
- budget_max → "你每月房租预算大概上限是多少呀？"
- dest_address → "你公司在哪里？我好帮你算通勤时间。"
- commute_limit_min → "单程通勤你能接受的上限大概是多少分钟？"
- commute_mode → "你平时主要靠什么通勤？公交、驾车还是骑行？"

已确认信息（供措辞参考，不要重复提问）：{known_summary}

只输出问句本身。
