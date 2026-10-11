import contextlib
import copy
import hashlib
import io
import json
import plistlib
import shutil
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compatibility
import patch as patch_cli
from search_wildcard import find_offsets


def fixture():
    data = bytearray(512)
    struct.pack_into('>II', data, 0, 0xCAFEBABE, 2)
    struct.pack_into('>IIIII', data, 8, 0x01000007, 3, 64, 128, 2)
    struct.pack_into('>IIIII', data, 28, 0x0100000C, 0, 256, 256, 2)
    struct.pack_into('<I', data, 256, 0xFEEDFACF)
    data[300:308] = bytes.fromhex('ffc300d1f44f01a9')
    profile = {
        'binary_sha256': hashlib.sha256(data).hexdigest(),
        'version': '5.7.1', 'build': 'test-build', 'bundle_id': 'com.macpaw.CleanMyMac5',
        'patches': [{'name': 'fixture', 'file_offset': 300,
                     'before': 'ffc300d1f44f01a9', 'after': '20008052c0035fd6'}],
    }
    return bytes(data), profile


class BinaryTests(unittest.TestCase):
    def setUp(self):
        self.data, self.profile = fixture()

    def test_only_arm64_bytes_change(self):
        result = compatibility.patched_bytes(self.data, self.profile)
        self.assertEqual(len(result), len(self.data))
        self.assertEqual(result[:300], self.data[:300])
        self.assertEqual(result[308:], self.data[308:])
        self.assertEqual(result[300:308], bytes.fromhex('20008052c0035fd6'))

    def test_modified_binary_is_rejected(self):
        with self.assertRaisesRegex(compatibility.CompatibilityError, 'SHA-256'):
            compatibility.patched_bytes(self.data + b'x', self.profile)

    def test_wrong_instruction_preimage_is_rejected(self):
        self.profile['patches'][0]['before'] = '0000000000000000'
        with self.assertRaisesRegex(compatibility.CompatibilityError, 'preimage'):
            compatibility.patched_bytes(self.data, self.profile)

    def test_intel_patch_is_rejected(self):
        self.profile['patches'][0]['file_offset'] = 64
        with self.assertRaisesRegex(compatibility.CompatibilityError, 'outside'):
            compatibility.patched_bytes(self.data, self.profile)

    def test_overlapping_patches_are_rejected(self):
        self.profile['patches'].append(copy.deepcopy(self.profile['patches'][0]))
        with self.assertRaisesRegex(compatibility.CompatibilityError, 'Overlapping patch'):
            compatibility.patched_bytes(self.data, self.profile)

    def test_truncated_file_is_rejected(self):
        with self.assertRaises(compatibility.CompatibilityError):
            compatibility.arm64_slice(b'\xca\xfe\xba\xbe')

    def test_out_of_bounds_slice_is_rejected(self):
        data = bytearray(self.data)
        struct.pack_into('>I', data, 40, 99999)
        with self.assertRaisesRegex(compatibility.CompatibilityError, 'bounds'):
            compatibility.arm64_slice(data)

    def test_duplicate_arm64_slices_are_rejected(self):
        data = bytearray(self.data)
        struct.pack_into('>I', data, 8, 0x0100000C)
        with self.assertRaisesRegex(compatibility.CompatibilityError, 'Duplicate'):
            compatibility.arm64_slice(data)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / 'Source.app'
        (self.app / 'Contents/MacOS').mkdir(parents=True)
        self.data, self.profile = fixture()
        self.binary = self.app / 'Contents/MacOS/CleanMyMac_5'
        self.binary.write_bytes(self.data)
        self.info = {
            'CFBundleExecutable': 'CleanMyMac_5',
            'CFBundleShortVersionString': self.profile['version'],
            'CFBundleVersion': self.profile['build'],
            'CFBundleIdentifier': self.profile['bundle_id'],
        }
        self.write_info()

    def write_info(self):
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps(self.info))

    def test_dry_run_does_not_write_and_reports_experimental(self):
        with patch('compatibility.load_profile', return_value=self.profile):
            report = compatibility.inspect_app(self.app)
        self.assertEqual(self.binary.read_bytes(), self.data)
        self.assertTrue(report['experimental_preflight_passed'])
        self.assertEqual(report['feature_validation'], 'not_verified')
        self.assertEqual(report['profile_status'], 'experimental')

    def test_new_build_is_unsupported(self):
        self.info['CFBundleVersion'] = 'different-build'
        self.write_info()
        with patch('compatibility.load_profile', return_value=self.profile):
            report = compatibility.inspect_app(self.app)
        self.assertFalse(report['experimental_preflight_passed'])

    def test_source_or_existing_destination_is_never_overwritten(self):
        with patch('patch.platform.system', return_value='Darwin'), patch('patch.platform.machine', return_value='arm64'):
            with self.assertRaises(compatibility.CompatibilityError):
                patch_cli.create_copy(self.app, self.app)
        self.assertEqual(self.binary.read_bytes(), self.data)

    def test_sign_failure_leaves_source_and_destination_untouched(self):
        destination = self.root / 'Output.app'

        def run(command):
            if command[0] == 'ditto':
                shutil.copytree(command[1], command[2])
            elif '--verify' in command:
                return
            else:
                raise compatibility.CompatibilityError('simulated signing failure')

        with patch('patch.platform.system', return_value='Darwin'), patch('patch.platform.machine', return_value='arm64'), patch('patch.load_profile', return_value=self.profile), patch('patch.run', side_effect=run):
            with self.assertRaisesRegex(compatibility.CompatibilityError, 'signing failure'):
                patch_cli.create_copy(self.app, destination)
        self.assertFalse(destination.exists())
        self.assertEqual(self.binary.read_bytes(), self.data)
        self.assertEqual(list(self.root.glob('.cleanmymac-stage-*')), [])

    def test_check_command_produces_json(self):
        stream = io.StringIO()
        with patch('compatibility.load_profile', return_value=self.profile), contextlib.redirect_stdout(stream):
            code = patch_cli.main(['--app', str(self.app), '--check', '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stream.getvalue())['profile_status'], 'experimental')


class WildcardTests(unittest.TestCase):
    def test_wildcard_matches_null_newline_and_literal_regex_characters(self):
        self.assertEqual(find_offsets(b'\x55\x00\x2e\x55\x0a\x2e', '55 ?? 2e'), [0, 3])

    def test_literal_zero_is_not_a_wildcard(self):
        self.assertEqual(find_offsets(b'\x55\x01\x55\x00', '55 00'), [2])

    def test_overlapping_matches(self):
        self.assertEqual(find_offsets(b'\x55\x55\x55', '55 55'), [0, 1])

    def test_invalid_patterns(self):
        for pattern in ('', '5', 'gg', '???', '5500'):
            with self.subTest(pattern=pattern), self.assertRaises(ValueError):
                find_offsets(b'abc', pattern)


if __name__ == '__main__':
    unittest.main()
