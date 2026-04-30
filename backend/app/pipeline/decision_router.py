"""
Decision router: chooses the next pipeline step based on extracted concept.

Used as the routing function for LangGraph's add_conditional_edges. The
return value is the name of the next node (or END).
"""

import logging
from app.config import settings
from app.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def decide_action(state: PipelineState) -> str:
    """
    Return the next graph step:
      - "wait":      batch not ready, accumulate more
      - "skip":      not visualizable; pipeline ends here
      - "summarize": summary-only ("in summary today we covered...")
      - "visualize": full visual generation (also produces summary)
    """
    if not state.get("is_ready"):
        return "wait"

    ctype = state.get("concept_type", "UNKNOWN")
    confidence = state.get("confidence", 0.0)

    if ctype in {"JOKE", "ADMIN", "UNKNOWN"}:
        logger.info(f"decision: skip ({ctype})")
        return "skip"

    if ctype == "SUMMARY":
        logger.info("decision: summarize-only")
        return "summarize"

    if ctype in {"TECHNICAL", "EXAMPLE"}:
        if confidence >= settings.concept_confidence_threshold:
            logger.info(f"decision: visualize ({ctype}, conf={confidence:.2f})")
            return "visualize"
        else:
            logger.info(
                f"decision: skip — low confidence ({ctype}, conf={confidence:.2f})"
            )
            return "skip"

    return "skip"
