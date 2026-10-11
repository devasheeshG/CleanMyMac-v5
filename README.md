# CleanMyMac v5 — Experimental ARM64 Patch & Compatibility Tools

Python tools for inspecting CleanMyMac 5 on macOS and reproducing a version-pinned Apple Silicon patch experiment. This project continues the research from [chakravartiraj/CleanMyMacX](https://github.com/chakravartiraj/CleanMyMacX) and [mwangaben/CleanMyMacX](https://github.com/mwangaben/CleanMyMacX).

**Status: experimental. There is no verified full-feature unlock for CleanMyMac 5.7.1 in this repository.** A patched copy passed signature checks and remained running during a short local startup test after removing vendor entitlements. Activation, cleanup, permissions, menu components, and paid features have not been verified. See [the local validation report](docs/LOCAL_VALIDATION.md).

## What this fork changes

- Detects the installed version, build, bundle identifier, and executable SHA-256.
- Inspects by default; running `patch.py` without arguments never modifies the app.
- Provides an experimental native ARM64 profile for one exact CleanMyMac 5.7.1 build.
- Checks the complete binary hash and every instruction preimage before preparing a patch.
- Creates a separate app copy, signs it, and checks its signature before publishing the copy to the requested local path.
- Refuses existing output paths and never installs over the source app.
- Fixes wildcard searches so `??` matches any single byte, including null and newline, while literal `00` remains literal.
- Includes automated tests for malformed binaries, mismatched builds, patch boundaries, read-only checks, and failure cleanup.

The inherited fork added version 5 path detection but retained the Intel 4.11.4 instructions. Its version 5 menu path actually points to the updater. These changes did not establish version 5 patch compatibility. The inherited script is archived at [legacy/patch_v4.py](legacy/patch_v4.py); the new command does not execute it.

## Compatibility

- **CleanMyMac 5.7.1, build `50701.0.2609301754`, bundle `com.macpaw.CleanMyMac5`:** experimental native ARM64 profile; startup observed, functionality unverified.
- **Intel Macs or launching the Intel slice through Rosetta:** unsupported by the new profile. The x86_64 slice is unchanged.
- **Other builds, App Store variants, Setapp variants, or modified executables:** unsupported unless the exact metadata and hash match the profile.
- **CleanMyMac X 4.11.4:** the inherited patch was documented for the Intel App Store build. It has not been retested here.

A matching application name or version number is insufficient. The exact executable fingerprint must match:

```text
e507ea1323a090f6218f233fa682b33862a7a5efcdda8d102a91c9f5906db5f1
```

## Requirements

Read-only checks and binary searches require Python 3.9 or newer and no third-party Python packages. Creating an experimental copy additionally requires macOS on Apple Silicon and the system `ditto` and `codesign` commands. No `sudo` is needed for a destination owned by your user.

## Quick start: inspect your installation

```bash
git clone git@github.com:devasheeshG/CleanMyMac-v5.git
cd CleanMyMac-v5
python3 patch.py --check
```

For machine-readable output or a different app location:

```bash
python3 patch.py --check --json
python3 patch.py --app "/path/to/CleanMyMac_5.app" --check --json
```

Exit codes:

- `0`: the exact experimental preimage matches, or a requested copy was prepared. This is **not** proof of feature compatibility.
- `1`: an I/O, validation, signing, or copy preparation error occurred.
- `2`: no matching experimental profile, or invalid command-line arguments.

## Reproduce the experimental patch

This is intended for testing, not an established installation fix. Ad-hoc signing with the vendor's restricted entitlements causes macOS AMFI to reject launch. The copy command therefore signs without those entitlements. That changes the app's identity and may affect existing permissions, application groups, keychain access, and other capabilities. Passing `codesign --verify` does not prove that those capabilities work.

Use a new destination that does not already exist:

```bash
python3 patch.py --apply --experimental \
  --output "$PWD/local-build/CleanMyMac-v5-Experimental.app"
```

The command:

1. Checks the source metadata, complete SHA-256, ARM64 slice, and five instruction preimages.
2. Copies the app into a temporary staging directory beside the destination and verifies the original signatures.
3. Changes only the five experimental ARM64 sites in the copied main executable.
4. Ad-hoc signs the copy without retaining vendor entitlements.
5. Runs strict recursive signature verification and moves the result into place without overwriting an existing path.

It does not launch the copy, clean files, install over `/Applications/CleanMyMac_5.app`, change a license, or modify system security settings. The copy retains the source bundle identifier and can share app data with the source, so it is not an isolated user-data environment. A preparation failure removes its staging directory and leaves the source unchanged.

## Verify a signature

```bash
sh verify.sh
sh verify.sh "$PWD/local-build/CleanMyMac-v5-Experimental.app"
```

The optional path defaults to the installed version 5 app. This command only checks signing integrity.

## Binary research tools

Search for the inherited Intel 4.11.4 signatures:

```bash
python3 search_hex.py "/path/to/executable"
```

Those signatures are historical diagnostics, not version 5 support indicators. For an exact or wildcard pattern:

```bash
python3 search_wildcard.py "/path/to/executable" "55 48 ?? 00"
```

Offsets are file offsets, not virtual memory addresses. Matches can overlap. Both search commands only read the supplied file; neither applies a patch.

The experimental profile lives in [profiles/5.7.1-arm64-experimental.json](profiles/5.7.1-arm64-experimental.json). Do not reuse its offsets for another build or edit its fingerprint to force a match.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests use synthetic binary fixtures. They verify the tooling's behavior, not CleanMyMac's activation or paid functionality. GitHub Actions runs them on Python 3.9 and 3.12. Local app startup evidence is documented separately.

## Repository layout

- `patch.py`: read-only preflight and experimental copy preparation.
- `compatibility.py`: bundle inspection and binary validation.
- `profiles/`: exact-build patch candidates and validation status.
- `search_hex.py`, `search_wildcard.py`: read-only binary searches.
- `verify.sh`: signature verification.
- `tests/`: tooling tests; no vendor binaries or account data.
- `docs/LOCAL_VALIDATION.md`: observed results and unresolved checks.
- `legacy/patch_v4.py`: inherited script retained for historical reference.

## Troubleshooting and contributing

**No matching profile / SHA-256 mismatch:** the build, distribution, or executable differs. The tool will not patch it. Keep the source app intact; there is no reason to delete and redownload it just to satisfy a fingerprint.

**The copy launches but features remain unavailable:** report the result as a failed or incomplete experiment. Startup does not establish that activation or feature checks were bypassed.

**Signature verification passes but macOS rejects launch:** signature structure and runtime authorization are separate checks. The original vendor entitlements cannot simply be retained with an ad-hoc identity. Do not disable macOS protections to make this experiment run.

For an issue or contribution, include the app version, build, bundle identifier, CPU architecture, preflight result, and exact steps that failed. Do not upload license tokens, account details, private logs, or application binaries. A future profile should remain experimental until activation, representative feature actions, permissions, helper components, and restart behavior have actually been tested.

## Credits and affiliation

Original CleanMyMac X patch: [mwangaben/CleanMyMacX](https://github.com/mwangaben/CleanMyMacX). Version 5 path-detection fork: [chakravartiraj/CleanMyMacX](https://github.com/chakravartiraj/CleanMyMacX).

This is an independent research project, not a MacPaw product or an official CleanMyMac update. CleanMyMac and MacPaw names belong to their respective owners. The inherited repository did not include a license file; this fork does not assert a new license over that inherited code.
