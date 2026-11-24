#!/bin/sh
# Compatibility entry point. The portable Node launcher owns timeout behavior.
set -u
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v node >/dev/null 2>&1; then
  exit 0
fi
exec node "$script_dir/droid-session-start.mjs"
