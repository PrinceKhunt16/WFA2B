from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_data_service
from app.schemas.common import SourceMetadata
from app.schemas.forecast import ForecastPoint, ForecastResponse
from app.services.data_service import DataService
from app.utils.datetime_utils import parse_date, parse_timestamp

router = APIRouter(prefix="/api/v1", tags=["forecasts"])


@router.get("/forecasts", response_model=ForecastResponse)
async def forecasts(
    date_value: str = Query(alias="date"),
    decision_cutoff: str | None = None,
    service: DataService = Depends(get_data_service),
) -> ForecastResponse:
    delivery_date = parse_date(date_value)
    explicit_cutoff = None
    cutoff_policy = None
    if decision_cutoff:
        if "T" in decision_cutoff:
            explicit_cutoff = parse_timestamp(decision_cutoff)
        else:
            cutoff_policy = decision_cutoff

    try:
        selected, _, cutoff = await service.selected_forecasts_for_date(
            delivery_date,
            explicit_cutoff=explicit_cutoff,
            cutoff_policy=cutoff_policy,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    source = _source("WINDFOR")
    records = [
        ForecastPoint(
            delivery_time=item["delivery_time"],
            delivery_date=delivery_date,
            forecast_generation=item["generation"],
            forecast_publication_time=item["publication_time"],
            selected=True,
            selection_status=item["selection_status"],
            source=source,
        )
        for item in selected
    ]
    return ForecastResponse(
        date=delivery_date,
        decision_cutoff=cutoff.timestamp,
        cutoff_policy=cutoff.policy,
        records=records,
        coverage_note=(
            "Selected from WINDFOR stream records returned for the bounded query window. "
            "Elexon does not document pagination or exhaustive historical revision coverage."
        ),
    )


def _source(dataset: str) -> SourceMetadata:
    from datetime import datetime, timezone

    return SourceMetadata(
        dataset=dataset,
        endpoint=f"/datasets/{dataset}/stream",
        fetched_at=datetime.now(timezone.utc),
        notes=["Values are reported in MW based on the observed official response schema."],
    )
