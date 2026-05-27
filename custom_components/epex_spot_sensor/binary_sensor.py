"""Support for monitoring if a sensor value is below/above a threshold."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, CONF_ENTITY_ID
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
import homeassistant.util.dt as dt_util

from .const import (
    ATTR_DATA,
    ATTR_END_TIME,
    ATTR_INTERVAL_ENABLED,
    ATTR_MEAN_PRICE_PER_KWH,
    ATTR_PRICE_PER_KWH,
    ATTR_RANK,
    ATTR_START_TIME,
    ATTR_VISUALIZATION_DATA,
    CONF_DURATION,
    CONF_DURATION_ENTITY_ID,
    CONF_DURATION_MODE,
    CONF_EARLIEST_START_TIME,
    CONF_INTERVAL_MODE,
    CONF_INTERVAL_START_TIME,
    CONF_LATEST_END_TIME,
    CONF_MIN_DURATION,
    CONF_PRICE_MODE,
    CONF_PRICE_TOLERANCE,
    DEFAULT_PRICE_TOLERANCE,
    DurationModes,
    IntervalModes,
    PriceModes,
)
from .contiguous_interval import calc_interval_for_contiguous
from .intermittent_interval import (
    calc_intervals_for_intermittent,
    is_now_in_intervals,
)
from .util import get_marketdata_from_sensor_attrs

_LOGGER = logging.getLogger(__name__)

DURATION_UOM_MAP = {
    "d": "days",
    "days": "days",
    "h": "hours",
    "hours": "hours",
    "min": "minutes",
    "minutes": "minutes",
    "s": "seconds",
    "sec": "seconds",
    "seconds": "seconds",
    "ms": "milliseconds",
    "msec": "milliseconds",
    "milliseconds": "milliseconds",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize threshold config entry."""
    registry = er.async_get(hass)
    entity_id = er.async_validate_entity_id(
        registry, config_entry.options[CONF_ENTITY_ID]
    )

    source_entity = registry.async_get(entity_id)
    dev_reg = dr.async_get(hass)
    # Resolve source entity device
    if (
        (source_entity is not None)
        and (source_entity.device_id is not None)
        and (
            (
                device := dev_reg.async_get(
                    device_id=source_entity.device_id,
                )
            )
            is not None
        )
    ):
        device_info = DeviceInfo(
            identifiers=device.identifiers,
            connections=device.connections,
        )
    else:
        device_info = None

    async_add_entities(
        [
            BinarySensor(
                hass,
                unique_id=config_entry.entry_id,
                name=config_entry.title,
                entity_id=entity_id,
                earliest_start_time=config_entry.options[CONF_EARLIEST_START_TIME],
                latest_end_time=config_entry.options[CONF_LATEST_END_TIME],
                duration=config_entry.options[CONF_DURATION],
                duration_entity_id=config_entry.options.get(CONF_DURATION_ENTITY_ID),
                interval_mode=config_entry.options[CONF_INTERVAL_MODE],
                price_mode=config_entry.options[CONF_PRICE_MODE],
                price_tolerance=config_entry.options.get(
                    CONF_PRICE_TOLERANCE, DEFAULT_PRICE_TOLERANCE
                ),
                duration_mode=config_entry.options.get(
                    CONF_DURATION_MODE, DurationModes.EXACT
                ),
                min_duration=config_entry.options.get(CONF_MIN_DURATION),
                device_info=device_info,
            )
        ]
    )


class BinarySensor(BinarySensorEntity):
    """Representation of a EPEX Spot binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        name: str,
        entity_id: str,
        earliest_start_time: time,
        latest_end_time: time,
        duration: timedelta,
        duration_entity_id: str | None,
        interval_mode: str,
        price_mode: str,
        price_tolerance: float,
        duration_mode: str,
        min_duration: timedelta | None,
        device_info: DeviceInfo | None = None,
    ) -> None:
        """Initialize the EPEX Spot binary sensor."""
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info
        self._attr_name = name
        self._hass = hass

        # configuration options
        self._entity_id = entity_id
        self._earliest_start_time = cv.time(earliest_start_time)
        self._latest_end_time = cv.time(latest_end_time)
        self._default_duration = cv.time_period_dict(duration)
        self._duration_entity_id = duration_entity_id
        self._price_mode = price_mode
        self._interval_mode = interval_mode
        self._price_tolerance = price_tolerance
        self._duration_mode = duration_mode
        self._min_duration = min_duration

        # price sensor values
        self._sensor_attributes = None
        self._cached_marketdata = []

        # calculated values
        self._duration: timedelta = self._default_duration
        self._interval_start_time = None
        self._interval_enabled: bool = False
        self._state: bool | None = None
        self._intervals: list | None = None
        self._visualization_data: dict[str, Any] = {}

        @callback
        def async_update_state(
            event: Event,
        ) -> None:
            """Handle price or duration sensor state changes."""
            self._update_state()

        entities_to_track = [entity_id]
        if duration_entity_id is not None:
            entities_to_track.append(duration_entity_id)
        self.async_on_remove(
            async_track_state_change_event(hass, entities_to_track, async_update_state)
        )

        # check every minute for new states
        self.async_on_remove(
            async_track_time_change(hass, async_update_state, second=0)
        )

    async def async_added_to_hass(self) -> None:
        """manually trigger first update"""
        self._update_state()

    @property
    def is_available(self) -> bool | None:
        """Return true if sensor is available."""
        return self._state is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        return {
            ATTR_ENTITY_ID: self._entity_id,
            CONF_EARLIEST_START_TIME: self._earliest_start_time,
            CONF_LATEST_END_TIME: self._latest_end_time,
            CONF_DURATION: str(self._duration),
            CONF_INTERVAL_START_TIME: self._interval_start_time,
            CONF_PRICE_MODE: self._price_mode,
            CONF_INTERVAL_MODE: self._interval_mode,
            ATTR_INTERVAL_ENABLED: self._interval_enabled,
            ATTR_MEAN_PRICE_PER_KWH: self._price_mode,
            ATTR_DATA: self._intervals,
            ATTR_VISUALIZATION_DATA: self._visualization_data or {},
        }

    @callback
    def _update_state(self) -> None:
        # set to unavailable by default
        self._sensor_attributes = None
        self._state = None

        # get price sensor attributes first
        self._visualization_data = {}
        if (new_state := self._hass.states.get(self._entity_id)) is None:
            _LOGGER.warning(f"Can't get states of {self._entity_id}")
            return

        try:
            self._sensor_attributes = new_state.attributes
        except (ValueError, TypeError):
            _LOGGER.warning(f"Can't get attributes of {self._entity_id}")
            return

        now = dt_util.now()

        # earliest_start always refers to today
        earliest_start = datetime.combine(now, self._earliest_start_time, now.tzinfo)

        # latest_end may refer to today or tomorrow
        latest_end = datetime.combine(now, self._latest_end_time, now.tzinfo)

        if self._latest_end_time <= self._earliest_start_time:
            # start and end refers to different days
            # --> check if we are still within the configured timespan
            # (which may have started yesterday)
            if now < latest_end:
                # yes, we are early in the day and before latest_end
                earliest_start -= timedelta(days=1)
            else:
                # no, we are behind latest_end, therefore we set latest_end time to
                # tomorrow (and use today for earliest_time)
                # -> there are 2 intervals: from start to midnight and from midnight
                # to end
                latest_end += timedelta(days=1)

        self._interval_enabled = earliest_start <= now <= latest_end
        self._interval_start_time = earliest_start
        self._interval_enabled = earliest_start <= now <= latest_end
        self._interval_start_time = earliest_start

        # calculate the actual duration (in case a duration entity is configured)
        self._calculate_duration()

        if self._interval_mode == IntervalModes.INTERMITTENT.value:
            self._update_state_for_intermittent(
                self._interval_start_time, latest_end, now
            )
        elif self._interval_mode == IntervalModes.CONTIGUOUS.value:
            self._update_state_for_contiguous(
                self._interval_start_time, latest_end, now
            )
        else:
            _LOGGER.error(f"invalid interval mode: {self._interval_mode}")

        self.async_write_ha_state()

    def _build_visualization_data(self, marketdata, intervals):
        marketdata_in_window = [
            entry
            for entry in marketdata
            if entry.start_time >= self._interval_start_time
        ]

        if not marketdata_in_window:
            return {
                "price_unit": None,
                "window_start": dt_util.as_local(self._interval_start_time).isoformat(),
                "window_end": None,
                "market_prices": [],
                "selected_intervals": intervals,
                "price_range": {"min": None, "max": None},
            }

        prices = [entry.price for entry in marketdata_in_window]
        min_price = min(prices)
        max_price = max(prices)

        return {
            "price_unit": marketdata_in_window[0].price_uom,
            "window_start": dt_util.as_local(self._interval_start_time).isoformat(),
            "window_end": dt_util.as_local(
                marketdata_in_window[-1].end_time
            ).isoformat(),
            "market_prices": [
                {
                    ATTR_START_TIME: dt_util.as_local(entry.start_time).isoformat(),
                    ATTR_END_TIME: dt_util.as_local(entry.end_time).isoformat(),
                    "price": entry.price,
                }
                for entry in marketdata_in_window
            ],
            "selected_intervals": intervals,
            "price_range": {"min": min_price, "max": max_price},
        }

    def _update_state_for_intermittent(
        self, earliest_start: time, latest_end: time, now: datetime
    ):
        marketdata = self._get_marketdata()

        intervals = calc_intervals_for_intermittent(
            marketdata=marketdata,
            earliest_start=earliest_start,
            latest_end=latest_end,
            duration=self._duration,
            most_expensive=self._price_mode == PriceModes.MOST_EXPENSIVE.value,
            price_tolerance_percent=self._price_tolerance,
            min_duration=self._min_duration
            if self._duration_mode == DurationModes.FLEXIBLE.value
            else None,
        )

        if intervals is None:
            # no intervals found, probably because data for next day is missing
            if now < earliest_start:
                # we are before the start time, o we just say sensor-state=off instead of unavailable # noqa: E501
                self._state = False
                self._intervals = []
            return

        self._state = is_now_in_intervals(now, intervals)

        # try to calculate intervals for next day also
        earliest_start += timedelta(days=1)
        if earliest_start >= latest_end:
            # do calculation only if latest_end is limited to 24h from earliest_start, # noqa: E501
            # --> avoid calculation if latest_end includes all available marketdata
            latest_end += timedelta(days=1)
            intervals2 = calc_intervals_for_intermittent(
                marketdata=marketdata,
                earliest_start=earliest_start,
                latest_end=latest_end,
                duration=self._duration,
                most_expensive=self._price_mode == PriceModes.MOST_EXPENSIVE.value,
                price_tolerance_percent=self._price_tolerance,
                min_duration=self._min_duration
                if self._duration_mode == DurationModes.FLEXIBLE.value
                else None,
            )

            if intervals2 is not None:
                intervals = [*intervals, *intervals2]

        self._intervals = [
            {
                ATTR_START_TIME: dt_util.as_local(e.start_time).isoformat(),
                ATTR_END_TIME: dt_util.as_local(e.end_time).isoformat(),
                ATTR_RANK: e.rank,
                ATTR_PRICE_PER_KWH: e.price,
            }
            for e in sorted(intervals, key=lambda e: e.start_time)
        ]
        self._visualization_data = self._build_visualization_data(
            marketdata, self._intervals
        )

    def _update_state_for_contiguous(
        self, earliest_start: time, latest_end: time, now: datetime
    ):
        marketdata = self._get_marketdata()

        result = calc_interval_for_contiguous(
            marketdata,
            earliest_start=earliest_start,
            latest_end=latest_end,
            duration=self._duration,
            most_expensive=self._price_mode == PriceModes.MOST_EXPENSIVE.value,
            price_tolerance_percent=self._price_tolerance,
            min_duration=self._min_duration
            if self._duration_mode == DurationModes.FLEXIBLE.value
            else None,
        )

        if result is None:
            # No interval found: next-day data may be missing or previous-day
            # data may no longer be available.
            self._state = False
            self._intervals = []
        else:
            self._state = result["start"] <= now < result["end"]
            self._intervals = [
                {
                    ATTR_START_TIME: dt_util.as_local(result["start"]).isoformat(),
                    ATTR_END_TIME: dt_util.as_local(result["end"]).isoformat(),
                    # "interval_price": result["interval_price"],
                }
            ]

        # try to calculate intervals for next day also
        earliest_start += timedelta(days=1)
        if earliest_start >= latest_end:
            # do calculation only if latest_end is limited to 24h from earliest_start,
            # --> avoid calculation if latest_end includes all available marketdata
            latest_end += timedelta(days=1)
            result = calc_interval_for_contiguous(
                marketdata,
                earliest_start=earliest_start,
                latest_end=latest_end,
                duration=self._duration,
                most_expensive=self._price_mode == PriceModes.MOST_EXPENSIVE.value,
                price_tolerance_percent=self._price_tolerance,
                min_duration=self._min_duration
                if self._duration_mode == DurationModes.FLEXIBLE.value
                else None,
            )

            if result is None:
                if len(self._intervals) == 0:
                    # no interval found up until today, and none for tomorrow
                    # we are likely before the next interval start and no
                    # longer have all previous-day data
                    # and tomorrows data are not available yet
                    self._state = False
                return

            self._intervals.append(
                {
                    ATTR_START_TIME: dt_util.as_local(result["start"]).isoformat(),
                    ATTR_END_TIME: dt_util.as_local(result["end"]).isoformat(),
                }
            )

        self._visualization_data = self._build_visualization_data(
            marketdata, self._intervals
        )

    def _get_marketdata(self):
        try:
            marketdata = get_marketdata_from_sensor_attrs(self._sensor_attributes)
        except KeyError as error:
            _LOGGER.error(
                f'Invalid price sensor "{self._entity_id}" selected for EPEX Spot Sensor "{self._attr_name}": {error}'  # noqa:E501
            )
            return []

        # now merge it with the cached info
        marketdata = [*marketdata, *self._cached_marketdata]

        # remove outdated entries (exact time doesn't matter)
        start_time = dt_util.now() - timedelta(days=1)
        marketdata = filter(lambda e: e.start_time >= start_time, marketdata)

        # eliminate duplicates
        dummy = {e.start_time: e for e in marketdata}

        # sort by start_time again
        marketdata = sorted(dummy.values(), key=lambda e: e.start_time)

        self._cached_marketdata = marketdata

        return marketdata

    def _calculate_duration(self):
        self._duration = self._default_duration
        self._min_duration = None  # Reset flexible settings

        if self._duration_entity_id is None:
            return

        # When entity is active, force exact mode
        self._duration_mode = DurationModes.EXACT.value
        self._min_duration = None

        duration_entity_state = self._hass.states.get(self._duration_entity_id)
        if duration_entity_state is None:
            return

        uom = duration_entity_state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if uom not in DURATION_UOM_MAP:
            _LOGGER.error(
                f'Invalid unit of measurement "{uom}" for duration entity {self._duration_entity_id}.\n'  # noqa
                "Valid unit of measurements: d, h, min, s, ms"
            )
            return

        self._duration = cv.time_period_dict(
            {DURATION_UOM_MAP[uom]: float(duration_entity_state.state)}
        )

        # set interval start time to duration entity last_changed
        # if duration entity is changed within interval
        if (
            self._interval_enabled
            and duration_entity_state.last_changed > self._interval_start_time
        ):
            self._interval_start_time = duration_entity_state.last_changed
