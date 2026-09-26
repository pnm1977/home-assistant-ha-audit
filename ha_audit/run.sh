#!/usr/bin/with-contenv bashio

set -u

VERSION="${HA_AUDIT_VERSION:-unknown}"

bashio::log.info "Starting HA Audit v${VERSION}"

echo ""

run_python() {
    local script="$1"
    local label="$2"

    if ! python3 "/${script}"; then
        bashio::log.error "${label} failed"
        return 1
    fi

    return 0
}


run_python \
    "audit.py" \
    "Core HA audit"

run_python \
    "config_scan.py" \
    "Configuration inventory"

run_python \
    "quality_scan.py" \
    "Configuration quality audit"

run_python \
    "not_provided_reference_scan.py" \
    "Not-provided entity reference audit"


bashio::log.info "HA Audit finished"
