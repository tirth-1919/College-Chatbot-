import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "AIT AI ASSISTANT"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Institution Info
    INSTITUTION_NAME: str = "Ahmedabad Institute of Technology"
    INSTITUTION_SHORT_NAME: str = "AIT"
    INSTITUTION_URL: str = "https://www.aitindia.in"
    
    # Security & Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ait-ai-super-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google OAuth (Graceful notification if empty)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    # Database
    # Defaults to SQLite for immediate local plug-and-play development, 
    # fully compatible with production PostgreSQL URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend/ait_assistant.db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    
    # AI Providers
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Storage & Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./backend/storage/uploads")
    IMAGE_STORAGE_DIR: str = os.getenv("IMAGE_STORAGE_DIR", "./backend/storage/images")
    MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25MB
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "docx", "xlsx", "csv", "txt", "md", "png", "jpg", "jpeg", "webp"
    ]
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://www.aitindia.in"
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
