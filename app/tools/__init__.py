"""工具层 —— Agent 的“手”，封装所有外部调用。

设计原则（手册 §7 代码规范）：
    1. 所有外部调用（地图 API / LLM API / 数据查询）必须经此层；
    2. 节点内不直接发 HTTP 请求，只调用工具函数；
    3. 工具函数统一风格：纯函数、异常就地转降级值、不向上抛裸异常。

工具列表：
    - listings.py: 房源检索（search_listings，本地 JSON 查询）
    - map.py: 地图工具（geocode, commute_time, haversine, 缓存管理）
    - llm.py: LLM 统一封装（llm_call, load_prompt, 重试逻辑）
    - mock.py: Mock 实现（离线开发，零网络，固定返回）

Mock 注入（§7）：
    - MOCK_LLM=1 → llm_call 委托 mock.mock_llm_call
    - MOCK_MAP=1 → geocode/commute_time 委托 mock.mock_geocode/mock_commute_time
    - MAP_FAIL_RATE>0 → 模拟地图超时，验证降级路径

开发顺序（手册 §11）：
    M1: tools/listings → tools/map(+mock) → tools/llm → prompts
"""
