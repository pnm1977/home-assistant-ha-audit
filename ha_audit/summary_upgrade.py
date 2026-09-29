"""Rendering helpers for HA Audit upgrade/readiness summary sections.

This module is intentionally presentation-only. The scanners and
summary_report.py continue to prepare the evidence values; these
functions only append the existing text sections to the summary.
"""

def render_update_readiness(add, context):
    compatibility_verdict_produced = context['compatibility_verdict_produced']
    core_upgrade_window = context['core_upgrade_window']
    correlation_status_label = context['correlation_status_label']
    coverage_reference_status_label = context['coverage_reference_status_label']
    coverage_status_label = context['coverage_status_label']
    format_update_category = context['format_update_category']
    format_update_name = context['format_update_name']
    readiness_already_crossed_count = context['readiness_already_crossed_count']
    readiness_available_updates = context['readiness_available_updates']
    readiness_beyond_target_count = context['readiness_beyond_target_count']
    readiness_ignored_count = context['readiness_ignored_count']
    readiness_in_progress_count = context['readiness_in_progress_count']
    readiness_issue_count = context['readiness_issue_count']
    readiness_pending_count = context['readiness_pending_count']
    readiness_relevant_count = context['readiness_relevant_count']
    readiness_relevant_ignored_count = context['readiness_relevant_ignored_count']
    readiness_relevant_unignored_count = context['readiness_relevant_unignored_count']
    readiness_unavailable_count = context['readiness_unavailable_count']
    readiness_unignored_count = context['readiness_unignored_count']
    release_status_label = context['release_status_label']
    update_readiness_available = context['update_readiness_available']
    validation_status_label = context['validation_status_label']

    # Update readiness
    # ------------------------------------------------------------

    add("")
    add("UPDATE READINESS")
    add("-" * 58)
    if update_readiness_available:
        add(
            f"Pending updates:             "
            f"{readiness_pending_count}"
        )
        if readiness_available_updates:
            add("")
            for item in readiness_available_updates:
                category = format_update_category(
                    item.get(
                        "category"
                    )
                )
                name = format_update_name(
                    item
                )
                installed = (
                    item.get(
                        "installed_version"
                    )
                    or "unknown"
                )
                latest = (
                    item.get(
                        "latest_version"
                    )
                    or "unknown"
                )
                if category in (
                    "Core",
                    "OS",
                    "Supervisor",
                ):
                    add(
                        f"{category}: "
                        f"{installed} -> {latest}"
                    )
                else:
                    add(
                        f"{category}: "
                        f"{name} "
                        f"{installed} -> {latest}"
                    )
        if core_upgrade_window.get(
            "pending"
        ):
            add("")
            add(
                "Core upgrade window:         "
                f"{core_upgrade_window.get('installed_version')}"
                " -> "
                f"{core_upgrade_window.get('target_version')}"
            )
        add("")
        add(
            f"Repair issues:               "
            f"{readiness_issue_count}"
        )
        add(
            f"Unignored Repairs:           "
            f"{readiness_unignored_count}"
        )
        add(
            f"Ignored Repairs:             "
            f"{readiness_ignored_count}"
        )
        add(
            f"Relevant to Core upgrade:    "
            f"{readiness_relevant_count}"
        )
        add(
            f"Relevant + unignored:        "
            f"{readiness_relevant_unignored_count}"
        )
        add(
            f"Relevant + ignored:          "
            f"{readiness_relevant_ignored_count}"
        )
        add(
            f"Already-crossed Repairs:     "
            f"{readiness_already_crossed_count}"
        )
        if readiness_beyond_target_count:
            add(
                f"Beyond pending target:       "
                f"{readiness_beyond_target_count}"
            )
        if readiness_unavailable_count:
            add(
                f"Unavailable update entities: "
                f"{readiness_unavailable_count}"
            )
        if readiness_in_progress_count:
            add(
                f"Updates in progress:         "
                f"{readiness_in_progress_count}"
            )
        add("")
        if core_upgrade_window.get(
            "pending"
        ):
            add(
                "Deterministic reference:     "
                f"{coverage_reference_status_label}"
            )
            add(
                "Compatibility coverage:      "
                f"{coverage_status_label}"
            )
            add(
                "Dynamic correlation:         "
                f"{correlation_status_label}"
            )
            add(
                "Correlation validation:      "
                f"{validation_status_label}"
            )
        else:
            add(
                "Deterministic reference:     "
                "NOT APPLICABLE"
            )
            add(
                "Compatibility coverage:      "
                "NOT APPLICABLE"
            )
            add(
                "Dynamic correlation:         "
                "NOT APPLICABLE"
            )
            add(
                "Correlation validation:      "
                "NOT APPLICABLE"
            )
        add(
            "Official release evidence:    "
            f"{release_status_label}"
        )
        add(
            "Readiness verdict:           "
            + (
                "PRODUCED"
                if compatibility_verdict_produced
                else "NOT PRODUCED"
            )
        )
        add("")
        add(
            "Update and Repair evidence is local. "
            "Official release evidence, deterministic reference "
            "availability, dynamic correlation, correlation validation, "
            "and deterministic compatibility results are shown "
            "separately below."
        )
    else:
        add(
            "Update readiness report unavailable."
        )

    # ------------------------------------------------------------


def render_official_release_evidence(add, context):
    core_upgrade_window = context['core_upgrade_window']
    release_applicability_reason = context['release_applicability_reason']
    release_applicable = context['release_applicable']
    release_breaking_group_count = context['release_breaking_group_count']
    release_crossed_count = context['release_crossed_count']
    release_crossed_group_count = context['release_crossed_group_count']
    release_evidence_available = context['release_evidence_available']
    release_external_fetch = context['release_external_fetch']
    release_failure_count = context['release_failure_count']
    release_family_count = context['release_family_count']
    release_fetch_success_count = context['release_fetch_success_count']
    release_official_sources_only = context['release_official_sources_only']
    release_partial_count = context['release_partial_count']
    release_range_status = context['release_range_status']
    release_requested_families = context['release_requested_families']
    release_same_family = context['release_same_family']
    release_status_label = context['release_status_label']
    release_structured_parse_count = context['release_structured_parse_count']
    release_success_count = context['release_success_count']

    # Official release evidence
    # ------------------------------------------------------------

    add("")
    add("OFFICIAL RELEASE EVIDENCE")
    add("-" * 58)
    if release_evidence_available:
        if release_applicable:
            add(
                "Upgrade window:              "
                f"{core_upgrade_window.get('installed_version')}"
                " -> "
                f"{core_upgrade_window.get('target_version')}"
            )
            if release_same_family:
                add(
                    "Core releases crossed:       "
                    "0 (same-family update)"
                )
            else:
                add(
                    f"Core releases crossed:       "
                    f"{release_crossed_count}"
                )
            if release_requested_families:
                add(
                    "Release families:            "
                    + ", ".join(
                        str(item)
                        for item
                        in release_requested_families
                    )
                )
            add(
                f"Official releases fetched:   "
                f"{release_fetch_success_count} / "
                f"{release_family_count}"
            )
            add(
                f"Breaking-change groups:      "
                f"{release_breaking_group_count}"
            )
            add(
                f"Crossed change groups:       "
                f"{release_crossed_group_count}"
            )
            add("")
            add(
                f"Successful parses:           "
                f"{release_success_count}"
            )
            add(
                f"Structured BIC parses:       "
                f"{release_structured_parse_count}"
            )
            add(
                f"Partial parses:              "
                f"{release_partial_count}"
            )
            add(
                f"Failed parses:               "
                f"{release_failure_count}"
            )
            add("")
            add(
                "Official sources only:       "
                + (
                    "YES"
                    if release_official_sources_only
                    else "NO"
                )
            )
            add(
                "Runtime fetch:               "
                + (
                    "PERFORMED"
                    if release_external_fetch
                    else "NOT PERFORMED"
                )
            )
            add(
                f"Evidence collection:         "
                f"{release_status_label}"
            )
            add(
                "Compatibility matching:      SEPARATE"
            )
            add(
                "Readiness verdict:           NOT PRODUCED"
            )
            add("")
            add(
                "Official evidence is collected release by release. "
                "Evidence completeness does not mean compatibility "
                "assessment is complete."
            )
            if release_same_family:
                add(
                    "Same-family monthly change groups are retained "
                    "as evidence but are not counted as newly crossed."
                )
        else:
            add(
                f"Evidence collection:         "
                f"{release_status_label}"
            )
            add(
                f"Release-range status:        "
                f"{release_range_status}"
            )
            if release_applicability_reason:
                add(
                    "Reason:                     "
                    f"{release_applicability_reason}"
                )
    else:
        add(
            "Official release evidence report unavailable."
        )

    # ------------------------------------------------------------


def render_compatibility_coverage(add, context):
    coverage_collector_label = context['coverage_collector_label']
    coverage_covered_group_count = context['coverage_covered_group_count']
    coverage_incomplete_reference_group_count = context['coverage_incomplete_reference_group_count']
    coverage_mapped_rule_count = context['coverage_mapped_rule_count']
    coverage_missing_mapped_rule_count = context['coverage_missing_mapped_rule_count']
    coverage_no_reference_group_count = context['coverage_no_reference_group_count']
    coverage_official_group_count = context['coverage_official_group_count']
    coverage_partial_group_count = context['coverage_partial_group_count']
    coverage_present_linked_rule_count = context['coverage_present_linked_rule_count']
    coverage_reference_status_label = context['coverage_reference_status_label']
    coverage_registry_group_count = context['coverage_registry_group_count']
    coverage_release_rows = context['coverage_release_rows']
    coverage_report_available = context['coverage_report_available']
    coverage_reported_rule_count = context['coverage_reported_rule_count']
    coverage_status = context['coverage_status']
    coverage_status_label = context['coverage_status_label']
    coverage_unlinked_rule_count = context['coverage_unlinked_rule_count']
    coverage_unmapped_group_count = context['coverage_unmapped_group_count']

    # Compatibility coverage
    # ------------------------------------------------------------

    add("")
    add("COMPATIBILITY COVERAGE")
    add("-" * 58)
    if coverage_report_available:
        add(
            f"Official crossed groups:      "
            f"{coverage_official_group_count}"
        )
        add(
            f"Registry-backed groups:       "
            f"{coverage_registry_group_count}"
        )
        add(
            f"Groups with rule coverage:    "
            f"{coverage_covered_group_count}"
        )
        add(
            f"Partially covered groups:     "
            f"{coverage_partial_group_count}"
        )
        add(
            f"Unmapped registry groups:     "
            f"{coverage_unmapped_group_count}"
        )
        add(
            f"No-reference groups:          "
            f"{coverage_no_reference_group_count}"
        )
        if coverage_incomplete_reference_group_count:
            add(
                f"Incomplete reference groups:  "
                f"{coverage_incomplete_reference_group_count}"
            )
        add("")
        add(
            f"Deterministic rules:          "
            f"{coverage_reported_rule_count}"
        )
        add(
            f"Mapped rules:                 "
            f"{coverage_mapped_rule_count}"
        )
        add(
            f"Linked rules present:         "
            f"{coverage_present_linked_rule_count}"
        )
        add(
            f"Missing mapped rules:         "
            f"{coverage_missing_mapped_rule_count}"
        )
        add(
            f"Unlinked rules:               "
            f"{coverage_unlinked_rule_count}"
        )
        if coverage_release_rows:
            add("")
            add("Release coverage:")
            for item in coverage_release_rows:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue
                release_family = item.get(
                    "release_family",
                    "unknown",
                )
                covered = item.get(
                    "covered_group_count",
                    0,
                )
                total = item.get(
                    "official_group_count",
                    0,
                )
                item_status = str(
                    item.get(
                        "coverage_status",
                        "unknown",
                    )
                ).replace(
                    "_",
                    " ",
                ).upper()
                item_reference_status = str(
                    item.get(
                        "reference_status",
                        "unknown",
                    )
                ).replace(
                    "_",
                    " ",
                ).upper()
                add(
                    f"  {release_family}: "
                    f"{covered} / {total} "
                    f"({item_status}; "
                    f"reference {item_reference_status})"
                )
        add("")
        add(
            f"Reference status:             "
            f"{coverage_reference_status_label}"
        )
        add(
            f"Coverage/reference state:     "
            f"{coverage_status_label}"
        )
        add(
            f"Collector health:             "
            f"{coverage_collector_label}"
        )
        add(
            "Readiness verdict:            NOT PRODUCED"
        )
        add("")
        add(
            "Coverage describes deterministic reference availability "
            "for official backward-incompatible change groups."
        )
        if coverage_status == "no_reference":
            add(
                "No deterministic reference exists for this release "
                "family. This is a supported dynamic-only state, not "
                "a collector failure."
            )
        elif coverage_status == "partial_reference":
            add(
                "Deterministic reference coverage exists for some "
                "crossed release families; remaining groups are "
                "dynamic-only."
            )
        elif coverage_status == "incomplete":
            add(
                "A deterministic registry exists, but expected mapping "
                "or rule evidence is incomplete and should be reviewed."
            )
        else:
            add(
                "A covered group means deterministic rules are linked; "
                "it does not mean every configuration path was inspected "
                "or that the installation is safe to update."
            )
    else:
        add(
            "Compatibility coverage report unavailable."
        )

    # ------------------------------------------------------------


def render_dynamic_upgrade_correlation(add, context):
    correlation_any_count = context['correlation_any_count']
    correlation_compatibility_assessed = context['correlation_compatibility_assessed']
    correlation_deterministic_influence = context['correlation_deterministic_influence']
    correlation_insufficient_count = context['correlation_insufficient_count']
    correlation_model_version = context['correlation_model_version']
    correlation_no_local_count = context['correlation_no_local_count']
    correlation_official_count = context['correlation_official_count']
    correlation_partial_count = context['correlation_partial_count']
    correlation_partial_groups = context['correlation_partial_groups']
    correlation_report_available = context['correlation_report_available']
    correlation_status_label = context['correlation_status_label']
    correlation_strong_count = context['correlation_strong_count']
    correlation_strong_groups = context['correlation_strong_groups']
    correlation_surface_count = context['correlation_surface_count']
    correlation_surface_groups = context['correlation_surface_groups']
    correlation_verdict_produced = context['correlation_verdict_produced']

    # Dynamic upgrade correlation
    # ------------------------------------------------------------

    add("")
    add("DYNAMIC UPGRADE CORRELATION")
    add("-" * 58)
    if correlation_report_available:
        add(
            f"Official change groups:       "
            f"{correlation_official_count}"
        )
        add(
            f"Specific code evidence:       "
            f"{correlation_strong_count}"
        )
        add(
            f"Local surface evidence:       "
            f"{correlation_surface_count}"
        )
        add(
            f"Partial evidence:             "
            f"{correlation_partial_count}"
        )
        add(
            f"No local evidence:            "
            f"{correlation_no_local_count}"
        )
        add(
            f"Insufficient evidence:        "
            f"{correlation_insufficient_count}"
        )
        add("")
        add(
            f"Groups with local evidence:   "
            f"{correlation_any_count} / "
            f"{correlation_official_count}"
        )
        add(
            "Evidence model:               "
            + (
                f"v{correlation_model_version}"
                if correlation_model_version is not None
                else "unknown"
            )
        )
        add(
            f"Correlation collection:       "
            f"{correlation_status_label}"
        )
        add(
            "Compatibility assessed:       "
            + (
                "YES"
                if correlation_compatibility_assessed
                else "NO"
            )
        )
        add(
            "Readiness verdict:            "
            + (
                "PRODUCED"
                if correlation_verdict_produced
                else "NOT PRODUCED"
            )
        )
        add(
            "Deterministic outcomes used:  "
            + (
                "YES"
                if correlation_deterministic_influence
                else "NO"
            )
        )
        if (
            correlation_strong_groups
            or correlation_surface_groups
            or correlation_partial_groups
        ):
            add("")
        if correlation_strong_groups:
            add("Specific:")
            for heading in correlation_strong_groups:
                add(
                    f"  {heading}"
                )
        if correlation_surface_groups:
            add("Local surface:")
            for heading in correlation_surface_groups:
                add(
                    f"  {heading}"
                )
        if correlation_partial_groups:
            add("Partial:")
            for heading in correlation_partial_groups:
                add(
                    f"  {heading}"
                )
        add("")
        add(
            "Dynamic correlation identifies local evidence related "
            "to official change groups."
        )
        add(
            "It does not decide whether the installation is affected, "
            "compatible, incompatible, or safe to update."
        )
    else:
        add(
            "Dynamic upgrade correlation report unavailable."
        )

    # ------------------------------------------------------------


def render_correlation_validation(add, context):
    validation_accuracy_score_produced = context['validation_accuracy_score_produced']
    validation_aligned_count = context['validation_aligned_count']
    validation_aligned_local_count = context['validation_aligned_local_count']
    validation_aligned_no_local_count = context['validation_aligned_no_local_count']
    validation_collector_label = context['validation_collector_label']
    validation_compatibility_assessed = context['validation_compatibility_assessed']
    validation_deterministic_gap_count = context['validation_deterministic_gap_count']
    validation_dynamic_gap_count = context['validation_dynamic_gap_count']
    validation_groups_compared = context['validation_groups_compared']
    validation_groups_observed = context['validation_groups_observed']
    validation_incomplete_reference_count = context['validation_incomplete_reference_count']
    validation_missing_reference_count = context['validation_missing_reference_count']
    validation_precision_headings = context['validation_precision_headings']
    validation_precision_review_count = context['validation_precision_review_count']
    validation_reference_count = context['validation_reference_count']
    validation_reference_status = context['validation_reference_status']
    validation_report_available = context['validation_report_available']
    validation_status_label = context['validation_status_label']
    validation_unresolved_count = context['validation_unresolved_count']
    validation_verdict_produced = context['validation_verdict_produced']

    # Correlation validation
    # ------------------------------------------------------------

    add("")
    add("CORRELATION VALIDATION")
    add("-" * 58)
    if validation_report_available:
        add(
            f"Official groups observed:      "
            f"{validation_groups_observed}"
        )
        add(
            f"Official groups compared:      "
            f"{validation_groups_compared}"
        )
        add(
            f"Deterministic references:      "
            f"{validation_reference_count}"
        )
        add(
            f"Groups without reference:      "
            f"{validation_missing_reference_count}"
        )
        if validation_incomplete_reference_count:
            add(
                f"Incomplete references:         "
                f"{validation_incomplete_reference_count}"
            )
        if validation_groups_compared:
            add("")
            add(
                f"Aligned local relevance:       "
                f"{validation_aligned_count} / "
                f"{validation_groups_compared}"
            )
            add(
                f"  Local evidence:              "
                f"{validation_aligned_local_count}"
            )
            add(
                f"  No local evidence:           "
                f"{validation_aligned_no_local_count}"
            )
            add("")
            add(
                f"Dynamic gaps:                  "
                f"{validation_dynamic_gap_count}"
            )
            add(
                f"Deterministic gaps:            "
                f"{validation_deterministic_gap_count}"
            )
            add(
                f"Unresolved comparisons:        "
                f"{validation_unresolved_count}"
            )
            add(
                f"Precision reviews:             "
                f"{validation_precision_review_count}"
            )
        add("")
        add(
            f"Reference validation:          "
            f"{validation_status_label}"
        )
        add(
            f"Collector health:              "
            f"{validation_collector_label}"
        )
        add(
            "Accuracy score:                "
            + (
                "PRODUCED"
                if validation_accuracy_score_produced
                else "NOT PRODUCED"
            )
        )
        add(
            "Compatibility assessed:        "
            + (
                "YES"
                if validation_compatibility_assessed
                else "NO"
            )
        )
        add(
            "Readiness verdict:             "
            + (
                "PRODUCED"
                if validation_verdict_produced
                else "NOT PRODUCED"
            )
        )
        if validation_precision_headings:
            add("")
            add("Precision review:")
            for heading in validation_precision_headings:
                add(
                    f"  {heading}"
                )
        add("")
        if validation_reference_status == "no_reference":
            add(
                "No deterministic reference exists for this release "
                "family. Dynamic correlation remains valid and "
                "independent."
            )
        elif validation_reference_status == "partial_reference":
            add(
                "Validation covers only official groups with a "
                "deterministic reference; remaining groups are "
                "dynamic-only."
            )
        elif validation_reference_status == "incomplete":
            add(
                "Expected deterministic reference material is "
                "incomplete, so the affected comparisons require "
                "review."
            )
        else:
            add(
                "Validation compares local-relevance alignment between "
                "the dynamic and deterministic paths."
            )
            add(
                "Alignment is reference evidence only. It is not an "
                "accuracy score, compatibility verdict, or proof that "
                "either path is correct."
            )
    else:
        add(
            "Correlation validation report unavailable."
        )

    # ------------------------------------------------------------


def render_upgrade_compatibility(add, context):
    compatibility_active_yaml_count = context['compatibility_active_yaml_count']
    compatibility_manual_review_count = context['compatibility_manual_review_count']
    compatibility_no_affected_count = context['compatibility_no_affected_count']
    compatibility_no_local_match_count = context['compatibility_no_local_match_count']
    compatibility_other_outcome_count = context['compatibility_other_outcome_count']
    compatibility_review_required_count = context['compatibility_review_required_count']
    compatibility_rule_count = context['compatibility_rule_count']
    compatibility_rule_pack_label = context['compatibility_rule_pack_label']
    compatibility_runtime_fetch = context['compatibility_runtime_fetch']
    compatibility_ui_prompts_inspected = context['compatibility_ui_prompts_inspected']
    compatibility_verdict_produced = context['compatibility_verdict_produced']
    compatibility_window = context['compatibility_window']
    compatibility_yaml_failures = context['compatibility_yaml_failures']
    coverage_status = context['coverage_status']
    upgrade_compatibility_available = context['upgrade_compatibility_available']

    # Upgrade compatibility
    # ------------------------------------------------------------

    add("")
    add("UPGRADE COMPATIBILITY")
    add("-" * 58)
    if upgrade_compatibility_available:
        if compatibility_rule_count:
            add(
                f"Core rule pack:              "
                f"{compatibility_rule_pack_label}"
            )
            add(
                "Upgrade window:              "
                f"{compatibility_window.get('installed_version')}"
                " -> "
                f"{compatibility_window.get('target_version')}"
            )
            add(
                f"Rules assessed:              "
                f"{compatibility_rule_count}"
            )
            add("")
            add(
                f"No local match:              "
                f"{compatibility_no_local_match_count}"
            )
            add(
                f"Local match, no affected use: "
                f"{compatibility_no_affected_count}"
            )
            add(
                f"Review required:             "
                f"{compatibility_review_required_count}"
            )
            add(
                f"Manual review:               "
                f"{compatibility_manual_review_count}"
            )
            if compatibility_other_outcome_count:
                add(
                    f"Other local outcomes:        "
                    f"{compatibility_other_outcome_count}"
                )
            add("")
            add(
                f"Active YAML checked:         "
                f"{compatibility_active_yaml_count}"
            )
            add(
                f"YAML scan failures:          "
                f"{len(compatibility_yaml_failures)}"
            )
            add("")
            add(
                "LLM UI-managed prompts:      "
                + (
                    "INSPECTED"
                    if compatibility_ui_prompts_inspected
                    else "NOT INSPECTED"
                )
            )
            add(
                "Compatibility scanner fetch: "
                + (
                    "PERFORMED"
                    if compatibility_runtime_fetch
                    else "NOT PERFORMED"
                )
            )
            add(
                "Readiness verdict:           "
                + (
                    "PRODUCED"
                    if compatibility_verdict_produced
                    else "NOT PRODUCED"
                )
            )
            add("")
            add(
                "Rule results are evidence for review, not a "
                "safe-to-update verdict."
            )
            if not compatibility_ui_prompts_inspected:
                add(
                    "UI-managed LLM prompt content is outside "
                    "the current local scan scope."
                )
        else:
            if coverage_status == "no_reference":
                add(
                    "No deterministic Core compatibility rule pack "
                    "is available for this upgrade window."
                )
                add(
                    "This is a supported dynamic-only state. "
                    "See DYNAMIC UPGRADE CORRELATION for the "
                    "available local evidence."
                )
            else:
                add(
                    "No version-specific Core compatibility "
                    "rule pack is applicable to this run."
                )
    else:
        add(
            "Upgrade compatibility report unavailable."
        )

    # ------------------------------------------------------------


def render_upgrade_sections(add, context):
    render_update_readiness(add, context)
    render_official_release_evidence(add, context)
    render_compatibility_coverage(add, context)
    render_dynamic_upgrade_correlation(add, context)
    render_correlation_validation(add, context)
    render_upgrade_compatibility(add, context)

