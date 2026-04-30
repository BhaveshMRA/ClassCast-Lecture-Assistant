"""
LangGraph wiring + entry point.

The graph:

    transcript_chunk
          │
          ▼
    [batch_accumulator]
          │  (always)
          ▼
    [concept_extractor]
          │
          ├── wait        ─► END  (batch not ready yet)
          ├── skip        ─► END  (joke / admin / unknown)
          ├── summarize   ─► [summary_generator] ─► END
          └── visualize   ─► [visual_generator] ─► END
                              (also publishes summary internally)
"""

import asyncio
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END

from app.broadcaster import broadcaster
from app.pipeline.state import PipelineState
from app.pipeline.batch_accumulator import batch_accumulator_node
from app.pipeline.concept_extractor import concept_extractor_node
from app.pipeline.decision_router import decide_action
from app.pipeline.summary_generator import summary_generator_node
from app.pipeline.visual_generator import visual_generator_node

logger = logging.getLogger(__name__)


def build_graph():
    """Build and compile the LangGraph state machine."""
    g = StateGraph(PipelineState)

    g.add_node("batch", batch_accumulator_node)
    g.add_node("extract", concept_extractor_node)
    g.add_node("summary_node", summary_generator_node)
    g.add_node("visual_node", visual_generator_node)

    g.set_entry_point("batch")
    g.add_edge("batch", "extract")

    g.add_conditional_edges(
        "extract",
        decide_action,
        {
            "wait": END,
            "skip": END,
            "summarize": "summary_node",
            "visualize": "visual_node",
        },
    )
    g.add_edge("summary_node", END)
    g.add_edge("visual_node", END)

    return g.compile()


# Compiled lazily on first use
_graph = None


async def process_transcript_chunk(chunk: str) -> None:
    """
    Entry point called from audio routes for each transcript chunk.
    Runs the chunk through the compiled graph and publishes an audit event.
    """
    global _graph
    if _graph is None:
        _graph = build_graph()
        logger.info("langgraph compiled")

    initial: PipelineState = {
        "transcript_chunk": chunk,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        result = await _graph.ainvoke(initial)
    except Exception as e:
        logger.exception(f"pipeline error: {e}")
        return

    # Audit event — published every time, regardless of outcome.
    # This is the Track-B-aligned audit trail.
    if result.get("is_ready"):
        if result.get("visual_html"):
            action = "VISUALIZE"
        elif result.get("summary"):
            action = "SUMMARIZE_ONLY"
        else:
            action = "SKIP"

        await broadcaster.publish(
            "audit",
            {
                "concept": result.get("concept"),
                "concept_type": result.get("concept_type", "UNKNOWN"),
                "confidence": result.get("confidence", 0.0),
                "action": action,
                "reason": f"concept_type={result.get('concept_type')} "
                f"confidence={result.get('confidence', 0):.2f}",
                "timestamp": initial["timestamp"],
            },
        )


async def process_slide_batch(slide_text: str, slide_number: int) -> None:
    """
    Entry point for slide-based processing.

    Unlike process_transcript_chunk, this SKIPS the batch accumulator because
    each slide is already a self-contained batch of content. It feeds directly
    into:
        concept_extractor  (Flash model  — identifies concept + type)
            └─► summary_generator  (Flash — fast plain-English summary)
            └─► visual_generator   (Pro   — animated HTML visual)

    Both generators run concurrently so the summary appears ~300ms after the
    slide is processed and the visual follows ~2-3s later.
    """
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"processing slide {slide_number}: {slide_text[:80]}...")

    # Build state with is_ready=True and accumulated_text already set.
    # This skips the batch accumulator entirely.
    state: PipelineState = {
        "transcript_chunk": slide_text,
        "timestamp": timestamp,
        "is_ready": True,
        "accumulated_text": slide_text,
    }

    # Step 1 — concept extraction (Flash)
    try:
        concept_result = await concept_extractor_node(state)
        state.update(concept_result)
    except Exception as e:
        logger.exception(f"slide {slide_number}: concept extraction failed: {e}")
        return

    # Step 2 — routing
    action = decide_action(state)
    logger.info(f"slide {slide_number}: action={action} concept={state.get('concept')!r}")

    # Step 3 — generate summary + visual
    action_taken = "SKIP"
    if action == "visualize":
        # Run summary (Flash) and visual (Pro) concurrently
        summary_result, _ = await asyncio.gather(
            summary_generator_node(state),
            _generate_slide_visual(state, slide_number),
        )
        action_taken = "VISUALIZE"
    elif action == "summarize":
        await summary_generator_node(state)
        action_taken = "SUMMARIZE_ONLY"
    # else: skip — no output published

    # Audit trail
    await broadcaster.publish(
        "audit",
        {
            "concept": state.get("concept"),
            "concept_type": state.get("concept_type", "UNKNOWN"),
            "confidence": state.get("confidence", 0.0),
            "action": action_taken,
            "reason": f"slide={slide_number} "
            f"concept_type={state.get('concept_type')} "
            f"confidence={state.get('confidence', 0):.2f}",
            "timestamp": timestamp,
        },
    )


async def _generate_slide_visual(state: PipelineState, slide_number: int) -> str:
    """Thin wrapper around visual_generator_node for slides (adds slide context)."""
    try:
        result = await visual_generator_node(state)
        return result.get("visual_html", "")
    except Exception as e:
        logger.exception(f"slide {slide_number}: visual generation failed: {e}")
        return ""
