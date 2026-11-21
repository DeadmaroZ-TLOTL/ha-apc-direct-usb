from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from .entity import ApcEntity

KEYS = {
    "charging": BinarySensorDeviceClass.BATTERY_CHARGING,
    "discharging": None, "ac_present": BinarySensorDeviceClass.POWER,
    "battery_present": None, "below_capacity_limit": BinarySensorDeviceClass.BATTERY,
    "shutdown_imminent": BinarySensorDeviceClass.PROBLEM,
    "runtime_limit_expired": BinarySensorDeviceClass.PROBLEM,
    "need_replacement": BinarySensorDeviceClass.PROBLEM, "overload": BinarySensorDeviceClass.PROBLEM,
    "voltage_not_regulated": BinarySensorDeviceClass.PROBLEM,
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(ApcBinarySensor(entry.runtime_data, key) for key in KEYS)


class ApcBinarySensor(ApcEntity, BinarySensorEntity):
    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self._attr_device_class = KEYS[key]

    @property
    def is_on(self):
        return self.coordinator.data[self.key]
