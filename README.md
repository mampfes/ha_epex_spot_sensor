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
   Required duration to complete the appliance. In **Exact** mode, this is the exact duration. In **Flexible** mode, this becomes the maximum duration.

4. Remaining Duration Entity  
   Optional entity which indicates the remaining duration. If entity is set, it replaces the static duration and overrides flexible duration mode. If the state of the `Remaining Duration Entity` changes between `Earliest Start Time` and `Latest End Time`, the configured `Earliest Start Time` will be ignore and the latest change time of the `Remaining Duration Entity` will the used instead.

5. Duration Mode  
   Selects whether the duration is **Exact** (default) or **Flexible**:

   - **Exact**: Find intervals of exactly the specified duration
   - **Flexible**: Find intervals between minimum and maximum duration, stopping when prices exceed the threshold

6. Minimum Duration  
   (Flexible mode only) The minimum required duration. Only appears when `Duration Mode` is set to **Flexible**. Must be less than or equal to the configured duration (maximum).

7. Price Tolerance (%)  
   Allow time slots within ±X% of the cheapest/most expensive price. Default is 0% (exact matching). Higher values provide more flexibility in scheduling while staying close to optimal prices.

   - **0%** = Exact cheapest/most expensive (default behavior)
   - **10-20%** = Moderate flexibility, good for most use cases
   - **50%+** = High flexibility, prioritizes convenience over cost optimization

   When multiple intervals are within tolerance, the system prefers earlier start times.

8. Price Mode  
   Selects whether the sensor shall react on the cheapest or the most expensive prices between `Earliest Start Time` and `Latest End Time`.

9. Interval Mode  
   Selects whether the specified duration shall be completed in a single, contiguous interval or can be split into multiple, not contiguous intervals (`intermittend`).

## Sensor Attributes

1. Earliest Start Time  
   Reflects the configured `Earliest Start Time`.

2. Latest End Time  
   Reflects the configured `Latest End Time`.

3. Duration  
   Reflects the used value for duration. In **Exact** mode, this is the configured duration (or `Remaining Duration Entity` state). In **Flexible** mode, this represents the maximum duration.

4. Remaining Duration Entity  
   Optional entity which indicates the remaining duration. If entity is set, it replaces the static duration and overrides flexible duration mode.

5. Duration Mode  
   Reflects the configured `Duration Mode` (**Exact** or **Flexible**). In Flexible mode, the system finds intervals between minimum and maximum duration that stay within the price threshold.

6. Minimum Duration  
   (Flexible mode only) The minimum required duration. Only present when `Duration Mode` is set to **Flexible**.

7. Price Tolerance  
   Reflects the configured `Price Tolerance` percentage (0-100%). Shows how much price flexibility is allowed when selecting time slots.

8. Interval Start Time
   Reflects the actual start time of the interval, which is either the configured `Earliest Start Time` or the latest change time of the `Remaining Duration Entity` if the state of the entity changed between `Earliest Start Time` and `Latest End Time`.

9. Price Mode  
   Reflects the configured `Price Mode`.

10. Interval Mode  
    Reflects the configured `Interval Mode`.

11. Enabled  
    Set to `true` if current time is between `Earliest Start Time` and `Latest End Time`.

12. Data  
    List of calculated intervals to switch sensor on, consisting of `start_time`, `end_time` and `rank` (for Interval Mode intermittend only).

## UI Visualization (historic + selected intervals)

Each binary sensor now exposes an additional attribute `visualization_data` that is designed for dashboards.
It contains:

- `market_prices`: historic/forecast price buckets (`start_time`, `end_time`, `price`)
- `selected_intervals`: the intervals chosen by the sensor logic
- `price_range`: min/max values for quick chart scaling
- `price_unit`, `window_start`, `window_end`

You can use this attribute with custom Lovelace cards (for example [apexcharts-card]) to overlay selected runtime intervals on top of the hourly prices.

Example template sensor to flatten data for charts:

```yaml
template:
  - sensor:
      - name: "Waschmaschine Price Points"
        state: "{{ now() }}"
        attributes:
          points: >-
            {{ state_attr('binary_sensor.waschmaschine', 'visualization_data').market_prices
               if state_attr('binary_sensor.waschmaschine', 'visualization_data') else [] }}
          selected: >-
            {{ state_attr('binary_sensor.waschmaschine', 'visualization_data').selected_intervals
               if state_attr('binary_sensor.waschmaschine', 'visualization_data') else [] }}
```
