from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database Settings
    DATABASE_URL: str
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # LLM Provider settings
    DEFAULT_LLM_PROVIDER: str = "ollama"

    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:4b"

    REQUEST_TIMEOUT: int = 600

    # RAG / Embedding Settings (Ollama nomic-embed-text)
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_TIMEOUT: int = 60

    # Chunking settings (in tokens)
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100

    # Retrieval settings
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 0.57

    # Transcript source directory
    TRANSCRIPT_SOURCE_DIR: str = "data/transcripts"

    # Agent settings
    AGENT_MAX_TURNS: int = 4
    AGENT_TIMEOUT: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

