# EPEX Spot Sensor

This component is an addition to the [EPEX Spot](https://github.com/mampfes/ha_epex_spot) integration.

EPEX Spot Sensor add one or more binary sensors which can be configured to turn on at the cheapest or most expensive time interval of the day. The length of the time interval can be configured, as well as whether the interval shall be used contiguously or intermittently.

![Helper Sensor](/images/setup.png)

If you like this component, please give it a star on [github](https://github.com/mampfes/hacs_epex_spot_sensor).

## Installation

1. Ensure that [HACS](https://hacs.xyz) is installed.

2. Open HACS, then select `Integrations`.

3. Select &#8942; and then `Custom repositories`.

4. Set `Repository` to *https://github.com/mampfes/ha_epex_spot_sensor*  
   and `Category` to _Integration_.

5. Install **EPEX Spot Sensor** integration via HACS:

   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mampfes&repository=ha_epex_spot_sensor)

   If the button doesn't work: Open `HACS` > `Integrations` > `Explore & Download Repositories` and select integration `EPEX Spot Sensor`.

6. Add helper(s) provided by **EPEX Spot Sensor** to Home Assistant:

   [![Open your Home Assistant instance and start setting up a new helpers.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=epex_spot_sensor)

   If the button doesn't work: Open `Settings` > `Devices & services` > `Helpers` > `Create Helper` and select `EPEX Spot Sensor`.

In case you would like to install manually:

1. Copy the folder `custom_components/epex_spot_sensor` to `custom_components` in your Home Assistant `config` folder.
2. Add helper(s) provided by **EPEX Spot Sensor** to Home Assistant:

   [![Open your Home Assistant instance and start setting up a new helpers.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=epex_spot_sensor)

   If the button doesn't work: Open `Settings` > `Devices & services` > `Helpers` > `Create Helper` and select `EPEX Spot Sensor`.
