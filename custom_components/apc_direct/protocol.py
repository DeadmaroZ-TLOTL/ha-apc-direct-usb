"""Direct USB HID for one descriptor-verified Back-UPS RS 500 profile.

The report layout is compiled from the actual descriptor using hid-tools.
No detach, reset, SET_CONFIGURATION, power commands or automatic write retry.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import threading
import time

MODEL = "Back-UPS RS 500"
REPORT_DESCRIPTOR_SHA256 = "1f6e71f3b24e30d23bdcec22e85461b8105a91d1d75169555fe3077753370773"


class ApcError(Exception):
    """A direct read or configuration operation failed."""


class WriteUncertain(ApcError):
    """A write was attempted, but its resulting value was not verified."""


@dataclass(frozen=True)
class Field:
    report: int
    length: int
    bit: int
    size: int
    scale: float = 1
    offset: float = 0
    signed: bool = False


FIELDS = {
    "battery_charge": Field(12, 2, 8, 8),
    "battery_voltage": Field(29, 3, 8, 16, .01),
    "battery_voltage_summary": Field(11, 3, 8, 16, .01),
    "battery_voltage_nominal": Field(31, 3, 8, 16, .01),
    "battery_runtime": Field(25, 3, 8, 16),
    "battery_temperature": Field(30, 3, 8, 16, .1, -273.15),
    "input_voltage": Field(32, 3, 8, 16, .1),
    "input_voltage_nominal": Field(70, 2, 8, 8),
    "output_voltage": Field(43, 3, 8, 16, .1),
    "output_frequency": Field(42, 3, 8, 16, .01),
    "load": Field(44, 3, 8, 16, .1),
    "nominal_real_power": Field(82, 3, 8, 16),
    "battery_date": Field(21, 3, 8, 16),
    "battery_charge_low": Field(17, 2, 8, 8),
    "battery_runtime_low": Field(26, 3, 8, 16),
    "battery_charge_warning": Field(15, 2, 8, 8),
    "input_sensitivity": Field(34, 2, 8, 8),
    "input_transfer_high": Field(35, 3, 8, 16),
    "input_transfer_low": Field(36, 3, 8, 16),
    "beeper": Field(20, 2, 8, 8),
    "charging": Field(51, 3, 8, 1),
    "discharging": Field(51, 3, 9, 1),
    "ac_present": Field(51, 3, 10, 1),
    "battery_present": Field(51, 3, 11, 1),
    "below_capacity_limit": Field(51, 3, 12, 1),
    "shutdown_imminent": Field(51, 3, 14, 1),
    "runtime_limit_expired": Field(51, 3, 15, 1),
    "need_replacement": Field(51, 3, 17, 1),
    "overload": Field(51, 3, 18, 1),
    "voltage_not_regulated": Field(51, 3, 19, 1),
}

# Runtime limits come from this UPS's descriptor, not another APC model.
NUMBER_SETTINGS = {
    "battery_charge_low": (0, 100, 1),
    "battery_runtime_low": (120, 1380, 1),
    "input_transfer_high": (254, 276, 1),
    "input_transfer_low": (182, 198, 1),
}
SELECT_SETTINGS = {
    "input_sensitivity": {"low": 0, "medium": 1, "high": 2},
    "beeper": {"disabled": 1, "enabled": 2, "muted": 3},
}
WRITABLE = frozenset((*NUMBER_SETTINGS, *SELECT_SETTINGS, "battery_date"))


def decode_value(field, data):
    if len(data) != field.length or data[0] != field.report:
        raise ApcError("Truncated or wrong USB report; no value inferred")
    raw = (int.from_bytes(data, "little") >> field.bit) & ((1 << field.size) - 1)
    if field.signed and raw & (1 << (field.size - 1)):
        raw -= 1 << field.size
    return raw


def pack_value(field, current, value):
    decode_value(field, current)
    if not 0 <= value < (1 << field.size):
        raise ValueError("Value does not fit the USB report")
    mask = ((1 << field.size) - 1) << field.bit
    number = (int.from_bytes(current, "little") & ~mask) | (value << field.bit)
    return number.to_bytes(field.length, "little")


def unpack_date(raw):
    try:
        return date(1980 + (raw >> 9), (raw >> 5) & 15, raw & 31)
    except ValueError:
        return None


def pack_date(value):
    if not isinstance(value, date) or not 1980 <= value.year <= 2107:
        raise ValueError("Battery date must be between 1980 and 2107")
    return ((value.year - 1980) << 9) | (value.month << 5) | value.day


class ApcUsb:
    def __init__(self, serial, device=None):
        if not isinstance(serial, str) or not serial.strip() or len(serial) > 128 or not serial.isprintable():
            raise ApcError("An explicit, printable UPS serial number is required")
        self.serial = serial.strip()
        self.device = device
        self._lock = threading.Lock()
        self._test_device = device is not None
        self._claimed = False
        self.last_write = None

    def _connect(self):
        if self.device is not None:
            return
        import usb.core
        import usb.util
        matches = []
        for device in usb.core.find(find_all=True, idVendor=0x051D, idProduct=0x0002):
            if device.serial_number.strip() == self.serial:
                matches.append(device)
        if len(matches) != 1:
            raise ApcError("The exact APC serial is not uniquely available")
        device = matches[0]
        if device.product != "Back-UPS RS 500 FW:30.j5.I USB FW:j5":
            raise ApcError("Unexpected APC model or firmware")
        try:
            # A live kernel/NUT owner is never forcibly detached.
            usb.util.claim_interface(device, 0)
            descriptor = bytes(device.ctrl_transfer(0x81, 6, 0x2200, 0, 1247, timeout=1000))
            if len(descriptor) != 1247 or hashlib.sha256(descriptor).hexdigest() != REPORT_DESCRIPTOR_SHA256:
                raise ApcError("Unsupported USB descriptor; all writes blocked")
        except Exception:
            usb.util.dispose_resources(device)
            raise
        self.device = device
        self._claimed = True

    def _get(self, field):
        data = bytes(self.device.ctrl_transfer(0xA1, 1, 0x300 | field.report, 0, field.length, timeout=500))
        decode_value(field, data)
        return data

    def _close(self):
        if self.device is not None and not self._test_device:
            import usb.util
            if self._claimed:
                try:
                    usb.util.release_interface(self.device, 0)
                except Exception:
                    pass
            usb.util.dispose_resources(self.device)
            self.device = None
            self._claimed = False

    def close(self):
        with self._lock:
            self._close()

    def snapshot(self):
        with self._lock:
            try:
                self._connect()
                start = time.time()
                reports = {}
                values = {}
                for key, field in FIELDS.items():
                    if field.report not in reports:
                        reports[field.report] = self._get(field)
                    raw = decode_value(field, reports[field.report])
                    if key == "battery_date":
                        values[key] = unpack_date(raw)
                    elif key in SELECT_SETTINGS:
                        values[key] = next((label for label, number in SELECT_SETTINGS[key].items() if number == raw), None)
                    elif field.size == 1:
                        values[key] = bool(raw)
                    else:
                        values[key] = round(raw * field.scale + field.offset, 3)
                if time.time() - start > 15:
                    raise ApcError("USB sample exceeded the freshness budget")
                values["sample_at"] = datetime.fromtimestamp(start, timezone.utc)
                values["duration"] = time.time() - start
                values["last_write"] = self.last_write
                return values
            except Exception:
                self._close()
                raise

    def set_setting(self, key, value):
        # Explicit allowlist: timer/test/calibration reports can never reach SET_REPORT.
        if key not in WRITABLE:
            raise ValueError("Not a supported configuration setting")
        if key in NUMBER_SETTINGS:
            low, high, step = NUMBER_SETTINGS[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high or value % step:
                raise ValueError("Setting outside this UPS's verified range")
            raw = int(value)
        elif key in SELECT_SETTINGS:
            if value not in SELECT_SETTINGS[key]:
                raise ValueError("Unsupported setting option")
            raw = SELECT_SETTINGS[key][value]
        else:
            raw = pack_date(value)
        field = FIELDS[key]
        with self._lock:
            self._connect()
            current = self._get(field)
            if decode_value(field, current) == raw:
                return
            payload = pack_value(field, current, raw)
            self.last_write = {"setting": key, "outcome": "unknown", "at": datetime.now(timezone.utc).isoformat()}
            try:
                count = self.device.ctrl_transfer(0x21, 9, 0x300 | field.report, 0, payload, timeout=1000)
                if count != len(payload):
                    raise WriteUncertain("Short USB write; not repeated")
                observed = decode_value(field, self._get(field))
                if observed != raw:
                    self.last_write.update(outcome="mismatch", observed=observed)
                    raise WriteUncertain("UPS readback differs; current state will be refreshed")
                self.last_write["outcome"] = "verified"
            except WriteUncertain:
                raise
            except Exception as error:
                self._close()
                raise WriteUncertain("USB write result uncertain; command not repeated") from error
