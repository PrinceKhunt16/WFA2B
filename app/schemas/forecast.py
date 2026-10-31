from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import SourceMetadata


class ForecastPoint(BaseModel):
    delivery_time: datetime
    delivery_date: date
    forecast_generation: float
    forecast_publication_time: datetime
    selected: bool
    selection_status: str
    units: str = "MW"
    source: SourceMetadata


class ActualPoint(BaseModel):
    delivery_time: datetime
    delivery_date: date
    actual_generation: float
    units: str = "MW"
    source: SourceMetadata


class ForecastResponse(BaseModel):
    date: date
    decision_cutoff: datetime
    cutoff_policy: str
    records: list[ForecastPoint]
    coverage_note: str


class ActualResponse(BaseModel):
    date: date
    records: list[ActualPoint]
