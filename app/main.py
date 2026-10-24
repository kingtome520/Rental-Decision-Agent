"""FastAPI 入口 —— 提供 /chat /chat/{thread_id} /trace/{thread_id} /health 四个端点。

对应《后端开发手册》模块 7 / 设计文档 §5.7 FastAPI 层协议。

职责：
    1. 定义 HTTP 接口协议（请求/响应模型）；
    2. 管理应用生命周期（lifespan 中初始化数据库和检查点）；
    3. 调用 LangGraph 图执行决策流程；
    4. 整形图执行结果为统一响应格式。

技术要点：
    - 图节点为同步阻塞（httpx），endpoint 用 def，FastAPI 自动丢线程池执行；
    - interrupt 值从 result["__interrupt__"] 取，统一整形为 ChatResponse；
    - 续跑用 Command(resume=text)，checkpointer 按 thread_id 恢复；
    - CORS 打开给 static/demo.html 用。

使用场景：
    - 启动服务：uvicorn app.main:app --reload --port 8000
    - 前端调用：POST /chat 发起新会话，POST /chat/{thread_id} 续跑
    - 调试观测：GET /trace/{thread_id} 查看完整决策链路
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import app.db as db


@asynccontextmanager
async def lifespan(application: FastAPI):
    """应用生命周期管理器 —— 启动时初始化数据库和检查点。

    Args:
        application: FastAPI 应用实例（未使用，但 lifespan 签名要求）。

    Yields:
        None: 应用运行期间。

    Note:
        - db.init_db() 幂等建表（业务表）；
        - TODO(M2): 初始化 SqliteSaver 并注入 graph.build（见手册模块 7）；
        - lifespan 是 FastAPI 推荐的资源管理方式，替代 on_event("startup")。
    """
    db.init_db()
    # TODO(M2): 初始化 SqliteSaver 并注入 graph.build（见手册模块 7）
    yield


# FastAPI 应用实例 —— 配置标题和生命周期管理器
app = FastAPI(title="Rental Decision Agent", lifespan=lifespan)
# CORS 中间件 —— 允许所有来源、方法、头部（开发阶段宽松，生产环境应收紧）
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    """聊天请求模型 —— POST /chat 和 /chat/{thread_id} 共用。

    Attributes:
        text: 用户输入的文本（自然语言）。
    """
    text: str


class ChatResponse(BaseModel):
    """聊天响应模型 —— 统一返回格式。

    Attributes:
        thread_id: 会话 ID，用于后续续跑。
        type: 响应类型，取值：
              - 'clarify': 澄清问句（待用户回答缺失槽位）
              - 'negotiate': 协商方案（待用户选择放宽方案）
              - 'report': 最终推荐报告（决策完成）
              - 'failed': 失败提示（如地理编码失败）
        content: 响应内容（根据 type 不同，可能是问句、方案列表、markdown 报告）。
    """
    thread_id: str
    type: str        # clarify | negotiate | report | failed
    content: str


def _format_result(thread_id: str, graph_result: dict) -> ChatResponse:
    """把图执行结果整形为协议响应（手册模块 7）。

    Args:
        thread_id: 会话 ID。
        graph_result: LangGraph 图执行结果字典，可能包含：
                      - __interrupt__: 中断值（待用户回答）
                      - status: 'done'（报告完成）或 'failed'（失败）
                      - report_text: markdown 报告文本（status=done 时）

    Returns:
        ChatResponse: 统一响应格式，type 根据结果自动判断。

    Raises:
        NotImplementedError: M2 待实现 interrupt 提取与 markdown 报告渲染。

    Note:
        三种出口：
        1. __interrupt__ 存在 → type='clarify' 或 'negotiate'，content 为问句/方案；
        2. status='done' → type='report'，content 为 markdown 报告；
        3. status='failed' → type='failed'，content 为失败原因。
    """
    # TODO(M2): 实现 interrupt 提取与 markdown 报告渲染
    raise NotImplementedError("依赖 M2 图实现（见 docs/后端开发手册.md 模块 5/7）")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """新会话：生成 thread_id，invoke 图。

    Args:
        req: 聊天请求，包含用户输入文本。

    Returns:
        ChatResponse: 统一响应（首次可能是澄清问句或直接出报告）。

    Raises:
        HTTPException(501): M2 待实现 LangGraph 图接入。

    Example:
        >>> curl -X POST http://localhost:8000/chat \
        ...   -H "Content-Type: application/json" \
        ...   -d '{"text": "预算3000，公司在西二旗软件园，通勤45分钟内"}'
    """
    # 生成唯一会话 ID（格式：t_ + 12位十六进制）
    thread_id = f"t_{uuid.uuid4().hex[:12]}"
    # TODO(M2): graph = build.get_graph(); result = graph.invoke({...}, config={"configurable": {"thread_id": thread_id}})
    raise HTTPException(501, detail="M2 待实现：LangGraph 图尚未接入")


@app.post("/chat/{thread_id}", response_model=ChatResponse)
def chat_resume(thread_id: str, req: ChatRequest):
    """续跑：回答澄清 / 选择协商方案。

    Args:
        thread_id: 会话 ID（从首次 /chat 返回）。
        req: 聊天请求，包含用户回答或选择。

    Returns:
        ChatResponse: 统一响应（可能是下一轮澄清、协商方案、或最终报告）。

    Raises:
        HTTPException(501): M2 待实现 interrupt 续跑接入。

    Example:
        >>> curl -X POST http://localhost:8000/chat/t_abc123 \
        ...   -H "Content-Type: application/json" \
        ...   -d '{"text": "公交"}'
    """
    # TODO(M2): Command(resume=req.text)
    raise HTTPException(501, detail="M2 待实现：interrupt 续跑尚未接入")


@app.get("/trace/{thread_id}")
def get_trace(thread_id: str):
    """观测：返回该会话的完整追踪记录（节点执行链路）。

    Args:
        thread_id: 会话 ID。

    Returns:
        dict: 包含 thread_id 和 steps（追踪记录列表）。

    Raises:
        HTTPException(404): 该 thread_id 无追踪记录。

    Example:
        >>> curl http://localhost:8000/trace/t_abc123
        >>> # 返回：{"thread_id": "t_abc123", "steps": [...]}
    """
    rows = db.get_traces(thread_id)
    if not rows:
        raise HTTPException(404, detail="thread 无 trace 记录")
    return {"thread_id": thread_id, "steps": rows}


@app.get("/health")
def health():
    """健康检查：验证数据库连通性。

    Returns:
        dict: {"status": "ok"} 表示服务正常。

    Note:
        - 通过查询 trace 表验证数据库可访问；
        - 用于负载均衡器、监控系统探活；
        - 若数据库不可达，会抛出异常（FastAPI 自动返回 500）。

    Example:
        >>> curl http://localhost:8000/health
        >>> # 返回：{"status": "ok"}
    """
    # 简单查询验证数据库可访问
    with db.get_engine().connect() as conn:
        conn.execute(db.select(db.trace.c.id).limit(1))
    return {"status": "ok"}
