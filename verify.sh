#!/bin/sh
# Signature verification does not establish activation or functional compatibility.
set -eu
app=${1:-/Applications/CleanMyMac_5.app}
codesign --verify --deep --strict "$app"
printf '%s\n' 'Signature check passed. Activation and feature behavior are not verified by codesign.'
