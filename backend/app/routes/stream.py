"""
SSE endpoint — students subscribe here to receive live events.
"""

import logging

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.broadcaster import broadcaster, sse_event_generator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stream")
async def stream(request: Request):
    """
    Server-Sent Events endpoint. Each connection gets its own queue.
    The frontend uses the native EventSource API to consume this.
    """
    queue = await broadcaster.subscribe()

    async def event_stream():
        try:
            async for event in sse_event_generator(queue):
                if await request.is_disconnected():
                    break
                yield event
        finally:
            await broadcaster.unsubscribe(queue)

    return EventSourceResponse(event_stream())
