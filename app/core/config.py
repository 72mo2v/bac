from typing import List, Optional

from pydantic import AliasChoices, AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Vendor E-Commerce"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "DEV_SECRET_KEY_REPLACE_IN_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # DATABASE
    POSTGRES_SERVER: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("POSTGRES_SERVER", "POSTGRES_HOST"),
    )
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "123"
    POSTGRES_DB: str = "shop_db"
    DATABASE_URL: Optional[str] = None

    # REDIS
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default_factory=list)
    ALLOWED_ORIGINS: Optional[str] = None

    # SMTP Settings
    MAIL_USERNAME: str = Field(
        default="test@example.com",
        validation_alias=AliasChoices("MAIL_USERNAME", "EMAIL_USER"),
    )
    MAIL_PASSWORD: str = Field(
        default="password",
        validation_alias=AliasChoices("MAIL_PASSWORD", "EMAIL_PASSWORD"),
    )
    MAIL_FROM: str = Field(
        default="test@example.com",
        validation_alias=AliasChoices("MAIL_FROM", "EMAIL_FROM"),
    )
    MAIL_PORT: int = Field(default=587, validation_alias=AliasChoices("MAIL_PORT", "EMAIL_PORT"))
    MAIL_SERVER: str = Field(
        default="smtp.gmail.com",
        validation_alias=AliasChoices("MAIL_SERVER", "EMAIL_HOST"),
    )
    MAIL_FROM_NAME: str = "E-Shop Platform"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True

    # Bero integration
    BERO_BASE_URL: str = "http://localhost:8001/api/v1"
    BERO_TIMEOUT_SECONDS: int = 20
    BERO_SYNC_INTERVAL_SECONDS: int = 60
    BERO_TOKEN_ENCRYPTION_KEY: Optional[str] = None

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @model_validator(mode="after")
    def finalize_derived_settings(self):
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
            )

        if self.ALLOWED_ORIGINS and not self.BACKEND_CORS_ORIGINS:
            self.BACKEND_CORS_ORIGINS = [
                origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()
            ]

        return self


settings = Settings()

