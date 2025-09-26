import logging
import time
from datetime import UTC, datetime, timedelta

from pydantic import Field, PrivateAttr

from weather_data_fetchers.core.base_model import BaseModel


class RateLimiter(BaseModel):
    rate_limit: float = Field(default=..., description="Rate limit in requests per window.")
    window: timedelta = Field(default=timedelta(minutes=1), description="Window for rate limiting.")

    _requests: list[tuple[datetime, float]] = PrivateAttr(default_factory=lambda: [])
    _logger: logging.Logger = PrivateAttr(default_factory=lambda: logging.getLogger(__name__))

    def _cleanup_requests(self) -> None:
        now = datetime.now(UTC)
        cutoff = now - self.window
        self._requests = [(ts, size) for ts, size in self._requests if ts > cutoff]

    def wait_if_needed(self, request_size: float) -> None:
        now = datetime.now(UTC)
        # Clean up old requests
        self._cleanup_requests()

        # Calculate current total size in window
        current_total = sum(size for _, size in self._requests)

        # Check if we can make the request now
        if current_total + request_size <= self.rate_limit or not self._requests:
            return

        # Need to wait
        oldest = min(ts for ts, _ in self._requests)
        wait_time = (oldest + self.window - now).total_seconds()
        if wait_time > 0:
            self._logger.warning("Rate limit exceeded, waiting for %d seconds", wait_time)
            time.sleep(wait_time)
            self._cleanup_requests()

    def record_request(self, request_size: float) -> None:
        now = datetime.now(UTC)
        self._requests.append((now, request_size))
