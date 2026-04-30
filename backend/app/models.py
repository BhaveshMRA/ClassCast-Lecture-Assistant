"""
Pydantic models for SSE event payloads. The wire format is JSON;
these models are how Python code constructs and validates payloads.
"""

from pydantic import BaseModel
from typing import Literal


ConceptType = Literal["TECHNICAL", "EXAMPLE", "ADMIN", "JOKE", "SUMMARY", "UNKNOWN"]
DecisionAction = Literal["VISUALIZE", "SUMMARIZE_ONLY", "SKIP"]


class HeartbeatEvent(BaseModel):
    tick: int
    timestamp: str
    clients: int


class SummaryEvent(BaseModel):
    concept: str | None
    text: str
    timestamp: str


class VisualEvent(BaseModel):
    concept: str | None
    html: str
    timestamp: str


class AuditEvent(BaseModel):
    """Track-B audit trail — published for every batch regardless of outcome."""
    concept: str | None
    concept_type: ConceptType
    confidence: float
    action: DecisionAction
    reason: str
    timestamp: str
