"""Tests for price tolerance in contiguous mode."""

from datetime import UTC, datetime, timedelta

from custom_components.epex_spot_sensor.contiguous_interval import (
    calc_interval_for_contiguous,
)


class MockMarketPrice:
    """Mock market price for testing."""

    def __init__(self, start_time, end_time, price):
        self.start_time = start_time
        self.end_time = end_time
        self.price = price


def test_tolerance_zero_matches_current_behavior():
    """Test that tolerance=0 returns exact same result as current behavior."""
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
        price_tolerance_percent=0.0,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=1)
    assert result["end"] == start + timedelta(hours=2)
    assert result["interval_price"] == 5
    assert result["price_per_hour"] == 5


def test_tolerance_10_percent_cheapest():
    """Test 10% tolerance in cheapest mode."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 20, 10 (cheapest), 11 (within 10%), 15, 12 (within 10%)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([20, 10, 11, 15, 12])
    ]

    # Cheapest is 10 at index 1 (01:00-02:00)
    # 10% tolerance: accept up to 10 * 1.10 = 11
    # Acceptable intervals: index 1 (10), index 2 (11)
    # Should prefer earliest: index 1
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=1)
    assert result["interval_price"] == 10


def test_tolerance_prefers_earlier_start():
    """Test that when multiple intervals are within tolerance, earlier is preferred."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 11, 12, 10 (cheapest), 11, 12
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([11, 12, 10, 11, 12])
    ]

    # Cheapest is 10 at index 2 (02:00-03:00)
    # 20% tolerance: accept up to 10 * 1.20 = 12
    # Acceptable: index 0 (11), 1 (12), 2 (10), 3 (11), 4 (12)
    # Should prefer earliest: index 0
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=20.0,
    )

    assert result is not None
    assert result["start"] == start  # index 0 is earliest
    assert result["interval_price"] == 11


def test_tolerance_20_percent():
    """Test 20% tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 25, 15, 20 (cheapest), 18, 30
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([25, 15, 20, 18, 30])
    ]

    # Cheapest is 15 at index 1 (01:00-02:00)
    # 20% tolerance: accept up to 15 * 1.20 = 18
    # Acceptable intervals: index 1 (15), index 3 (18)
    # Should prefer earliest: index 1
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=20.0,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=1)
    assert result["interval_price"] == 15


def test_tolerance_50_percent():
    """Test 50% tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 30, 20 (cheapest), 25, 35, 28
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([30, 20, 25, 35, 28])
    ]

    # Cheapest is 20 at index 1 (01:00-02:00)
    # 50% tolerance: accept up to 20 * 1.50 = 30
    # Acceptable intervals: index 0 (30), index 1 (20), index 2 (25), index 4 (28)
    # Should prefer earliest: index 0
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=50.0,
    )

    assert result is not None
    assert result["start"] == start  # index 0 is earliest
    assert result["interval_price"] == 30


def test_tolerance_100_percent_all_acceptable():
    """Test 100% tolerance - all intervals acceptable, select earliest."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 30, 20 (cheapest), 25, 35, 28
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([30, 20, 25, 35, 28])
    ]

    # Cheapest is 20 at index 1 (01:00-02:00)
    # 100% tolerance: accept up to 20 * 2.00 = 40
    # All intervals acceptable
    # Should prefer earliest: index 0
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=100.0,
    )

    assert result is not None
    assert result["start"] == start  # index 0 is earliest
    assert result["interval_price"] == 30


def test_tolerance_no_intervals_within_threshold_fallback(caplog):
    """Test fallback when no intervals within threshold.

    Note: This test creates a scenario where the tolerance is actually impossible
    to satisfy. In the current implementation, since we calculate tolerance based
    on the optimal price within the search window, the optimal interval itself
    will always be within tolerance. Therefore, this test verifies that the
    algorithm correctly handles the case where tolerance=0 would be the effective
    behavior.

    To truly test the fallback warning, we would need a different scenario that's
    not currently possible with the implementation (which is by design - the optimal
    is always acceptable).
    """
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 30, 10 (cheapest), 25, 35, 28
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([30, 10, 25, 35, 28])
    ]

    # Within window [2,5), cheapest is 25 at index 2
    # With 1% tolerance: accept up to 25 * 1.01 = 25.25
    # The optimal (25) is always within its own tolerance
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start + timedelta(hours=2),
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=1.0,
    )

    # Should return the optimal within the constrained window
    assert result is not None
    assert result["start"] == start + timedelta(hours=2)
    assert result["interval_price"] == 25
    # Note: With current implementation, fallback warning won't trigger because
    # the optimal interval is always within tolerance. This is the expected behavior
    # per the specification - fallback only occurs in edge cases (e.g., when
    # start_times is empty, which is handled by returning None earlier).


def test_tolerance_most_expensive_mode():
    """Test price tolerance in most expensive mode."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 20, 30 (most expensive), 28, 15, 29
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([20, 30, 28, 15, 29])
    ]

    # Most expensive is 30 at index 1 (01:00-02:00)
    # 10% tolerance: accept down to 30 * 0.90 = 27
    # Acceptable intervals: index 1 (30), index 2 (28), index 4 (29)
    # Should prefer earliest: index 1
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=True,
        price_tolerance_percent=10.0,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=1)
    assert result["interval_price"] == 30


def test_tolerance_most_expensive_prefers_earlier():
    """Test most expensive mode prefers earlier start when multiple within tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 28, 29, 30 (most expensive), 28, 29
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([28, 29, 30, 28, 29])
    ]

    # Most expensive is 30 at index 2 (02:00-03:00)
    # 10% tolerance: accept down to 30 * 0.90 = 27
    # All intervals acceptable (all >= 27)
    # Should prefer earliest: index 0
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1),
        most_expensive=True,
        price_tolerance_percent=10.0,
    )

    assert result is not None
    assert result["start"] == start  # index 0 is earliest
    assert result["interval_price"] == 28


def test_tolerance_multi_hour_interval():
    """Test price tolerance with multi-hour contiguous interval."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices for 6 hours: 10, 15, 20, 12, 18, 25
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 15, 20, 12, 18, 25])
    ]

    # Find cheapest 3-hour contiguous block
    # Possible blocks:
    # 00-03: 10+15+20 = 45 (avg 15/hr)
    # 01-04: 15+20+12 = 47 (avg 15.67/hr)
    # 02-05: 20+12+18 = 50 (avg 16.67/hr)
    # 03-06: 12+18+25 = 55 (avg 18.33/hr)
    # Cheapest is 00-03 at 15/hr

    # 20% tolerance: accept up to 15 * 1.20 = 18/hr
    # Acceptable blocks: 00-03 (15/hr), 01-04 (15.67/hr), 02-05 (16.67/hr)
    # Should prefer earliest: 00-03
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=6),
        duration=timedelta(hours=3),
        most_expensive=False,
        price_tolerance_percent=20.0,
    )

    assert result is not None
    assert result["start"] == start
    assert result["end"] == start + timedelta(hours=3)
    assert result["interval_price"] == 45
    assert result["price_per_hour"] == 15


def test_tolerance_with_earliest_start_constraint():
    """Test tolerance respects earliest_start constraint."""
    start = datetime(2023, 10, 1, 0, 0, 0, tzinfo=UTC)
    # Prices: 10, 15, 20, 12, 18, 25
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 15, 20, 12, 18, 25])
    ]

    # Cheapest in window [2,6) is 12 at index 3 (03:00-04:00)
    # 50% tolerance: accept up to 12 * 1.50 = 18
    # Acceptable in window: index 3 (12), index 4 (18)
    # Should prefer earliest: index 3
    result = calc_interval_for_contiguous(
        marketdata,
        earliest_start=start + timedelta(hours=2),  # Start from 02:00
        latest_end=start + timedelta(hours=6),
        duration=timedelta(hours=1),
        most_expensive=False,
        price_tolerance_percent=50.0,
    )

    assert result is not None
    assert result["start"] == start + timedelta(hours=3)
    assert result["interval_price"] == 12
