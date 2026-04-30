"""
Centralized configuration loaded from environment / .env file.
All other modules import `settings` from here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- server ---
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # --- OpenRouter ---
    openrouter_api_key: str = ""
    openrouter_flash_model: str = "google/gemini-2.5-flash"
    openrouter_pro_model: str = "anthropic/claude-haiku-4.5"

    # --- Whisper (used in Step 2) ---
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # --- pipeline tuning (used in Step 3) ---
    batch_sentence_count: int = 2
    batch_timeout_seconds: float = 8.0
    concept_confidence_threshold: float = 0.5


settings = Settings()
