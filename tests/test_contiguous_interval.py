from datetime import UTC, datetime, timedelta

from custom_components.epex_spot_sensor.contiguous_interval import (
    calc_interval_for_contiguous,
)


class MockMarketPrice:
    def __init__(self, start_time, end_time, price):
        self.start_time = start_time
        self.end_time = end_time
        self.price = price


def test_calc_interval_for_contiguous_simple():
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Duration 1 hour, find cheapest (5 at index 1, 01:00-02:00)
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=False,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=1)
    assert result["end"] == start + timedelta(hours=2)
    assert result["interval_price"] == 5


def test_calc_interval_for_contiguous_most_expensive():
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Duration 1 hour, find most expensive (20 at index 2, 02:00-03:00)
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=True,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=2)
    assert result["end"] == start + timedelta(hours=3)
    assert result["interval_price"] == 20


def test_calc_interval_for_contiguous_insufficient_data():
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=i), start + timedelta(hours=i + 1), 10)
        for i in range(2)
    ]

    # Latest end is 4 hours later, but we only have 2 hours of data
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=False,
    )

    assert result is None


def test_calc_interval_for_contiguous_crossing_midnight():
    # Data from 22:00 to 02:00 next day
    start = datetime(2023, 10, 1, 22, 0, 0, tzinfo=UTC)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 10, 5, 10])  # 22-23, 23-00, 00-01 (cheap), 01-02
    ]

    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=False,
    )

    assert result is not None
    # Cheapest is 00:00-01:00 (index 2)
    assert result["start"] == start + timedelta(hours=2)
    assert result["end"] == start + timedelta(hours=3)
    assert result["interval_price"] == 5


def test_calc_interval_price_missing_data():
    """Test _calc_interval_price with missing market data (repro for PR #45)."""
    from custom_components.epex_spot_sensor.contiguous_interval import (
        _calc_interval_price,
    )

    # Scenario: Request calculation for a duration where part of the data is missing.
    # We have data for 12:00-13:00.
    # We request calculation for 12:00-14:00.
    # 13:00-14:00 is missing.

    start_time = datetime(2023, 10, 10, 12, 0, tzinfo=UTC)
    marketdata = [MockMarketPrice(start_time, start_time + timedelta(hours=1), 10.0)]

    duration = timedelta(hours=2)

    # This should return None for missing data, but currently raises AttributeError
    # because _calc_interval_price accesses .end_time on a missing market price.
    price = _calc_interval_price(marketdata, start_time, duration)
    assert price is None
