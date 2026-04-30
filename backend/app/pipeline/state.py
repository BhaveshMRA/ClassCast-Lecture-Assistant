"""
Pipeline state passed between LangGraph nodes.

Each node reads keys it cares about and adds/updates keys for downstream nodes.
NotRequired fields are populated as the state flows through the graph.
"""

from typing import TypedDict, NotRequired
from app.models import ConceptType, DecisionAction


class PipelineState(TypedDict):
    # --- inputs ---
    transcript_chunk: str        # raw text from Whisper
    timestamp: str               # ISO format timestamp

    # --- filled by batch_accumulator ---
    accumulated_text: NotRequired[str]
    is_ready: NotRequired[bool]

    # --- filled by concept_extractor ---
    concept: NotRequired[str | None]
    concept_type: NotRequired[ConceptType]
    confidence: NotRequired[float]

    # --- filled by decision_router (via routing function) ---
    action: NotRequired[DecisionAction]
    reason: NotRequired[str]

    # --- filled by generators ---
    summary: NotRequired[str]
    visual_html: NotRequired[str]
