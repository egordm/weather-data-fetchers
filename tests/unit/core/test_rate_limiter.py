from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from weather_data_fetchers.core.rate_limiter import RateLimiter

RATE_LIMIT = 10.0
WINDOW_MINUTES = 1
REQUEST_SIZE_1 = 1.0
REQUEST_SIZE_2 = 2.0
REQUEST_SIZE_3 = 3.0
REQUEST_SIZE_5 = 5.0
REQUEST_SIZE_8 = 8.0
REQUEST_SIZE_15 = 15.0
REQUEST_SIZE_2_5 = 2.5


@pytest.fixture
def rate_limiter() -> RateLimiter:
    """Fixture providing a RateLimiter instance with default settings.

    Returns:
        A RateLimiter instance with rate_limit=10.0 and window=1 minute.
    """
    return RateLimiter(rate_limit=RATE_LIMIT, window=timedelta(minutes=WINDOW_MINUTES))


class TestRateLimiter:
    def test_cleanup_requests_removes_old_requests(self, rate_limiter: RateLimiter):
        # Arrange
        now = datetime.fromisoformat("2025-09-27T12:00:00+00:00")
        rate_limiter.record_request(REQUEST_SIZE_1, now - timedelta(minutes=2))  # Old
        rate_limiter.record_request(REQUEST_SIZE_2, now - timedelta(seconds=30))  # Within window

        # Act
        rate_limiter.cleanup_requests(now)

        # Assert
        assert len(rate_limiter._requests) == 1
        assert rate_limiter._requests[0][1] == REQUEST_SIZE_2

    @patch("time.sleep")
    def test_wait_if_needed_no_wait_when_under_limit(self, mock_sleep: MagicMock, rate_limiter: RateLimiter):
        # Arrange
        now = datetime.fromisoformat("2025-09-27T12:00:00+00:00")
        rate_limiter.record_request(REQUEST_SIZE_5, now - timedelta(seconds=30))  # Total 5.0 < 10.0

        # Act
        rate_limiter.wait_if_needed(REQUEST_SIZE_3, now)

        # Assert
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_wait_if_needed_waits_when_over_limit(self, mock_sleep: MagicMock, rate_limiter: RateLimiter):
        # Arrange
        now = datetime.fromisoformat("2025-09-27T12:00:00+00:00")
        oldest = now - timedelta(seconds=30)
        rate_limiter.record_request(REQUEST_SIZE_8, oldest)  # Total 8.0 + 3.0 > 10.0
        wait_time = (oldest + rate_limiter.window - now).total_seconds()

        # Act
        rate_limiter.wait_if_needed(REQUEST_SIZE_3, now)

        # Assert
        mock_sleep.assert_called_once_with(wait_time)

    @patch("time.sleep")
    def test_wait_if_needed_no_requests_allows_any_size(self, mock_sleep: MagicMock, rate_limiter: RateLimiter):
        # Arrange
        now = datetime.fromisoformat("2025-09-27T12:00:00+00:00")
        # No requests recorded

        # Act
        rate_limiter.wait_if_needed(REQUEST_SIZE_15, now)  # Even if > rate_limit

        # Assert
        mock_sleep.assert_not_called()