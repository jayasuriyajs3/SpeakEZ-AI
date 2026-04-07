from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cors_allow_origins: list[str] = ["http://localhost:5173"]
    storage_backend: str = "sqlite"  # sqlite|mongodb
    database_url: str = "sqlite:///./speakez.sqlite"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "speakez"

    # STT: local Whisper by default; optional OpenAI provider
    speakez_stt_provider: str = "local"  # local|openai
    openai_api_key: str | None = None
    whisper_model: str = "small"  # tiny|base|small|medium|large-v3 (downloaded by faster-whisper)
    whisper_device: str = "auto"  # auto|cpu|cuda

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

