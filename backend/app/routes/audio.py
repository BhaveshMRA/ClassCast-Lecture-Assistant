"""
Audio file upload route — accepts a WAV, transcribes it in chunks,
and feeds each chunk through the pipeline as if it had arrived live.

Useful for pre-recorded demos and reliable testing.
"""

import logging

from fastapi import APIRouter, UploadFile, File, BackgroundTasks

from app.services.whisper import WhisperService
from app.utils.audio import load_wav_chunks
from app.pipeline.graph import process_transcript_chunk

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ingest/audio")
async def ingest_audio(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """
    Accept a WAV upload. Each ~5-second chunk is transcribed and pushed
    through the pipeline. Returns immediately; processing happens in the
    background and events stream out via SSE.
    """
    audio_bytes = await file.read()
    background_tasks.add_task(_process_uploaded_audio, audio_bytes)
    return {
        "status": "queued",
        "filename": file.filename,
        "size_bytes": len(audio_bytes),
    }


async def _process_uploaded_audio(audio_bytes: bytes) -> None:
    """
    Iterate over chunks of the uploaded audio, transcribe each, and feed
    transcripts into the pipeline. Each chunk's transcript is processed
    independently — the batch accumulator inside the pipeline handles
    grouping into meaningful units.
    """
    chunk_count = 0
    for chunk_array in load_wav_chunks(audio_bytes, chunk_seconds=5.0):
        chunk_count += 1
        try:
            transcript = WhisperService.transcribe(chunk_array)
        except Exception as e:
            logger.exception(f"whisper failed on chunk {chunk_count}: {e}")
            continue

        if transcript:
            logger.info(f"transcript chunk {chunk_count}: {transcript[:80]}...")
            await process_transcript_chunk(transcript)
