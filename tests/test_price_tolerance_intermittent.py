"""Tests for price tolerance in intermittent mode."""

from datetime import datetime, timedelta

from custom_components.epex_spot_sensor.intermittent_interval import (
    calc_intervals_for_intermittent,
)


class MockMarketPrice:
    def __init__(self, start_time, end_time, price):
        self.start_time = start_time
        self.end_time = end_time
        self.price = price


def test_tolerance_zero_matches_current_behavior():
    """Test that tolerance=0 produces the same result as no tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10, 8])
    ]

    # Without tolerance
    intervals_no_tolerance = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
    )

    # With tolerance=0
    intervals_zero_tolerance = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=0.0,
    )

    # Should be identical
    assert intervals_no_tolerance is not None
    assert intervals_zero_tolerance is not None
    assert len(intervals_no_tolerance) == len(intervals_zero_tolerance)

    # Sort by start time for comparison
    intervals_no_tolerance.sort(key=lambda x: x.start_time)
    intervals_zero_tolerance.sort(key=lambda x: x.start_time)

    for i, (int1, int2) in enumerate(
        zip(intervals_no_tolerance, intervals_zero_tolerance)
    ):
        assert int1.start_time == int2.start_time
        assert int1.end_time == int2.end_time
        assert abs(int1.price - int2.price) < 0.001


def test_tolerance_10_percent_cheapest():
    """Test 10% tolerance prefers earlier slots within threshold."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 10.5, 11, 15, 20
    # Cheapest is 10 at hour 0
    # 10% threshold = 10 * 1.1 = 11
    # Acceptable: 10 (hour 0), 10.5 (hour 1), 11 (hour 2)
    # Should pick hours 0, 1 (earliest 2 hours)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 10.5),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 11),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 15),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 20),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 0 and 1 (earliest acceptable slots)
    assert intervals[0].start_time == start
    assert intervals[0].end_time == start + timedelta(hours=1)
    assert intervals[1].start_time == start + timedelta(hours=1)
    assert intervals[1].end_time == start + timedelta(hours=2)


def test_tolerance_20_percent_cheapest():
    """Test 20% tolerance with more acceptable slots."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 10.5, 11, 12, 15
    # Cheapest is 10 at hour 0
    # 20% threshold = 10 * 1.2 = 12
    # Acceptable: 10 (hour 0), 10.5 (hour 1), 11 (hour 2), 12 (hour 3)
    # Should pick hours 0, 1, 2 (earliest 3 hours)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 10.5),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 11),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 12),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 15),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=3),
        most_expensive=False,
        price_tolerance_percent=20.0,
    )

    assert intervals is not None
    assert len(intervals) == 3

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 0, 1, 2 (earliest acceptable slots)
    assert intervals[0].start_time == start
    assert intervals[1].start_time == start + timedelta(hours=1)
    assert intervals[2].start_time == start + timedelta(hours=2)


def test_tolerance_50_percent_cheapest():
    """Test 50% tolerance with many acceptable slots."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 12, 14, 15, 20
    # Cheapest is 10 at hour 0
    # 50% threshold = 10 * 1.5 = 15
    # Acceptable: 10 (hour 0), 12 (hour 1), 14 (hour 2), 15 (hour 3)
    # Should pick hours 0, 1 (earliest 2 hours)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 12),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 14),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 15),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 20),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=50.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 0 and 1 (earliest acceptable slots)
    assert intervals[0].start_time == start
    assert intervals[1].start_time == start + timedelta(hours=1)


def test_tolerance_prefer_earlier_when_multiple_options():
    """Test that earlier start times are preferred when using tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 15, 10, 10.5, 11, 20
    # Cheapest is 10 at hour 1
    # 10% threshold = 10 * 1.1 = 11
    # Acceptable: 10 (hour 1), 10.5 (hour 2), 11 (hour 3)
    # Should pick hours 1, 2 (earliest acceptable slots)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 15),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 10),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 10.5),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 11),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 20),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 1 and 2 (earliest acceptable slots)
    assert intervals[0].start_time == start + timedelta(hours=1)
    assert intervals[0].end_time == start + timedelta(hours=2)
    assert intervals[1].start_time == start + timedelta(hours=2)
    assert intervals[1].end_time == start + timedelta(hours=3)


def test_tolerance_fallback_when_insufficient_slots():
    """Test fallback to strict price ordering when tolerance too restrictive."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 15, 20, 25, 30
    # Cheapest is 10 at hour 0
    # 10% threshold = 10 * 1.1 = 11
    # Acceptable: only 10 (hour 0) - insufficient for 2 hours
    # Should fall back to strict ordering: hours 0, 1
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 15),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 20),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 25),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 30),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should fall back to strict price ordering: hours 0, 1
    assert intervals[0].start_time == start
    assert intervals[1].start_time == start + timedelta(hours=1)

    # Total duration should be satisfied
    total_duration = sum(
        [(i.end_time - i.start_time).total_seconds() for i in intervals]
    )
    assert total_duration == timedelta(hours=2).total_seconds()


def test_tolerance_100_percent_all_acceptable():
    """Test tolerance=100% makes all slots acceptable."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 15, 20, 25, 30
    # Cheapest is 10 at hour 0
    # 100% threshold = 10 * 2 = 20
    # Acceptable: 10 (hour 0), 15 (hour 1), 20 (hour 2)
    # Should pick hours 0, 1, 2 (earliest acceptable slots)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 15),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 20),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 25),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 30),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=3),
        most_expensive=False,
        price_tolerance_percent=100.0,
    )

    assert intervals is not None
    assert len(intervals) == 3

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 0, 1, 2 (earliest acceptable slots)
    assert intervals[0].start_time == start
    assert intervals[1].start_time == start + timedelta(hours=1)
    assert intervals[2].start_time == start + timedelta(hours=2)


def test_tolerance_partial_slot_handling():
    """Test partial slot handling with tolerance."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 10.5, 11, 15, 20
    # Cheapest is 10 at hour 0
    # 10% threshold = 10 * 1.1 = 11
    # Acceptable: 10 (hour 0), 10.5 (hour 1), 11 (hour 2)
    # Duration 1.5 hours - should pick hours 0 (full) and 1 (partial 0.5h)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 10.5),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 11),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 15),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 20),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=1.5),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hour 0 (full) and hour 1 (partial)
    assert intervals[0].start_time == start
    assert intervals[0].end_time == start + timedelta(hours=1)

    # Second interval should be partial (0.5h) and connected to first
    assert intervals[1].start_time == start + timedelta(hours=1)
    assert intervals[1].end_time == start + timedelta(hours=1.5)

    # Total duration should be 1.5 hours
    total_duration = sum(
        [(i.end_time - i.start_time).total_seconds() for i in intervals]
    )
    assert total_duration == timedelta(hours=1.5).total_seconds()


def test_tolerance_most_expensive_mode():
    """Test tolerance in most_expensive mode."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 15, 18, 20, 25
    # Most expensive is 25 at hour 4
    # 10% threshold = 25 * 0.9 = 22.5
    # Acceptable: 25 (hour 4) - only one slot
    # Should fall back to strict ordering and pick hours 4, 3
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 15),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 18),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 20),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 25),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=True,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should fall back to strict price ordering (most expensive first)
    # Hours 4 and 3
    assert intervals[0].start_time == start + timedelta(hours=3)
    assert intervals[1].start_time == start + timedelta(hours=4)


def test_tolerance_most_expensive_with_acceptable_slots():
    """Test tolerance in most_expensive mode with sufficient acceptable slots."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 15, 18, 19, 20
    # Most expensive is 20 at hour 4
    # 10% threshold = 20 * 0.9 = 18
    # Acceptable: 20 (hour 4), 19 (hour 3), 18 (hour 2)
    # Should pick hours 2, 3 (earliest acceptable slots)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 15),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 18),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 19),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 20),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=True,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 2 and 3 (earliest acceptable slots)
    assert intervals[0].start_time == start + timedelta(hours=2)
    assert intervals[0].end_time == start + timedelta(hours=3)
    assert intervals[1].start_time == start + timedelta(hours=3)
    assert intervals[1].end_time == start + timedelta(hours=4)


def test_tolerance_with_gaps_in_acceptable_slots():
    """Test tolerance when acceptable slots are not contiguous."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 15, 10.5, 20, 11
    # Cheapest is 10 at hour 0
    # 10% threshold = 10 * 1.1 = 11
    # Acceptable: 10 (hour 0), 10.5 (hour 2), 11 (hour 4)
    # Should pick hours 0, 2 (earliest acceptable slots, skipping hour 1)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 15),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 10.5),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 20),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 11),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=2),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 2

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should be hours 0 and 2 (earliest acceptable slots)
    assert intervals[0].start_time == start
    assert intervals[0].end_time == start + timedelta(hours=1)
    assert intervals[1].start_time == start + timedelta(hours=2)
    assert intervals[1].end_time == start + timedelta(hours=3)


def test_tolerance_edge_case_exact_threshold():
    """Test behavior when a slot is exactly at the threshold."""
    start = datetime(2023, 10, 1, 0, 0, 0)
    # Prices: 10, 10.5, 11, 15, 20
    # Cheapest is 10 at hour 0
    # 10% threshold = 10 * 1.1 = 11 (exact)
    # Acceptable: 10 (hour 0), 10.5 (hour 1), 11 (hour 2)
    # Should pick hours 0, 1, 2 (earliest acceptable slots)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=0), start + timedelta(hours=1), 10),
        MockMarketPrice(start + timedelta(hours=1), start + timedelta(hours=2), 10.5),
        MockMarketPrice(start + timedelta(hours=2), start + timedelta(hours=3), 11),
        MockMarketPrice(start + timedelta(hours=3), start + timedelta(hours=4), 15),
        MockMarketPrice(start + timedelta(hours=4), start + timedelta(hours=5), 20),
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=5),
        duration=timedelta(hours=3),
        most_expensive=False,
        price_tolerance_percent=10.0,
    )

    assert intervals is not None
    assert len(intervals) == 3

    # Sort by start time
    intervals.sort(key=lambda x: x.start_time)

    # Should include all three acceptable slots
    assert intervals[0].start_time == start
    assert intervals[1].start_time == start + timedelta(hours=1)
    assert intervals[2].start_time == start + timedelta(hours=2)
