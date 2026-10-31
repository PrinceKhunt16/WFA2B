from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_data_service
from app.schemas.common import SourceMetadata
from app.schemas.forecast import ActualPoint, ActualResponse
from app.services.data_service import DataService
from app.utils.datetime_utils import parse_date

router = APIRouter(prefix="/api/v1", tags=["actuals"])


@router.get("/actuals", response_model=ActualResponse)
async def actuals(
    date_value: str = Query(alias="date"),
    service: DataService = Depends(get_data_service),
) -> ActualResponse:
    delivery_date = parse_date(date_value)
    records = await service.actuals_for_date(delivery_date)
    source = SourceMetadata(
        dataset="FUELHH",
        endpoint="/datasets/FUELHH/stream",
        fetched_at=datetime.now(timezone.utc),
        notes=["FUELHH reports half-hourly average generation in MW."],
    )
    points = []
    for record in records:
        try:
            points.append(
                ActualPoint(
                    delivery_time=record["startTime"],
                    delivery_date=delivery_date,
                    actual_generation=float(record["generation"]),
                    source=source,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    points.sort(key=lambda point: point.delivery_time)
    return ActualResponse(date=delivery_date, records=points)
