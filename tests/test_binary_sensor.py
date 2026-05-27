from datetime import timedelta
from unittest.mock import patch

import pytest
from custom_components.epex_spot_sensor.const import (
    CONF_DURATION,
    CONF_EARLIEST_START_TIME,
    CONF_INTERVAL_MODE,
    CONF_LATEST_END_TIME,
    CONF_PRICE_MODE,
    IntervalModes,
    PriceModes,
)
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)


@pytest.fixture
def mock_market_data():
    return [
        {
            "start_time": dt_util.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            + timedelta(hours=i),
            "end_time": dt_util.now().replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(hours=i + 1),
            "price": 10.0,
        }
        for i in range(24)
    ]


async def test_binary_sensor_setup(hass):
    """Test setting up the binary sensor."""
    config_entry = MockConfigEntry(
        domain="epex_spot_sensor",
        title="Test Sensor",
        options={
            CONF_ENTITY_ID: "sensor.epex_spot_price",
            CONF_EARLIEST_START_TIME: "00:00:00",
            CONF_LATEST_END_TIME: "23:59:59",
            CONF_DURATION: {"hours": 1},
            CONF_INTERVAL_MODE: IntervalModes.CONTIGUOUS.value,
            CONF_PRICE_MODE: PriceModes.CHEAPEST.value,
        },
    )
    config_entry.add_to_hass(hass)

    with patch(
        "custom_components.epex_spot_sensor.binary_sensor.get_marketdata_from_sensor_attrs",
        return_value=[],
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_sensor")
    assert state is not None
    assert state.state == "unknown"  # Unavailable because no market data yet


async def test_binary_sensor_logs_actionable_error_for_sensor_without_data(
    hass, caplog
):
    """Test selected source sensors without price data get an actionable error."""
    hass.states.async_set(
        "sensor.epex_spot_data_price",
        "0.12",
        {"price_per_kwh": 0.12},
    )

    config_entry = MockConfigEntry(
        domain="epex_spot_sensor",
        title="Cheap Power 1h",
        options={
            CONF_ENTITY_ID: "sensor.epex_spot_data_price",
            CONF_EARLIEST_START_TIME: "00:00:00",
            CONF_LATEST_END_TIME: "23:59:59",
            CONF_DURATION: {"hours": 1},
            CONF_INTERVAL_MODE: IntervalModes.CONTIGUOUS.value,
            CONF_PRICE_MODE: PriceModes.CHEAPEST.value,
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        'Invalid price sensor "sensor.epex_spot_data_price" selected for EPEX '
        'Spot Sensor "Cheap Power 1h": "sensor attributes must contain a '
        "'data' list with start_time, end_time, and price_per_kwh entries; "
        "select an EPEX Spot Market Price or Total Price sensor, for example "
        "sensor.epex_spot_data_market_price or "
        'sensor.epex_spot_data_total_price"'
    ) in caplog.text


async def test_binary_sensor_update_state(hass, freezer):
    """Test sensor state update with market data."""
    now = dt_util.now().replace(hour=12, minute=0, second=0, microsecond=0)
    freezer.move_to(now)

    # Mock market data: 12:00-13:00 is cheapest (5.0), others 10.0
    market_data = []
    for i in range(24):
        start = now.replace(hour=0, minute=0, second=0) + timedelta(hours=i)
        price = 5.0 if i == 12 else 10.0
        market_data.append(
            {
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=1)).isoformat(),
                "price_per_kwh": price,
            }
        )

    # Mock the source sensor
    hass.states.async_set("sensor.epex_spot_price", "10.0", {"data": market_data})

    config_entry = MockConfigEntry(
        domain="epex_spot_sensor",
        title="Test Sensor",
        options={
            CONF_ENTITY_ID: "sensor.epex_spot_price",
            CONF_EARLIEST_START_TIME: "00:00:00",
            CONF_LATEST_END_TIME: "23:59:59",
            CONF_DURATION: {"hours": 1},
            CONF_INTERVAL_MODE: IntervalModes.CONTIGUOUS.value,
            CONF_PRICE_MODE: PriceModes.CHEAPEST.value,
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Trigger update
    # Force update by changing the source entity or calling update method?
    # The sensor listens to state changes of source entity.
    # We already set it. But setup happens after.
    # The sensor also updates on time change.

    # Let's trigger a state change on the source sensor
    hass.states.async_set("sensor.epex_spot_price", "12.0", {"data": market_data})
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_sensor")
    assert state is not None
    # At 12:00, we are in the cheapest interval (12:00-13:00)
    assert state.state == "on"

    visualization_data = state.attributes.get("visualization_data")
    assert isinstance(visualization_data, dict)

    # Move time to 13:01
    future = now + timedelta(hours=1, minutes=1)
    freezer.move_to(future)
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_sensor")
    assert state.state == "off"


async def test_binary_sensor_crossing_midnight(hass, freezer):
    """Test sensor state update when interval crosses midnight."""
    now = dt_util.now().replace(hour=23, minute=0, second=0, microsecond=0)
    freezer.move_to(now)

    # Mock market data for today and tomorrow
    # Today: expensive
    # Tomorrow 00:00-01:00: cheapest
    market_data = []
    # Today's data
    for i in range(24):
        start = now.replace(hour=0, minute=0, second=0) + timedelta(hours=i)
        price = 10.0
        market_data.append(
            {
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=1)).isoformat(),
                "price_per_kwh": price,
            }
        )

    # Tomorrow's data
    tomorrow = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
    for i in range(24):
        start = tomorrow + timedelta(hours=i)
        price = 5.0 if i == 0 else 10.0  # 00:00-01:00 is cheapest
        market_data.append(
            {
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=1)).isoformat(),
                "price_per_kwh": price,
            }
        )

    # Mock the source sensor
    hass.states.async_set("sensor.epex_spot_price", "10.0", {"data": market_data})

    config_entry = MockConfigEntry(
        domain="epex_spot_sensor",
        title="Test Sensor Midnight",
        options={
            CONF_ENTITY_ID: "sensor.epex_spot_price",
            CONF_EARLIEST_START_TIME: "22:00:00",
            CONF_LATEST_END_TIME: "02:00:00",  # Crosses midnight
            CONF_DURATION: {"hours": 1},
            CONF_INTERVAL_MODE: IntervalModes.CONTIGUOUS.value,
            CONF_PRICE_MODE: PriceModes.CHEAPEST.value,
        },
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Trigger update
    hass.states.async_set("sensor.epex_spot_price", "10.0", {"data": market_data})
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_sensor_midnight")
    assert state is not None
    # At 23:00, we are NOT in the cheapest interval (which is tomorrow 00:00-01:00)
    assert state.state == "off"

    # Move time to 00:00 tomorrow
    future = tomorrow
    freezer.move_to(future)
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_sensor_midnight")
    assert state.state == "on"

    # Move time to 01:01 tomorrow
    future = tomorrow + timedelta(hours=1, minutes=1)
    freezer.move_to(future)
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.test_sensor_midnight")
    assert state.state == "off"
