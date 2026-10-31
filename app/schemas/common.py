from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: str
    endpoint: str
    fetched_at: datetime
    units: str = "MW"
    notes: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: str
    message: str
    upstream_status: int | None = None
    details: dict[str, Any] | None = None
