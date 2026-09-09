#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  file=$1
  text=$2
  grep -Fq "$text" "$file" || fail "$file does not contain: $text"
}

for file in Dockerfile compose.yaml compose.cf-net.yaml .dockerignore .env.example docker-healthcheck.sh; do
  [ -f "$ROOT/$file" ] || fail "$file is missing"
done

assert_contains "$ROOT/Dockerfile" 'TARGETARCH'
assert_contains "$ROOT/Dockerfile" '071624c66e9ef2ecb1a46e87d8805f7e2bdac123b179f32e2d9b2d0a16a30853'
assert_contains "$ROOT/Dockerfile" '7498561d2737e522802a76e51b748457a57e730e1d62aacfea0cc08bc8f0ef65'
assert_contains "$ROOT/Dockerfile" 'NET_ADMIN'
assert_contains "$ROOT/Dockerfile" 'docker-healthcheck.sh'
assert_contains "$ROOT/compose.yaml" '12321'
assert_contains "$ROOT/compose.yaml" '/data'
assert_contains "$ROOT/compose.yaml" 'NET_ADMIN'
assert_contains "$ROOT/compose.yaml" '/dev/net/tun'
assert_contains "$ROOT/compose.cf-net.yaml" 'external: true'
assert_contains "$ROOT/compose.cf-net.yaml" 'name: cf-net'

printf 'docker file tests passed\n'
