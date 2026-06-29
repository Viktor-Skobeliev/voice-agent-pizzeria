"""Runtime configuration.

Loaded from environment variables / ``.env`` and validated on startup so the
worker fails fast with a clear message instead of crashing mid-call.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings. Env var names match field names (case-insensitive)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- OpenAI: the realtime model is both the brain and the voice ---
    openai_api_key: str
    openai_realtime_model: str = "gpt-realtime-mini"
    openai_realtime_voice: str = "marin"

    # --- LiveKit: required only to run the live worker; tests/evals don't need it ---
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    log_level: str = "INFO"

    def require_livekit(self) -> None:
        """Raise with an actionable message if LiveKit creds are missing for a live run."""
        missing = [
            name
            for name, value in (
                ("LIVEKIT_URL", self.livekit_url),
                ("LIVEKIT_API_KEY", self.livekit_api_key),
                ("LIVEKIT_API_SECRET", self.livekit_api_secret),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing LiveKit credentials: "
                + ", ".join(missing)
                + ". Set them in .env (see .env.example) — get a free project at "
                "https://cloud.livekit.io."
            )


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so the .env is parsed once per process."""
    return Settings()  # type: ignore[call-arg]  # values come from env / .env
