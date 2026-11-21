from homeassistant.components.date import DateEntity
from homeassistant.helpers.entity import EntityCategory
from .entity import ApcEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ApcDate(entry.runtime_data, "battery_date")])


class ApcDate(ApcEntity, DateEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self):
        return self.coordinator.data[self.key]

    async def async_set_value(self, value):
        await self.coordinator.async_write(self.key, value)
