"""
Audio decoding helpers.

- load_wav_chunks: iterate a WAV file in fixed-duration chunks at 16kHz mono float32
- bytes_to_array:  convert raw int16 PCM bytes from WebSocket into float32 array
"""

import io
from typing import Iterator

import numpy as np


def load_wav_chunks(
    audio_bytes: bytes, chunk_seconds: float = 5.0
) -> Iterator[np.ndarray]:
    """
    Yield successive chunks of audio as float32 numpy arrays at 16kHz mono.
    Resamples and downmixes if necessary.
    """
    import soundfile as sf

    data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")

    # Downmix to mono if stereo
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Resample to 16kHz if necessary
    if sr != 16000:
        from scipy.signal import resample_poly
        data = resample_poly(data, 16000, sr)

    chunk_samples = int(chunk_seconds * 16000)
    for i in range(0, len(data), chunk_samples):
        chunk = data[i : i + chunk_samples]
        if len(chunk) > 0:
            yield chunk


def bytes_to_array(pcm_bytes: bytes) -> np.ndarray:
    """
    Convert 16-bit signed PCM bytes (e.g. from WebSocket) to float32
    numpy array normalized to [-1.0, 1.0].
    """
    int16_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    return int16_array.astype(np.float32) / 32768.0
