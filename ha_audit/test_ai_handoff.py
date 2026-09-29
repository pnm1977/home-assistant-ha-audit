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
Core evidence collection:    COMPLETE
Config check:                VALID

WHY THIS RESULT
----------------------------------------------------------
Home Assistant health:
  2 device(s) currently have no healthy state entities.

Core update:
  No known blockers were found in the evidence HA Audit inspected.
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
        "## Purpose",
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
        (
            "Do not recommend deleting entities"
        ),
        (
            "general Home Assistant health and "
            "Core update guidance"
        ),
        "## Important limitations",
        (
            "request the relevant detailed report "
            "rather than inventing missing information"
        ),
        "## Requested analysis",
        "## HA Audit evidence",
        "Home Assistant health:       NEEDS ATTENTION",
        "Core update:                 NO KNOWN BLOCKERS FOUND",
        "OS update:                   UPDATE AVAILABLE",
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
        "Requested analysis:           PASS"
    )
    print(
        "Audit evidence embedded:      PASS"
    )

    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
