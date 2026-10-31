from datetime import timezone

import pytest

from app.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        elexon_max_retries=0,
        cache_ttl_seconds=0,
        max_date_range_days=31,
    )


@pytest.fixture
def utc() -> timezone:
    return timezone.utc
