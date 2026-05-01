"""
Visual generator: produces an animated HTML snippet for the concept.

This is the SLOW path (~2-3s via Gemini Pro). To avoid a blank screen,
it launches the SUMMARY generator concurrently — the summary publishes
~300ms after the batch is ready, and the visual fades in ~2s after that.
"""

import asyncio
import logging

from app.services.gemini import GeminiService
from app.broadcaster import broadcaster
from app.pipeline.state import PipelineState
from app.pipeline.summary_generator import summary_generator_node
from app.course_state import course_state

logger = logging.getLogger(__name__)

VISUAL_PROMPT_TEMPLATE = """Generate a self-contained HTML snippet that visually demonstrates this concept.

Concept: {concept}
{syllabus_context}
Lecture context:
\"\"\"{text}\"\"\"

Strict requirements:
- Output a single <div> wrapping all content (no <html>, <head>, or <body> tags)
- Inline <style> with CSS keyframe animations showing motion or data flow
- Inline <script> for interactivity if it aids learning (sliders, buttons)
- Light theme with dark text — clean, minimal, readable
- The visual MUST animate or respond to user input — not static
- Pedagogically meaningful, not just decorative
- Total size under 4 KB
- Use simple shapes (divs, SVG primitives), no external assets, no images

Output ONLY the HTML snippet. No markdown fences, no explanation, no preamble.
"""


def _strip_code_fences(text: str) -> str:
    """Some models wrap output in ``` despite instructions. Strip if present."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        else:
            text = text[3:]
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return text.strip()


async def _generate_and_publish_visual(
    concept: str | None, text: str, timestamp: str
) -> str:
    """Generate the HTML, publish a `visual` event, return the HTML."""
    syllabus = course_state.get_syllabus()
    syllabus_context = f"Course Material Context (align your visual with this):\n{syllabus}\n" if syllabus else ""
    
    prompt = VISUAL_PROMPT_TEMPLATE.format(
        concept=concept or "the concept just discussed", text=text, syllabus_context=syllabus_context
    )
    try:
        html = await GeminiService.generate("pro", prompt, max_output_tokens=4096)
        html = _strip_code_fences(html)
    except Exception as e:
        logger.exception(f"visual generation failed: {e}")
        return ""

    if not html:
        logger.warning("visual generator returned empty html; skipping publish")
        return ""

    await broadcaster.publish(
        "visual",
        {"concept": concept, "html": html, "timestamp": timestamp},
    )
    logger.info(f"visual published: concept={concept!r} size={len(html)}b")
    return html


async def visual_generator_node(state: PipelineState) -> dict:
    """
    Two-phase: launch summary (Flash) and visual (Pro) concurrently.
    Summary publishes from inside its own node ~300ms in;
    visual publishes here ~2-3s in.
    """
    concept = state.get("concept")
    text = state["accumulated_text"]
    timestamp = state["timestamp"]

    summary_task = asyncio.create_task(summary_generator_node(state))
    visual_task = asyncio.create_task(
        _generate_and_publish_visual(concept, text, timestamp)
    )

    summary_result, visual_html = await asyncio.gather(
        summary_task, visual_task, return_exceptions=False
    )

    return {
        "summary": summary_result.get("summary", ""),
        "visual_html": visual_html,
    }
