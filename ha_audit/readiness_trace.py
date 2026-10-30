"""Presentation-only trace of the Core update readiness decision.

Input is the already evaluated readiness guidance. This module never changes
an update recommendation or reinterprets unrelated compatibility groups.
"""

from readiness_guidance import STATE_NO_UPDATE


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _group_label(row):
    family = row.get("release_family")
    heading = row.get("heading")
    if not isinstance(family, str) or not family.strip():
        return None
    if not isinstance(heading, str) or not heading.strip():
        return None
    return f"{family} — {heading}"


def _validated_groups(reconciliation):
    """Return classified exact-group evidence, or None on ambiguity."""
    if not isinstance(reconciliation, dict):
        return None
    if reconciliation.get("status") not in ("reconciled", "unchanged"):
        return None
    original = _count(reconciliation.get("original_insufficient_count"))
    remaining = _count(reconciliation.get("remaining_insufficient_count"))
    resolved = reconciliation.get("resolved_groups")
    unresolved = reconciliation.get("unresolved_groups")
    if (original is None or remaining is None
            or not isinstance(resolved, list)
            or not isinstance(unresolved, list)
            or original != len(resolved) + len(unresolved)
            or remaining != len(unresolved)):
        return None

    automatic, manual, still_open = [], [], []
    seen = set()
    for row in resolved + unresolved:
        if not isinstance(row, dict):
            return None
        label = _group_label(row)
        if label is None:
            return None
        key = (row["release_family"], row["heading"])
        if key in seen:
            return None
        seen.add(key)

    for row in resolved:
        label = _group_label(row)
        if row.get("source") == "explicit_user_confirmation":
            if (row.get("outcome") != "user_checked_no_issue"
                    or not isinstance(row.get("reviewed_at"), str)
                    or not row["reviewed_at"].strip()):
                return None
            manual.append((label, row["reviewed_at"]))
        elif (not row.get("source")
              and isinstance(row.get("rule_id"), str)
              and row["rule_id"].strip()
              and row.get("outcome") in
              ("no_affected_usage_found", "review_required")):
            # The existing reconciler represents local machine checks using
            # rule_id + outcome, and explicit user review using source.
            automatic.append((label, row["rule_id"], row["outcome"]))
        else:
            return None
    still_open = [_group_label(row) for row in unresolved]
    return original, remaining, automatic, manual, still_open


def render_readiness_trace(add, context):
    """Append a human-readable evidence trace to the detailed audit summary.

    Called with the same locals() context already used by summary_upgrade.py.
    The existing readiness engine remains the sole decision authority.
    """
    guidance = context.get("core_guidance") if isinstance(context, dict) else None
    add("")
    add("CORE READINESS EVIDENCE TRACE")
    add("-" * 58)
    if not isinstance(guidance, dict):
        add("Decision evidence: UNAVAILABLE; do not infer clearance.")
        return

    status = guidance.get("status")
    add(f"Core guidance:               {status or 'UNKNOWN'}")
    if status == STATE_NO_UPDATE:
        add("No Core update is pending; reconciliation is not applicable.")
        return

    reasons = guidance.get("reason_codes")
    if isinstance(reasons, list) and all(isinstance(x, str) for x in reasons):
        if reasons:
            add("Decision reason codes:       " + ", ".join(reasons))
        else:
            add("Decision reason codes:       none reported")
    else:
        add("Decision reason codes:       unavailable or inconsistent")

    classified = _validated_groups(guidance.get("dynamic_reconciliation"))
    if classified is None:
        add("Uncertainty trace:           UNAVAILABLE / INCONSISTENT")
        add("Do not assume that missing trace data means zero unresolved groups.")
        return

    original, remaining, automatic, manual, unresolved = classified
    add(f"Initially uncertain groups:  {original}")
    add(f"Reconciled local checks:     {len(automatic)}")
    add(f"Accepted user confirmations: {len(manual)}")
    add(f"Still unresolved groups:     {remaining}")
    add("")
    add("The DYNAMIC UPGRADE CORRELATION section shows the original")
    add("insufficient-evidence count before these later checks and")
    add("confirmations. This trace shows the subsequent outcome.")

    if automatic:
        add("")
        add("Automatically assessed (local rule evidence):")
        for label, rule, outcome in automatic:
            add(f"  - {label} | rule {rule} | {outcome.replace('_', ' ')}")
    if any(outcome == "review_required" for _, _, outcome in automatic):
        add("  A local rule requiring review is NOT a clearance to update.")
    if manual:
        add("")
        add("Explicitly confirmed by user (NOT machine-verified):")
        for label, timestamp in manual:
            add(f"  - {label} | confirmed {timestamp}")
    if unresolved:
        add("")
        add("Insufficient evidence still requiring assessment:")
        for label in unresolved:
            add(f"  - {label}")
    add("")
    add("This trace accounts only for reconciliation of insufficient-evidence")
    add("groups, not complete inspection of all official changes or UI settings.")
    add("A user confirmation is an assertion; a local check covers only its")
    add("specified scope. Neither is a guarantee that updating is safe.")
