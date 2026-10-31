import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ElexonError(Exception):
    def __init__(self, message: str, endpoint: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code


@dataclass
class CacheEntry:
    expires_at: float
    payload: Any


class ElexonClient:
    """Async client for the documented Elexon BMRS API endpoints."""

    def __init__(self, http_client: httpx.AsyncClient, settings: Settings) -> None:
        self.http_client = http_client
        self.settings = settings
        self._cache: dict[str, CacheEntry] = {}

    async def close(self) -> None:
        await self.http_client.aclose()

    async def _get_json(self, path: str, params: dict[str, str]) -> Any:
        url = f"{self.settings.elexon_base_url.rstrip('/')}/{path.lstrip('/') }"
        cache_key = f"{url}?{httpx.QueryParams(params)}"
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > time.monotonic():
            return cached.payload

        transient_statuses = {429, 500, 502, 503, 504}
        attempts = self.settings.elexon_max_retries + 1
        last_error: ElexonError | None = None

        for attempt in range(attempts):
            try:
                response = await self.http_client.get(
                    url,
                    params=params,
                    timeout=self.settings.elexon_timeout_seconds,
                )
            except httpx.TimeoutException:
                last_error = ElexonError(
                    "Elexon request timed out",
                    endpoint=path,
                    status_code=504,
                )
                logger.warning("Elexon timeout endpoint=%s attempt=%s", path, attempt + 1)
            except httpx.HTTPError as error:
                last_error = ElexonError(
                    f"Elexon request failed: {error}",
                    endpoint=path,
                )
                logger.warning("Elexon HTTP error endpoint=%s attempt=%s", path, attempt + 1)
            else:
                if response.status_code in transient_statuses:
                    retry_after = response.headers.get("Retry-After")
                    last_error = ElexonError(
                        f"Elexon returned HTTP {response.status_code}",
                        endpoint=path,
                        status_code=response.status_code,
                    )
                    logger.warning(
                        "Elexon transient response endpoint=%s status=%s attempt=%s",
                        path,
                        response.status_code,
                        attempt + 1,
                    )
                    if attempt + 1 < attempts:
                        await asyncio.sleep(_retry_delay(attempt, retry_after))
                        continue
                elif response.is_error:
                    detail = response.text[:500]
                    raise ElexonError(
                        f"Elexon returned HTTP {response.status_code}: {detail}",
                        endpoint=path,
                        status_code=response.status_code,
                    )
                else:
                    try:
                        payload = response.json()
                    except ValueError as error:
                        raise ElexonError(
                            "Elexon returned invalid JSON",
                            endpoint=path,
                            status_code=response.status_code,
                        ) from error
                    if not isinstance(payload, (list, dict)):
                        raise ElexonError(
                            "Elexon returned an unexpected JSON structure",
                            endpoint=path,
                            status_code=response.status_code,
                        )
                    if self.settings.cache_ttl_seconds:
                        self._cache[cache_key] = CacheEntry(
                            time.monotonic() + self.settings.cache_ttl_seconds,
                            payload,
                        )
                    return payload

            if attempt + 1 < attempts:
                await asyncio.sleep(_retry_delay(attempt, None))

        raise last_error or ElexonError("Elexon request failed", endpoint=path)

    async def fetch_actuals(self, delivery_date: date) -> list[dict[str, Any]]:
        """Fetch FUELHH wind actuals by settlement date."""
        payload = await self._get_json(
            "/datasets/FUELHH/stream",
            {
                "settlementDateFrom": delivery_date.isoformat(),
                "settlementDateTo": delivery_date.isoformat(),
                "fuelType": "WIND",
                "format": "json",
            },
        )
        return _records(payload)

    async def fetch_forecasts(
        self,
        publication_from: datetime,
        publication_to: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch WINDFOR revisions by documented publication-time filters."""
        payload = await self._get_json(
            "/datasets/WINDFOR/stream",
            {
                "publishDateTimeFrom": _iso_utc(publication_from),
                "publishDateTimeTo": _iso_utc(publication_to),
                "format": "json",
            },
        )
        return _records(payload)


def _retry_delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 5.0)
        except ValueError:
            pass
    return min(0.25 * (2**attempt), 2.0)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _records(payload: list[Any] | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        values = payload
    else:
        values = payload.get("data", [])
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise ElexonError("Elexon returned no record list", endpoint="datasets")
    return values
