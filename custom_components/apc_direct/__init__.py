"""APC Direct USB integration."""
from datetime import timedelta
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, PLATFORMS
from .protocol import ApcUsb

LOGGER = logging.getLogger(__name__)


class ApcCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=5))
        self.usb = ApcUsb(entry.data["serial"])

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.usb.snapshot)
        except Exception as error:
            raise UpdateFailed(f"Direct APC USB read failed: {error}") from error

    async def async_write(self, key, value):
        try:
            await self.hass.async_add_executor_job(self.usb.set_setting, key, value)
        except Exception as error:
            raise HomeAssistantError(f"APC setting not verified: {error}") from error
        finally:
            await self.async_refresh()


async def async_setup_entry(hass, entry):
    coordinator = ApcCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await hass.async_add_executor_job(coordinator.usb.close)
        raise
    entry.runtime_data = coordinator

    async def close(event):
        await hass.async_add_executor_job(coordinator.usb.close)

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, close))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.async_add_executor_job(entry.runtime_data.usb.close)
        return True
    return False
