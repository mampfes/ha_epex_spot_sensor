"""Constants for the EPEX Spot Sensor integration."""

from enum import Enum

DOMAIN = "epex_spot_sensor"

CONF_EARLIEST_START_TIME = "earliest_start_time"
CONF_LATEST_END_TIME = "latest_end_time"
CONF_DURATION = "duration"
CONF_DURATION_ENTITY_ID = "duration_entity_id"
CONF_INTERVAL_START_TIME = "interval_start_time"

CONF_INTERVAL_MODE = "interval_mode"

CONF_PRICE_TOLERANCE = "price_tolerance"
DEFAULT_PRICE_TOLERANCE = 0.0

CONF_DURATION_MODE = "duration_mode"
CONF_MIN_DURATION = "min_duration"


class DurationModes(Enum):
    """Duration modes for config validation."""

    EXACT = "exact"
    FLEXIBLE = "flexible"


DEFAULT_DURATION_MODE = DurationModes.EXACT


class IntervalModes(Enum):
    """Work modes for config validation."""

    CONTIGUOUS = "contiguous"
    INTERMITTENT = "intermittent"


CONF_PRICE_MODE = "price_mode"


class PriceModes(Enum):
    """Price modes for config validation."""

    CHEAPEST = "cheapest"
    MOST_EXPENSIVE = "most_expensive"


ATTR_INTERVAL_ENABLED = "enabled"
ATTR_START_TIME = "start_time"
ATTR_END_TIME = "end_time"
ATTR_RANK = "rank"
ATTR_DATA = "data"
ATTR_PRICE_PER_KWH = "price_per_kwh"
ATTR_MEAN_PRICE_PER_KWH = "mean_price_per_kwh"
ATTR_VISUALIZATION_DATA = "visualization_data"
