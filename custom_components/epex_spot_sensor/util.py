import logging

from homeassistant.helpers import (
    config_validation as cv,
)

_LOGGER = logging.getLogger(__name__)


class Marketprice:
    def __init__(self, entry):
        self._start_time = cv.datetime(entry["start_time"])
        self._end_time = cv.datetime(entry["end_time"])
        if (x := entry.get("price_eur_per_mwh")) is not None:
            self._price = x
            self._price_uom = "EUR/MWh"
        elif (x := entry.get("price_gbp_per_mwh")) is not None:
            self._price = x
            self._price_uom = "GBP/MWh"
        elif (x := entry.get("price_ct_per_kwh")) is not None:
            self._price = x
            self._price_uom = "ct/kWh"
        elif (x := entry.get("price_pence_per_kwh")) is not None:
            self._price = x
            self._price_uom = "pence/kWh"
        elif (x := entry.get("price_per_kwh")) is not None:
            self._price = x
            self._price_uom = "€/£/kWh"
        else:
            raise KeyError("No valid price field found.")

    def __repr__(self):
        return f"{self.__class__.__name__}(start: {self._start_time.isoformat()}, end: {self._end_time.isoformat()}, marketprice: {self._price} {self._price_uom})"  # noqa: E501

    @property
    def start_time(self):
        return self._start_time

    @property
    def end_time(self):
        return self._end_time

    @property
    def price(self):
        return self._price

    @property
    def price_uom(self):
        return self._price_uom


def get_marketdata_from_sensor_attrs(attributes):
    """Convert sensor attributes to market price list."""
    try:
        data = attributes["data"]
    except KeyError:
        raise KeyError("'data' missing in sensor attributes")

    return [Marketprice(e) for e in data]
