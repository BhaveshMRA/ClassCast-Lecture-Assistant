"""Test the broadcaster pub/sub layer end-to-end without a real server."""

import asyncio
import pytest

from app.broadcaster import broadcaster, sse_event_generator


@pytest.mark.asyncio
async def test_fanout_to_multiple_subscribers():
    alice = await broadcaster.subscribe()
    bob = await broadcaster.subscribe()
    assert broadcaster.client_count == 2

    await broadcaster.publish("test", {"msg": "hello"})

    a = await asyncio.wait_for(alice.get(), timeout=1.0)
    b = await asyncio.wait_for(bob.get(), timeout=1.0)
    assert a["type"] == "test" and a["data"] == {"msg": "hello"}
    assert b["type"] == "test" and b["data"] == {"msg": "hello"}


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    alice = await broadcaster.subscribe()
    bob = await broadcaster.subscribe()

    await broadcaster.unsubscribe(alice)
    await broadcaster.publish("test", {"msg": "after-unsub"})

    # Bob still gets it
    b = await asyncio.wait_for(bob.get(), timeout=1.0)
    assert b["data"] == {"msg": "after-unsub"}

    # Alice's queue stays empty
    assert alice.empty()


@pytest.mark.asyncio
async def test_sse_event_format():
    queue = await broadcaster.subscribe()
    await broadcaster.publish("summary", {"text": "hello"})

    gen = sse_event_generator(queue)
    event = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
    assert event["event"] == "summary"
    assert "hello" in event["data"]


@pytest.mark.asyncio
async def test_slow_client_does_not_block():
    """A full queue should not block other subscribers from receiving."""
    fast = await broadcaster.subscribe()
    slow = await broadcaster.subscribe()
    # Fill slow's queue to capacity
    for i in range(100):
        slow.put_nowait({"type": "filler", "data": {}})

    # This publish should still deliver to fast even though slow is full
    await broadcaster.publish("test", {"msg": "ok"})
    f = await asyncio.wait_for(fast.get(), timeout=1.0)
    assert f["data"] == {"msg": "ok"}
