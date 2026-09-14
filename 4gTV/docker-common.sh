#!/bin/sh
# Shared validation. Persisted state is plain text, never sourced as shell code.

fourgtv_error() {
    printf '4gtv: %s\n' "$1" >&2
    exit "${2:-64}"
}

fourgtv_validate_port() {
    case "$1" in
        ''|0*|*[!0-9]*) fourgtv_error 'PORT must be a decimal integer from 1 to 65535 (no leading zeroes)' ;;
    esac
    [ "${#1}" -le 5 ] && [ "$1" -le 65535 ] ||
        fourgtv_error 'PORT must be a decimal integer from 1 to 65535'
}

fourgtv_validate_path() {
    [ -n "$1" ] || return 0
    case "$1" in
        /*) ;;
        *) fourgtv_error 'BASE_PATH must begin with /' ;;
    esac
    case "$1" in
        /|*/|*//*|*[!A-Za-z0-9_/-]*)
            fourgtv_error 'BASE_PATH allows letters, digits, _, - and single / separators; no trailing slash' ;;
    esac
}

fourgtv_read_path() {
    [ ! -L "$1" ] && [ -f "$1" ] ||
        fourgtv_error 'Saved base path must be an initialized regular file, not a symlink'
    fourgtv_saved_path=$(cat "$1") || fourgtv_error 'Cannot read saved base path' 70
    fourgtv_validate_path "$fourgtv_saved_path"
    printf '%s' "$fourgtv_saved_path"
}
