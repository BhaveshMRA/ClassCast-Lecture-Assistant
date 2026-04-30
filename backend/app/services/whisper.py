"""
Whisper transcription service.

Uses faster-whisper (CTranslate2 backend) which is 4-6x faster than
the reference Whisper implementation. Model loads once at startup.
"""

import logging
from typing import Union
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class WhisperService:
    """Singleton wrapper around faster-whisper.WhisperModel."""

    _model = None

    @classmethod
    def get(cls):
        """Lazy-load the model on first access."""
        if cls._model is None:
            # Import here so Step 1 doesn't require faster-whisper installed
            from faster_whisper import WhisperModel

            logger.info(
                f"loading whisper model: {settings.whisper_model} "
                f"({settings.whisper_device}, {settings.whisper_compute_type})"
            )
            cls._model = WhisperModel(
                settings.whisper_model,
                device=settings.whisper_device,
                compute_type=settings.whisper_compute_type,
            )
            logger.info("whisper model loaded")
        return cls._model

    @classmethod
    def transcribe(
        cls,
        audio: Union[np.ndarray, str],
        language: str = "en",
    ) -> str:
        """
        Transcribe audio. `audio` can be a file path or a float32 numpy array
        sampled at 16kHz mono. Returns concatenated text from all segments.
        """
        model = cls.get()
        segments, _info = model.transcribe(
            audio,
            language=language,
            vad_filter=True,  # skip silence — prevents "uh"/"um" spam
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text
