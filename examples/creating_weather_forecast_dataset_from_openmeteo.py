"""Example script demonstrating how to fetch weather data from Open-Meteo API.

This script shows how to use the OpenMeteoDataRepository to fetch both regular
and versioned weather forecast data for a specific location and time range.
The data is saved to parquet files for further analysis.
"""

import logging
from datetime import date
from pathlib import Path

from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude

from weather_data_fetchers.core import DateRange
from weather_data_fetchers.openmeteo import OpenMeteoDataRepository

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

output_dir = Path(__file__).resolve().parent

repository = OpenMeteoDataRepository()


data = repository.get_forecasts(
    coordinate=Coordinate(latitude=Latitude(52.090737), longitude=Longitude(5.12142)),
    date_range=DateRange(
        start=date.fromisoformat("2024-01-01"),
        end=date.fromisoformat("2025-01-08"),
    ),
)

logger.info("Fetched weather data:")
logger.info(data.data.head())

data.to_parquet(path=output_dir / "weather_data.parquet")


versioned_data = repository.get_versioned_forecasts(
    coordinate=Coordinate(latitude=Latitude(52.090737), longitude=Longitude(5.12142)),
    date_range=DateRange(
        start=date.fromisoformat("2024-01-01"),
        end=date.fromisoformat("2025-01-08"),
    ),
)

logger.info("Fetched versioned weather data:")
logger.info(versioned_data.data_parts[0].data.head())

versioned_data.to_parquet(path=output_dir / "weather_data_versioned.parquet")
