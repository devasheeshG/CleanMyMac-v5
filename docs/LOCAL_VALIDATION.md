# CleanMyMac 5.7.1 local validation

Test date: 2026-10-11. Host architecture: native ARM64 macOS.

## Exact input

- Version: `5.7.1`
- Build: `50701.0.2609301754`
- Bundle identifier: `com.macpaw.CleanMyMac5`
- Main executable: `CleanMyMac_5`
- Universal binary: x86_64 and arm64 slices
- Original executable SHA-256: `e507ea1323a090f6218f233fa682b33862a7a5efcdda8d102a91c9f5906db5f1`

The three inherited Intel 4.11.4 signatures have zero matches in their fork-selected binaries. The old target identifiers were absent in the main executable and 134 framework executables inspected. Upstream comparison identified one additional commit in the path-detection fork: [6eadc55](https://github.com/chakravartiraj/CleanMyMacX/commit/6eadc55c1bef6ec3b878f01e8fb7ef3cce525941). It did not update the patch instructions.

## Candidate preparation

Static analysis found the version 5 native activation layer and its Combine activation subject. The experimental profile changes a getter and four candidate subject-value instructions in the ARM64 slice of the main executable. This is a hypothesis about activation behavior, not a proven full-feature fix. The profile pins the complete executable hash and original instructions. The Intel slice and framework executables are not patched.

## Observed results

- Original app was read for metadata, signatures, and disassembly; its main executable was not modified.
- All five expected instruction preimages matched.
- A separate app copy was patched and ad-hoc signed.
- Strict recursive `codesign` verification passed.
- Retaining original vendor entitlements caused immediate `SIGKILL` on launch, exit code `-9`.
- AMFI reported error `-424`: the file was ad-hoc signed but contained restricted entitlements.
- Re-signing the copy without vendor entitlements allowed the process to remain alive for an initial 10-second startup observation and a subsequent 30-second observation of the CLI-prepared copy. Both test processes were then terminated.
- The CLI successfully prepared a separate copy and passed signature checks. The installed executable SHA-256 was unchanged after the startup test.
- The tooling's 17 automated tests passed locally.

The installed app was not replaced. No cleanup action or deliberate account/credential changes were performed. The copy retains the original bundle identifier and may share app data; startup was not isolated from the user's data directories. Vendor binaries and private runtime logs are excluded from the repository.

## What is not verified

The session did not expose the required native Computer Use tool, so the UI could not be inspected or driven. There is no evidence yet that the patch unlocks paid features, changes the activation screen correctly, or makes cleanup actions work.

Further validation is required for native activation state, representative feature actions, Full Disk Access and other permissions, application groups and keychain access after identity changes, menu and helper components, relaunch, and updater behavior. Intel and other builds are unsupported by this profile.

**Conclusion: an experimental patch can be prepared and can start without vendor entitlements. A properly working CleanMyMac 5.7.1 installation fix has not been established.**

## Public solution search

GitHub and web searches included CleanMyMac 5.7.1, ARM64 patches, `ActivationManagerMPA`, and `MPALibLicenseValidationResult`. They did not yield a public source solution verified for this exact build. The original [mwangaben repository](https://github.com/mwangaben/CleanMyMacX), [AntonioBerna's repository](https://github.com/AntonioBerna/clean-my-mac-x), and [mio-19's repository](https://github.com/mio-19/CleanMyMacXPatcher) target CleanMyMac X rather than an established fix for this input. This search result is not proof that no other solution exists.
