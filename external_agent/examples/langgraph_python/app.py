import logging
import uuid
import time
import asyncio
import json
from typing import Optional, Dict, Any

from fastapi import FastAPI, Header, Depends, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    MessageResponse,
    DEFAULT_MODEL,
)
from security import get_current_user
from tools import web_search_duckduckgo, news_search_duckduckgo
from llm_utils import get_llm_stream

# ─── Logger setup ───────────────────────────────────────────────────────────────
logger = logging.getLogger("external-agent")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
)
logger.addHandler(handler)

# ─── App init ───────────────────────────────────────────────────────────────────
app = FastAPI()

# ─── Test SSE endpoint ──────────────────────────────────────────────────────────
@app.post("/chat/completions-test")
async def completions_test(_req: Request):
    """
    Quick endpoint to verify SSE is working.
    """
    async def publisher():
        yield 'data: {"choices":[{"delta":{"content":"👋 test"}}]}\n\n'
        await asyncio.sleep(0.5)
        yield 'data: {"choices":[{"delta":{"content":" success"}}]}\n\n'
    return EventSourceResponse(publisher())

# ─── Main chat/completions ──────────────────────────────────────────────────────
@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    X_IBM_THREAD_ID: Optional[str] = Header(
        None, alias="X-IBM-THREAD-ID", description="Optional thread ID"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    logger.info(f"Received request: {request.json()}")
    # determine thread_id
    thread_id = X_IBM_THREAD_ID or (request.extra_body.thread_id if request.extra_body else "")
    logger.info(f"Using thread_id: {thread_id}")

    model = request.model or DEFAULT_MODEL
    selected_tools = [web_search_duckduckgo, news_search_duckduckgo]

    # ALWAYS stream as SSE
    async def sse_publisher():
        async for token in get_llm_stream(request.messages, model, thread_id, selected_tools):
            logger.debug(f"Yielding chunk: {token!r}")
            payload = {"choices":[{"delta":{"content":token}}]}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(sse_publisher(), media_type="text/event-stream")

# ─── Uvicorn launcher ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
