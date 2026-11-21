import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN
from .protocol import ApcUsb


class ApcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            serial = user_input.get("serial", "").strip()
            if not serial or len(serial) > 128 or not serial.isprintable():
                errors["serial"] = "invalid_serial"
            else:
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                client = ApcUsb(serial)
                try:
                    await self.hass.async_add_executor_job(client.snapshot)
                except Exception:
                    errors["base"] = "cannot_connect"
                finally:
                    await self.hass.async_add_executor_job(client.close)
                if not errors:
                    return self.async_create_entry(title="APC Back-UPS RS 500 USB", data={"serial": serial})
        return self.async_show_form(step_id="user", errors=errors,
            data_schema=vol.Schema({vol.Required("serial"): str}))
