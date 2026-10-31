from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_data_service
from app.schemas.accuracy import AccuracyResponse, ExcludedRecord
from app.services.accuracy_service import calculate_metrics, compare_records
from app.services.data_service import DataService
from app.utils.datetime_utils import date_range_days, delivery_date_bounds, parse_date

router = APIRouter(prefix="/api/v1", tags=["accuracy"])


@router.get("/accuracy", response_model=AccuracyResponse)
async def accuracy(
    start_date: str,
    end_date: str,
    decision_cutoff: str | None = Query(default=None),
    service: DataService = Depends(get_data_service),
) -> AccuracyResponse:
    start = parse_date(start_date, "start_date")
    end = parse_date(end_date, "end_date")
    _validate_range(start, end, service)
    all_rows = []
    exclusions = []
    for delivery_date in _dates(start, end):
        explicit_cutoff = None
        cutoff_policy = decision_cutoff
        if decision_cutoff and "T" in decision_cutoff:
            from app.utils.datetime_utils import parse_timestamp

            explicit_cutoff = parse_timestamp(decision_cutoff)
            cutoff_policy = None
        try:
            forecasts, forecast_exclusions, _ = await service.selected_forecasts_for_date(
                delivery_date,
                explicit_cutoff=explicit_cutoff,
                cutoff_policy=cutoff_policy,
            )
        except ValueError as error:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail=str(error)) from error
        actuals = await service.actuals_for_date(delivery_date)
        rows, matching_exclusions = compare_records(forecasts, actuals)
        all_rows.extend(rows)
        exclusions.extend(forecast_exclusions)
        exclusions.extend(matching_exclusions)

    metrics = calculate_metrics(all_rows)
    matched = metrics.matched_intervals
    range_start, _ = delivery_date_bounds(start)
    _, range_end = delivery_date_bounds(end)
    expected = int((range_end - range_start).total_seconds() // 3600)
    coverage = round((matched / expected) * 100, 2) if expected else None
    missing_forecasts = sum(row["status"] == "missing_forecast" for row in all_rows)
    missing_actuals = sum(row["status"] == "missing_actual" for row in all_rows)
    return AccuracyResponse(
        start_date=start,
        end_date=end,
        decision_cutoff_policy=decision_cutoff or service.settings.default_cutoff_policy,
        mae=metrics.mae,
        rmse=metrics.rmse,
        bias=metrics.bias,
        matched_intervals=matched,
        expected_interval_count=expected,
        coverage_percentage=coverage,
        missing_forecast_count=missing_forecasts,
        missing_actual_count=missing_actuals,
        excluded_records=[ExcludedRecord(**_clean_exclusion(item)) for item in exclusions[:100]],
        limitations=[
            "Expected intervals assume 24 hourly WINDFOR delivery intervals per UK calendar day.",
            "Elexon does not document exhaustive WINDFOR revision pagination for this stream.",
        ],
    )


def _dates(start: date, end: date):
    from datetime import timedelta

    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _validate_range(start: date, end: date, service: DataService) -> None:
    if end < start:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="end_date must not be before start_date")
    if date_range_days(start, end) > service.settings.max_date_range_days:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=f"date range cannot exceed {service.settings.max_date_range_days} days",
        )


def _clean_exclusion(item: dict) -> dict:
    delivery_time = item.get("delivery_time")
    return {"delivery_time": delivery_time, "reason": item.get("reason", "unknown")}
