"""
ClassCast backend — FastAPI app entry point.

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.broadcaster import broadcaster
from app.routes import stream, audio, ws_audio, slides

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("classcast.log")
    ]
)
logger = logging.getLogger("classcast")


# ----------------------------------------------------------------------------
# Background heartbeat — proves the broadcast pipe works without needing audio.
# ----------------------------------------------------------------------------
async def heartbeat_loop() -> None:
    """Every 2 seconds, publish a heartbeat to all connected clients."""
    counter = 0
    while True:
        try:
            await asyncio.sleep(2)
            counter += 1
            await broadcaster.publish(
                "heartbeat",
                {
                    "tick": counter,
                    "timestamp": datetime.utcnow().isoformat(),
                    "clients": broadcaster.client_count,
                },
            )
        except asyncio.CancelledError:
            logger.info("heartbeat loop cancelled (shutting down)")
            break
        except Exception as e:
            logger.exception(f"heartbeat error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start/stop background tasks with the app."""
    logger.info("starting ClassCast backend")
    task = asyncio.create_task(heartbeat_loop())

    # Pre-warm Whisper so the first real transcription isn't slow
    try:
        from app.services.whisper import WhisperService
        WhisperService.get()  # triggers model load
        logger.info("whisper model pre-warmed")
    except Exception as e:
        logger.warning(f"whisper pre-warm skipped: {e}")

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info("ClassCast backend stopped")


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------
app = FastAPI(title="ClassCast", version="0.1.0", lifespan=lifespan)

# Open CORS for hackathon — restrict for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(stream.router)
app.include_router(audio.router)
app.include_router(ws_audio.router)
app.include_router(slides.router)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "connected_clients": broadcaster.client_count,
    }


@app.post("/test/publish")
async def test_publish(payload: dict) -> dict:
    """
    Manual test endpoint — POST any JSON to broadcast it to all clients.
        curl -X POST localhost:8000/test/publish \\
             -H "Content-Type: application/json" \\
             -d '{"message": "hello"}'
    """
    await broadcaster.publish("test", payload)
    return {"published": True, "delivered_to": broadcaster.client_count}
