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

run_quiet_python \
    "availability_scan.py" \
    "Unavailable entity availability audit"

run_quiet_python \
    "unavailable_history_scan.py" \
    "Unavailable entity history audit"

run_quiet_python \
    "update_readiness_scan.py" \
    "Update readiness audit"

run_quiet_python \
    "upgrade_impact_scan.py" \
    "Upgrade impact inventory"

run_quiet_python \
    "upgrade_compatibility_scan.py" \
    "Upgrade compatibility audit"

run_quiet_python \
    "release_evidence_scan.py" \
    "Official release evidence audit"

run_quiet_python \
    "compatibility_coverage_scan.py" \
    "Compatibility coverage mapping audit"

run_quiet_python \
    "upgrade_correlation_scan.py" \
    "Dynamic upgrade correlation audit"

run_quiet_python \
    "correlation_validation_scan.py" \
    "Correlation validation audit"

run_quiet_python \
    "log_scan.py" \
    "System Log collection probe"

run_quiet_python \
    "log_family_scan.py" \
    "System Log issue family probe"

run_quiet_python \
    "log_fingerprint_scan.py" \
    "System Log stable fingerprint probe"

run_quiet_python \
    "log_ownership_scan.py" \
    "System Log ownership probe"

run_quiet_python \
    "log_priority_evidence.py" \
    "System Log priority evidence probe"

run_quiet_python \
    "log_priority_scan.py" \
    "System Log priority probe"

run_quiet_python \
    "log_persistence_scan.py" \
    "System Log persistence probe"

run_quiet_python \
    "log_recurrence_scan.py" \
    "System Log recurrence evidence"


if run_quiet_python \
    "summary_report.py" \
    "Latest-run summary generation"; then

    run_quiet_python \
        "ai_handoff.py" \
        "AI / LLM handoff generation"

    if ! python3 /user_summary.py; then
        bashio::log.error \
            "Plain-English user summary generation failed"
    fi
else
    bashio::log.error \
        "Latest-run summary generation failed"
fi

bashio::log.info "HA Audit finished"
