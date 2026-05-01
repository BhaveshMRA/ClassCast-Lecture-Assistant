"""
Broadcaster: publishes events to all connected SSE clients.

Each connected client gets its own asyncio.Queue. When `publish()` is called,
the message is dropped into every queue. The SSE endpoint reads from its own
queue and yields events to the browser.

Clean disconnects: when a client drops, its queue is removed via the
`unsubscribe()` call in the SSE generator's finally block.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from app import db

logger = logging.getLogger(__name__)


class Broadcaster:
    """In-memory pub/sub for SSE. One instance per process is enough."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        """Register a new client. Returns the queue they should read from."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.add(queue)
        logger.info(f"client subscribed; total clients = {len(self._subscribers)}")
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a client's queue. Called when the SSE connection drops."""
        async with self._lock:
            self._subscribers.discard(queue)
        logger.info(f"client unsubscribed; total clients = {len(self._subscribers)}")

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Send an event to every connected client.

        event_type: a label the frontend uses to route (e.g. "heartbeat", "summary", "visual")
        data: any JSON-serializable dict
        """
        message = {"type": event_type, "data": data}
        
        # Intercept and persist important events to SQLite
        if event_type in ["summary", "visual", "transcript", "audit"]:
            db.insert_event(event_type, data)
            
        async with self._lock:
            targets = list(self._subscribers)

        delivered = 0
        for queue in targets:
            try:
                queue.put_nowait(message)
                delivered += 1
            except asyncio.QueueFull:
                logger.warning("dropping message to slow client (queue full)")
        logger.debug(f"published {event_type} to {delivered}/{len(targets)} clients")

    @property
    def client_count(self) -> int:
        return len(self._subscribers)


# Single shared instance for the app
broadcaster = Broadcaster()


async def sse_event_generator(queue: asyncio.Queue) -> AsyncIterator[dict]:
    """
    Yields SSE-formatted events from a client's queue.

    The dict shape ({"event": ..., "data": ...}) is what sse-starlette expects.
    """
    try:
        while True:
            message = await queue.get()
            yield {
                "event": message["type"],
                "data": json.dumps(message["data"]),
            }
    except asyncio.CancelledError:
        raise
