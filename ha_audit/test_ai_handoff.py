from datetime import datetime, timezone

import ai_handoff


SAMPLE_SUMMARY = """==========================================================
HA AUDIT vtest - CURRENT RUN SUMMARY
==========================================================

OVERVIEW
----------------------------------------------------------
Home Assistant health:       NEEDS ATTENTION
Core update:                 NO KNOWN BLOCKERS FOUND
OS update:                   UPDATE AVAILABLE

WHY THIS RESULT
----------------------------------------------------------
Home Assistant health:
  2 device(s) currently have no healthy state entities.

SYSTEM
----------------------------------------------------------
Core:                        2026.8.3
OS:                          18.2

UPDATE READINESS
----------------------------------------------------------
Pending updates:             2

OFFICIAL RELEASE EVIDENCE
----------------------------------------------------------
Evidence collection:         COMPLETE

COMPATIBILITY COVERAGE
----------------------------------------------------------
Coverage/reference state:    COMPLETE

DYNAMIC UPGRADE CORRELATION
----------------------------------------------------------
Correlation collection:      COMPLETE

CORRELATION VALIDATION
----------------------------------------------------------
Reference validation:        COMPLETE

UPGRADE COMPATIBILITY
----------------------------------------------------------
Review required:             0

CONFIGURATION
----------------------------------------------------------
Missing active includes:     0

ENTITY HEALTH
----------------------------------------------------------
Unavailable:                 10

AVAILABILITY CONTEXT
----------------------------------------------------------
Whole device unavailable:    2 entities / 2 devices

UNAVAILABLE HISTORY CONTEXT
----------------------------------------------------------
History query failures:      0

REVIEW
----------------------------------------------------------
Not provided + active YAML:  0

NOT-PROVIDED HISTORY SAFETY
----------------------------------------------------------
History query failures:      0

NEXT ACTIONS
----------------------------------------------------------
[i] Review 2 unavailable devices.

DETAILED REPORTS
----------------------------------------------------------
audit_snapshot.json
"""


class FixedDateTime(datetime):
    @classmethod
    def now(
        cls,
        tz=None,
    ):
        value = cls(
            2026,
            9,
            29,
            10,
            30,
            0,
            tzinfo=timezone.utc,
        )

        if tz is not None:
            return value.astimezone(tz)

        return value


def main():
    original_datetime = ai_handoff.datetime
    original_version = ai_handoff.VERSION

    try:
        ai_handoff.datetime = FixedDateTime
        ai_handoff.VERSION = "test"

        handoff = ai_handoff.build_handoff(
            SAMPLE_SUMMARY
        )

    finally:
        ai_handoff.datetime = original_datetime
        ai_handoff.VERSION = original_version

    required_text = (
        "# HA Audit AI / LLM Handoff",
        "HA Audit vtest",
        (
            "Generated: "
            "2026-09-29T10:30:00+00:00"
        ),
        "vendor-neutral handoff",
        "ChatGPT",
        "Claude",
        "Gemini",
        "local LLMs",
        "## Instructions for the receiving AI",
        (
            "Treat HA Audit findings as evidence, "
            "not as proof"
        ),
        (
            "Do not claim that a Home Assistant "
            "update is guaranteed safe."
        ),
        "Do not recommend deleting entities",
        "## Important limitations",
        "## Requested analysis",
        "## HA Audit evidence",
        "OVERVIEW",
        "WHY THIS RESULT",
        "SYSTEM",
        "UPDATE READINESS",
        "OFFICIAL RELEASE EVIDENCE",
        "UPGRADE COMPATIBILITY",
        "CONFIGURATION",
        "AVAILABILITY CONTEXT",
        "UNAVAILABLE HISTORY CONTEXT",
        "REVIEW",
        "NOT-PROVIDED HISTORY SAFETY",
        "NEXT ACTIONS",
    )

    missing = [
        text
        for text in required_text
        if text not in handoff
    ]

    if missing:
        raise AssertionError(
            "Missing expected handoff text: "
            + ", ".join(missing)
        )

    excluded_text = (
        "COMPATIBILITY COVERAGE",
        "DYNAMIC UPGRADE CORRELATION",
        "CORRELATION VALIDATION",
        "ENTITY HEALTH",
        "DETAILED REPORTS",
    )

    unexpected = [
        text
        for text in excluded_text
        if text in handoff
    ]

    if unexpected:
        raise AssertionError(
            "Unexpected verbose section in handoff: "
            + ", ".join(unexpected)
        )

    if not handoff.endswith(
        "```\n"
    ):
        raise AssertionError(
            "Handoff should finish after the "
            "evidence code block."
        )

    print("")
    print("=" * 62)
    print("HA AUDIT AI / LLM HANDOFF TEST")
    print("=" * 62)

    print(
        "Vendor-neutral purpose:       PASS"
    )
    print(
        "Receiving-AI instructions:    PASS"
    )
    print(
        "Safety limitations:           PASS"
    )
    print(
        "Selected evidence sections:   PASS"
    )
    print(
        "Verbose sections excluded:    PASS"
    )

    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
