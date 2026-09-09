#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
ENTRYPOINT="$ROOT/docker-entrypoint.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  file=$1
  text=$2
  grep -Fq "$text" "$file" || fail "$file does not contain: $text"
}

[ -x "$ENTRYPOINT" ] || fail "docker-entrypoint.sh is missing or not executable"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM

cat > "$work/fake-iptv-proxy" <<'EOF'
#!/bin/sh
printf '%s\n' "$*" > "${TEST_OUTPUT:?}"
EOF
chmod +x "$work/fake-iptv-proxy"

# A first start creates a usable config and passes its path to the binary.
data="$work/data-new"
output="$work/args-new"
mkdir -p "$data"
IPTV_DATA_DIR="$data" \
IPTV_PROXY_BIN="$work/fake-iptv-proxy" \
IPTV_PORT=21999 \
IPTV_TIMEZONE_OFFSET_HOURS=-7 \
IPTV_PANEL_USERNAME=tester \
IPTV_PANEL_PASSWORD='secret-pass' \
TEST_OUTPUT="$output" \
  "$ENTRYPOINT"

expected_hash=$(printf '%s' 'secret-pass' | sha256sum | cut -d ' ' -f 1)
assert_contains "$data/config.toml" 'bind = "[::]:21999"'
assert_contains "$data/config.toml" 'timezone_offset_hours = -7'
assert_contains "$data/config.toml" 'username = "tester"'
assert_contains "$data/config.toml" "password_sha256 = \"$expected_hash\""
assert_contains "$data/config.toml" 'disk_path = "./cache"'
[ "$(cat "$output")" = "$data/config.toml" ] || fail "binary did not receive config path"
[ -d "$data/cache" ] || fail "cache directory was not created"

# Existing configuration must survive container restarts unchanged.
data="$work/data-existing"
output="$work/args-existing"
mkdir -p "$data"
printf '%s\n' 'keep-this-config' > "$data/config.toml"
IPTV_DATA_DIR="$data" \
IPTV_PROXY_BIN="$work/fake-iptv-proxy" \
IPTV_PANEL_PASSWORD='replacement' \
TEST_OUTPUT="$output" \
  "$ENTRYPOINT"
[ "$(cat "$data/config.toml")" = 'keep-this-config' ] || fail "existing config was overwritten"

# Invalid numeric values fail before launching the service.
if IPTV_DATA_DIR="$work/data-invalid-port" IPTV_PROXY_BIN="$work/fake-iptv-proxy" \
  IPTV_PORT=70000 TEST_OUTPUT="$work/invalid-port-output" "$ENTRYPOINT" 2>/dev/null; then
  fail "invalid port was accepted"
fi
if IPTV_DATA_DIR="$work/data-invalid-timezone" IPTV_PROXY_BIN="$work/fake-iptv-proxy" \
  IPTV_TIMEZONE_OFFSET_HOURS=UTC TEST_OUTPUT="$work/invalid-timezone-output" "$ENTRYPOINT" 2>/dev/null; then
  fail "invalid timezone offset was accepted"
fi
if IPTV_DATA_DIR="$work/data-malformed-timezone" IPTV_PROXY_BIN="$work/fake-iptv-proxy" \
  IPTV_TIMEZONE_OFFSET_HOURS=-7oops TEST_OUTPUT="$work/malformed-timezone-output" "$ENTRYPOINT" 2>/dev/null; then
  fail "malformed timezone offset was accepted"
fi

printf 'entrypoint tests passed\n'
