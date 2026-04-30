"""
WebSocket endpoint for live microphone audio.

Frontend uses Web Audio API + AudioWorklet to capture raw 16kHz mono PCM
and stream it as int16 bytes over this WebSocket. We buffer ~5 seconds
at a time, transcribe, and push the result through the pipeline.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.whisper import WhisperService
from app.utils.audio import bytes_to_array
from app.pipeline.graph import process_transcript_chunk
from app.broadcaster import broadcaster

router = APIRouter()
logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2  # int16
BUFFER_SECONDS = 5.0
BUFFER_BYTES = int(BUFFER_SECONDS * SAMPLE_RATE * BYTES_PER_SAMPLE)


@router.websocket("/ingest/ws")
async def audio_websocket(ws: WebSocket):
    """
    Accept a continuous stream of 16-bit PCM bytes at 16kHz mono.
    Whenever the buffer reaches ~5s, transcribe and pipeline.
    """
    await ws.accept()
    logger.info("instructor connected via websocket")
    await broadcaster.publish("mic_status", {"status": "on"})

    buffer = bytearray()
    chunk_count = 0

    try:
        while True:
            data = await ws.receive_bytes()
            buffer.extend(data)

            if len(buffer) >= BUFFER_BYTES:
                chunk_count += 1
                audio_array = bytes_to_array(bytes(buffer[:BUFFER_BYTES]))
                # Keep any leftover bytes in the buffer for next iteration
                del buffer[:BUFFER_BYTES]

                # Spawn a background task so we immediately go back to receive_bytes()
                async def process_and_publish(audio_data, count):
                    try:
                        transcript = await asyncio.to_thread(WhisperService.transcribe, audio_data)
                        if transcript:
                            logger.info(f"live chunk {count}: {transcript[:80]}...")
                            await broadcaster.publish("transcript", {"text": transcript})
                            await process_transcript_chunk(transcript)
                    except Exception as e:
                        logger.exception(f"whisper failed on ws chunk {count}: {e}")

                asyncio.create_task(process_and_publish(audio_array, chunk_count))
    except WebSocketDisconnect:
        logger.info("instructor disconnected")
        await broadcaster.publish("mic_status", {"status": "off"})
    except Exception as e:
        logger.exception(f"websocket error: {e}")
        await broadcaster.publish("mic_status", {"status": "off"})
        try:
            await ws.close()
        except Exception:
            pass
