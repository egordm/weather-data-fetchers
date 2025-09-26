from datetime import timedelta

import pandas as pd


def resample_timeseries(df: pd.DataFrame, sample_interval: timedelta) -> pd.DataFrame:
    """Resample a timeseries DataFrame to a specified interval using linear interpolation.

    Args:
        df: The DataFrame to resample.
        sample_interval: The target sampling interval.

    Returns:
        The resampled DataFrame.
    """
    return df.resample(sample_interval).interpolate(method="linear")  # pyright: ignore[reportUnknownMemberType]
