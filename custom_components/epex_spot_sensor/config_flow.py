"""Config flow for EPEX Spot Sensor component."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from .const import (
    CONF_DURATION,
    CONF_DURATION_ENTITY_ID,
    CONF_DURATION_MODE,
    CONF_EARLIEST_START_TIME,
    CONF_INTERVAL_MODE,
    CONF_LATEST_END_TIME,
    CONF_MIN_DURATION,
    CONF_PRICE_MODE,
    CONF_PRICE_TOLERANCE,
    DEFAULT_PRICE_TOLERANCE,
    DOMAIN,
    DurationModes,
    IntervalModes,
    PriceModes,
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=SENSOR_DOMAIN)
        ),
        vol.Required(CONF_EARLIEST_START_TIME): selector.TimeSelector(),
        vol.Required(CONF_LATEST_END_TIME): selector.TimeSelector(),
        vol.Required(
            CONF_DURATION_MODE, default=DurationModes.EXACT
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                translation_key=CONF_DURATION_MODE,
                mode=selector.SelectSelectorMode.LIST,
                options=[e.value for e in DurationModes],
            )
        ),
        vol.Required(CONF_DURATION, default={"hours": 1}): selector.DurationSelector(),
        vol.Optional(CONF_DURATION_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=[INPUT_NUMBER_DOMAIN, SENSOR_DOMAIN])
        ),
        vol.Optional(CONF_MIN_DURATION): selector.DurationSelector(),
        vol.Required(
            CONF_PRICE_MODE, default=PriceModes.CHEAPEST
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                translation_key=CONF_PRICE_MODE,
                mode=selector.SelectSelectorMode.LIST,
                options=[e.value for e in PriceModes],
            )
        ),
        vol.Required(
            CONF_INTERVAL_MODE, default=IntervalModes.INTERMITTENT
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                translation_key=CONF_INTERVAL_MODE,
                mode=selector.SelectSelectorMode.LIST,
                options=[e.value for e in IntervalModes],
            )
        ),
        vol.Optional(
            CONF_PRICE_TOLERANCE, default=DEFAULT_PRICE_TOLERANCE
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=0,
                max=100,
                step=1,
                unit_of_measurement="%",
            ),
        ),
        #        vol.Required(
        #            CONF_HYSTERESIS, default=DEFAULT_HYSTERESIS
        #        ): selector.NumberSelector(
        #            selector.NumberSelectorConfig(
        #                mode=selector.NumberSelectorMode.BOX, step="any"
        #            ),
        #        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): selector.TextSelector(),
    }
).extend(OPTIONS_SCHEMA.schema)

CONFIG_FLOW = {"user": SchemaFlowFormStep(CONFIG_SCHEMA)}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for Threshold."""

    config_flow = CONFIG_FLOW

    def async_get_options_flow(self, config_entry):
        """Return options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        name: str = options[CONF_NAME]
        return name


class OptionsFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle options flow with conditional fields."""

    config_flow = {}
    options_flow = {"init": SchemaFlowFormStep(OPTIONS_SCHEMA)}

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return options.get(CONF_NAME, "EPEX Spot Sensor")
