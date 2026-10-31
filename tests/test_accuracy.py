import math

from app.services.accuracy_service import calculate_metrics, compare_records


def test_metrics_use_forecast_minus_actual() -> None:
    metrics = calculate_metrics(
        [
            {"forecast_generation": 110, "actual_generation": 100},
            {"forecast_generation": 80, "actual_generation": 100},
        ]
    )
    assert metrics.mae == 15
    assert math.isclose(metrics.rmse, math.sqrt(250))
    assert metrics.bias == -5
    assert metrics.matched_intervals == 2


def test_compare_averages_half_hourly_actuals() -> None:
    forecasts = [
        {
            "delivery_time": "2026-01-15T10:00:00+00:00",
            "generation": 110,
            "publication_time": "2026-01-14T10:00:00+00:00",
        }
    ]
    actuals = [
        {"startTime": "2026-01-15T10:00:00Z", "generation": 100},
        {"startTime": "2026-01-15T10:30:00Z", "generation": 120},
    ]
    rows, exclusions = compare_records(forecasts, actuals)
    assert not exclusions
    assert rows[0]["actual_generation"] == 110
    assert rows[0]["error"] == 0


def test_missing_forecast_is_not_zero() -> None:
    rows, exclusions = compare_records(
        [],
        [{"startTime": "2026-01-15T10:00:00Z", "generation": 50}],
    )
    assert rows[0]["forecast_generation"] is None
    assert rows[0]["status"] == "missing_forecast"
    assert exclusions[0]["reason"] == "no_eligible_forecasts"
