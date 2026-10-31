from datetime import date, datetime, timezone

import httpx
import pytest

from app.clients.elexon_client import ElexonClient, ElexonError


@pytest.mark.asyncio
async def test_client_builds_documented_query_parameters(settings) -> None:
    requests_seen = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return httpx.Response(200, json=[{"startTime": "2026-01-15T00:00:00Z", "generation": 1}])

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = ElexonClient(http_client, settings)
    await client.fetch_actuals(date(2026, 1, 15))
    await client.fetch_forecasts(
        datetime(2026, 1, 14, tzinfo=timezone.utc),
        datetime(2026, 1, 16, tzinfo=timezone.utc),
    )

    assert requests_seen[0].url.params["settlementDateFrom"] == "2026-01-15"
    assert requests_seen[0].url.params["fuelType"] == "WIND"
    assert requests_seen[1].url.params["publishDateTimeFrom"].endswith("Z")
    await client.close()


@pytest.mark.asyncio
async def test_client_raises_on_invalid_json(settings) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    client = ElexonClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings)
    with pytest.raises(ElexonError, match="invalid JSON"):
        await client.fetch_actuals(date(2026, 1, 15))
    await client.close()


@pytest.mark.asyncio
async def test_client_raises_on_upstream_failure(settings) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream failed")

    client = ElexonClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)), settings)
    with pytest.raises(ElexonError) as error:
        await client.fetch_actuals(date(2026, 1, 15))
    assert error.value.status_code == 500
    await client.close()
