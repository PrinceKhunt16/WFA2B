from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_data_service
from app.schemas.accuracy import ComparisonPoint, ComparisonResponse
from app.schemas.common import SourceMetadata
from app.services.accuracy_service import compare_records
from app.services.data_service import DataService
from app.utils.datetime_utils import parse_date, parse_timestamp

router = APIRouter(prefix="/api/v1", tags=["comparison"])


@router.get("/comparison", response_model=ComparisonResponse)
async def comparison(
    date_value: str = Query(alias="date"),
    decision_cutoff: str | None = None,
    service: DataService = Depends(get_data_service),
) -> ComparisonResponse:
    delivery_date = parse_date(date_value)
    explicit_cutoff = (
        parse_timestamp(decision_cutoff)
        if decision_cutoff and "T" in decision_cutoff
        else None
    )
    cutoff_policy = decision_cutoff if decision_cutoff and "T" not in decision_cutoff else None
    try:
        forecasts, excluded, cutoff = await service.selected_forecasts_for_date(
            delivery_date,
            explicit_cutoff=explicit_cutoff,
            cutoff_policy=cutoff_policy,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    actuals = await service.actuals_for_date(delivery_date)
    records, matching_exclusions = compare_records(forecasts, actuals)
    all_exclusions = excluded + matching_exclusions
    return ComparisonResponse(
        date=delivery_date,
        decision_cutoff=cutoff.timestamp,
        cutoff_policy=cutoff.policy,
        records=[ComparisonPoint(**record) for record in records],
        source=SourceMetadata(
            dataset="FUELHH+WINDFOR",
            endpoint="/datasets/FUELHH/stream and /datasets/WINDFOR/stream",
            fetched_at=datetime.now(timezone.utc),
            notes=[
                "WINDFOR is hourly in observed responses; FUELHH half-hours are averaged per hour.",
                f"Excluded records considered: {len(all_exclusions)}.",
            ],
        ),
        limitations=[
            "Historical WINDFOR stream revision completeness is not documented by Elexon.",
            "Accuracy is coverage-qualified and does not fabricate missing values.",
        ],
    )
