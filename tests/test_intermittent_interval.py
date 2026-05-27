from datetime import datetime, timedelta

from custom_components.epex_spot_sensor.intermittent_interval import (
    calc_intervals_for_intermittent,
)


class MockMarketPrice:
    def __init__(self, start_time, end_time, price):
        self.start_time = start_time
        self.end_time = end_time
        self.price = price


def test_calc_intervals_for_intermittent_simple():
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
    )

    assert intervals is not None
    assert len(intervals) == 2

    # The function sorts by price internally to pick, but returns a list.
    # The function sorts by price internally to pick, but returns a list.
    # Let's check the values.
    prices = sorted([i.price for i in intervals])
    assert prices == [5.0, 10.0]

    # Check total active time
    total_time = sum([(i.end_time - i.start_time).total_seconds() for i in intervals])
    assert total_time == 7200  # 2 hours


def test_calc_intervals_for_intermittent_most_expensive():
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Duration 1 hour, find most expensive (20)
    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=True,
    )

    assert intervals is not None
    assert len(intervals) == 1
    assert intervals[0].price == 20.0


def test_calc_intervals_for_intermittent_partial_slots():
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(
            start + timedelta(hours=i), start + timedelta(hours=i + 1), price
        )
        for i, price in enumerate([10, 5, 20, 10])
    ]

    # Duration 1.5 hours.
    # Cheapest is 1h at 5, and 0.5h at 10.
    # The logic sorts by price.
    # 1. 5.0 (01:00-02:00)
    # 2. 10.0 (00:00-01:00) OR 10.0 (03:00-04:00). Stable sort?
    # Let's see.

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1.5),
        most_expensive=False,
    )

    assert intervals is not None
    # Should have 2 intervals
    assert len(intervals) == 2

    # Calculate total price
    # 1 hour * 5 = 5
    # 0.5 hour * 10 = 5
    # Total price attribute on interval object is price * duration / hour
    # Interval 1: price=5, duration=1h -> val=5
    # Interval 2: price=10, duration=0.5h -> val=5

    total_val = sum([i.price for i in intervals])
    assert total_val == 10.0


def test_calc_intervals_for_intermittent_insufficient_data():
    start = datetime(2023, 10, 1, 0, 0, 0)
    marketdata = [
        MockMarketPrice(start + timedelta(hours=i), start + timedelta(hours=i + 1), 10)
        for i in range(2)
    ]

    intervals = calc_intervals_for_intermittent(
        marketdata,
        earliest_start=start,
        latest_end=start + timedelta(hours=4),
        duration=timedelta(hours=1),
        most_expensive=False,
    )

    assert intervals is None


def test_intermittent_vs_contiguous():
    """Test that intermittent sensor is always cheaper or equal to contiguous."""
    from custom_components.epex_spot_sensor.contiguous_interval import (
        calc_interval_for_contiguous,
    )

    start = datetime(2023, 10, 1, 0, 0, 0)
    # Scenario 1: Contiguous is optimal
    marketdata1 = [
        MockMarketPrice(start + timedelta(hours=i), start + timedelta(hours=i + 1), p)
        for i, p in enumerate([10, 10, 100])
    ]
    # Scenario 2: Intermittent is better (gap)
    marketdata2 = [
        MockMarketPrice(start + timedelta(hours=i), start + timedelta(hours=i + 1), p)
        for i, p in enumerate([10, 100, 10])
    ]

    for marketdata in [marketdata1, marketdata2]:
        earliest_start = start
        latest_end = start + timedelta(hours=3)
        duration = timedelta(hours=2)

        intermittent = calc_intervals_for_intermittent(
            marketdata, earliest_start, latest_end, duration
        )
        contiguous = calc_interval_for_contiguous(
            marketdata, earliest_start, latest_end, duration, most_expensive=False
        )

        assert intermittent is not None
        assert contiguous is not None

        intermittent_price = sum(i.price for i in intermittent)
        contiguous_price = contiguous["interval_price"]

        assert intermittent_price <= contiguous_price


def test_intermittent_connectivity_optimization():
    """Test that intermittent sensor prefers to connect intervals if possible."""
    # 00:00-01:00: 10
    # 01:00-02:00: 100
    # 02:00-03:00: 10
    # Duration 1.5h.
    # Picks 00:00 (1h) and 02:00 (0.5h).
    # 02:00 is isolated.
    # If we have:
    # 00:00-01:00: 10
    # 01:00-02:00: 20
    # 02:00-03:00: 10
    # Duration 2.5h.
    # Picks 00:00 (1h), 02:00 (1h). Total 2h.
    # Needs 0.5h from 01:00.
    # 01:00 is between 00:00 and 02:00.
    # Option A (Start): 01:00-01:30 connects to 00:00.
    # Result: 00:00-01:30, 02:00-03:00.
    # Option B (End): 01:30-02:00 connects to 02:00.
    # Result: 00:00-01:00, 01:30-03:00.
    # Both are equal score (1 connection).

    # Case: 23:00 (Rank 4), 00:00 (Rank 3), 01:00 (Rank 2), 02:00 (Rank 1).
    # Duration 3.5h.
    # Picks 02:00, 01:00, 00:00 (All full). [00:00-03:00].
    # Picks 23:00 (0.5h).
    # Option A (Start): 23:00-23:30. No connection.
    # Option B (End): 23:30-00:00. Connects to 00:00.
    # Should pick Option B.

    start = datetime(2025, 1, 1, 23, 0, 0)
    marketdata = [
        MockMarketPrice(start, start + timedelta(hours=1), 10.4),  # 23:00
        MockMarketPrice(
            start + timedelta(hours=1), start + timedelta(hours=2), 10.3
        ),  # 00:00
        MockMarketPrice(
            start + timedelta(hours=2), start + timedelta(hours=3), 10.2
        ),  # 01:00
        MockMarketPrice(
            start + timedelta(hours=3), start + timedelta(hours=4), 10.1
        ),  # 02:00
    ]

    earliest_start = start
    latest_end = start + timedelta(hours=4)
    duration = timedelta(hours=3.5)

    intervals = calc_intervals_for_intermittent(
        marketdata, earliest_start, latest_end, duration
    )

    assert intervals is not None

    # We expect 23:30-00:00, 00:00-01:00, 01:00-02:00, 02:00-03:00
    # Merged: 23:30-03:00.

    # Find the 23:00 interval
    int_23 = next(i for i in intervals if i.start_time.hour == 23)

    # It should end at 00:00 (next day)
    assert int_23.end_time == start + timedelta(hours=1)
    # It should start at 23:30
    assert int_23.start_time == start + timedelta(minutes=30)


def test_intermittent_perfect_slot_optimization():
    """Test that intermittent sensor finds the perfect contiguous slot."""
    # User feedback: "there should be a perfect slot on the 25th from 1am to 4am"
    # This implies 01:00-02:00, 02:00-03:00, 03:00-04:00 are the cheapest 3 hours.

    start = datetime(2025, 11, 25, 0, 0, 0)
    marketdata = [
        MockMarketPrice(start, start + timedelta(hours=1), 0.10344),  # 00:00
        MockMarketPrice(
            start + timedelta(hours=1), start + timedelta(hours=2), 0.10251
        ),  # 01:00 (Cheap)
        MockMarketPrice(
            start + timedelta(hours=2), start + timedelta(hours=3), 0.10162
        ),  # 02:00 (Cheap)
        MockMarketPrice(
            start + timedelta(hours=3), start + timedelta(hours=4), 0.10568
        ),  # 03:00 (Cheap)
        MockMarketPrice(
            start + timedelta(hours=4), start + timedelta(hours=5), 0.11483
        ),  # 04:00
    ]

    earliest_start = start
    latest_end = start + timedelta(hours=5)
    duration = timedelta(hours=3)

    intervals = calc_intervals_for_intermittent(
        marketdata, earliest_start, latest_end, duration
    )

    assert intervals is not None
    intervals.sort(key=lambda x: x.start_time)

    # The algorithm picks the 3 cheapest hours:
    # 02:00 (0.10162), 01:00 (0.10251), 00:00 (0.10344)
    # So it returns: 00:00, 01:00, 02:00 (which happens to be contiguous)
    start_times = [i.start_time.strftime("%H:%M") for i in intervals]
    assert start_times == ["00:00", "01:00", "02:00"]

    # Verify total price is optimal
    total_price = sum([i.price for i in intervals])
    expected_price = 0.10162 + 0.10251 + 0.10344
    assert abs(total_price - expected_price) < 0.0001


def test_intermittent_with_2h15m_duration():
    """Test that intermittent sensor handles 2:15:00 duration correctly."""
    # User requested: "add a test with a slot of 2:15:00"

    start = datetime(2025, 11, 25, 0, 0, 0)
    marketdata = [
        MockMarketPrice(start, start + timedelta(hours=1), 0.10344),  # 00:00
        MockMarketPrice(
            start + timedelta(hours=1), start + timedelta(hours=2), 0.10251
        ),  # 01:00 (Cheapest)
        MockMarketPrice(
            start + timedelta(hours=2), start + timedelta(hours=3), 0.10162
        ),  # 02:00 (2nd cheapest)
        MockMarketPrice(
            start + timedelta(hours=3), start + timedelta(hours=4), 0.10568
        ),  # 03:00 (3rd cheapest)
        MockMarketPrice(
            start + timedelta(hours=4), start + timedelta(hours=5), 0.11483
        ),  # 04:00
    ]

    earliest_start = start
    latest_end = start + timedelta(hours=5)
    duration = timedelta(hours=2, minutes=15)

    intervals = calc_intervals_for_intermittent(
        marketdata, earliest_start, latest_end, duration
    )

    assert intervals is not None
    intervals.sort(key=lambda x: x.start_time)

    # The algorithm picks the cheapest 2.25 hours:
    # 02:00 (1h @ 0.10162), 01:00 (1h @ 0.10251), 00:00 (0.25h @ 0.10344)
    # So it returns: 00:00-00:15, 01:00-02:00, 02:00-03:00
    assert len(intervals) == 3

    # Check the partial interval - should be at 00:00
    partial = next(
        (i for i in intervals if (i.end_time - i.start_time).total_seconds() < 3600),
        None,
    )
    assert partial is not None
    assert partial.start_time.hour == 0

    # With connectivity optimization, it should connect to 01:00
    # So it should be 00:45-01:00 (not 00:00-00:15)
    assert partial.end_time == start + timedelta(hours=1)
    assert partial.start_time == start + timedelta(minutes=45)

    # Total duration should be 2:15:00
    total_duration = sum(
        [(i.end_time - i.start_time).total_seconds() for i in intervals]
    )
    assert total_duration == timedelta(hours=2, minutes=15).total_seconds()
