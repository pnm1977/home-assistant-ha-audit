#!/usr/bin/with-contenv bashio

set -u

VERSION="${HA_AUDIT_VERSION:-unknown}"

bashio::log.info "Starting HA Audit v${VERSION}"

echo ""


run_quiet_python() {
    local script="$1"
    local label="$2"
    local temp_log="/tmp/${script%.py}.log"

    if python3 "/${script}" >"${temp_log}" 2>&1; then
        return 0
    fi

    bashio::log.error "${label} failed"

    if [ -s "${temp_log}" ]; then
        echo ""
        echo "Output from failed stage:"
        echo "------------------------------------------"
        cat "${temp_log}"
        echo "------------------------------------------"
    fi

    return 1
}


run_quiet_python \
    "audit.py" \
    "Core HA audit"

run_quiet_python \
    "config_scan.py" \
    "Configuration inventory"

run_quiet_python \
    "quality_scan.py" \
    "Configuration quality audit"

run_quiet_python \
    "not_provided_reference_scan.py" \
    "Not-provided entity reference audit"

run_quiet_python \
    "recorder_health_scan.py" \
    "Recorder history availability audit"

run_quiet_python \
    "not_provided_history_scan.py" \
    "Not-provided entity history audit"


if ! python3 /summary_report.py; then
    bashio::log.error "Latest-run summary generation failed"
fi


bashio::log.info "HA Audit finished"
