"""Test flexible duration configuration fields."""

from custom_components.epex_spot_sensor import config_flow
from custom_components.epex_spot_sensor.const import (
    CONF_DURATION_MODE,
    CONF_MIN_DURATION,
    CONF_PRICE_TOLERANCE,
)
from homeassistant.const import CONF_ENTITY_ID


class TestFlexibleDurationConfig:
    """Test flexible duration configuration fields."""

    def test_duration_mode_field_exists(self):
        """Test that duration_mode field exists in options schema."""
        schema = config_flow.OPTIONS_SCHEMA

        # Check that duration_mode field exists
        assert CONF_DURATION_MODE in schema.schema

    def test_min_duration_field_exists(self):
        """Test that min_duration field exists in options schema."""
        schema = config_flow.OPTIONS_SCHEMA

        # Check that min_duration field exists (now always present as optional)
        assert CONF_MIN_DURATION in schema.schema

    def test_price_tolerance_field_exists(self):
        """Test that price_tolerance field exists (Phase 1 - should pass)."""
        schema = config_flow.OPTIONS_SCHEMA

        # This should PASS (Phase 1 implemented)
        assert CONF_PRICE_TOLERANCE in schema.schema

    def test_config_validation_with_exact_mode(self):
        """Test that config validation works with exact mode."""
        schema = config_flow.OPTIONS_SCHEMA

        # Try to create config with exact mode
        config_data = {
            CONF_ENTITY_ID: "sensor.epex_spot_price",
            "earliest_start_time": "22:00:00",
            "latest_end_time": "06:00:00",
            "duration_mode": "exact",
            "duration": {"hours": 4},
            "price_mode": "cheapest",
            "interval_mode": "intermittent",
            "price_tolerance": 15,
        }

        # This should work
        result = schema(config_data)
        assert result is not None

    def test_config_validation_with_flexible_mode(self):
        """Test config validation with flexible mode including min_duration."""
        schema = config_flow.OPTIONS_SCHEMA

        # Try to create config with flexible mode
        config_data = {
            CONF_ENTITY_ID: "sensor.epex_spot_price",
            "earliest_start_time": "22:00:00",
            "latest_end_time": "06:00:00",
            "duration_mode": "flexible",
            "duration": {"hours": 4},
            "min_duration": {"hours": 2},
            "price_mode": "cheapest",
            "interval_mode": "intermittent",
            "price_tolerance": 15,
        }

        # This should work
        result = schema(config_data)
        assert result is not None
