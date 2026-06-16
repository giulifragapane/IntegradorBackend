# app/core/config.py
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # ----- Base de datos -----
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(alias="POSTGRES_PORT")

    # ----- JWT -----
    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(alias="ALGORITHM")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    auth_rate_limit_max_attempts: int = Field(default=5, alias="AUTH_RATE_LIMIT_MAX_ATTEMPTS")
    auth_rate_limit_window_minutes: int = Field(default=15, alias="AUTH_RATE_LIMIT_WINDOW_MINUTES")

    # ----- MercadoPago -----
    mp_access_token: str = Field(alias="MP_ACCESS_TOKEN")
    mp_public_key: str = Field(alias="MP_PUBLIC_KEY")
    mp_webhook_url: str = Field(alias="MP_WEBHOOK_URL")
    mp_webhook_secret: str = Field(alias="MP_WEBHOOK_SECRET")

    # ----- Front / URLs externas -----
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    ngrok_url: str = Field(alias="NGROK_URL")

    # ----- Cloudinary -----
    cloudinary_cloud_name: str = Field(alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(alias="CLOUDINARY_API_SECRET")

    # Nivel de log. 
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
