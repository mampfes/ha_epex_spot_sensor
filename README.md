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

## Configuration Options

1. Earliest Start Time  
   Earliest time to start the appliance.

2. Latest End Time  
   Latest time to end the appliance. Set it to same value as earliest start time to cover 24h. If set to smaller value than earliest start time, it automatically refers to following day.

3. Duration  
   Required duration to complete the appliance.

4. Remaining Duration Entity  
   Optional entity which indicates the remaining duration. If entity is set, it replaces the static duration. If the state of the `Remaining Duration Entity` changes between `Earliest Start Time` and `Latest End Time`, the configured `Earliest Start Time` will be ignore and the latest change time of the `Remaining Duration Entity` will the used instead.

5. Price Mode  
   Selects whether the sensor shall react on the cheapest or the most expensive prices between `Earliest Start Time` and `Latest End Time`.

6. Interval Mode  
   Selects whether the specified duration shall be completed in a single, contiguous interval or can be split into multiple, not contiguous intervals (`intermittend`).

## Sensor Attributes

1. Earliest Start Time  
   Reflects the configured `Earliest Start Time`.

2. Latest End Time  
   Reflects the configured `Latest End Time`.

3. Duration  
   Reflects the used value for duration, which is either the configured duration if the `Remaining Duration Entity` is not set; or the state of the `Remaining Duration Entity`.

4. Remaining Duration Entity  
   Optional entity which indicates the remaining duration. If entity is set, it replaces the static duration.

5. Interval Start Time
   Reflects the actual start time of the interval, which is either the configured `Earliest Start Time` or the latest change time of the `Remaining Duration Entity` if the state of the entity changed between `Earliest Start Time` and `Latest End Time`.

6. Price Mode  
   Reflects the configured `Price Mode`.

7. Price Mode  
   Reflects the configured `Interval Mode`.

8. Enabled  
   Set to `true` if current time is between `Earliest Start Time` and `Latest End Time`.

9. Data  
   List of calculated intervals to switch sensor on, consisting of `start_time`, `end_time` and `rank` (for Interval Mode intermittend only).
