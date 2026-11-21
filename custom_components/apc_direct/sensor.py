from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from .entity import ApcEntity

SENSORS = {
    "battery_charge": ("%", SensorDeviceClass.BATTERY),
    "battery_voltage": ("V", SensorDeviceClass.VOLTAGE),
    "battery_voltage_summary": ("V", SensorDeviceClass.VOLTAGE),
    "battery_voltage_nominal": ("V", SensorDeviceClass.VOLTAGE),
    "battery_runtime": ("s", SensorDeviceClass.DURATION),
    "battery_temperature": ("\u00b0C", SensorDeviceClass.TEMPERATURE),
    "input_voltage": ("V", SensorDeviceClass.VOLTAGE),
    "input_voltage_nominal": ("V", SensorDeviceClass.VOLTAGE),
    "output_voltage": ("V", SensorDeviceClass.VOLTAGE),
    "output_frequency": ("Hz", SensorDeviceClass.FREQUENCY),
    "load": ("%", None), "nominal_real_power": ("W", SensorDeviceClass.POWER),
    "battery_charge_low": ("%", None), "battery_runtime_low": ("s", SensorDeviceClass.DURATION),
    "battery_charge_warning": ("%", None), "input_transfer_high": ("V", SensorDeviceClass.VOLTAGE),
    "input_transfer_low": ("V", SensorDeviceClass.VOLTAGE),
    "sample_at": (None, SensorDeviceClass.TIMESTAMP), "duration": ("s", SensorDeviceClass.DURATION),
    "status": (None, None), "status_data": (None, None), "battery_chemistry": (None, None),
    "battery_date": (None, None), "battery_manufacture_date": (None, None),
    "input_sensitivity": (None, None), "beeper": (None, None),
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(ApcSensor(entry.runtime_data, key) for key in SENSORS)


class ApcSensor(ApcEntity, SensorEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self._attr_native_unit_of_measurement, self._attr_device_class = SENSORS[key]
        if self._attr_native_unit_of_measurement:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if key in ("battery_voltage_summary", "battery_voltage_nominal", "input_voltage_nominal", "nominal_real_power", "sample_at", "duration", "battery_chemistry"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if key == "battery_voltage_summary":
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        data = self.coordinator.data
        if self.key in ("status", "status_data"):
            codes = ["OL" if data["ac_present"] else "OB"]
            for key, code in (("below_capacity_limit", "LB"), ("overload", "OVER"),
                              ("need_replacement", "RB"), ("discharging", "DISCHRG")):
                if data[key]:
                    codes.append(code)
            if self.key == "status_data":
                return " ".join(codes)
            return ", ".join({"OL":"Online", "OB":"On battery", "LB":"Low Battery", "OVER":"Overload",
                              "RB":"Replace battery", "DISCHRG":"Discharging"}[code] for code in codes)
        if self.key == "battery_chemistry":
            return "PbAc"
        if self.key in ("battery_date", "battery_manufacture_date"):
            value = data.get("battery_date")
            return value.strftime("%Y/%m/%d") if value is not None else None
        return data.get(self.key)
