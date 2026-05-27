from datetime import datetime, timedelta

from custom_components.epex_spot_sensor.intermittent_interval import (
    calc_intervals_for_intermittent,
)


class MockMarketPrice:
    def __init__(self, start_time, end_time, price):
        self.start_time = start_time
        self.end_time = end_time
        self.price = price


def test_exact_mode_backward_compatibility():
    """Test that exact mode (min_duration = duration) works as before."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Duration 2 hours, find cheapest (5 and 10)
    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=2),
        most_expensive=False,
        min_duration=timedelta(hours=2),  # exact
    )

    assert intervals is not None
    assert len(intervals) == 2

    prices = sorted([i.price for i in intervals])
    assert prices == [5.0, 10.0]

    total_time = sum([(i.end_time - i.start_time).total_seconds() for i in intervals])
    assert total_time == 7200  # 2 hours


def test_flexible_duration_with_price_threshold():
    """Test flexible duration stops at price threshold."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 5, 10, 20, 50 (expensive)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([5, 10, 20, 50])
    ]

    # Min 1 hour, max 4 hours, tolerance 50%
    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=4),  # max
        most_expensive=False,
        price_tolerance_percent=50.0,
        min_duration=timedelta(hours=1),
    )

    assert intervals is not None
    # Should select 5, 10, 20, but stop at 50 since 50 > 20 * 1.5 = 30
    # Reference after min: first slot is 5, then 10/5=2 > 1.5.
    # That means it should stop after the first slot.
    # But that can't be, because tolerance is 50%, 2>1.5 yes.
    # But in test, perhaps adjust.

    # Let's calculate: select first cheapest: 5, active=1h >=1h, reference=5
    # Next: 10, 10/5=2 >1.5, stop. So only 1 interval.

    # But to test stopping later, need better data.

    # Let's use prices 5, 6, 15, 50
    # 6/5=1.2 <1.5, 15/5=3>1.5, so select 5,6, stop at 15.

    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([5, 6, 15, 50])
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=4),
        most_expensive=False,
        price_tolerance_percent=50.0,
        min_duration=timedelta(hours=1),
    )

    assert intervals is not None
    assert len(intervals) == 2  # 5 and 6
    prices = sorted([i.price for i in intervals])
    assert prices == [5.0, 6.0]
    total_time = sum([(i.end_time - i.start_time).total_seconds() for i in intervals])
    assert total_time == 7200  # 2 hours


def test_min_duration_guarantee():
    """Test that min_duration is guaranteed, else None."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([50])  # only 1 hour, expensive
    ]

    # Min 2 hours, but only 1 available
    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=4),
        most_expensive=False,
        min_duration=timedelta(hours=2),
    )

    assert intervals is None


def test_max_duration_limit():
    """Test that max_duration is not exceeded."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=i), start + timedelta(hours=i + 1), 5)
        for i in range(10)  # plenty
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=10),
        duration=timedelta(hours=3),  # max 3
        most_expensive=False,
        min_duration=timedelta(hours=1),
    )

    assert intervals is not None
    total_time = sum([(i.end_time - i.start_time).total_seconds() for i in intervals])
    assert total_time <= 10800  # <=3 hours
    assert total_time >= 3600  # >=1 hour


def test_with_price_tolerance():
    """Test integration with price tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([5, 10, 20, 50])
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=4),
        most_expensive=False,
        price_tolerance_percent=100.0,  # allow up to 10
        min_duration=timedelta(hours=1),
    )

    # Reference 5, threshold 5*2=10, so filter to 5,10
    # Then select 5,10
    assert intervals is not None
    assert len(intervals) == 2
    prices = sorted([i.price for i in intervals])
    assert prices == [5.0, 10.0]


def test_edge_case_no_data():
    """Test with no market data."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    intervals = calc_intervals_for_intermittent(
        [],
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=2),
        min_duration=timedelta(hours=1),
    )
    assert intervals is None


def test_edge_case_insufficient_after_filter():
    """Test when filtering leaves insufficient slots within tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(start, start + timedelta(hours=1), 100),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 200),
    ]

    # Reference 100, threshold 100*1.1=110, 200>110, filter to [100]
    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=10.0,
        min_duration=timedelta(hours=2),  # Require 2h, but only 1h available
    )

    # Should return None because cannot meet min_duration
    assert intervals is None
