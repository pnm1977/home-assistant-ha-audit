# HA Audit

**Home Assistant health, configuration and Core update-readiness checks — with an investigation Web UI.**

HA Audit helps you identify what deserves attention, understand the evidence behind a finding, and review a pending Home Assistant Core update. It checks your installation without automatically repairing, deleting or changing Home Assistant configuration.

**Recommended workflow:** Run → Read → Investigate → Act → Rerun.

> **Current documentation:** HA Audit v0.8.23 (0.8.x series). The project is under active development. Findings are evidence-based guidance, not guarantees that a system is healthy or that an update is safe.

## Run an audit

1. In Home Assistant, open **Settings → Apps → HA Audit**.
2. Select **Start**. Check the **Log** tab for the latest run summary and any errors.
3. After the audit finishes, select **Open Web UI**.
4. Start with **Where to focus**, then expand an issue to review the evidence or record your investigation.

**The audit runs when the app starts.** Its Web UI remains available while the app is running, even after the audit finishes. Keeping the Web UI open **does not** continuously rescan Home Assistant. Restart the app (or stop and start it) to collect a new audit.

If an audit stage fails, review the app log. Missing or incomplete evidence must not be interpreted as a clean bill of health.

## What HA Audit checks

- **System health:** Core, Supervisor and OS information, update availability, Repairs and key health indicators.
- **Configuration:** Validation; active YAML include trees; missing include targets and entity references; possible duplicate automation IDs, aliases and script names; and configuration review candidates.
- **Devices and availability:** Entity and device inventory; unavailable and unknown states; partial versus whole-device availability; and Recorder history where available.
- **System Log:** Related warnings and errors grouped into issue families, evidence-based technical priorities, and recurrence across independent audit runs.
- **Core update readiness:** Official Home Assistant release evidence, locally relevant compatibility checks, evidence coverage, and a conservative recommendation that separates upgrade concerns from general system health.

HA Audit retains detailed reports alongside a concise user-facing summary. Not every potential issue is included in the short summary; lower-priority findings remain available in the detailed evidence.

## Investigate findings in the Web UI

### Where to focus

The Web UI separates a finding's **technical priority** (for example, HIGH) from the **investigation recommendation**:

| Category | Meaning |
| --- | --- |
| **Investigate / continue** | Further investigation is warranted. |
| **Monitoring** | You are watching a previously observed problem or a change you have made. |
| **Explanation to verify** | A saved explanation requires more evidence or conflicts with sampled evidence. |
| **Sampled power-off — no immediate action** | Sampled errors for an explained finding occurred while its recorded controlling switch was OFF. Unchecked and future errors are not dismissed. |

A finding can remain **HIGH** and **RECURRING 24H+** even when its immediate investigation recommendation changes. HA Audit does not rewrite the original log priority or erase historical evidence.

### Save investigation context

Expand **Issues needing review → Review / update** to save:

- A status: **Investigating**, **Monitoring**, **Explained** or **Resolved**.
- Notes about observations, changes and next checks (up to 4,000 characters).
- An optional physical **Power-control switch** entity, such as `switch.some_smart_plug`.
- An optional **Scheduled maintenance** window, with start and end times, a time zone and daily, weekly or monthly frequency. Weekly schedules can select weekdays; monthly schedules can use a calendar date or a weekday occurrence.

Feedback and its change history are saved in HA Audit's own private app configuration storage. Existing records are retained across audits and app updates when that storage is preserved. Saving feedback does **not** change Home Assistant entities, automation settings or System Log entries.

### Automatic evidence checks

If a power-control switch is saved, HA Audit can compare **sampled System Log timestamps** with the switch's Recorder history and report **OFF**, **ON** or **UNKNOWN**.

If a maintenance schedule is saved, HA Audit can compare sampled timestamps against the configured local-time window and report **INSIDE**, **OUTSIDE** or **UNKNOWN**. The schedule uses the supplied time zone, including applicable daylight-saving rules, and supports windows crossing midnight.

The interface can also distinguish **NEW ACTIVITY**, **RETAINED EVIDENCE** and **BASELINE** using cross-run history. Retained evidence means no independently new activity was detected in that audit; it does not prove that a problem is fixed.

**Evidence limits matter:** Home Assistant deduplicates some System Log entries, so only selected first/last timestamps may be available. A switch being OFF or an error falling inside a maintenance window is consistent with an explanation, **not proof of causation**. Missing history is unknown, not evidence that an error is harmless. Technical priorities and saved investigation statuses are preserved.

## Core update guidance

HA Audit keeps **general Home Assistant health** separate from **Core update readiness**. It reports what was checked and what could not be assessed. For example:

- **ASSESSMENT INCOMPLETE:** Some relevant compatibility evidence or coverage is missing; this is not automatically a blocker.
- **NO KNOWN BLOCKERS FOUND:** No known blocker was identified in the evidence checked; this is **not** a safety guarantee.

Review any required checks and remaining uncertainty before updating. HA Audit does **not** install updates.

## AI handoff and detailed reports

Use **Copy for AI** or **Download handoff** in the Web UI to obtain `ha_audit_ai_handoff.md`, including the latest audit context and saved investigation notes. The companion `ha_audit_ai_evidence.json` and other detailed JSON reports provide more technical information.

The current-run summary is also stored as `ha_audit_latest.txt`. Reports reside in the app's private configuration storage (under `/addon_configs` where Home Assistant exposes it).

**Nothing is automatically sent to an external AI provider.** You choose whether to copy or share a report. Review any handoff before sharing: it may include device names, entity IDs, IP addresses or personal investigation notes.

## Safety and limitations

- HA Audit does not automatically change, repair or delete Home Assistant configuration or entities.
- Saving investigation notes and schedules changes only HA Audit's own data.
- An unavailable entity or missing Recorder history does not, by itself, justify deleting anything.
- Some Home Assistant UI-managed configuration cannot be inspected through the YAML scan.
- Audit conclusions depend on the evidence available at the time, including Recorder retention and System Log deduplication.

For detailed walkthroughs, see the [User Guide](DOCS.md). For development history, see the [Changelog](CHANGELOG.md).
