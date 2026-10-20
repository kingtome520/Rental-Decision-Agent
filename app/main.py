"""FastAPI 入口 —— /chat /chat/{thread_id} /trace/{thread_id} /health。

对应《后端开发手册》模块 7 / 设计文档 §5.7 FastAPI 层协议。
要点：
- 图节点为同步阻塞（httpx），endpoint 用 def，FastAPI 自动丢线程池执行；
- interrupt 值从 result["__interrupt__"] 取，统一整形为 ChatResponse；
- 续跑用 Command(resume=text)，checkpointer 按 thread_id 恢复；
- checkpointer / 业务表在 lifespan 初始化。
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
    db.init_db()
    # TODO(M2): 初始化 SqliteSaver 并注入 graph.build（见手册模块 7）
    yield


app = FastAPI(title="Rental Decision Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    thread_id: str
    type: str        # clarify | negotiate | report | failed
    content: str


def _format_result(thread_id: str, graph_result: dict) -> ChatResponse:
    """把图执行结果整形为协议响应（手册模块 7）。

    三种出口：__interrupt__（待用户回答）/ status=done（report）/ status=failed。
    """
    # TODO(M2): 实现 interrupt 提取与 markdown 报告渲染
    raise NotImplementedError("依赖 M2 图实现（见 docs/后端开发手册.md 模块 5/7）")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """新会话：生成 thread_id，invoke 图。"""
    thread_id = f"t_{uuid.uuid4().hex[:12]}"
    # TODO(M2): graph = build.get_graph(); result = graph.invoke({...}, config={"configurable": {"thread_id": thread_id}})
    raise HTTPException(501, detail="M2 待实现：LangGraph 图尚未接入")


@app.post("/chat/{thread_id}", response_model=ChatResponse)
def chat_resume(thread_id: str, req: ChatRequest):
    """续跑：回答澄清 / 选择协商方案。"""
    # TODO(M2): Command(resume=req.text)
    raise HTTPException(501, detail="M2 待实现：interrupt 续跑尚未接入")


@app.get("/trace/{thread_id}")
def get_trace(thread_id: str):
    """观测：该会话完整 trace（M4 落 DB 后生效）。"""
    rows = db.get_traces(thread_id)
    if not rows:
        raise HTTPException(404, detail="thread 无 trace 记录")
    return {"thread_id": thread_id, "steps": rows}


@app.get("/health")
def health():
    with db.get_engine().connect() as conn:
        conn.execute(db.select(db.trace.c.id).limit(1))
    return {"status": "ok"}
