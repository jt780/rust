#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/docker-common.sh"

port=${PORT:-8080}
data_dir=${FOURGTV_DATA_DIR:-/data}
fourgtv_validate_port "$port"
base_path=$(fourgtv_read_path "$data_dir/.docker-base-path")

# The hidden-prefix homepage intentionally has no trailing slash.
route=${base_path:-/}
exec wget -q -T 4 -O /dev/null "http://127.0.0.1:${port}${route}"
