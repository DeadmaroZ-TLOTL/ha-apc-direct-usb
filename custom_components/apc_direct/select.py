from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import EntityCategory
from .entity import ApcEntity
from .protocol import SELECT_SETTINGS


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(ApcSelect(entry.runtime_data, key) for key in SELECT_SETTINGS)


class ApcSelect(ApcEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, key):
        super().__init__(coordinator, key)
        self._attr_options = list(SELECT_SETTINGS[key])

    @property
    def current_option(self):
        return self.coordinator.data[self.key]

    async def async_select_option(self, option):
        await self.coordinator.async_write(self.key, option)
