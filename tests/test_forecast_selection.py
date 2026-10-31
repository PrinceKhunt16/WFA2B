from datetime import date, datetime, timezone

from app.services.forecast_selection import resolve_cutoff, select_latest_eligible_forecasts

UTC = timezone.utc


def record(start: str, publish: str, generation: int) -> dict:
    return {"startTime": start, "publishTime": publish, "generation": generation}


def test_selects_latest_revision_before_cutoff() -> None:
    forecasts = [
        record("2026-01-15T10:00:00Z", "2026-01-14T07:30:00Z", 100),
        record("2026-01-15T10:00:00Z", "2026-01-15T07:30:00Z", 120),
        record("2026-01-15T10:00:00Z", "2026-01-15T12:30:00Z", 140),
    ]
    cutoff = resolve_cutoff(date(2026, 1, 15), "previous_day_11:00_europe_london")

    selected, excluded = select_latest_eligible_forecasts(forecasts, date(2026, 1, 15), cutoff)

    assert selected[0]["generation"] == 100
    assert any(item["reason"] == "published_after_decision_cutoff" for item in excluded)


def test_explicit_cutoff_rejects_later_revision() -> None:
    cutoff = resolve_cutoff(
        date(2026, 1, 15),
        "previous_day_11:00_europe_london",
        datetime(2026, 1, 14, 12, tzinfo=UTC),
    )
    selected, _ = select_latest_eligible_forecasts(
        [record("2026-01-15T00:00:00Z", "2026-01-14T12:00:01Z", 10)],
        date(2026, 1, 15),
        cutoff,
    )
    assert selected == []


def test_dst_cutoff_uses_europe_london() -> None:
    cutoff = resolve_cutoff(date(2026, 7, 15), "previous_day_11:00_europe_london")
    assert cutoff.timestamp.isoformat() == "2026-07-14T10:00:00+00:00"
