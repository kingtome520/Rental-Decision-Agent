# 毕业生租房决策 Agent（Rental Decision Agent）

> 输入预算、通勤目的地与偏好，Agent 多轮澄清缺失信息 → 筛选模拟房源 → 高德 API 精算通勤 → 无解时回溯/协商 → 输出 3–5 套候选 + 理由 + 风险提示。
> 核心卖点：**有状态决策图** —— 澄清 interrupt、两阶段通勤、双层回溯与协商续跑、ID 白名单防幻觉。

## 文档索引

| 文档 | 说明 |
|---|---|
| [设计.md](./设计.md) | PRD v0.2：需求 + 架构 + 数据设计 + 里程碑 |
| [docs/后端开发手册.md](./docs/后端开发手册.md) | 按模块的实现分解（功能/技术/依赖包/验收） |
| [docs/decisions.md](./docs/decisions.md) | ADR 决策记录（≥5 条） |
| [eval/README.md](./eval/README.md) | 评估画像标注规范 |

## 技术栈

Python 3.12 · FastAPI · LangGraph（StateGraph + interrupt + SqliteSaver） · DeepSeek · 高德 Web 服务 API · SQLAlchemy Core（SQLite 默认 / MySQL 可选）

## 快速开始

```powershell
# 1. 环境（必须 Python 3.12）
python3.12 -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置
Copy-Item .env.example .env   # 填入 AMAP_KEY / LLM_API_KEY

# 3. 生成模拟房源数据（200 条）
python scripts/generate_listings.py

# 4. 启动服务
uvicorn app.main:app --reload --port 8000

# 5. 演示（三段式）
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{\"text\": \"预算3000，公司在西二旗软件园，通勤45分钟内\"}'
curl -X POST http://localhost:8000/chat/{thread_id} -H "Content-Type: application/json" -d '{\"text\": \"公交\"}'
curl http://localhost:8000/trace/{thread_id}
```

或直接打开 `static/demo.html`（30 行极简前端）。

## 离线 / 零成本模式

`.env` 中设 `MOCK_LLM=1 MOCK_MAP=1`，无需任何 Key 即可跑通全流程与测试。

## 目录结构

见设计文档 §7；开发顺序见《后端开发手册》§11。

## 状态

- [ ] M1 骨架 + 单轮直筒子
- [ ] M2 LangGraph 状态图 + 澄清 interrupt
- [ ] M3 回溯 + 协商续跑
- [ ] M4 防幻觉 + 观测
- [ ] M5 评估 + 基线对比
- [ ] M6 打磨（README / 录屏 / ADR）
