STATE_NO_UPDATE = "NO CORE UPDATE PENDING"
STATE_BLOCKER = "KNOWN BLOCKER FOUND"
STATE_INCOMPLETE = "ASSESSMENT INCOMPLETE"
STATE_REVIEW = "REVIEW BEFORE UPDATING"
STATE_CLEAR = "NO KNOWN BLOCKERS FOUND"


def _count(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def evaluate_core_update_guidance(
    *,
    core_update_pending,
    update_readiness_available,
    core_window_complete,
    collector_error_count,
    configuration_check_state,
    release_evidence_complete,
    compatibility_coverage_usable,
    dynamic_correlation_complete,
    dynamic_correlation_insufficient_count,
    correlation_validation_usable,
    deterministic_compatibility_required,
    deterministic_compatibility_available,
    deterministic_yaml_failure_count,
    relevant_unignored_repair_count,
    compatibility_review_required_count,
    compatibility_manual_review_count,
    known_blocker_count=0,
):
    """Return conservative top-level Core update guidance.

    All inputs are evidence already produced by HA Audit.
    This helper does not scan Home Assistant and does not
    declare an update safe.
    """

    if not core_update_pending:
        return {
            "status": STATE_NO_UPDATE,
            "assessment_complete": True,
            "reason_codes": [],
        }

    if _count(known_blocker_count):
        return {
            "status": STATE_BLOCKER,
            "assessment_complete": True,
            "reason_codes": [
                "known_blocker",
            ],
        }

    incomplete = []

    if not update_readiness_available:
        incomplete.append(
            "update_readiness_unavailable"
        )

    if not core_window_complete:
        incomplete.append(
            "core_version_window_incomplete"
        )

    if _count(collector_error_count):
        incomplete.append(
            "core_collector_error"
        )

    config_state = str(
        configuration_check_state
        or ""
    ).strip().lower()

    if config_state in {
        "",
        "unknown",
        "error",
    }:
        incomplete.append(
            "configuration_check_incomplete"
        )

    if not release_evidence_complete:
        incomplete.append(
            "official_release_evidence_incomplete"
        )

    if not compatibility_coverage_usable:
        incomplete.append(
            "compatibility_coverage_incomplete"
        )

    if not dynamic_correlation_complete:
        incomplete.append(
            "dynamic_correlation_incomplete"
        )

    if _count(
        dynamic_correlation_insufficient_count
    ):
        incomplete.append(
            "dynamic_correlation_insufficient_evidence"
        )

    if not correlation_validation_usable:
        incomplete.append(
            "correlation_validation_incomplete"
        )

    if deterministic_compatibility_required:
        if not deterministic_compatibility_available:
            incomplete.append(
                "deterministic_compatibility_unavailable"
            )

        if _count(
            deterministic_yaml_failure_count
        ):
            incomplete.append(
                "deterministic_yaml_read_failure"
            )

    if incomplete:
        return {
            "status": STATE_INCOMPLETE,
            "assessment_complete": False,
            "reason_codes": incomplete,
        }

    review = []

    if config_state != "valid":
        review.append(
            "configuration_invalid"
        )

    if _count(
        relevant_unignored_repair_count
    ):
        review.append(
            "relevant_unignored_repair"
        )

    if _count(
        compatibility_review_required_count
    ):
        review.append(
            "compatibility_review_required"
        )

    if _count(
        compatibility_manual_review_count
    ):
        review.append(
            "compatibility_manual_review"
        )

    if review:
        return {
            "status": STATE_REVIEW,
            "assessment_complete": True,
            "reason_codes": review,
        }

    return {
        "status": STATE_CLEAR,
        "assessment_complete": True,
        "reason_codes": [],
    }
