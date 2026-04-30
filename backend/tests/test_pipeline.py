"""Test the pipeline routing logic with mocked Gemini responses."""

import pytest
from unittest.mock import AsyncMock, patch

from app.pipeline.batch_accumulator import BatchBuffer
from app.pipeline.decision_router import decide_action
from app.pipeline.state import PipelineState


@pytest.fixture(autouse=True)
def reset_buffer():
    BatchBuffer.reset()


# ---- decision_router ----

def test_skip_joke():
    state: PipelineState = {
        "transcript_chunk": "...",
        "timestamp": "now",
        "is_ready": True,
        "concept": None,
        "concept_type": "JOKE",
        "confidence": 0.9,
    }
    assert decide_action(state) == "skip"


def test_skip_admin():
    state: PipelineState = {
        "transcript_chunk": "...", "timestamp": "now",
        "is_ready": True, "concept": None,
        "concept_type": "ADMIN", "confidence": 0.95,
    }
    assert decide_action(state) == "skip"


def test_visualize_technical():
    state: PipelineState = {
        "transcript_chunk": "...", "timestamp": "now",
        "is_ready": True, "concept": "Newton's third law",
        "concept_type": "TECHNICAL", "confidence": 0.95,
    }
    assert decide_action(state) == "visualize"


def test_summarize_summary_block():
    state: PipelineState = {
        "transcript_chunk": "...", "timestamp": "now",
        "is_ready": True, "concept": None,
        "concept_type": "SUMMARY", "confidence": 0.8,
    }
    assert decide_action(state) == "summarize"


def test_skip_low_confidence():
    state: PipelineState = {
        "transcript_chunk": "...", "timestamp": "now",
        "is_ready": True, "concept": "maybe gradient descent",
        "concept_type": "TECHNICAL", "confidence": 0.3,
    }
    assert decide_action(state) == "skip"


def test_wait_when_not_ready():
    state: PipelineState = {
        "transcript_chunk": "...", "timestamp": "now",
        "is_ready": False,
    }
    assert decide_action(state) == "wait"


# ---- batch_accumulator ----

def test_buffer_flushes_on_sentence_count():
    is_ready, _ = BatchBuffer.add_and_check("Hello world.")
    assert not is_ready  # only 1 sentence so far (default count = 2)
    is_ready, text = BatchBuffer.add_and_check("How are you.")
    assert is_ready
    assert "Hello world" in text and "How are you" in text


# ---- concept_extractor with mocked Gemini ----

@pytest.mark.asyncio
async def test_concept_extractor_mocked():
    from app.pipeline.concept_extractor import concept_extractor_node

    mocked = {"concept": "Newton's third law", "concept_type": "TECHNICAL", "confidence": 0.92}
    with patch("app.pipeline.concept_extractor.GeminiService.generate_json",
               new=AsyncMock(return_value=mocked)):
        state: PipelineState = {
            "transcript_chunk": "...", "timestamp": "now",
            "is_ready": True, "accumulated_text": "Newton's third law states ...",
        }
        result = await concept_extractor_node(state)
        assert result["concept"] == "Newton's third law"
        assert result["concept_type"] == "TECHNICAL"
        assert result["confidence"] == pytest.approx(0.92)
