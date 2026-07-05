# AC Infinity Controller 67 for Home Assistant

Experimental Home Assistant custom integration for the BLE-only AC Infinity
Controller 67.

This integration exposes fan control from off through speed 10 and the
controller probe temperature. It is intended for local control and telemetry
over Bluetooth or an active ESPHome Bluetooth proxy.

## Status

This is an early custom integration. It has been tested with one Controller 67
setup and should be treated as experimental.

Do not rely on this integration as the only ventilation or environmental
control for anything safety-critical.

## Features

- Local BLE control, no cloud account required
- Manual config flow by controller BLE address
- Bluetooth discovery by `BLE_FAN` local name where available
- Fan percentage control in 10% steps
- Temperature sensor from the controller probe
- Temperature state updates rounded to `0.1 °C` to reduce recorder noise
- Home Assistant diagnostics for connection troubleshooting
- HACS custom repository metadata

## Requirements

- Home Assistant with Bluetooth support
- AC Infinity Controller 67 BLE controller
- A Bluetooth adapter or ESPHome Bluetooth proxy in range
- If using ESPHome Bluetooth proxy, it must support active connections

Passive Bluetooth proxy mode is not enough. The integration needs a BLE GATT
connection so it can write commands to the controller.

The AC Infinity mobile app should be closed while Home Assistant is controlling
the fan. The controller appears to allow only one active BLE client at a time.

## Installation

### HACS Custom Repository

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add this repository URL:

   ```text
   https://github.com/crhymes/ac-infinity-67
   ```

5. Select category **Integration**.
6. Install **AC Infinity Controller 67**.
7. Restart Home Assistant.

### Manual Installation

Copy this directory:

```text
custom_components/ac_infinity_67
```

into your Home Assistant config directory so the final path is:

```text
<config>/custom_components/ac_infinity_67
```

Restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings** -> **Devices & services**.
2. Select **Add integration**.
3. Search for **AC Infinity Controller 67**.
4. Enter the controller BLE address when prompted.

Use the BLE address shown by Home Assistant Bluetooth discovery, ESPHome logs,
or another BLE scanner. Example format:

```text
AA:BB:CC:DD:EE:FF
```

## Speed Mapping

Home Assistant fan percentage maps to Controller 67 speed as follows:

| Home Assistant | Controller speed |
| --- | --- |
| `0%` | `0`, off |
| `10%` | `1` |
| `20%` | `2` |
| `30%` | `3` |
| `40%` | `4` |
| `50%` | `5` |
| `60%` | `6` |
| `70%` | `7` |
| `80%` | `8` |
| `90%` | `9` |
| `100%` | `10` |

If a dashboard card only shows on/off, use the entity more-info panel or call
the `fan.set_percentage` service directly.

## Example Automation

This example turns the fan on when the home HVAC is actively heating or cooling
and turns it off when the HVAC becomes idle. Replace the entity IDs with the
ones from your Home Assistant instance.

```yaml
alias: Sync AC Infinity fan with HVAC
mode: restart
trigger:
  - platform: state
    entity_id: climate.home
    attribute: hvac_action
condition: []
action:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.attributes.hvac_action in ['heating', 'cooling'] }}"
        sequence:
          - service: fan.set_percentage
            target:
              entity_id: fan.ac_infinity_controller_67
            data:
              percentage: 50
    default:
      - service: fan.turn_off
        target:
          entity_id: fan.ac_infinity_controller_67
```

## Troubleshooting

If the entity does not connect:

- Confirm the controller is in range of the Bluetooth adapter or proxy.
- Confirm ESPHome Bluetooth proxy is configured for active connections.
- Close the AC Infinity mobile app.
- Power-cycle the Controller 67.
- Reload the integration or restart Home Assistant.

The integration retries discovery every 60 seconds after startup. If Home
Assistant starts before the Bluetooth proxy sees the controller, it should
connect later once the controller is visible.

## Diagnostics

Home Assistant diagnostics are supported for the config entry. The diagnostics
payload redacts the configured BLE address and includes:

- availability
- connection attempt count
- last connection attempt and success timestamps
- whether the device came from Home Assistant Bluetooth discovery or direct
  Bleak scan
- last BLE error
- current decoded temperature and raw temperature value
- current decoded speed and raw speed byte

## Notes

This project is not affiliated with or endorsed by AC Infinity.

## License

MIT License. See [LICENSE](LICENSE).
