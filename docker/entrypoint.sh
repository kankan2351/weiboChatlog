#!/usr/bin/env bash
set -euo pipefail

# Allow direct shell access without XVFB wrapper
if [[ $# -gt 0 ]]; then
    case "$1" in
        bash|/bin/bash|sh|/bin/sh)
            exec "$@"
            ;;
    esac
fi

# Allow opting out of xvfb for full browser sessions (e.g., Strategy B login)
if [[ "${RUN_HEADFUL:-false}" == "true" ]]; then
    exec "$@"
fi

# Default to command passed in (or from CMD) wrapped with xvfb-run so Selenium has a display.
if command -v xvfb-run >/dev/null 2>&1; then
    exec xvfb-run -a "$@"
else
    exec "$@"
fi
