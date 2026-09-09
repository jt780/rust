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
assert_contains "$ROOT/Dockerfile" 'TARGETVARIANT'
assert_contains "$ROOT/Dockerfile" 'ff34976227157319a251770e14b2f907e6237f0001f9d8c5ea79a517a43c01a7'
assert_contains "$ROOT/Dockerfile" '2948ee1f0eff22a48a351653f2df9f29dc424708bacd670f34378476efab5a4b'
assert_contains "$ROOT/Dockerfile" '739516d7705d3134998a9a47ed141d68c1fa8b98ae39df6aa3f6211984af5149'
assert_contains "$ROOT/Dockerfile" 'INSTALL_FFMPEG'
assert_contains "$ROOT/Dockerfile" 'docker-healthcheck.sh'
assert_contains "$ROOT/compose.yaml" '19899'
assert_contains "$ROOT/compose.yaml" '/data'
assert_contains "$ROOT/compose.cf-net.yaml" 'external: true'
assert_contains "$ROOT/compose.cf-net.yaml" 'name: cf-net'

printf 'docker file tests passed\n'
