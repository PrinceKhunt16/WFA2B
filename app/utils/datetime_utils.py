from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

UK_TZ = ZoneInfo("Europe/London")
UTC = timezone.utc


def parse_date(value: str, name: str = "date") -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"{name} must use YYYY-MM-DD format") from error


def parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="decision_cutoff must be an ISO-8601 timestamp",
        ) from error
    if parsed.tzinfo is None:
        raise HTTPException(status_code=422, detail="decision_cutoff must include a timezone")
    return parsed.astimezone(UTC)


def utc_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def delivery_date_bounds(delivery_date: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(delivery_date, time.min, tzinfo=UK_TZ)
    end_local = datetime.combine(delivery_date + timedelta(days=1), time.min, tzinfo=UK_TZ)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def date_range_days(start: date, end: date) -> int:
    return (end - start).days + 1
