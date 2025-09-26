from collections.abc import Iterator
from datetime import date, timedelta
from typing import Self, override

from pydantic import BaseModel


class DateRange(BaseModel):
    start: date
    end: date

    @override
    def __str__(self) -> str:
        return f"{self.start.isoformat()}:{self.end.isoformat()}"

    @property
    def num_days(self) -> int:
        return (self.end - self.start).days + 1

    def split(self, max_days: int) -> Iterator[Self]:
        for offset in range(0, self.num_days, max_days):
            chunk_start = self.start + timedelta(days=offset)
            chunk_end = min(chunk_start + timedelta(days=max_days - 1), self.end)
            yield self.__class__(start=chunk_start, end=chunk_end)
