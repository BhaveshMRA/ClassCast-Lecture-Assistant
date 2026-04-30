"""
Summary generator: produces a short plain-English summary of the batch.

This is the FAST path. It runs in ~300ms via Gemini Flash and publishes
a `summary` event to all connected clients. When the visual generator runs
in parallel, the student sees the summary first and the visual ~2s later.
"""

import logging

from app.services.gemini import GeminiService
from app.broadcaster import broadcaster
from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Summarize this lecture excerpt in 2-3 plain English sentences for a student.
Focus on what the professor is teaching, not how they're saying it.
Avoid jargon when possible; if jargon is unavoidable, briefly clarify.
Output only the summary text — no preamble, no markdown.

Concept: {concept}

Excerpt:
\"\"\"{text}\"\"\"

Summary:"""


async def summary_generator_node(state: PipelineState) -> dict:
    """LangGraph node — generates and publishes a summary."""
    text = state["accumulated_text"]
    concept = state.get("concept", "this concept")
    timestamp = state["timestamp"]

    prompt = PROMPT_TEMPLATE.format(text=text, concept=concept or "this concept")

    try:
        summary = await GeminiService.generate("flash", prompt)
        summary = summary.strip()
    except Exception as e:
        logger.exception(f"summary generation failed: {e}")
        summary = ""

    if summary:
        await broadcaster.publish(
            "summary",
            {"concept": concept, "text": summary, "timestamp": timestamp},
        )
        logger.info(f"summary published: {summary[:80]}...")

    return {"summary": summary}
