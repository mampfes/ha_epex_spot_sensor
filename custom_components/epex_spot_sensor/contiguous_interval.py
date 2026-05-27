import logging
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

SECONDS_PER_HOUR = 60 * 60


def _find_market_price(marketdata, dt: datetime):
    for mp in marketdata:
        if dt >= mp.start_time and dt < mp.end_time:
            return mp

    return None


def _calc_interval_price(marketdata, start_time: datetime, duration: timedelta):
    """Calculate price for given start time and duration."""
    total_price = 0
    stop_time = start_time + duration

    while start_time < stop_time:
        mp = _find_market_price(marketdata, start_time)

        if mp is None:
            return None

        if mp.end_time > stop_time:
            active_duration_in_this_segment = stop_time - start_time
        else:
            active_duration_in_this_segment = mp.end_time - start_time

        total_price += (
            mp.price
            * active_duration_in_this_segment.total_seconds()
            / SECONDS_PER_HOUR
        )

        start_time = mp.end_time

    return total_price


def _calc_start_times(
    marketdata, earliest_start: datetime, latest_end: datetime, duration: timedelta
):
    """Calculate list of meaningful start times."""
    start_times = set()
    start_time = earliest_start

    # add earliest possible start (if duration matches)
    if earliest_start + duration <= latest_end:
        start_times.add(earliest_start)

    for md in marketdata:
        # add start times for market data segment start
        if md.start_time >= earliest_start and md.start_time + duration <= latest_end:
            start_times.add(md.start_time)

        # add start times for market data segment end
        start_time = md.end_time - duration
        if md.end_time <= latest_end and earliest_start <= start_time:
            start_times.add(start_time)

    # add latest possible start (if duration matches)
    start_time = latest_end - duration
    if earliest_start <= start_time:
        start_times.add(start_time)

    return sorted(start_times)


def _calc_flexible_start_times(
    marketdata,
    earliest_start: datetime,
    latest_end: datetime,
    min_duration: timedelta,
    max_duration: timedelta,
):
    """Calculate meaningful start times for flexible duration range."""
    start_times = set()

    # Candidates for min_duration
    min_candidates = _calc_start_times(
        marketdata, earliest_start, latest_end, min_duration
    )

    # Candidates for max_duration
    max_candidates = _calc_start_times(
        marketdata, earliest_start, latest_end, max_duration
    )

    # Combine
    start_times.update(min_candidates)
    start_times.update(max_candidates)

    return sorted(list(set(start_times)))


def _find_extreme_price_interval(
    marketdata,
    start_times,
    duration: timedelta,
    most_expensive: bool = False,
    price_tolerance_percent: float = 0.0,
):
    """Find the lowest/highest price for all given start times.

        The argument cmp is a lambda which is used to differentiate between
    lowest and highest price.

    Args:
        marketdata: Market price data
        start_times: List of candidate start times
        duration: Duration of the interval
        most_expensive: If True, find most expensive; otherwise find cheapest
        price_tolerance_percent: Price tolerance percentage (0.0 = no tolerance)

    Returns:
        Dict with start, end, interval_price, price_per_hour, or None if no
        valid interval
    """
    interval_price: float | None = None
    interval_start_time: timedelta | None = None

    if most_expensive:

        def cmp(a, b):
            return a > b

    else:

        def cmp(a, b):
            return a < b

    # Find optimal interval (cheapest or most expensive)
    for start in start_times:
        price = _calc_interval_price(marketdata, start, duration)
        if price is None:
            continue

        if interval_price is None or (
            price > interval_price if most_expensive else price < interval_price
        ):
            interval_price = price
            interval_start_time = start

    if interval_start_time is None or interval_price is None:
        return None

    # Build optimal result
    optimal_result = {
        "start": interval_start_time,
        "end": interval_start_time + duration,
        "interval_price": interval_price,
        "price_per_hour": interval_price * SECONDS_PER_HOUR / duration.total_seconds(),
    }

    # If tolerance is 0, return optimal (backward compatibility)
    if price_tolerance_percent == 0.0:
        return optimal_result

    # Calculate price threshold based on optimal price
    price_per_hour = optimal_result["price_per_hour"]

    if most_expensive:
        # For most expensive mode, threshold is lower bound
        threshold = price_per_hour * (1 - price_tolerance_percent / 100)

        def within_threshold(price):
            return price >= threshold

    else:
        # For cheapest mode, threshold is upper bound
        threshold = price_per_hour * (1 + price_tolerance_percent / 100)

        def within_threshold(price):
            return price <= threshold

    # Find all intervals within threshold
    candidates = []
    for start in start_times:
        price = _calc_interval_price(marketdata, start, duration)
        if price is None:
            continue

        price_per_hour_candidate = price * SECONDS_PER_HOUR / duration.total_seconds()

        if within_threshold(price_per_hour_candidate):
            candidates.append(
                {
                    "start": start,
                    "end": start + duration,
                    "interval_price": price,
                    "price_per_hour": price_per_hour_candidate,
                }
            )

    # If no candidates within threshold, fall back to optimal
    if len(candidates) == 0:
        _LOGGER.warning(
            "No intervals found within price tolerance (%.1f%%), "
            "using optimal interval",
            price_tolerance_percent,
        )
        return optimal_result

    # Prefer earliest start time (Decision 3)
    candidates.sort(key=lambda x: x["start"])
    return candidates[0]


def _find_flexible_extreme_price_interval(
    marketdata,
    start_times,
    min_duration: timedelta,
    max_duration: timedelta,
    latest_end: datetime,
    most_expensive: bool = False,
    price_tolerance_percent: float = 0.0,
):
    """Find best interval within flexible duration range."""

    best_result = None
    best_price_per_hour = None

    # Define test durations
    test_durations = [
        min_duration,
        max_duration,
    ]
    # Add midpoint if significantly different
    if max_duration > min_duration * 2:
        midpoint = min_duration + (max_duration - min_duration) / 2
        test_durations.append(midpoint)

    # For each candidate start time
    for start in start_times:
        for test_duration in test_durations:
            if start + test_duration > latest_end:
                continue

            price = _calc_interval_price(marketdata, start, test_duration)
            if price is None:
                continue

            price_per_hour = price * SECONDS_PER_HOUR / test_duration.total_seconds()

            # Check if this is better than current best
            is_better = best_price_per_hour is None or (
                price_per_hour < best_price_per_hour
                if not most_expensive
                else price_per_hour > best_price_per_hour
            )

            if is_better:
                best_result = {
                    "start": start,
                    "end": start + test_duration,
                    "interval_price": price,
                    "price_per_hour": price_per_hour,
                }
                best_price_per_hour = price_per_hour

    if best_result is None:
        return None

    # Apply price tolerance logic (reuse existing logic)
    if price_tolerance_percent > 0.0:
        # Find all intervals within tolerance of best_result
        optimal_price_per_hour = best_result["price_per_hour"]

        if most_expensive:
            # For most expensive mode, threshold is lower bound
            threshold = optimal_price_per_hour * (1 - price_tolerance_percent / 100)

            def within_threshold(price):
                return price >= threshold

        else:
            # For cheapest mode, threshold is upper bound
            threshold = optimal_price_per_hour * (1 + price_tolerance_percent / 100)

            def within_threshold(price):
                return price <= threshold

        # Find all intervals within threshold
        candidates = []
        for start in start_times:
            for test_duration in test_durations:
                if start + test_duration > latest_end:
                    continue
                price = _calc_interval_price(marketdata, start, test_duration)
                if price is None:
                    continue
                price_per_hour_candidate = (
                    price * SECONDS_PER_HOUR / test_duration.total_seconds()
                )
                if within_threshold(price_per_hour_candidate):
                    candidates.append(
                        {
                            "start": start,
                            "end": start + test_duration,
                            "interval_price": price,
                            "price_per_hour": price_per_hour_candidate,
                        }
                    )

        # If no candidates within threshold, fall back to optimal
        if len(candidates) == 0:
            _LOGGER.warning(
                "No intervals found within price tolerance (%.1f%%), "
                "using optimal interval",
                price_tolerance_percent,
            )
            return best_result

    else:
        # No tolerance, use the best result
        candidates = [best_result]

    # Prefer earliest start time
    candidates.sort(key=lambda x: x["start"])
    return candidates[0]


def calc_interval_for_contiguous(
    marketdata,
    earliest_start: datetime,
    latest_end: datetime,
    duration: timedelta,
    most_expensive: bool = True,
    price_tolerance_percent: float = 0.0,
    min_duration: timedelta | None = None,
):
    if len(marketdata) == 0:
        return None

    if marketdata[-1].end_time < latest_end:
        return None

    # Handle flexible duration
    if min_duration is None:
        min_duration = duration  # exact mode
    max_duration = duration

    if min_duration > max_duration:
        raise ValueError("min_duration cannot be greater than max_duration")

    if min_duration == max_duration:
        # Exact mode
        start_times = _calc_start_times(
            marketdata,
            earliest_start=earliest_start,
            latest_end=latest_end,
            duration=duration,
        )
        start_times = sorted(list(set(start_times)))
        return _find_extreme_price_interval(
            marketdata, start_times, duration, most_expensive, price_tolerance_percent
        )
    else:
        # Flexible mode
        start_times = _calc_flexible_start_times(
            marketdata,
            earliest_start=earliest_start,
            latest_end=latest_end,
            min_duration=min_duration,
            max_duration=max_duration,
        )
        return _find_flexible_extreme_price_interval(
            marketdata,
            start_times,
            min_duration,
            max_duration,
            latest_end,
            most_expensive,
            price_tolerance_percent,
        )
