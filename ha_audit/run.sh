#!/usr/bin/with-contenv bashio

set -u

VERSION="${HA_AUDIT_VERSION:-unknown}"

bashio::log.info "Starting HA Audit v${VERSION}"

echo ""

# The Web UI must never present the previous run's reports as current when
# an audit stage fails. Write an atomic run marker before collecting evidence.
RUN_STATE_FILE="/config/ha_audit_run_status.json"
RUN_STARTED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%S+00:00')"
ANY_STAGE_FAILED=0
SUMMARY_STATUS="not_generated"
HANDOFF_STATUS="not_generated"
ISSUES_STATUS="not_verified"

write_run_state() {
    local state="$1"
    python3 - "${RUN_STATE_FILE}" "${state}" "${RUN_STARTED_AT_UTC}" \
        "${SUMMARY_STATUS}" "${HANDOFF_STATUS}" "${ISSUES_STATUS}" <<'PYTHON'
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
state, started, summary, handoff, issues = sys.argv[2:]
now = datetime.now(timezone.utc).isoformat(timespec="seconds")
payload = {
    "schema_version": 1,
    "status": state,
    "run_started_at_utc": started,
    "run_finished_at_utc": now if state != "running" else None,
    "summary_status": summary,
    "handoff_status": handoff,
    "issues_status": issues,
}
path.parent.mkdir(parents=True, exist_ok=True)
temp_name = None
try:
    fd, temp_name = tempfile.mkstemp(prefix=".ha_audit_run_status_", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")
    os.replace(temp_name, path)
except BaseException:
    if temp_name is not None:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
    raise
PYTHON
}

if ! write_run_state "running"; then
    bashio::log.error "Cannot record audit start; refusing to show potentially stale reports"
    exit 1
fi


run_quiet_python() {
    local script="$1"
    local label="$2"
    local temp_log="/tmp/${script%.py}.log"

    if python3 "/${script}" >"${temp_log}" 2>&1; then
        case "${script}" in
            log_priority_final.py) ISSUES_STATUS="ok" ;;
            summary_report.py) SUMMARY_STATUS="ok" ;;
            investigation_handoff.py) HANDOFF_STATUS="ok" ;;
        esac
        return 0
    fi

    ANY_STAGE_FAILED=1
    case "${script}" in
        log_priority_final.py) ISSUES_STATUS="failed" ;;
        summary_report.py) SUMMARY_STATUS="failed" ;;
        investigation_handoff.py) HANDOFF_STATUS="failed" ;;
    esac
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

# Supplement existing compatibility evidence with the generic, version-aware
# YAML checks. This stage does NOT alter the readiness verdict; its report is
# separate until the evidence is reviewed and integrated deliberately.
run_quiet_python \
    "core_compatibility_runner.py" \
    "Generic Core compatibility checks"

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

run_quiet_python \
    "log_correlation_scan.py" \
    "System Log availability and Repairs correlation"

run_quiet_python \
    "log_priority_final.py" \
    "System Log enriched priority"

run_quiet_python \
    "ai_evidence.py" \
    "Structured AI evidence generation"


if run_quiet_python \
    "summary_report.py" \
    "Latest-run summary generation"; then

    if run_quiet_python \
        "ai_handoff.py" \
        "AI / LLM handoff generation"; then

        run_quiet_python \
            "investigation_handoff.py" \
            "Saved investigation context handoff"
    fi

    if ! python3 /user_summary.py; then
        ANY_STAGE_FAILED=1
        bashio::log.error \
            "Plain-English user summary generation failed"
    fi
else
    bashio::log.error \
        "Latest-run summary generation failed"
fi

# A failed stage, including any upstream collector, makes the overall run
# incomplete. The saved investigation history is intentionally untouched.
if [ "${ANY_STAGE_FAILED}" -eq 0 ] && \
   [ "${SUMMARY_STATUS}" = "ok" ] && \
   [ "${HANDOFF_STATUS}" = "ok" ] && \
   [ "${ISSUES_STATUS}" = "ok" ]; then
    RUN_RESULT="complete"
else
    RUN_RESULT="incomplete"
    bashio::log.warning "Audit incomplete: latest reports will be withheld by the Web UI"
fi

if ! write_run_state "${RUN_RESULT}"; then
    bashio::log.error "Cannot record audit result; refusing to show potentially stale reports"
    exit 1
fi

bashio::log.info "HA Audit finished (${RUN_RESULT})"


# Keep the app running after the audit so Home Assistant Ingress can serve the latest report.
bashio::log.info "Starting HA Audit read-only web interface"
exec python3 /web_ui.py
