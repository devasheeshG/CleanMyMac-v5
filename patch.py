#!/usr/bin/env python3
"""Inspect by default; create an explicitly requested patched app copy."""

import argparse
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from compatibility import CompatibilityError, find_app, inspect_app, load_profile, patched_bytes
from local_adapter import inject_adapter


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise CompatibilityError('Command failed: ' + command[0] + '\n' + result.stderr.strip())


def create_copy(app, output):
    """Stage, patch, and sign a new bundle; never overwrite an existing app."""
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise CompatibilityError('Patching requires native ARM64 macOS.')
    output = output.expanduser().resolve()
    if output.suffix != '.app' or output.exists():
        raise CompatibilityError('Output must be a new, nonexistent .app path.')
    if app == output or app in output.parents or output in app.parents:
        raise CompatibilityError('Output must be separate from the source app.')
    profile = load_profile()
    patched_bytes((app / 'Contents/MacOS/CleanMyMac_5').read_bytes(), profile)
    output.parent.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix='.cleanmymac-stage-', dir=output.parent))
    staged = workspace / output.name
    try:
        run(['ditto', str(app), str(staged)])
        run(['codesign', '--verify', '--deep', '--strict', str(staged)])
        binary = staged / 'Contents/MacOS/CleanMyMac_5'
        replacement = inject_adapter(patched_bytes(binary.read_bytes(), profile))
        stat = binary.stat()
        pending = binary.with_name(binary.name + '.pending')
        pending.write_bytes(replacement)
        os.chmod(pending, stat.st_mode & 0o777)
        os.replace(pending, binary)
        library = staged / 'Contents/Frameworks/CMM5LocalData.dylib'
        adapter_source = Path(__file__).resolve().parent / 'native/CMM5LocalData.m'
        run(['clang', '-dynamiclib', '-arch', 'arm64', '-fobjc-arc', '-framework', 'Foundation',
             str(adapter_source), '-o', str(library)])
        run(['codesign', '--force', '--sign', '-', '--timestamp=none', str(library)])
        # Restricted vendor entitlements are rejected with an ad-hoc signature.
        # Dropping them permits startup, but does not preserve all functionality.
        run(['codesign', '--force', '--sign', '-', '--timestamp=none', str(staged)])
        run(['codesign', '--verify', '--deep', '--strict', str(staged)])
        # Atomic no-clobber publication on macOS; never replace a user's bundle.
        libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        if rename(os.fsencode(staged), os.fsencode(output), 4):
            raise OSError(ctypes.get_errno(), 'Cannot publish staged app without replacing an existing path')
    finally:
        shutil.rmtree(workspace)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, help='Source app; defaults to /Applications/CleanMyMac.app')
    parser.add_argument('--check', action='store_true', help='Read-only compatibility check (default)')
    parser.add_argument('--json', action='store_true', help='Print the compatibility report as JSON')
    parser.add_argument('--apply', action='store_true', help='Create a separate patched app copy')
    parser.add_argument('--output', type=Path, help='New .app path; existing paths are never replaced')
    args = parser.parse_args(argv)
    if args.check and args.apply:
        parser.error('--check and --apply are mutually exclusive')
    if args.apply and args.output is None:
        parser.error('--apply requires --output /new/path.app')
    if not args.apply and args.output is not None:
        parser.error('--output requires --apply')
    try:
        app = find_app(args.app)
        report = inspect_app(app)
        if args.apply:
            if not report['preflight_passed']:
                raise CompatibilityError(report['reason'])
            output = create_copy(app, args.output)
            report.update(output=str(output), signature_check='passed',
                          entitlements_preserved=False,
                          startup_and_features_validated_by_this_run=False)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print('CleanMyMac', report['version'], 'build', report['build'])
            print('Profile:', report['profile_status'])
            print(report['reason'])
            if args.apply:
                print('Patched app copy:', report['output'])
                print('Vendor entitlements were not retained. The copy uses a local data adapter; features remain under test.')
                print('Source app unchanged. This command does not launch or install over it.')
        return 0 if report['preflight_passed'] else 2
    except (CompatibilityError, OSError) as error:
        if args.json:
            print(json.dumps({'error': str(error)}))
        else:
            print('ERROR:', error, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
