"""
Core configuration module for C-OCR platform.
Loads environment variables and provides application settings.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Info
    PROJECT_NAME: str = "C-OCR"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "OCR + Template-based Data Extraction Platform"

    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    ASYNC_DATABASE_URL: str = Field(..., env="ASYNC_DATABASE_URL")

    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")
    CELERY_BROKER_URL: str = Field(..., env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: str = Field(..., env="CELERY_RESULT_BACKEND")

    # Storage
    STORAGE_PATH: str = Field(default="./storage", env="STORAGE_PATH")
    UPLOAD_MAX_SIZE: int = Field(default=52428800, env="UPLOAD_MAX_SIZE")  # 50MB

    # Security
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(default=1440, env="JWT_EXPIRATION_MINUTES")
    API_KEY_HASH_SALT: str = Field(..., env="API_KEY_HASH_SALT")

    # OCR
    OCR_ENGINE_PRIMARY: str = Field(default="paddle", env="OCR_ENGINE_PRIMARY")
    OCR_ENGINE_FALLBACK: str = Field(default="tesseract", env="OCR_ENGINE_FALLBACK")
    OCR_LANGS: str = Field(default="en", env="OCR_LANGS")
    DEFAULT_DPI: int = Field(default=300, env="DEFAULT_DPI")

    # Template
    TEMPLATE_MATCH_THRESHOLD: float = Field(default=0.75, env="TEMPLATE_MATCH_THRESHOLD")

    # Server
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    WORKERS: int = Field(default=4, env="WORKERS")
    RELOAD: bool = Field(default=True, env="RELOAD")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or list."""
        if isinstance(v, str):
            return json.loads(v)
        return v

    # Multi-tenancy
    MULTI_TENANT_MODE: bool = Field(default=True, env="MULTI_TENANT_MODE")
    DEFAULT_TENANT_NAME: str = Field(default="Default Tenant", env="DEFAULT_TENANT_NAME")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_DAILY_QUOTA: int = Field(default=1000, env="RATE_LIMIT_DAILY_QUOTA")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")

    # Environment
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
