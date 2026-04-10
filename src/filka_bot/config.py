from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    gigachat_credentials: str = Field(alias="GIGACHAT_CREDENTIALS")
    gigachat_scope: str = Field(default="GIGACHAT_API_PERS", alias="GIGACHAT_SCOPE")
    gigachat_model: str = Field(default="GigaChat", alias="GIGACHAT_MODEL")
    gigachat_verify_ssl_certs: bool = Field(default=True, alias="GIGACHAT_VERIFY_SSL_CERTS")
    filka_max_history: int = Field(default=12, alias="FILKA_MAX_HISTORY")
    filka_db_path: Path = Field(default=Path("data/filka.db"), alias="FILKA_DB_PATH")
    filka_log_path: Path = Field(default=Path("logs/filka.log"), alias="FILKA_LOG_PATH")
    filka_allowed_user_ids: list[int] = Field(default_factory=list, alias="FILKA_ALLOWED_USER_IDS")
    filka_allow_empty_whitelist: bool = Field(default=True, alias="FILKA_ALLOW_EMPTY_WHITELIST")
    filka_required_chat_id: str = Field(default="", alias="FILKA_REQUIRED_CHAT_ID")
    filka_required_chat_url: str = Field(default="", alias="FILKA_REQUIRED_CHAT_URL")
    filka_max_document_chars: int = Field(default=12000, alias="FILKA_MAX_DOCUMENT_CHARS")
    filka_cache_ttl_seconds: int = Field(default=3600, alias="FILKA_CACHE_TTL_SECONDS")
    filka_spam_window_seconds: int = Field(default=20, alias="FILKA_SPAM_WINDOW_SECONDS")
    filka_spam_max_requests: int = Field(default=6, alias="FILKA_SPAM_MAX_REQUESTS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("filka_allowed_user_ids", mode="before")
    @classmethod
    def parse_allowed_user_ids(cls, value: object) -> list[int]:
        if value is None:
            return []
        if isinstance(value, list):
            return [int(item) for item in value]
        if isinstance(value, (tuple, set)):
            return [int(item) for item in value]
        if isinstance(value, str):
            if not value.strip():
                return []
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return []


@lru_cache
def get_settings() -> Settings:
    return Settings()
