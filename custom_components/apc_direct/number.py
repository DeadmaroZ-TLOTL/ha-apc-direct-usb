from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity import EntityCategory
from .entity import ApcEntity
from .protocol import NUMBER_SETTINGS


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(ApcNumber(entry.runtime_data, key) for key in NUMBER_SETTINGS)


class ApcNumber(ApcEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self._attr_native_min_value, self._attr_native_max_value, self._attr_native_step = NUMBER_SETTINGS[key]
        self._attr_native_unit_of_measurement = "%" if key == "battery_charge_low" else ("s" if key == "battery_runtime_low" else "V")

    @property
    def native_value(self):
        return self.coordinator.data[self.key]

    async def async_set_native_value(self, value):
        await self.coordinator.async_write(self.key, value)
