from collections.abc import Iterator
from datetime import date, timedelta
from typing import Self, override

from pydantic import BaseModel


class DateRange(BaseModel):
    """Represents a range of dates with start and end."""

    start: date
    end: date

    @override
    def __str__(self) -> str:
        return f"{self.start.isoformat()}:{self.end.isoformat()}"

    @property
    def num_days(self) -> int:
        """Number of days in the range."""
        return (self.end - self.start).days + 1

    def split(self, max_days: int) -> Iterator[Self]:
        """Split the range into chunks of max_days.

        Yields:
            DateRange: Chunks of the original range.
        """
        for offset in range(0, self.num_days, max_days):
            chunk_start = self.start + timedelta(days=offset)
            chunk_end = min(chunk_start + timedelta(days=max_days - 1), self.end)
            yield self.__class__(start=chunk_start, end=chunk_end)
