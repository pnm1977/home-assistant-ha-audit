FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

ENV HA_AUDIT_VERSION=${BUILD_VERSION}

RUN apk add --no-cache \
    python3 \
    py3-requests \
    py3-websocket-client \
    py3-yaml

COPY run.sh /
COPY audit.py /
COPY config_scan.py /
COPY quality_scan.py /
COPY not_provided_reference_scan.py /
COPY recorder_health_scan.py /
COPY not_provided_history_scan.py /
COPY availability_scan.py /
COPY unavailable_history_scan.py /
COPY update_readiness_scan.py /
COPY upgrade_impact_scan.py /
COPY upgrade_compatibility_scan.py /
COPY release_evidence_scan.py /
COPY compatibility_coverage_scan.py /
COPY upgrade_correlation_scan.py /
COPY correlation_validation_scan.py /
COPY log_scan.py /
COPY log_family_scan.py /
COPY log_ownership_scan.py /
COPY log_priority_evidence.py /
COPY readiness_guidance.py /
COPY health_guidance.py /
COPY upgrade_decision.py /
COPY summary_overview.py /
COPY summary_upgrade.py /
COPY summary_report.py /
COPY ai_handoff.py /
COPY user_summary.py /

RUN chmod a+x /run.sh

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

CMD ["/run.sh"]
