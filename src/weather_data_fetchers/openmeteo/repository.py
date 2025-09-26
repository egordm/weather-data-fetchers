import logging
from collections.abc import Sequence
from datetime import timedelta
from logging import Logger
from typing import cast

import pandas as pd
from pydantic import BaseModel, Field, PrivateAttr
from pydantic_extra_types.coordinate import Coordinate

from weather_data_fetchers.core.utils.datetime import DateRange
from weather_data_fetchers.core.utils.pandas import resample_timeseries
from weather_data_fetchers.openmeteo.client import OpenMeteoDataClient, OpenMeteoRequestParams
from weather_data_fetchers.openmeteo.models import (
    DEFAULT_FEATURES,
    DEFAULT_FEATURES_VERSIONED,
    OpenMeteoFeature,
    OpenMeteoFeatureVersioned,
)


class OpenMeteoDataRepository(BaseModel):
    """Repository for transforming Open-Meteo data into structured datasets."""

    client: OpenMeteoDataClient = Field(default_factory=OpenMeteoDataClient)
    _logger: Logger = PrivateAttr(default_factory=lambda: logging.getLogger(__name__))

    def get_weather_data_versioned(
        self,
        coordinate: Coordinate,
        date_range: DateRange,
        variables: Sequence[OpenMeteoFeatureVersioned] = DEFAULT_FEATURES_VERSIONED,
        lead_time_days: Sequence[int] = [0, 1, 2, 3, 4, 5],
        sample_interval: timedelta = timedelta(minutes=15),
    ) -> pd.DataFrame:
        self._logger.info("Fetching versioned weather data for location (%s)", coordinate)
        suffixes = ["" if d == 0 else f"_previous_day{d}" for d in lead_time_days]
        request_variables = [f"{variable}{suffix}" for variable in variables for suffix in suffixes]

        data_raw = self.client.get_hourly_data(
            url=self.client.forecast_previous_runs_url,
            params=OpenMeteoRequestParams(
                coordinate=coordinate,
                variables=request_variables,
                date_range=date_range,
            ),
        )

        versioned_data = pd.concat(
            objs=[
                data_raw.filter(items=[f"{variable}{suffix}" for variable in variables])
                .set_axis(labels=variables, axis="columns")
                .pipe(resample_timeseries, sample_interval=sample_interval)
                .pipe(_versioned_timeseries_from_lead_time, lead_time=timedelta(days=d))
                for d, suffix in zip(lead_time_days, suffixes, strict=True)
            ],
            axis=0,
        )

        return versioned_data.dropna(how="all", subset=variables)

    def get_weather_data(
        self,
        coordinate: Coordinate,
        date_range: DateRange,
        variables: Sequence[OpenMeteoFeature] = DEFAULT_FEATURES,
        sample_interval: timedelta = timedelta(minutes=15),
    ) -> pd.DataFrame:
        self._logger.info("Fetching historical weather data for location (%s)", coordinate)
        raw_data = self.client.get_hourly_data(
            url=self.client.forecast_historical_url,
            params=OpenMeteoRequestParams(
                coordinate=coordinate,
                variables=variables,
                date_range=date_range,
            ),
        )
        return raw_data.pipe(resample_timeseries, sample_interval=sample_interval)


def _versioned_timeseries_from_lead_time(df: pd.DataFrame, lead_time: timedelta) -> pd.DataFrame:
    df = df.copy()
    df.insert(loc=0, column="timestamp", value=df.index)
    df.insert(loc=1, column="available_at", value=cast(pd.Series, df.index) - lead_time)
    return df.reset_index(drop=True)
