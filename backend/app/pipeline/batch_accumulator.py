"""
Batch accumulator: buffers transcript chunks into meaningful units.

Flush triggers (whichever comes first):
  - BATCH_SENTENCE_COUNT sentence-ending punctuation marks seen
  - BATCH_TIMEOUT_SECONDS elapsed since last flush

This is a process-singleton — fine for the hackathon. For multi-instructor
deployment, key it by session_id.
"""

import re
import time
import logging

from app.config import settings
from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

SENTENCE_END = re.compile(r"[.!?]+\s")


class BatchBuffer:
    """Module-level state. One buffer per server process."""

    _text: str = ""
    _last_flush: float = time.time()

    @classmethod
    def add_and_check(cls, chunk: str) -> tuple[bool, str]:
        """
        Append a chunk and check if we should flush.
        Returns (is_ready, accumulated_text).
        """
        cls._text = (cls._text + " " + chunk).strip()

        # Count sentence boundaries
        boundaries = len(SENTENCE_END.findall(cls._text + " "))
        elapsed = time.time() - cls._last_flush

        should_flush = (
            boundaries >= settings.batch_sentence_count
            or elapsed > settings.batch_timeout_seconds
        )

        if should_flush and cls._text:
            ready_text = cls._text
            cls._text = ""
            cls._last_flush = time.time()
            logger.debug(
                f"batch flushed: boundaries={boundaries} elapsed={elapsed:.1f}s "
                f"text='{ready_text[:80]}...'"
            )
            return True, ready_text

        return False, ""

    @classmethod
    def reset(cls) -> None:
        """Clear the buffer (used in tests)."""
        cls._text = ""
        cls._last_flush = time.time()


async def batch_accumulator_node(state: PipelineState) -> dict:
    """LangGraph node — adds is_ready and accumulated_text to state."""
    is_ready, accumulated = BatchBuffer.add_and_check(state["transcript_chunk"])
    return {"is_ready": is_ready, "accumulated_text": accumulated}
