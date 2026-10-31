from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from app.utils.datetime_utils import UTC

UK_TZ = ZoneInfo("Europe/London")


@dataclass(frozen=True)
class Cutoff:
    timestamp: datetime
    policy: str


def resolve_cutoff(
    delivery_date: date,
    policy: str,
    explicit_cutoff: datetime | None = None,
) -> Cutoff:
    if explicit_cutoff is not None:
        return Cutoff(explicit_cutoff.astimezone(UTC), "explicit_timestamp")

    if policy == "previous_day_11:00_europe_london":
        local_cutoff = datetime.combine(
            delivery_date - timedelta(days=1),
            time(hour=11),
            tzinfo=UK_TZ,
        )
        return Cutoff(local_cutoff.astimezone(UTC), policy)

    if policy == "previous_day_12:00_europe_london":
        local_cutoff = datetime.combine(
            delivery_date - timedelta(days=1),
            time(hour=12),
            tzinfo=UK_TZ,
        )
        return Cutoff(local_cutoff.astimezone(UTC), policy)

    raise ValueError(f"Unsupported cutoff policy: {policy}")


def select_latest_eligible_forecasts(
    forecast_records: list[dict],
    delivery_date: date,
    cutoff: Cutoff,
) -> tuple[list[dict], list[dict]]:
    """Select one latest pre-cutoff forecast per delivery interval.

    WINDFOR is documented as hourly, while FUELHH is half-hourly. This function
    only selects forecast records; comparison code is responsible for matching
    actuals at the forecast delivery granularity.
    """
    normalized: list[dict] = []
    excluded: list[dict] = []

    for record in forecast_records:
        try:
            delivery_time = _parse_timestamp(record["startTime"])
            publication_time = _parse_timestamp(record["publishTime"])
            generation = float(record["generation"])
        except (KeyError, TypeError, ValueError):
            excluded.append({"record": record, "reason": "invalid_forecast_record"})
            continue

        if delivery_time.astimezone(UK_TZ).date() != delivery_date:
            continue
        if publication_time > cutoff.timestamp:
            excluded.append(
                {
                    "record": record,
                    "reason": "published_after_decision_cutoff",
                }
            )
            continue
        normalized.append(
            {
                "delivery_time": delivery_time,
                "publication_time": publication_time,
                "generation": generation,
                "record": record,
            }
        )

    selected: list[dict] = []
    for delivery_time, group in _group_by_delivery_time(normalized).items():
        # If duplicate rows share a publication timestamp, choose the last
        # deterministic row after sorting the raw record representation.
        winner = sorted(
            group,
            key=lambda item: (item["publication_time"], repr(item["record"])),
        )[-1]
        winner["selection_status"] = "selected_latest_before_cutoff"
        selected.append(winner)

    selected.sort(key=lambda item: item["delivery_time"])
    return selected, excluded


def _group_by_delivery_time(records: list[dict]) -> dict[datetime, list[dict]]:
    groups: dict[datetime, list[dict]] = {}
    for record in records:
        groups.setdefault(record["delivery_time"], []).append(record)
    return groups


def _parse_timestamp(value: str | datetime) -> datetime:
    parsed = pd.Timestamp(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    return parsed.to_pydatetime().astimezone(UTC)
