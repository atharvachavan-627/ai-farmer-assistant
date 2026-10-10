"""
Application Configuration for AI Farmer Assistant.

Uses environment variables with reliable defaults based on project root.
No hardcoded personal machine paths.
"""

from pathlib import Path
from typing import List, Set
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings:
    """Application settings and configuration parameters."""

    # Project Paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    DATA_DIR: Path = PROJECT_ROOT / "data"

    # Model & KB Locations
    MODEL_PATH: Path = Path(
        os.getenv(
            "MODEL_PATH",
            str(PROJECT_ROOT / "models" / "mobilenetv2_finetuned" / "best_finetuned_model.pth")
        )
    )
    # Fallback to baseline model if fine-tuned checkpoint is not found
    if not MODEL_PATH.exists():
        BASELINE_FALLBACK = PROJECT_ROOT / "models" / "mobilenetv2" / "best_model.pth"
        if BASELINE_FALLBACK.exists():
            MODEL_PATH = BASELINE_FALLBACK

    CLASS_MAPPING_PATH: Path = Path(
        os.getenv(
            "CLASS_MAPPING_PATH",
            str(PROJECT_ROOT / "models" / "mobilenetv2" / "class_mapping.json")
        )
    )

    TREATMENT_KB_PATH: Path = Path(
        os.getenv(
            "TREATMENT_KB_PATH",
            str(PROJECT_ROOT / "data" / "treatment_recommendations.json")
        )
    )

    # Classification & Agronomic Thresholds
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))

    # File Upload Restrictions
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))  # 10 MB

    ALLOWED_MIME_TYPES: Set[str] = {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp"
    }

    ALLOWED_EXTENSIONS: Set[str] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    # CORS Configurations
    @property
    def cors_origins(self) -> List[str]:
        raw_origins = os.getenv("CORS_ORIGINS", "")
        if raw_origins:
            return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(PROJECT_ROOT / 'data' / 'ai_farmer_assistant.db').as_posix()}"
    )

    # Session and Authentication Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-ai-farmer-assistant-2026")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "session_id")
    CSRF_COOKIE_NAME: str = os.getenv("CSRF_COOKIE_NAME", "csrf_token")
    CSRF_HEADER_NAME: str = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")
    SESSION_EXPIRE_SECONDS: int = int(os.getenv("SESSION_EXPIRE_SECONDS", str(7 * 24 * 3600)))  # 7 days
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1")
    SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "lax")

    # Service Meta
    APP_NAME: str = "AI Farmer Assistant API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()


def get_settings() -> Settings:
    """Returns application settings."""
    return settings
