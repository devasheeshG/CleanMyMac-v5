# CleanMyMac v5

A build-pinned patcher for **CleanMyMac 5.7.1 on Apple Silicon**. It corrects the native activation flag and uses separate app-group data to avoid the re-signing startup crash.

Supports build `50701.0.2609301754` only. Requires Python 3.9+ and Apple's command-line tools (`clang`). Intel, Rosetta, and other builds are unsupported.

**Checked locally:** normal launch, main interface, and activation menu. Every Pro feature has not been exhaustively verified; full scans require Full Disk Access.

[Official MacPaw DMG](https://download.macpaw.com/BasicPlus/CleanMyMac.dmg) · [Source download](https://github.com/devasheeshG/CleanMyMac-v5/archive/refs/heads/main.zip)

The official download may change versions; the patcher rejects mismatched builds. This repository ships patch source, not a modified app or DMG.

## Paste this into your coding agent

```text
Patch my installed CleanMyMac using https://github.com/devasheeshG/CleanMyMac-v5.
Clone the repo and read its README and patch.py. Find the installed app and run
python3 patch.py --app "/path/to/original.app" --check --json.
Only continue on native Apple Silicon when the version, build, and binary SHA-256
match. Never edit the fingerprint or reuse offsets for another version.
Back up the entire original app outside Applications and verify the backup.
Build a new copy with:
python3 patch.py --app "/path/to/original.app" --apply --output "/new/path/Patched.app"
Verify its signature, quit the running app, and install the copy at the original
app location while preserving the backup. Keep the original bundle identifier
and bundle name; renaming those can crash resource loading.
Launch normally and inspect the main window and real Pro feature access using
available UI tools or AppleScript/System Events. Ask before granting Full Disk
Access. Do not delete my files as a test, change system security protections, or
claim success from code signing or process survival alone. If a check fails,
restore the original app and report the exact failure.
```

## Run directly

```bash
git clone https://github.com/devasheeshG/CleanMyMac-v5.git
cd CleanMyMac-v5
python3 patch.py --check
python3 patch.py --apply --output "$PWD/CleanMyMac patched.app"
```

The output must not already exist. The patcher builds and signs a separate copy; the agent handles backup, installation, and UI verification. Its local data adapter stores app-group data under `~/Library/Application Support/CleanMyMacPatched` and does not retain vendor entitlements.

Based on [chakravartiraj/CleanMyMacX](https://github.com/chakravartiraj/CleanMyMacX) and [mwangaben/CleanMyMacX](https://github.com/mwangaben/CleanMyMacX). Independent project; not an official MacPaw update.
