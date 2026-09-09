#!/bin/sh
set -eu

port=${IPTV_PORT:-19899}
exec wget -q -O /dev/null "http://127.0.0.1:${port}/health"
