"""Core configuration settings for the Document Ingestion Service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "document-ingestion-service"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/document_ingestion"
    database_pool_size: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Storage
    upload_dir: Path = Path("./temp")
    max_upload_size_mb: int = 50

    # OCR
    ocr_confidence_threshold: float = 0.3
    ocr_language: str = "en"

    # LLM
    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1

    # Local LLM (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    local_llm_model: str = "llama3"
    use_local_llm: bool = False

    # Dashboard
    streamlit_port: int = 8501

    @field_validator("upload_dir", mode="before")
    @classmethod
    def create_upload_dir(cls, v: str | Path) -> Path:
        """Ensure upload directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_size_bytes(self) -> int:
        """Max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def allowed_extensions(self) -> set[str]:
        """Allowed file extensions for upload."""
        return {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
