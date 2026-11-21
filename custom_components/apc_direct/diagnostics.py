async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {"source": "direct USB HID", "model": "Back-UPS RS 500", "firmware": "30.j5.I",
            "last_update_success": coordinator.last_update_success,
            "data": coordinator.data, "last_write": coordinator.usb.last_write}
