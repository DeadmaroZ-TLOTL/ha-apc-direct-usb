from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, MODEL

LABELS = {
    "battery_charge": "Battery charge", "battery_voltage": "Battery voltage",
    "battery_voltage_summary": "Battery summary voltage", "battery_voltage_nominal": "Nominal battery voltage",
    "battery_runtime": "Battery runtime", "battery_temperature": "Battery temperature",
    "input_voltage": "Input voltage", "input_voltage_nominal": "Nominal input voltage",
    "output_voltage": "Output voltage", "output_frequency": "Output frequency",
    "load": "Load", "nominal_real_power": "Nominal real power", "battery_date": "Battery replacement date",
    "battery_charge_low": "Low battery charge threshold", "battery_runtime_low": "Low battery runtime threshold",
    "battery_charge_warning": "Battery warning charge threshold", "input_sensitivity": "Input sensitivity",
    "input_transfer_high": "High voltage transfer point", "input_transfer_low": "Low voltage transfer point",
    "beeper": "Audible alarm", "charging": "Charging reported by UPS", "discharging": "Discharging",
    "ac_present": "Mains present", "battery_present": "Battery present",
    "below_capacity_limit": "Low battery", "shutdown_imminent": "Shutdown imminent",
    "runtime_limit_expired": "Battery runtime limit expired", "need_replacement": "Battery needs replacement",
    "overload": "Overload", "voltage_not_regulated": "Voltage not regulated (UPS flag)",
    "sample_at": "Last USB sample", "duration": "USB reading duration", "status": "Status",
    "status_data": "Status codes", "battery_chemistry": "Battery chemistry",
    "battery_manufacture_date": "Battery date (UPS alias)",
}


class ApcEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        self.key = key
        serial = coordinator.usb.serial
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_name = LABELS[key]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)}, name="APC Back-UPS RS 500",
            manufacturer="American Power Conversion", model=MODEL, serial_number=serial, sw_version="30.j5.I / USB j5")

    @property
    def extra_state_attributes(self):
        if not self.coordinator.data:
            return None
        # One timestamp sensor tracks polling; changing every entity's attributes
        # on each poll would needlessly multiply recorder database writes.
        return {"source": "direct USB HID", "last_setting_write": self.coordinator.usb.last_write}
