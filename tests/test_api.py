from datetime import datetime, timezone

import httpx
import pytest

from app.main import app


class FakeService:
    class Settings:
        default_cutoff_policy = "previous_day_11:00_europe_london"
        max_date_range_days = 31
        analysis_start_date = "2026-01-15"
        analysis_end_date = "2026-01-15"

    settings = Settings()

    async def actuals_for_date(self, _date):
        return [
            {"startTime": "2026-01-15T10:00:00Z", "generation": 100},
            {"startTime": "2026-01-15T10:30:00Z", "generation": 120},
        ]

    async def selected_forecasts_for_date(self, _date, explicit_cutoff=None, cutoff_policy=None):
        from app.services.forecast_selection import resolve_cutoff

        cutoff = resolve_cutoff(
            _date,
            cutoff_policy or self.settings.default_cutoff_policy,
            explicit_cutoff,
        )
        return [
            {
                "delivery_time": datetime(2026, 1, 15, 10, tzinfo=timezone.utc),
                "publication_time": datetime(2026, 1, 14, 10, tzinfo=timezone.utc),
                "generation": 110,
                "selection_status": "selected_latest_before_cutoff",
            }
        ], [], cutoff


@pytest.mark.asyncio
async def test_health_and_comparison_routes() -> None:
    app.state.data_service = FakeService()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        comparison = await client.get("/api/v1/comparison?date=2026-01-15")

    assert health.status_code == 200
    assert comparison.status_code == 200
    body = comparison.json()
    assert body["records"][0]["error"] == 0


@pytest.mark.asyncio
async def test_accuracy_rejects_reversed_range() -> None:
    app.state.data_service = FakeService()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/accuracy?start_date=2026-01-16&end_date=2026-01-15")
    assert response.status_code == 422
