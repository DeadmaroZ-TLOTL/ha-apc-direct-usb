import json
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_manifest(self):
        manifest=json.loads((ROOT/'custom_components/apc_direct/manifest.json').read_text())
        self.assertEqual(manifest['domain'],'apc_direct')
        self.assertEqual(manifest['requirements'],['pyusb==1.3.1'])
        self.assertTrue(manifest['config_flow'])

    def test_english_translation_matches(self):
        component=ROOT/'custom_components/apc_direct'
        self.assertEqual(json.loads((component/'strings.json').read_text()),
                         json.loads((component/'translations/en.json').read_text()))

    def test_dashboard_has_no_power_actions(self):
        card=json.loads((ROOT/'examples/dashboard.json').read_text())
        self.assertFalse(card['show_header_toggle'])
        def visit(item):
            if isinstance(item,dict):
                if 'action' in item:self.assertIn(item['action'],('navigate','more-info','none'))
                if 'entity' in item:self.assertIn('.apc_back_ups_rs_500_',item['entity'])
                for value in item.values():visit(value)
            elif isinstance(item,list):
                for value in item:visit(value)
        visit(card)

    def test_brand_assets_are_png(self):
        brand=ROOT/'custom_components/apc_direct/brand'
        for name,side in (('icon.png',256),('icon@2x.png',512)):
            data=(brand/name).read_bytes()
            self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II',data[16:24]),(side,side))

    def test_fixture_is_synthetic(self):
        data=json.loads((ROOT/'tests/synthetic_usb_fixture.json').read_text())
        self.assertIn('Synthetic',data['description'])
        self.assertNotIn('serial',data)
        self.assertNotIn('measured_at',data)


if __name__=='__main__':unittest.main()
