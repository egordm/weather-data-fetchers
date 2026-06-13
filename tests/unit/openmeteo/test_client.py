from datetime import date

import pytest
from pydantic_extra_types.coordinate import Coordinate

from weather_data_fetchers.core.types import DateRange
from weather_data_fetchers.openmeteo.client import (
    OpenMeteoDataClient,
    OpenMeteoRequestParams,
    OpenMeteoUnits,
)


@pytest.fixture
def params() -> OpenMeteoRequestParams:
    return OpenMeteoRequestParams(
        coordinate=Coordinate(52.0, 5.0),  # pyright: ignore[reportCallIssue]
        variables=["temperature_2m", "wind_speed_10m"],
        date_range=DateRange(start=date(2023, 1, 1), end=date(2023, 12, 31)),
        units=OpenMeteoUnits(wind_speed="ms"),
    )


class TestOpenMeteoUnits:
    def test_defaults_match_api_defaults(self) -> None:
        assert OpenMeteoUnits().to_api_params() == {
            "wind_speed_unit": "kmh",
            "temperature_unit": "celsius",
            "precipitation_unit": "mm",
        }

    def test_request_params_carry_units_into_api_params(self, params: OpenMeteoRequestParams) -> None:
        api_params = params.to_api_params()

        assert api_params["wind_speed_unit"] == "ms"
        assert api_params["temperature_unit"] == "celsius"

    def test_split_propagates_units_to_every_chunk(self, params: OpenMeteoRequestParams) -> None:
        chunks = params.split(max_request_size=2.0)

        assert len(chunks) > 1
        assert all(chunk.units.wind_speed == "ms" for chunk in chunks)
        assert all(chunk.variables == params.variables for chunk in chunks)


class TestCacheExpiry:
    def test_historical_endpoints_cache_forever_and_recent_keeps_a_ttl(self) -> None:
        """Archive + historical-forecast responses never expire (immutable data; a TTL only
        forces rate-limited re-fetches), while the previous-runs endpoint (recent model runs,
        still appended to) falls through to the default 1h TTL.
        """
        from requests_cache import NEVER_EXPIRE
        from requests_cache.policy.expiration import get_url_expiration

        client = OpenMeteoDataClient()
        patterns = client._urls_expire_after()  # pyright: ignore[reportPrivateUsage]

        archive_url = f"{client.measurement_archive_url}?latitude=52.0&start_date=2023-01-01"
        historical_url = f"{client.forecast_historical_url}?latitude=52.0&start_date=2023-01-01"
        recent_url = f"{client.forecast_previous_runs_url}?latitude=52.0"

        assert get_url_expiration(archive_url, patterns) == NEVER_EXPIRE
        assert get_url_expiration(historical_url, patterns) == NEVER_EXPIRE
        assert get_url_expiration(recent_url, patterns) is None  # default TTL applies
