from datetime import date
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("apc_protocol", ROOT/"custom_components/apc_direct/protocol.py")
p = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = p
SPEC.loader.exec_module(p)
FIXTURE = json.loads((Path(__file__).with_name("synthetic_usb_fixture.json")).read_text())
TEST_SERIAL = "TEST00000001"


class FakeUsb:
    def __init__(self):
        self.reports = {int(k):bytes.fromhex(v) for k,v in FIXTURE["reports"].items()}
        self.calls = []
        self.write_error = False
        self.readback_error = False
        self.clamp = False

    def ctrl_transfer(self, kind, request, value, interface, data, timeout):
        self.calls.append((kind, request, value, interface, data))
        assert interface == 0 and value >> 8 == 3
        report = value & 255
        if kind == 0xA1:
            assert request == 1
            if self.readback_error and any(c[0]==0x21 for c in self.calls):
                raise OSError("USB disconnected after write")
            return self.reports[report]
        assert kind == 0x21 and request == 9
        if self.write_error:
            raise OSError("Uncertain USB acknowledgement")
        if not self.clamp:
            self.reports[report] = bytes(data)
        return len(data)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.device = FakeUsb()
        self.client = p.ApcUsb(TEST_SERIAL, device=self.device)

    def writes(self):
        return [c for c in self.device.calls if c[0] == 0x21]

    def test_exact_descriptor_hash(self):
        self.assertEqual(hashlib.sha256(bytes.fromhex(FIXTURE["descriptor"])).hexdigest(), p.REPORT_DESCRIPTOR_SHA256)

    def test_offsets_match_hidtools_compiled_profile(self):
        for key,field in p.FIELDS.items():
            with self.subTest(key=key):
                self.assertEqual(len(self.device.reports[field.report]), field.length)
                if key == "input_voltage":
                    continue  # APC exposes this buffered/array report outside variable fields.
                fields=FIXTURE["metadata"][str(field.report)]["fields"]
                self.assertTrue(any(f["start"]==field.bit and f["size"]==field.size for f in fields))

    def test_status_usage_identity(self):
        expected={"charging":0x850044, "discharging":0x850045, "ac_present":0x8500D0,
                  "battery_present":0x8500D1, "below_capacity_limit":0x850042,
                  "shutdown_imminent":0x840069, "runtime_limit_expired":0x850043,
                  "need_replacement":0x85004B, "overload":0x840065, "voltage_not_regulated":0x8500DB}
        for key,usage in expected.items():
            field=p.FIELDS[key]
            actual=next(f for f in FIXTURE["metadata"][str(field.report)]["fields"] if f["start"]==field.bit)
            self.assertEqual(actual["usage"],usage,key)

    def test_synthetic_measurements(self):
        data=self.client.snapshot()
        self.assertEqual(data["battery_charge"],75)
        self.assertEqual(data["battery_voltage"],12.5)
        self.assertEqual(data["battery_voltage_summary"],12.5)
        self.assertEqual(data["battery_runtime"],900)
        self.assertEqual(data["input_voltage"],230.0)
        self.assertEqual(data["output_voltage"],230.0)
        self.assertAlmostEqual(data["battery_temperature"],24.95)
        self.assertEqual(data["battery_date"],date(2020,1,2))
        self.assertTrue(data["charging"])
        self.assertFalse(data["below_capacity_limit"])
        self.assertFalse(data["runtime_limit_expired"])
        self.assertFalse(data["shutdown_imminent"])
        self.assertEqual(self.writes(),[])

    def test_single_read_per_report(self):
        self.client.snapshot()
        ids=[c[2] for c in self.device.calls]
        self.assertEqual(len(ids),len(set(ids)))

    def test_number_write_readback(self):
        self.client.set_setting("battery_charge_low",11)
        self.assertEqual(self.writes()[0][4],bytes([17,11]))
        self.assertEqual(self.client.last_write["outcome"],"verified")

    def test_all_supported_fields_roundtrip(self):
        values={"battery_charge_low":11,"battery_runtime_low":121,"input_transfer_high":267,
                "input_transfer_low":191,"input_sensitivity":"high","beeper":"enabled","battery_date":date(2024,6,15)}
        for key,value in values.items():
            self.client.set_setting(key,value)
        self.assertEqual(set(values),set(p.WRITABLE))
        data=self.client.snapshot()
        for key,value in values.items():
            self.assertEqual(data[key],value)

    def test_unchanged_value_does_not_write(self):
        self.client.set_setting("input_sensitivity","medium")
        self.assertEqual(self.writes(),[])

    def test_unknown_writes_never_retried(self):
        self.device.write_error=True
        with self.assertRaises(p.WriteUncertain):
            self.client.set_setting("battery_charge_low",11)
        self.assertEqual(len(self.writes()),1)
        self.assertEqual(self.client.last_write["outcome"],"unknown")
        self.client.snapshot()
        self.assertEqual(len(self.writes()),1)

    def test_missing_readback_is_not_success(self):
        self.device.readback_error=True
        with self.assertRaises(p.WriteUncertain):
            self.client.set_setting("battery_charge_low",11)
        self.assertEqual(len(self.writes()),1)
        self.assertEqual(self.client.last_write["outcome"],"unknown")

    def test_readback_mismatch_is_not_success(self):
        self.device.clamp=True
        with self.assertRaises(p.WriteUncertain):
            self.client.set_setting("battery_charge_low",11)
        self.assertEqual(self.client.last_write["outcome"],"mismatch")
        self.assertEqual(self.client.last_write["observed"],10)

    def test_no_power_test_or_calibration_write(self):
        for key in ("load.off","shutdown","shutdown_imminent","battery_voltage","test", "battery_float_voltage", "driver.killpower"):
            with self.assertRaises(ValueError):
                self.client.set_setting(key,1)
        self.assertEqual(self.device.calls,[])

    def test_invalid_values_never_touch_usb(self):
        for value in (-1,101,True,float("nan"),float("inf"),10.5,"11",None):
            with self.assertRaises(ValueError):
                self.client.set_setting("battery_charge_low",value)
        self.assertEqual(self.device.calls,[])

    def test_bad_enum_never_touches_usb(self):
        with self.assertRaises(ValueError):
            self.client.set_setting("input_sensitivity","maximum")
        self.assertEqual(self.device.calls,[])

    def test_short_or_wrong_report_not_zero(self):
        for value in (b"",b"\x0c",b"\x0d\x00"):
            self.device.reports[12]=value
            with self.assertRaises(p.ApcError):
                self.client.snapshot()

    def test_date_limits(self):
        for d in (date(1980,1,1),date(2107,12,31),date(2020,1,2)):
            self.assertEqual(p.unpack_date(p.pack_date(d)),d)
        self.assertIsNone(p.unpack_date(0))
        with self.assertRaises(ValueError):p.pack_date(date(1979,1,1))

    def test_serial_scope(self):
        for invalid in (None, "", "   ", "invalid\nserial", "x"*129):
            with self.assertRaises(p.ApcError):p.ApcUsb(invalid)
        self.assertEqual(p.ApcUsb("  TEST00000002  ").serial,"TEST00000002")

    def test_payload_preserves_other_bits(self):
        field=p.Field(51,3,12,1)
        before=bytes.fromhex("339d08")
        after=p.pack_value(field,before,0)
        self.assertEqual(int.from_bytes(before,"little")^int.from_bytes(after,"little"),1<<12)


if __name__=="__main__":unittest.main()
