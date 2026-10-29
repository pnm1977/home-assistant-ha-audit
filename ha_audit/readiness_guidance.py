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


def classify_generic_compatibility_evidence(report, *, installed_version, target_version):
    """Classify only the evidence quality of the local generic rule report.

    An unregistered rule pack is *not* a failure and *not* a clearance.
    The caller must still consider official releases, dynamic correlation,
    deterministic references and other readiness evidence independently.
    Fail closed if the report is stale, inconsistent, or lacks inspected YAML.
    """
    if not isinstance(report, dict):
        return "incomplete"
    if (not installed_version or not target_version
            or report.get("installed_version") != installed_version
            or report.get("target_version") != target_version):
        return "incomplete"
    if report.get("schema_version") != 1:
        return "incomplete"

    status = report.get("status")
    count = report.get("selected_rule_count")
    rules = report.get("rules")
    failures = report.get("read_failures")
    if (not isinstance(count, int) or isinstance(count, bool) or count < 0
            or not isinstance(rules, list) or not isinstance(failures, list)
            or failures or count != len(rules)):
        return "incomplete"

    if status == "no_registered_checks":
        return "not_applicable" if count == 0 else "incomplete"
    if status != "local_checks_completed" or count == 0:
        return "incomplete"

    summary = report.get("summary")
    if not isinstance(summary, dict):
        return "incomplete"
    review_count = summary.get("review_required_count")
    incomplete_count = summary.get("incomplete_rule_count")
    if (not isinstance(review_count, int) or isinstance(review_count, bool)
            or not isinstance(incomplete_count, int)
            or isinstance(incomplete_count, bool) or incomplete_count != 0
            or review_count < 0):
        return "incomplete"

    actual_review = 0
    for rule in rules:
        if not isinstance(rule, dict):
            return "incomplete"
        rule_status = rule.get("status")
        findings = rule.get("findings")
        checked = rule.get("files_checked")
        rule_failures = rule.get("read_failures")
        if (rule_status not in ("review_required", "no_affected_usage_found")
                or not isinstance(findings, list)
                or not isinstance(rule_failures, list) or rule_failures
                or not isinstance(checked, int) or isinstance(checked, bool)
                or checked <= 0):
            return "incomplete"
        if rule_status == "no_affected_usage_found":
            if findings:
                return "incomplete"
        else:
            if not findings:
                return "incomplete"
            actual_review += 1
    if actual_review != review_count:
        return "incomplete"
    return "review" if actual_review else "checked"


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
    generic_check_report=None,
    generic_installed_version=None,
    generic_target_version=None,
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

    # Optional until summary_report.py passes the new report (next step).
    # A clean local check never overrides dynamic correlation uncertainty.
    generic_check_result = None
    if generic_check_report is not None:
        generic_check_result = classify_generic_compatibility_evidence(
            generic_check_report,
            installed_version=generic_installed_version,
            target_version=generic_target_version,
        )
        if generic_check_result == "incomplete":
            incomplete.append("generic_compatibility_evidence_incomplete")
        if generic_check_result == "review":
            # Preserve unresolved evidence as INCOMPLETE while retaining the
            # actionable generic finding in reason_codes.
            if incomplete:
                incomplete.append("generic_compatibility_review_required")

    if incomplete:
        return {
            "status": STATE_INCOMPLETE,
            "assessment_complete": False,
            "reason_codes": incomplete,
        }

    review = []

    if generic_check_result == "review":
        review.append("generic_compatibility_review_required")

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
