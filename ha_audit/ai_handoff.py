import os
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

SUMMARY_FILE = "/config/ha_audit_latest.txt"

OUTPUT_FILE = "/config/ha_audit_ai_handoff.md"


def load_summary():
    try:
        with open(
            SUMMARY_FILE,
            "r",
            encoding="utf-8",
        ) as handle:
            return handle.read().strip()
    except Exception as exc:
        raise RuntimeError(
            "Could not read HA Audit summary: "
            f"{exc}"
        ) from exc


def build_handoff(summary):
    generated_at = datetime.now(
        timezone.utc
    ).isoformat()

    lines = [
        "# HA Audit AI / LLM Handoff",
        "",
        (
            "This file was generated automatically by "
            f"HA Audit v{VERSION}."
        ),
        "",
        f"Generated: {generated_at}",
        "",
        "## Purpose",
        "",
        (
            "This is a vendor-neutral handoff for analysis "
            "by an AI or large language model."
        ),
        "",
        (
            "It is intended for assistants such as ChatGPT, "
            "Claude, Gemini, local LLMs, or other systems "
            "capable of analysing Home Assistant evidence."
        ),
        "",
        (
            "The evidence below comes from HA Audit's "
            "current-run summary."
        ),
        "",
        "## Instructions for the receiving AI",
        "",
        (
            "- Treat HA Audit findings as evidence, not as "
            "proof of a fault or guarantee of safety."
        ),
        (
            "- Clearly distinguish facts reported by HA Audit "
            "from your own inference or advice."
        ),
        (
            "- Do not claim that a Home Assistant update is "
            "guaranteed safe."
        ),
        (
            "- Do not recommend deleting entities, devices, "
            "YAML, automations, scripts, or configuration "
            "solely because they are unavailable, unknown, "
            "or not currently provided."
        ),
        (
            "- Treat availability and Recorder-history "
            "findings as context unless stronger evidence "
            "shows an actual fault."
        ),
        (
            "- Respect HA Audit's distinction between general "
            "Home Assistant health and Core update guidance."
        ),
        (
            "- If evidence collection is incomplete, say what "
            "is missing rather than filling the gap with an "
            "assumption."
        ),
        (
            "- Prioritise concrete findings that deserve "
            "attention before informational observations."
        ),
        (
            "- Explain findings in normal Home Assistant "
            "language suitable for a smart-home enthusiast."
        ),
        (
            "- When suggesting a change, explain which HA Audit "
            "evidence supports that suggestion."
        ),
        "",
        "## Important limitations",
        "",
        (
            "- HA Audit is read-only and does not prove that "
            "an installation is fault-free."
        ),
        (
            "- Core update guidance is conservative "
            "evidence-based guidance, not a safe-to-update "
            "guarantee."
        ),
        (
            "- Availability classifications may represent "
            "intentional, temporary, or feature-level states."
        ),
        (
            "- Recorder history only covers the history that "
            "was actually available to HA Audit."
        ),
        (
            "- Some Home Assistant configuration may be "
            "UI-managed or otherwise outside the local scan "
            "scope."
        ),
        (
            "- The detailed JSON reports contain more evidence "
            "than this handoff. If the summary is insufficient, "
            "request the relevant detailed report rather than "
            "inventing missing information."
        ),
        "",
        "## Requested analysis",
        "",
        (
            "Using the evidence below, identify what deserves "
            "attention first, explain why, and separate "
            "actionable findings from informational context."
        ),
        "",
        (
            "If a Core or OS update is pending, explain the "
            "available readiness evidence and any limitations "
            "without claiming certainty."
        ),
        "",
        "## HA Audit evidence",
        "",
        "```text",
        summary,
        "```",
        "",
    ]

    return "\n".join(lines)


def main():
    summary = load_summary()

    handoff = build_handoff(
        summary
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(handoff)

    print(
        "AI / LLM handoff written to "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
