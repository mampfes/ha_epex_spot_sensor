from datetime import UTC, datetime, timedelta

from custom_components.epex_spot_sensor.contiguous_interval import (
    calc_interval_for_contiguous,
)


class MockMarketPrice:
    def __init__(self, start_time, end_time, price):
        self.start_time = start_time
        self.end_time = end_time
        self.price = price


def test_flexible_duration_exact_mode():
    """Test flexible duration with min_duration = max_duration (exact mode)."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Duration 1 hour, min_duration=1 hour (exact mode)
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=False,
        min_duration=timedelta(hours=1),
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=1)
    assert result["end"] == start + timedelta(hours=2)
    assert result["interval_price"] == 5


def test_flexible_duration_range():
    """Test flexible duration with min < max."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10, 15, 25])
    ]

    # Min 1 hour, max 2 hours, find cheapest
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=6),
        duration=timedelta(hours=2),  # max_duration
        most_expensive=False,
        min_duration=timedelta(hours=1),
    )

    assert result is not None
    # Should find the cheapest per-hour 1-hour interval at 01:00-02:00.
    assert result["start"] == start + timedelta(hours=1)
    assert result["end"] == start + timedelta(hours=2)
    assert result["interval_price"] == 5


def test_flexible_duration_with_tolerance():
    """Test flexible duration with price tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10, 15])
    ]

    # Min 1 hour, max 2 hours, with 10% tolerance
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=10.0,
        min_duration=timedelta(hours=1),
    )

    assert result is not None
    # Should still pick the cheapest, but with tolerance logic applied
    assert result["interval_price"] == 5


def test_flexible_duration_no_valid_intervals():
    """Test flexible duration with no valid intervals in range."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5])
    ]

    # Min 3 hours, max 4 hours, but only 2 hours of data
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=2),
        duration=timedelta(hours=4),
        most_expensive=False,
        min_duration=timedelta(hours=3),
    )

    assert result is None


def test_flexible_duration_most_expensive():
    """Test flexible duration finding most expensive."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Min 1 hour, max 2 hours, most expensive
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=2),
        most_expensive=True,
        min_duration=timedelta(hours=1),
    )

    assert result is not None
    # Should pick the 1-hour at 02:00-03:00 with 20
    assert result["start"] == start + timedelta(hours=2)
    assert result["end"] == start + timedelta(hours=3)
    assert result["interval_price"] == 20
