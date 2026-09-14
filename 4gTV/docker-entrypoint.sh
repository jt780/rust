#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$script_dir/docker-common.sh"

umask 077
PORT=${PORT:-8080}
data_dir=${FOURGTV_DATA_DIR:-/data}
binary=${FOURGTV_BIN:-/usr/local/bin/4gtv}
requested_path=${BASE_PATH:-}

fourgtv_validate_port "$PORT"
case "$data_dir" in
    /*) ;;
    *) fourgtv_error 'FOURGTV_DATA_DIR must be an absolute path' ;;
esac
state="$data_dir/.docker-base-path"
# An ignored first-run default must not invalidate existing persisted settings.
if [ ! -e "$state" ] && [ ! -L "$state" ]; then
    case "$requested_path" in
        ''|off) ;;
        *) fourgtv_validate_path "$requested_path" ;;
    esac
fi
[ -x "$binary" ] || fourgtv_error '4gtv binary is missing or not executable' 70

mkdir -p "$data_dir" || fourgtv_error 'Cannot create data directory; prepare a writable bind mount for the container UID/GID' 70
[ -w "$data_dir" ] || fourgtv_error 'Data directory must be writable by the container UID/GID; create ./data and set FOURGTV_UID/FOURGTV_GID' 70

for name in 4gtv_admin_key.txt 4gtv_config.json; do
    target="$data_dir/$name"
    if [ -L "$target" ] || { [ -e "$target" ] && [ ! -f "$target" ]; }; then
        fourgtv_error 'Application configuration and key must be regular files, not symlinks'
    fi
done

if [ -e "$state" ] || [ -L "$state" ]; then
    BASE_PATH=$(fourgtv_read_path "$state")
else
    case "$requested_path" in
        off) BASE_PATH='' ;;
        '')
            random_bytes=$(od -An -N10 -tx1 /dev/urandom) || fourgtv_error 'Cannot generate a private base path' 70
            BASE_PATH="/$(printf '%s' "$random_bytes" | tr -d ' \n')"
            ;;
        *) BASE_PATH=$requested_path ;;
    esac
    fourgtv_validate_path "$BASE_PATH"
    path_tmp=$(mktemp "$data_dir/.docker-base-path.XXXXXX")
    trap 'rm -f "$path_tmp"' 0
    trap 'exit 70' HUP INT TERM
    printf '%s\n' "$BASE_PATH" > "$path_tmp"
    mv "$path_tmp" "$state"
    trap - 0 HUP INT TERM
fi

# A new umask alone does not repair permissions on imported credentials.
chmod 0600 "$state"
for name in 4gtv_admin_key.txt 4gtv_config.json; do
    [ ! -f "$data_dir/$name" ] || chmod 0600 "$data_dir/$name"
done

export PORT BASE_PATH
cd "$data_dir"
exec "$binary" "$@"
