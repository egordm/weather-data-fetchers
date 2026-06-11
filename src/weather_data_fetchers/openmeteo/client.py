import logging
from collections.abc import Sequence
from datetime import timedelta
from logging import Logger
from typing import Any, Literal, Self, cast, override

import pandas as pd
from pydantic import Field, PrivateAttr, SecretStr
from pydantic_extra_types.coordinate import Coordinate

from weather_data_fetchers.core.base_model import BaseModel
from weather_data_fetchers.core.exceptions import MissingExtraError
from weather_data_fetchers.core.rate_limiter import RateLimiter
from weather_data_fetchers.core.types import DateRange
from weather_data_fetchers.core.utils.itertools import not_none

try:
    import niquests
    import openmeteo_requests
    import requests_cache
    from retry_requests import retry  # pyright: ignore[reportUnknownVariableType]
except ImportError as e:
    raise MissingExtraError(extra="openmeteo") from e


class OpenMeteoUnits(BaseModel):
    """Unit selection for Open-Meteo responses. Defaults match the API defaults.

    Note the API default for wind speed is km/h, NOT m/s; physics consumers (e.g. turbine power
    curves) almost always want `wind_speed="ms"` and should say so explicitly.
    """

    wind_speed: Literal["kmh", "ms", "mph", "kn"] = "kmh"
    temperature: Literal["celsius", "fahrenheit"] = "celsius"
    precipitation: Literal["mm", "inch"] = "mm"

    def to_api_params(self) -> dict[str, str]:
        """Convert to API unit parameters.

        Returns:
            Dictionary of unit-selection API parameters.
        """
        return {
            "wind_speed_unit": self.wind_speed,
            "temperature_unit": self.temperature,
            "precipitation_unit": self.precipitation,
        }


class OpenMeteoRequestParams(BaseModel):
    """Parameters for Open-Meteo API requests."""

    coordinate: Coordinate
    variables: Sequence[str]
    date_range: DateRange
    units: OpenMeteoUnits = Field(default_factory=OpenMeteoUnits)

    def to_api_params(self) -> dict[str, Any]:
        """Convert to API parameters dict.

        Returns:
            Dictionary of API parameters.
        """
        return {
            "latitude": self.coordinate.latitude,
            "longitude": self.coordinate.longitude,
            "hourly": self.variables,
            "start_date": self.date_range.start.isoformat(),
            "end_date": self.date_range.end.isoformat(),
            **self.units.to_api_params(),
        }

    @property
    def request_size(self) -> float:
        """Estimated request size for rate limiting."""
        n_days = self.date_range.num_days
        n_vars = len(self.variables)
        n_locations, n_models = 1, 1
        return max(round((n_days / 14.0) * (n_vars / 10.0) * n_locations * n_models, 1), 1.0)

    def split(self, max_request_size: float) -> Sequence[Self]:
        """Split request into smaller chunks.

        Returns:
            List of split request parameters.
        """
        max_days_per_chunk = max(1, int(max_request_size * 140 / len(self.variables)))

        # model_copy keeps every other field (units, future additions) intact on the chunks.
        return [
            self.model_copy(update={"date_range": date_range})
            for date_range in self.date_range.split(max_days_per_chunk)
        ]


class OpenMeteoDataClient(BaseModel):
    """Client for fetching weather data from Open-Meteo API."""

    api_key: SecretStr | None = Field(
        default=None, description="API key for Open-Meteo. If not provided, free tier will be used."
    )

    forecast_previous_runs_url: str = Field(default="https://previous-runs-api.open-meteo.com/v1/forecast")
    forecast_historical_url: str = Field(default="https://historical-forecast-api.open-meteo.com/v1/forecast")
    measurement_archive_url: str = Field(default="https://archive-api.open-meteo.com/v1/archive")

    max_request_size: float = Field(
        default=10.0,
        description="Maximum size of a single request in call cost.",
    )

    _client: openmeteo_requests.Client = PrivateAttr()
    _minutely_rate_limiter: RateLimiter = PrivateAttr()
    _hourly_rate_limiter: RateLimiter = PrivateAttr()
    _logger: Logger = PrivateAttr(default_factory=lambda: logging.getLogger(__name__))

    @staticmethod
    def _custom_filter(response: requests_cache.Response) -> bool:
        return not response.text.startswith("Unexpected error")

    @override
    def model_post_init(self, context: Any) -> None:
        cache_session = requests_cache.CachedSession(
            cache_name=".cache", expire_after=3600, filter_fn=OpenMeteoDataClient._custom_filter
        )
        retry_session = cast(niquests.Session, retry(cache_session, retries=5, backoff_factor=0.2))
        self._client = openmeteo_requests.Client(session=retry_session)
        self._minutely_rate_limiter = RateLimiter(
            rate_limit=600.0 if self.api_key is None else 1_000_000.0,
            window=timedelta(minutes=1),
        )
        self._hourly_rate_limiter = RateLimiter(
            rate_limit=5000.0 if self.api_key is None else 1_000_000.0,
            window=timedelta(hours=1),
        )

    def get_hourly_data(
        self,
        url: str,
        params: OpenMeteoRequestParams,
    ) -> pd.DataFrame:
        """Fetch hourly weather data, splitting large requests if needed.

        Returns:
            DataFrame with weather data.
        """
        split_params = params.split(self.max_request_size)
        if len(split_params) == 1:
            return self._get_hourly_data_unsafe(url, split_params[0])

        self._logger.info(
            "Splitting request into %d chunks due to large size (call_count=%.2f > max=%.2f)",
            len(split_params),
            params.request_size,
            self.max_request_size,
        )

        dataframes: list[pd.DataFrame] = [self._get_hourly_data_unsafe(url, p) for p in split_params]

        combined_df: pd.DataFrame = pd.concat(dataframes, axis=0).sort_index()
        self._logger.info("Combined %d chunks into dataframe with %d rows", len(split_params), len(combined_df))
        return combined_df

    def _get_hourly_data_unsafe(
        self,
        url: str,
        params: OpenMeteoRequestParams,
    ) -> pd.DataFrame:
        # Wait if necessary for rate limiting
        self._minutely_rate_limiter.wait_if_needed(params.request_size)
        self._hourly_rate_limiter.wait_if_needed(params.request_size)

        self._logger.info(
            "Fetching weather data for %s with %d features",
            params.date_range,
            len(params.variables),
        )

        # Record the request for rate limiting
        self._minutely_rate_limiter.record_request(params.request_size)
        self._hourly_rate_limiter.record_request(params.request_size)

        # Make the API call
        responses = self._client.weather_api(  # pyright: ignore[reportUnknownVariableType]
            url=url,
            params={
                **params.to_api_params(),
                "apikey": self.api_key.get_secret_value() if self.api_key else None,
            },
        )

        if len(responses) != 1:
            raise RuntimeError("Expected a single response, got multiple.")

        hourly = responses[0].Hourly()
        if hourly is None:
            raise RuntimeError("No hourly data in response")

        self._logger.info("Successfully fetched and processed hourly data")
        return pd.DataFrame(
            data={
                str(variable): not_none(hourly.Variables(i)).ValuesAsNumpy()
                for i, variable in enumerate(params.variables)
            },
            index=pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
                name="timestamp",
            ),
        )
