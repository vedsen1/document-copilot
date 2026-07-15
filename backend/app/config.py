from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase (Auth + API)
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Postgres (Alembic + direct DB access — use the direct/session connection, not the pooler)
    database_url: str

    # OpenAI (LLM + embeddings)
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dimensions: int = Field(default=1536, ge=1)

    # Server
    allowed_origins: Annotated[list[str], NoDecode]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            if not origins:
                raise ValueError("ALLOWED_ORIGINS must include at least one origin")
            return origins
        return value


settings = Settings()
