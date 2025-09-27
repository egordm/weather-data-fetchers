# Weather Data Fetchers

A Python package for fetching weather data from various APIs, providing a unified interface for accessing historical measurements, forecasts, and versioned forecast data.

## Installation

Install the package from PyPI:

```bash
pip install weather-data-fetchers
```

## Supported Data Sources

The package currently supports fetching weather data from:

- **Open-Meteo API**: A free weather API providing historical measurements, forecast data, and versioned forecasts with lead times.

## Usage

### Open-Meteo Data Repository

The `OpenMeteoDataRepository` class provides methods to fetch different types of weather data from the Open-Meteo API.

#### Basic Forecast Data

```python
from datetime import date
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude

from weather_data_fetchers.core import DateRange
from weather_data_fetchers.openmeteo import OpenMeteoDataRepository

repository = OpenMeteoDataRepository()

# Fetch forecast data for a location and date range
data = repository.get_forecasts(
    coordinate=Coordinate(latitude=Latitude(52.090737), longitude=Longitude(5.12142)),
    date_range=DateRange(
        start=date.fromisoformat("2024-01-01"),
        end=date.fromisoformat("2025-01-08"),
    ),
)

# The data is returned as a pandas DataFrame
print(data.head())
```

#### Versioned Forecast Data

Versioned forecasts include data from previous model runs, allowing you to see how forecasts evolved over time:

```python
# Fetch versioned forecast data with lead times
versioned_data = repository.get_versioned_forecasts(
    coordinate=Coordinate(latitude=Latitude(52.090737), longitude=Longitude(5.12142)),
    date_range=DateRange(
        start=date.fromisoformat("2024-01-01"),
        end=date.fromisoformat("2025-01-08"),
    ),
)

print(versioned_data.head())
```

#### Historical Measurements

```python
# Fetch historical measurement data
measurements = repository.get_measurements(
    coordinate=Coordinate(latitude=Latitude(52.090737), longitude=Longitude(5.12142)),
    date_range=DateRange(
        start=date.fromisoformat("2024-01-01"),
        end=date.fromisoformat("2025-01-08"),
    ),
)

print(measurements.head())
```

### Data Processing

All methods return pandas DataFrames with standardized column names and datetime indexing. The data can be easily saved to various formats:

```python
# Save to Parquet
data.to_parquet("weather_data.parquet")

# Save to CSV
data.to_csv("weather_data.csv")
```

### Features

- **Rate Limit Conscious**: Built-in rate limiting and request caching to prevent API quota exhaustion
- **Flexible Data Processing**: Automatic resampling and standardization of time series data
- **Multiple Data Types**: Supports historical measurements, forecasts, and versioned forecasts with lead times

For a complete working example, see [`examples/creating_weather_forecast_dataset_from_openmeteo.py`](examples/creating_weather_forecast_dataset_from_openmeteo.py).

## Development

This package uses modern Python development tools:

- **uv** for dependency management
- **pytest** for testing
- **ruff** for linting and formatting
- **pyright** for type checking
