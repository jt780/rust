#!/bin/sh
set -eu

DATA_DIR=${MIXFLOW_DATA_DIR:-/data}
CONFIG="$DATA_DIR/config.toml"
port=${MIXFLOW_PANEL_PORT:-12321}
entry=""

if [ -f "$CONFIG" ]; then
  entry=$(awk '
    /^[[:space:]]*\[/ { inpanel = ($0 ~ /^[[:space:]]*\[panel\]/) }
    inpanel && $0 ~ /^[[:space:]]*entry[[:space:]]*=/ {
      sub(/^[^=]*=[[:space:]]*/, "")
      gsub(/^["\047]|["\047][[:space:]]*$/, "")
      sub(/[[:space:]]*$/, "")
      print; exit
    }' "$CONFIG")
fi

exec wget -q -O /dev/null "http://127.0.0.1:${port}${entry:-/}"
