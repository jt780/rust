#!/bin/sh
set -eu

DATA_DIR=${MIXFLOW_DATA_DIR:-/data}
BIN=${MIXFLOW_BIN:-/usr/local/bin/mixflow}
CONFIG="$DATA_DIR/config.toml"
PORT=${MIXFLOW_PANEL_PORT:-12321}
ADDR=${MIXFLOW_PANEL_ADDR:-::}
USERNAME=${MIXFLOW_PANEL_USERNAME:-admin}
PASSWORD=${MIXFLOW_PANEL_PASSWORD:-admin123}
ENTRY_PATH=${MIXFLOW_PANEL_PATH:-off}

case "$PORT" in
  ''|*[!0-9]*) echo "MIXFLOW_PANEL_PORT must be an integer from 1 to 65535" >&2; exit 64 ;;
esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || {
  echo "MIXFLOW_PANEL_PORT must be an integer from 1 to 65535" >&2
  exit 64
}
case "$ENTRY_PATH" in
  off|/*) ;;
  *) echo "MIXFLOW_PANEL_PATH must be off or start with /" >&2; exit 64 ;;
esac

mkdir -p "$DATA_DIR"

if [ ! -f "$CONFIG" ]; then
  umask 077
  "$BIN" init -c "$CONFIG"
  "$BIN" panel \
    --port "$PORT" \
    --addr "$ADDR" \
    --user "$USERNAME" \
    --pass "$PASSWORD" \
    --path "$ENTRY_PATH" \
    -c "$CONFIG"
  echo "Created $CONFIG"
fi

cd "$DATA_DIR"
exec "$BIN" run -c "$CONFIG"
