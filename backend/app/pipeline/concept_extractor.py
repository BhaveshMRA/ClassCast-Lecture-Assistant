"""
Concept extractor: identifies the key concept and classifies the batch.

Uses Gemini Flash for speed (~400ms). Output is structured JSON.
"""

import logging

from app.services.gemini import GeminiService
from app.pipeline.state import PipelineState
from app.course_state import course_state

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are analyzing a snippet of a college lecture.
Identify the key concept being taught (if any) and classify the snippet.
{syllabus_context}

Snippet:
\"\"\"{text}\"\"\"

Respond with JSON only (no markdown, no code fences):
{{
  "concept": "<short concept name, e.g. 'Newton's third law', or null if none>",
  "concept_type": "TECHNICAL | EXAMPLE | ADMIN | JOKE | SUMMARY | UNKNOWN",
  "confidence": <number between 0.0 and 1.0>
}}

Classification rules:
- TECHNICAL: a teachable concept that can be visualized (algorithms, physics, chemistry, biology processes, math)
- EXAMPLE: a concrete example illustrating a previously-taught concept ("imagine pushing a wall...")
- ADMIN: announcements, scheduling, instructions ("homework due Friday", "open your laptops")
- JOKE: banter, off-topic remarks, side conversations, anecdotes unrelated to the subject
- SUMMARY: explicit recap ("in summary, today we covered...")
- UNKNOWN: unclear, fragmentary, or impossible to classify

Confidence reflects how certain you are about both the concept and the type.
"""


async def concept_extractor_node(state: PipelineState) -> dict:
    """LangGraph node — populates concept, concept_type, confidence."""
    if not state.get("is_ready"):
        return {"concept": None}

    text = state["accumulated_text"]
    
    syllabus = course_state.get_syllabus()
    syllabus_context = f"\nCourse Material Context (use this to correctly identify terminology):\n{syllabus}\n" if syllabus else ""
    
    prompt = PROMPT_TEMPLATE.format(text=text, syllabus_context=syllabus_context)

    try:
        result = await GeminiService.generate_json("flash", prompt)
    except Exception as e:
        logger.exception(f"concept extraction failed: {e}")
        return {
            "concept": None,
            "concept_type": "UNKNOWN",
            "confidence": 0.0,
        }

    concept = result.get("concept")
    if isinstance(concept, str) and concept.lower() in {"null", "none", ""}:
        concept = None

    concept_type = result.get("concept_type", "UNKNOWN")
    if concept_type not in {"TECHNICAL", "EXAMPLE", "ADMIN", "JOKE", "SUMMARY", "UNKNOWN"}:
        concept_type = "UNKNOWN"

    try:
        confidence = float(result.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    logger.info(
        f"extracted: concept={concept!r} type={concept_type} conf={confidence:.2f}"
    )

    return {
        "concept": concept,
        "concept_type": concept_type,
        "confidence": confidence,
    }
