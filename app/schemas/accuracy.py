from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import SourceMetadata


class ComparisonPoint(BaseModel):
    delivery_time: datetime
    forecast_generation: float | None = None
    actual_generation: float | None = None
    error: float | None = None
    absolute_error: float | None = None
    squared_error: float | None = None
    forecast_publication_time: datetime | None = None
    cutoff_satisfied: bool
    status: str
    reason: str | None = None
    units: str = "MW"


class ComparisonResponse(BaseModel):
    date: date
    decision_cutoff: datetime
    cutoff_policy: str
    records: list[ComparisonPoint]
    source: SourceMetadata
    limitations: list[str]


class ExcludedRecord(BaseModel):
    delivery_time: datetime | None = None
    reason: str
    count: int = 1


class AccuracyResponse(BaseModel):
    start_date: date
    end_date: date
    decision_cutoff_policy: str
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    matched_intervals: int
    expected_interval_count: int | None
    coverage_percentage: float | None
    missing_forecast_count: int
    missing_actual_count: int
    excluded_records: list[ExcludedRecord]
    limitations: list[str]


class SummaryResponse(BaseModel):
    evaluation_date_range: str
    metrics: AccuracyResponse
    evaluated_intervals: int
    status: str
