#!/bin/sh
set -eu

DATA_DIR=${IPTV_DATA_DIR:-/data}
BIN=${IPTV_PROXY_BIN:-/usr/local/bin/iptv-proxy}
CONFIG="$DATA_DIR/config.toml"
PORT=${IPTV_PORT:-19899}
USERNAME=${IPTV_PANEL_USERNAME:-admin}
PASSWORD=${IPTV_PANEL_PASSWORD:-admin}
TIMEZONE_OFFSET=${IPTV_TIMEZONE_OFFSET_HOURS:-8}

case "$PORT" in
  ''|*[!0-9]*) echo "IPTV_PORT must be an integer from 1 to 65535" >&2; exit 64 ;;
esac
[ "$PORT" -ge 1 ] && [ "$PORT" -le 65535 ] || {
  echo "IPTV_PORT must be an integer from 1 to 65535" >&2
  exit 64
}
case "$TIMEZONE_OFFSET" in
  ''|-) echo "IPTV_TIMEZONE_OFFSET_HOURS must be an integer" >&2; exit 64 ;;
  -*) timezone_digits=${TIMEZONE_OFFSET#-} ;;
  *) timezone_digits=$TIMEZONE_OFFSET ;;
esac
case "$timezone_digits" in
  ''|*[!0-9]*) echo "IPTV_TIMEZONE_OFFSET_HOURS must be an integer" >&2; exit 64 ;;
esac

mkdir -p "$DATA_DIR/cache"

if [ ! -f "$CONFIG" ]; then
  command -v sha256sum >/dev/null 2>&1 || {
    echo "sha256sum is required to create config.toml" >&2
    exit 70
  }
  PASSWORD_HASH=$(printf '%s' "$PASSWORD" | sha256sum | cut -d ' ' -f 1)
  umask 077
  cat > "$CONFIG" <<EOF
# Generated on first container start. Later environment changes do not overwrite it.
[server]
bind = "[::]:$PORT"
timezone_offset_hours = $TIMEZONE_OFFSET
log_level = "info"

[panel]
enabled = true
username = "$USERNAME"
password_sha256 = "$PASSWORD_HASH"
session_ttl = 86400

[cache]
backend = "disk"
disk_path = "./cache"
m3u8_max_entries = 500
segment_max_entries = 2000
disk_max_mb = 0

[auth]
token_enabled = false
EOF
  echo "Created $CONFIG"
fi

cd "$DATA_DIR"
exec "$BIN" "$CONFIG"
