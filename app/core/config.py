from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="WIND_", extra="ignore")

    app_name: str = "Wind Forecast Accuracy API"
    environment: str = "development"
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    elexon_max_retries: int = Field(default=2, ge=0, le=5)
    cache_ttl_seconds: int = Field(default=300, ge=0, le=86400)
    max_date_range_days: int = Field(default=31, ge=1, le=366)
    default_cutoff_policy: str = "previous_day_11:00_europe_london"
    analysis_start_date: str = "2026-01-01"
    analysis_end_date: str = "2026-01-31"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
