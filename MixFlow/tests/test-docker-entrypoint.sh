#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
ENTRYPOINT="$ROOT/docker-entrypoint.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

[ -x "$ENTRYPOINT" ] || fail "docker-entrypoint.sh is missing or not executable"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM

cat > "$work/fake-mixflow" <<'EOF'
#!/bin/sh
cmd=$1
shift
case "$cmd" in
  init)
    [ "$1" = "-c" ]
    cat > "$2" <<'CONFIG'
[panel]
enabled = true
addr = "::"
port = 12321
username = "admin"
password = "admin123"
entry = ""
CONFIG
    ;;
  panel)
    printf '%s\n' "$*" > "${TEST_PANEL_ARGS:?}"
    ;;
  run)
    printf '%s\n' "$*" > "${TEST_RUN_ARGS:?}"
    ;;
  *) exit 2 ;;
esac
EOF
chmod +x "$work/fake-mixflow"

# First start initializes config, applies panel settings, and runs foreground.
data="$work/data-new"
mkdir -p "$data"
MIXFLOW_DATA_DIR="$data" \
MIXFLOW_BIN="$work/fake-mixflow" \
MIXFLOW_PANEL_PORT=23456 \
MIXFLOW_PANEL_ADDR=0.0.0.0 \
MIXFLOW_PANEL_USERNAME=tester \
MIXFLOW_PANEL_PASSWORD=secret-pass \
MIXFLOW_PANEL_PATH=/hidden \
TEST_PANEL_ARGS="$work/panel-args" \
TEST_RUN_ARGS="$work/run-args" \
  "$ENTRYPOINT"

[ -f "$data/config.toml" ] || fail "config was not initialized"
[ "$(cat "$work/panel-args")" = "--port 23456 --addr 0.0.0.0 --user tester --pass secret-pass --path /hidden -c $data/config.toml" ] || fail "panel arguments are wrong"
[ "$(cat "$work/run-args")" = "-c $data/config.toml" ] || fail "run arguments are wrong"

# Existing config is preserved and environment settings are not reapplied.
data="$work/data-existing"
mkdir -p "$data"
printf '%s\n' 'keep-this-config' > "$data/config.toml"
printf '%s\n' 'unchanged' > "$work/panel-existing"
MIXFLOW_DATA_DIR="$data" \
MIXFLOW_BIN="$work/fake-mixflow" \
MIXFLOW_PANEL_PASSWORD=replacement \
TEST_PANEL_ARGS="$work/panel-existing" \
TEST_RUN_ARGS="$work/run-existing" \
  "$ENTRYPOINT"
[ "$(cat "$data/config.toml")" = 'keep-this-config' ] || fail "existing config was overwritten"
[ "$(cat "$work/panel-existing")" = 'unchanged' ] || fail "existing config was changed"

# "off" is accepted for disabling the hidden entry path.
data="$work/data-off"
mkdir -p "$data"
MIXFLOW_DATA_DIR="$data" \
MIXFLOW_BIN="$work/fake-mixflow" \
MIXFLOW_PANEL_PATH=off \
TEST_PANEL_ARGS="$work/panel-off" \
TEST_RUN_ARGS="$work/run-off" \
  "$ENTRYPOINT"
grep -Fq -- '--path off' "$work/panel-off" || fail "off path was not passed through"

# Invalid ports and paths fail before launching the service.
if MIXFLOW_DATA_DIR="$work/data-invalid-port" MIXFLOW_BIN="$work/fake-mixflow" \
  MIXFLOW_PANEL_PORT=70000 TEST_PANEL_ARGS="$work/invalid-panel" TEST_RUN_ARGS="$work/invalid-run" \
  "$ENTRYPOINT" 2>/dev/null; then
  fail "invalid port was accepted"
fi
if MIXFLOW_DATA_DIR="$work/data-invalid-path" MIXFLOW_BIN="$work/fake-mixflow" \
  MIXFLOW_PANEL_PATH=hidden TEST_PANEL_ARGS="$work/invalid-path-panel" TEST_RUN_ARGS="$work/invalid-path-run" \
  "$ENTRYPOINT" 2>/dev/null; then
  fail "path without a leading slash was accepted"
fi

printf 'entrypoint tests passed\n'
