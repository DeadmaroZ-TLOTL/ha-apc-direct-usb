# APC Direct USB

Home Assistant custom integration for direct USB HID monitoring and bounded
configuration of a **Back-UPS RS 500**. No NUT server, cloud account or network
credentials are needed by the integration.

**Experimental, narrowly supported hardware profile.** This is not a universal
APC driver and is not an official APC or Home Assistant integration.

## Supported Profile

| Property | Supported value |
| --- | --- |
| Model | APC Back-UPS RS 500 |
| Firmware / USB firmware | `30.j5.I` / `j5` |
| USB vendor / product | `051d:0002` |
| HID report descriptor | 1247 bytes |
| Descriptor SHA-256 | `1f6e71f3b24e30d23bdcec22e85461b8105a91d1d75169555fe3077753370773` |
| Baseline Home Assistant version | 2026.11.1 |

The protocol was checked against one physical device with this profile. The
public package uses a user-configured serial number and synthetic test data.
Other firmware, models and descriptors are rejected, even if their USB IDs match.
Your Home Assistant host must already provide USB access and a working libusb
backend; virtual machines require the appropriate USB passthrough.

## Measurements

- Battery charge, voltage, runtime and temperature.
- Mains and output voltage, output frequency and load percentage.
- Separate reported charging, discharging, mains and battery-presence flags.
- Low-battery, runtime-limit, replacement, overload, shutdown and voltage flags.
- Configuration readback, last USB sample time and read duration.

Polling is approximately every five seconds. Missing or malformed reports make
the entities unavailable; missing measurements are not replaced with zero.
The separate PowerSummary battery voltage is disabled by default to avoid
confusing it with the main battery-voltage report.

A charging flag does **not** independently establish charge current or a healthy
battery. Estimated runtime and SOC remain values reported by the UPS. The
integration does not invent charge-current or actual-output-power measurements.

## Configuration Controls

| Entity | Profile range or options |
| --- | --- |
| Low battery charge threshold | 0-100% |
| Low battery runtime threshold | 120-1380 seconds |
| High mains transfer point | 254-276 V |
| Low mains transfer point | 182-198 V |
| Input sensitivity | Low, medium, high |
| Audible alarm | Disabled, enabled, muted |
| Battery date | 1980-2107 |

Ranges come from the supported descriptor, not another APC model. Firmware can
reject or round an individual value; the readback must match before success is
reported. Changing a battery date may have device-specific effects: it is not a
charging repair or a substitute for physically checking a battery.

Configuration writes are explicit user actions. Each changed value uses one
allowlisted USB write followed by readback. Unchanged values are not written.
An uncertain result is reported as an error and is never automatically replayed.

**No output-off, reboot, shutdown countdown, battery test or calibration commands
are exposed.** The integration does not implement automatic host shutdown. NUT
software defaults such as `ups.delay.start` are not presented as hardware settings.

## Installation

1. Back up your Home Assistant configuration and identify the existing USB owner.
2. Copy `custom_components/apc_direct` into your HA `custom_components` directory,
   or add this repository to HACS as a custom **Integration** repository.
3. Restart Home Assistant to discover the new custom integration.
4. Safely stop only the previous driver for this UPS. Disabling the HA NUT
   integration alone does not release the NUT USB driver. Do not stop a shared
   NUT instance that is monitoring other devices.
5. Open **Settings > Devices & services > Add integration > APC Direct USB** and
   enter the serial number printed on your UPS.
6. Verify fresh measurements before retiring your previous monitoring setup.
   If the profile is unsupported, restore the previous driver.

Do not run NUT, apcupsd and this integration against the same USB interface at
the same time. The integration will not forcibly detach another owner, reset
the USB device, change USB configuration or automatically stop other software.

HACS metadata and brand assets are included. This repository has not been
submitted to the default HACS store. See the official
[HACS custom repository guidance](https://www.hacs.xyz/docs/faq/custom_repositories/).

## Dashboard

[`examples/dashboard.json`](examples/dashboard.json) contains an English card
using native Home Assistant rows. Adjust the example entity IDs to match the
ones created on your installation, then paste the JSON into a manual card's code
editor. It includes status, battery, load and mains readings, fault flags, sample
timing, Settings navigation and History. It contains no power-switching actions.

Your previous NUT entity IDs and dashboard configuration are not automatically
migrated by this public package.

## Tests

Run offline tests with Python 3.14:

```console
python -m unittest discover -s tests -v
python -m compileall -q custom_components tests
```

Tests use a synthetic USB device and synthetic reports. They verify descriptor
layout, identity selection, read-only polling, setting allowlists, readback,
uncertain writes and dashboard actions. Tests do not access real USB hardware.
GitHub Actions runs the offline suite on each push and pull request; full Home
Assistant end-to-end tests are not included.

## Privacy And Support

The repository contains no installation-specific addresses, serial numbers,
credentials, historical telemetry or deployment helpers. Diagnostics downloaded
from your own installation may contain operational data: review them before
sharing. Do not post access tokens or full HA configuration files in issues.

For a compatibility report, provide the model, firmware, USB IDs, descriptor
length and descriptor hash. Do not include your serial number.

## References

- [Home Assistant integration documentation](https://contributors.home-assistant.io/core/integrations/)
- [APC Back-UPS RS 500 NUT device reference](https://networkupstools.org/ddl/APC/Back-UPS_RS_500.html)
- [USB Power Device Class specification](https://www.usb.org/document-library/power-device-class-document-v10)
- [PyUSB](https://github.com/pyusb/pyusb)
