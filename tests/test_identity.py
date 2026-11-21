import sys
import types
import unittest
from unittest.mock import patch

from test_protocol import FIXTURE, TEST_SERIAL, p


class DescriptorDevice:
    def __init__(self,serial,descriptor=None,product=None):
        self.serial_number=serial
        self.product=product or 'Back-UPS RS 500 FW:30.j5.I USB FW:j5'
        self.descriptor=descriptor if descriptor is not None else bytes.fromhex(FIXTURE['descriptor'])
        self.calls=[]

    def ctrl_transfer(self,*args,**kwargs):
        self.calls.append(args)
        return self.descriptor


class IdentityTests(unittest.TestCase):
    def modules(self,devices,busy=False):
        calls=[]
        usb=types.ModuleType('usb');core=types.ModuleType('usb.core');util=types.ModuleType('usb.util')
        core.find=lambda **kwargs:devices
        def claim(device,interface):
            calls.append(('claim',device.serial_number,interface))
            if busy:raise OSError('USB owner busy')
        util.claim_interface=claim
        util.release_interface=lambda device,interface:calls.append(('release',device.serial_number,interface))
        util.dispose_resources=lambda device:calls.append(('dispose',device.serial_number))
        usb.core=core;usb.util=util
        return {'usb':usb,'usb.core':core,'usb.util':util},calls

    def test_only_configured_serial_is_claimed(self):
        other=DescriptorDevice('OTHER0000001');selected=DescriptorDevice(TEST_SERIAL+'  ')
        modules,calls=self.modules([other,selected])
        with patch.dict(sys.modules,modules):
            client=p.ApcUsb(TEST_SERIAL);client._connect()
            self.assertIs(client.device,selected)
            self.assertEqual(other.calls,[])
            self.assertEqual(selected.calls[0],(0x81,6,0x2200,0,1247))
            client.close()
        self.assertEqual([c[0] for c in calls],['claim','release','dispose'])

    def test_ambiguous_serial_is_rejected(self):
        modules,calls=self.modules([DescriptorDevice(TEST_SERIAL),DescriptorDevice(TEST_SERIAL)])
        with patch.dict(sys.modules,modules):
            with self.assertRaises(p.ApcError):p.ApcUsb(TEST_SERIAL)._connect()
        self.assertEqual(calls,[])

    def test_unknown_descriptor_releases_resources(self):
        device=DescriptorDevice(TEST_SERIAL,b'unsupported')
        modules,calls=self.modules([device])
        with patch.dict(sys.modules,modules):
            with self.assertRaises(p.ApcError):p.ApcUsb(TEST_SERIAL)._connect()
        self.assertEqual([c[0] for c in calls],['claim','dispose'])
        self.assertTrue(all(c[0]&0x80 for c in device.calls))

    def test_wrong_firmware_is_not_claimed(self):
        device=DescriptorDevice(TEST_SERIAL,product='Unsupported firmware')
        modules,calls=self.modules([device])
        with patch.dict(sys.modules,modules):
            with self.assertRaises(p.ApcError):p.ApcUsb(TEST_SERIAL)._connect()
        self.assertEqual(calls,[])

    def test_busy_owner_is_not_detached_or_reset(self):
        device=DescriptorDevice(TEST_SERIAL);modules,calls=self.modules([device],busy=True)
        with patch.dict(sys.modules,modules):
            with self.assertRaises(OSError):p.ApcUsb(TEST_SERIAL)._connect()
        self.assertEqual([c[0] for c in calls],['claim','dispose'])
        self.assertEqual(device.calls,[])


if __name__=='__main__':unittest.main()
