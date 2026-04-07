from pydantic_settings import BaseSettings
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    cors_allow_origins: list[str] = ["http://localhost:5173"]
    storage_backend: str = "sqlite"  # sqlite|mongodb
    database_url: str = f"sqlite:///{(BASE_DIR / 'speakez.sqlite').as_posix()}"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "speakez"

    # STT: local Whisper by default; optional OpenAI provider
    speakez_stt_provider: str = "local"  # local|openai
    openai_api_key: str | None = None
    whisper_model: str = "small"  # tiny|base|small|medium|large-v3 (downloaded by faster-whisper)
    whisper_device: str = "auto"  # auto|cpu|cuda

    class Config:
        env_file = str(BASE_DIR / ".env")
        extra = "ignore"


settings = Settings()

