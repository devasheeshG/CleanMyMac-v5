"""Version-pinned CleanMyMac binary inspection; no network or account access."""

import hashlib
import json
import plistlib
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_APPS = (Path('/Applications/CleanMyMac.app'), Path('/Applications/CleanMyMac_5.app'), Path('/Applications/CleanMyMac-MAS.app'))


class CompatibilityError(ValueError):
    pass


def load_profile():
    return json.loads((ROOT / 'profiles' / '5.7.1-arm64.json').read_text())


def find_app(path=None):
    if path is not None:
        return Path(path).expanduser().resolve()
    for app in DEFAULT_APPS:
        if app.is_dir():
            return app.resolve()
    raise CompatibilityError('CleanMyMac app not found; use --app /path/to/app.app.')


def arm64_slice(data):
    """Return the ARM64 slice bounds in a universal Mach-O file."""
    try:
        magic, count = struct.unpack_from('>II', data)
        if magic != 0xCAFEBABE or count > 32:
            raise CompatibilityError('Expected a universal Mach-O binary.')
        if len(data) < 8 + count * 20:
            raise CompatibilityError('Truncated Mach-O architecture table.')
        slices = []
        for index in range(count):
            cpu, _, start, size, _ = struct.unpack_from('>IIIII', data, 8 + index * 20)
            if start < 8 + count * 20 or size < 32 or start + size > len(data):
                raise CompatibilityError('Invalid Mach-O slice bounds.')
            slices.append((start, start + size))
            if cpu == 0x0100000C:
                if 'arm' in locals():
                    raise CompatibilityError('Duplicate ARM64 architecture slices.')
                arm = (start, size)
        ordered = sorted(slices)
        if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
            raise CompatibilityError('Overlapping Mach-O architecture slices.')
        if 'arm' not in locals():
            raise CompatibilityError('ARM64 architecture is absent.')
        if struct.unpack_from('<I', data, arm[0])[0] != 0xFEEDFACF:
            raise CompatibilityError('Invalid ARM64 Mach-O header.')
        return arm
    except struct.error as error:
        raise CompatibilityError('Truncated Mach-O file.') from error


def patched_bytes(data, profile):
    """Validate the complete preimage before changing any byte in memory."""
    if hashlib.sha256(data).hexdigest() != profile['binary_sha256']:
        raise CompatibilityError('Binary SHA-256 does not match the exact supported build.')
    start, size = arm64_slice(data)
    intervals = []
    for patch in profile['patches']:
        old, new = bytes.fromhex(patch['before']), bytes.fromhex(patch['after'])
        offset = patch['file_offset']
        if not old or len(old) != len(new) or offset % 4 or len(old) % 4:
            raise CompatibilityError('Invalid ARM64 patch length or alignment.')
        if not start <= offset or offset + len(old) > start + size:
            raise CompatibilityError('Patch lies outside the ARM64 slice.')
        if data[offset:offset + len(old)] != old:
            raise CompatibilityError('Instruction preimage mismatch: ' + patch['name'])
        intervals.append((offset, offset + len(old)))
    ordered = sorted(intervals)
    if any(left[1] > right[0] for left, right in zip(ordered, ordered[1:])):
        raise CompatibilityError('Overlapping patch sites.')
    result = bytearray(data)
    for patch in profile['patches']:
        offset = patch['file_offset']
        replacement = bytes.fromhex(patch['after'])
        result[offset:offset + len(replacement)] = replacement
    return bytes(result)


def inspect_app(app):
    profile = load_profile()
    try:
        info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException) as error:
        raise CompatibilityError('Cannot read app Info.plist: ' + str(error)) from error
    executable = info.get('CFBundleExecutable', '')
    if not executable or Path(executable).name != executable:
        raise CompatibilityError('Invalid bundle executable name.')
    binary = app / 'Contents/MacOS' / executable
    try:
        data = binary.read_bytes()
    except OSError as error:
        raise CompatibilityError('Cannot read app executable: ' + str(error)) from error
    report = {
        'app': str(app),
        'version': info.get('CFBundleShortVersionString'),
        'build': info.get('CFBundleVersion'),
        'bundle_id': info.get('CFBundleIdentifier'),
        'binary_sha256': hashlib.sha256(data).hexdigest(),
        'profile_status': 'unsupported',
        'preflight_passed': False,
        'feature_validation': 'not_verified',
    }
    if any(report[key] != profile[key] for key in ('version', 'build', 'bundle_id')):
        report['reason'] = 'No profile for this exact version, build, and distribution.'
        return report
    try:
        patched_bytes(data, profile)
    except CompatibilityError as error:
        report['reason'] = str(error)
        return report
    report.update(profile_status=profile['status'], preflight_passed=True,
                  patch_sites=len(profile['patches']),
                  reason='Exact preimage matches the corrected patch profile. Functional validation is required.')
    return report
