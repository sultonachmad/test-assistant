"""Application configuration using Pydantic Settings."""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Info
    PROJECT_NAME: str = "Personal Assistant API"
    VERSION: str = "1.0.0"

    @model_validator(mode='after')
    def decrypt_sensitive_values(self):
        """Decrypt any encrypted values (with ENC: prefix) in settings."""
        from app.core.encryption import decrypt_value, is_encrypted

        # List of sensitive fields that may be encrypted
        sensitive_fields = [
            'GOOGLE_CLIENT_SECRET',
            'NEXTAUTH_SECRET',
            'SMTP_PASSWORD',
            'TAIGA_PASSWORD',
            'TAIGA_AUTH_TOKEN',
            'LLM_GATEWAY_KEY',
        ]

        # Get the secret for decryption (NEXTAUTH_SECRET itself shouldn't be encrypted)
        secret = object.__getattribute__(self, 'NEXTAUTH_SECRET')
        if not secret:
            return self

        for field in sensitive_fields:
            if field == 'NEXTAUTH_SECRET':
                continue  # Can't decrypt the key itself
            value = getattr(self, field, None)
            if value and is_encrypted(value):
                try:
                    decrypted = decrypt_value(value, secret)
                    object.__setattr__(self, field, decrypted)
                except Exception:
                    pass  # Leave original value if decryption fails

        return self

    # Database
    POSTGRES_DSN: str = "postgresql://user:password@localhost:5432/assistant_db"

    # LLM Gateway
    LLM_GATEWAY_URL: str = "http://localhost:4000"
    LLM_GATEWAY_KEY: str = ""
    LLM_MODEL: str = "gpt-4.1-mini"
    LLM_MODEL_SUMMARY: str = "gpt-4.1-mini"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # NextAuth (for JWT validation)
    NEXTAUTH_SECRET: str = ""

    # Email (SMTP)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True

    # Sync Settings
    SYNC_INTERVAL_MINUTES: int = 15
    SYNC_EMAIL_MAX_RESULTS: int = 100
    SYNC_CALENDAR_DAYS_AHEAD: int = 30
    SYNC_CHAT_MAX_MESSAGES: int = 50

    # Feature Flags
    FEATURE_TAIGA_ENABLE: bool = False
    FEATURE_EMAIL_NOTIFY: bool = True
    FEATURE_CALENDAR_NOTIFY: bool = True

    # Taiga Integration
    TAIGA_URL: str = ""  # e.g., https://taiga.ecquaria.org
    TAIGA_USERNAME: str = ""  # Taiga username (for login)
    TAIGA_PASSWORD: str = ""  # Taiga password (for login)
    TAIGA_AUTH_TOKEN: str = ""  # Auth token (optional - auto-generated from username/password)
    TAIGA_PROJECT_ID: int = 0  # Default project ID (numeric)
    TAIGA_PROJECT_SLUG: str = ""  # Project slug (e.g., "tecq-ai-bd" from URL /project/tecq-ai-bd)

    # App Settings
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
