"""End-to-end pipeline test with mocked Gemini."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.broadcaster import broadcaster
from app.pipeline.graph import process_transcript_chunk


@pytest.mark.asyncio
async def test_end_to_end_visualize_path():
    """Speak something technical; verify summary + visual + audit events fire."""
    queue = await broadcaster.subscribe()

    concept_response = {
        "concept": "Newton's third law",
        "concept_type": "TECHNICAL",
        "confidence": 0.95,
    }
    summary_text = "Newton's third law says action equals reaction."
    visual_html = "<div>animated visual</div>"

    async def fake_generate(model, prompt, **kwargs):
        if "Summarize" in prompt:
            return summary_text
        return visual_html

    async def fake_generate_json(model, prompt):
        return concept_response

    with patch("app.pipeline.concept_extractor.GeminiService.generate_json",
               new=AsyncMock(side_effect=fake_generate_json)), \
         patch("app.pipeline.summary_generator.GeminiService.generate",
               new=AsyncMock(return_value=summary_text)), \
         patch("app.pipeline.visual_generator.GeminiService.generate",
               new=AsyncMock(return_value=visual_html)):

        # Two sentences -> batch flushes, pipeline runs end-to-end
        await process_transcript_chunk(
            "Newton's third law states action and reaction. "
            "For every action there is an equal and opposite reaction."
        )

    received = []
    while not queue.empty():
        received.append(await queue.get())

    types = [m["type"] for m in received]
    assert "summary" in types
    assert "visual" in types
    assert "audit" in types

    audit = next(m for m in received if m["type"] == "audit")
    assert audit["data"]["action"] == "VISUALIZE"
    assert audit["data"]["concept"] == "Newton's third law"


@pytest.mark.asyncio
async def test_end_to_end_skip_path_for_joke():
    """Speak a joke; verify NO summary or visual is broadcast, only audit."""
    queue = await broadcaster.subscribe()

    async def fake_generate_json(model, prompt):
        return {"concept": None, "concept_type": "JOKE", "confidence": 0.95}

    with patch("app.pipeline.concept_extractor.GeminiService.generate_json",
               new=AsyncMock(side_effect=fake_generate_json)):
        await process_transcript_chunk(
            "Anyway, who's getting coffee after class. I really need one."
        )

    received = []
    while not queue.empty():
        received.append(await queue.get())

    types = [m["type"] for m in received]
    assert "summary" not in types
    assert "visual" not in types
    assert "audit" in types
    audit = next(m for m in received if m["type"] == "audit")
    assert audit["data"]["action"] == "SKIP"
