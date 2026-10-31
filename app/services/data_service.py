from datetime import date, datetime, timedelta
from typing import Any

from app.clients.elexon_client import ElexonClient
from app.core.config import Settings
from app.services.forecast_selection import Cutoff, resolve_cutoff, select_latest_eligible_forecasts
from app.utils.datetime_utils import delivery_date_bounds


class DataService:
    """Coordinate API retrieval and forecast selection."""

    def __init__(self, client: ElexonClient, settings: Settings) -> None:
        self.client = client
        self.settings = settings

    async def actuals_for_date(self, delivery_date: date) -> list[dict[str, Any]]:
        return await self.client.fetch_actuals(delivery_date)

    async def selected_forecasts_for_date(
        self,
        delivery_date: date,
        explicit_cutoff: datetime | None = None,
        cutoff_policy: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Cutoff]:
        cutoff = resolve_cutoff(
            delivery_date,
            cutoff_policy or self.settings.default_cutoff_policy,
            explicit_cutoff,
        )
        start, end = delivery_date_bounds(delivery_date)
        # Query a bounded window around the delivery date. The result is still
        # filtered by delivery interval and publication cutoff locally.
        forecast_records = await self.client.fetch_forecasts(
            start - timedelta(days=3),
            end + timedelta(days=1),
        )
        selected, excluded = select_latest_eligible_forecasts(
            forecast_records,
            delivery_date,
            cutoff,
        )
        return selected, excluded, cutoff

    async def raw_forecasts_for_date(self, delivery_date: date) -> list[dict[str, Any]]:
        start, end = delivery_date_bounds(delivery_date)
        return await self.client.fetch_forecasts(start - timedelta(days=3), end + timedelta(days=1))
