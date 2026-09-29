STATE_INCOMPLETE = "ASSESSMENT INCOMPLETE"
STATE_ATTENTION = "NEEDS ATTENTION"
STATE_CLEAR = "NO PRIORITY ISSUES"


def _count(value):
    try:
        return max(
            0,
            int(value),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def evaluate_health_guidance(
    *,
    configuration_check_state,
    collector_error_count,
    missing_include_count,
    missing_entity_count,
    duplicate_automation_id_count,
    referenced_not_provided_count,
    whole_device_unavailable_count,
    ungrouped_unavailable_count,
):
    """Return conservative Home Assistant health guidance.

    This helper uses existing HA Audit evidence only.

    It does not diagnose faults and does not treat every
    unavailable or partially available entity as a problem.
    """

    incomplete = []

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

    if _count(
        collector_error_count
    ):
        incomplete.append(
            "audit_collector_error"
        )

    if incomplete:
        return {
            "status": STATE_INCOMPLETE,
            "assessment_complete": False,
            "reason_codes": incomplete,
        }

    attention = []

    if config_state != "valid":
        attention.append(
            "configuration_invalid"
        )

    if _count(
        missing_include_count
    ):
        attention.append(
            "missing_active_include"
        )

    if _count(
        missing_entity_count
    ):
        attention.append(
            "missing_active_entity_reference"
        )

    if _count(
        duplicate_automation_id_count
    ):
        attention.append(
            "duplicate_automation_id"
        )

    if _count(
        referenced_not_provided_count
    ):
        attention.append(
            "not_provided_referenced_in_yaml"
        )

    if _count(
        whole_device_unavailable_count
    ):
        attention.append(
            "whole_device_unavailable"
        )

    if _count(
        ungrouped_unavailable_count
    ):
        attention.append(
            "ungrouped_unavailable"
        )

    if attention:
        return {
            "status": STATE_ATTENTION,
            "assessment_complete": True,
            "reason_codes": attention,
        }

    return {
        "status": STATE_CLEAR,
        "assessment_complete": True,
        "reason_codes": [],
    }
