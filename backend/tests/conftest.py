"""Shared pytest fixtures."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def reset_broadcaster():
    """Ensure each test starts with a clean broadcaster."""
    from app.broadcaster import broadcaster
    # snapshot any current subscribers and clear them
    broadcaster._subscribers.clear()
    yield
    broadcaster._subscribers.clear()
