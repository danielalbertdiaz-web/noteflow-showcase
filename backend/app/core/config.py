from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/noteflow"

    @model_validator(mode="after")
    def fix_database_url(self):
        """Render gives postgres:// but asyncpg needs postgresql+asyncpg://"""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            self.DATABASE_URL = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            self.DATABASE_URL = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "changeme-use-a-real-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Magic link
    MAGIC_LINK_EXPIRE_MINUTES: int = 15

    # Deepgram
    DEEPGRAM_API_KEY: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Google AI
    GOOGLE_AI_API_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID: str = ""

    # AWS / S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = "noteflow-audio"
    S3_REGION: str = "us-east-1"

    # Encryption (32-byte hex key for AES-256)
    ENCRYPTION_KEY: str = ""

    # App
    APP_URL: str = "http://localhost:3000"

    # SMTP
    SMTP_HOST: str = "smtp.sendgrid.net"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Kinnser / Browser automation
    KINNSER_BROWSER_WS_URL: Optional[str] = None

    # Sentry
    SENTRY_DSN: Optional[str] = None


settings = Settings()
