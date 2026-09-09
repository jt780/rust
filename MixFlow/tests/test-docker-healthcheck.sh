#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
HEALTHCHECK="$ROOT/docker-healthcheck.sh"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM
mkdir -p "$work/bin" "$work/data"
cat > "$work/bin/wget" <<'EOF'
#!/bin/sh
for arg in "$@"; do url=$arg; done
printf '%s\n' "$url" > "${TEST_URL:?}"
EOF
chmod +x "$work/bin/wget"

cat > "$work/data/config.toml" <<'EOF'
[panel]
port = 12321
entry = "/hidden"
EOF
PATH="$work/bin:$PATH" MIXFLOW_DATA_DIR="$work/data" MIXFLOW_PANEL_PORT=23456 \
  TEST_URL="$work/url-hidden" "$HEALTHCHECK"
[ "$(cat "$work/url-hidden")" = 'http://127.0.0.1:23456/hidden' ] || fail "hidden path was not checked"

cat > "$work/data/config.toml" <<'EOF'
[panel]
entry = ""
EOF
PATH="$work/bin:$PATH" MIXFLOW_DATA_DIR="$work/data" MIXFLOW_PANEL_PORT=23456 \
  TEST_URL="$work/url-root" "$HEALTHCHECK"
[ "$(cat "$work/url-root")" = 'http://127.0.0.1:23456/' ] || fail "root path was not checked"

printf 'healthcheck tests passed\n'
