# HA Audit — Home Assistant health and upgrade-readiness checks

**Understand what needs attention before changing anything.**

HA Audit is a Home Assistant app that reviews system health, configuration, unavailable devices, System Log issues, and evidence relevant to a pending Home Assistant Core update. It provides a concise summary, an investigation Web UI, and detailed reports for deeper analysis.

HA Audit **does not automatically repair or change Home Assistant**. Its recommended workflow is **run → read → investigate → act → rerun**.

> **Project status:** Under active development. Findings and update guidance are evidence-based, not guarantees that a system is healthy or an update is safe.

## What you can do

- **Understand system health:** Review the most important findings without having to interpret every log message.
- **Assess Core updates:** See what HA Audit checked, which compatibility concerns were found, and which parts of the assessment remain incomplete.
- **Review configuration:** Check the active YAML include tree, missing references, duplicate automation or script definitions, and potential cleanup candidates.
- **Understand availability:** Distinguish partial device unavailability from wholly unavailable devices, using Recorder history where available.
- **Investigate recurring problems:** Group and prioritise System Log issues, distinguish historical recurrence from newly detected activity, and preserve investigation notes across runs.
- **Verify possible explanations:** Compare sampled error timestamps with a device's controlling switch or a saved maintenance schedule.
- **Share evidence with an AI assistant:** Copy or download a vendor-neutral handoff for further analysis, under your control.

## Install and run

1. In Home Assistant, open **Settings → Apps → App Store**.
2. Open the App Store menu, choose **Repositories**, and add:

   ```text
   https://github.com/pnm1977/home-assistant-ha-audit
   ```

3. Find **HA Audit** and install it.
4. Open **Settings → Apps → HA Audit** and select **Start**.
5. Check the **Log** for the run summary, then select **Open Web UI** to review findings.

**The audit runs when the app starts.** When the audit finishes, the Web UI remains accessible while the app is running. Leaving it open does **not** continuously rescan Home Assistant. To collect new evidence, restart the app (or stop and start it).

See the **[User Guide](ha_audit/DOCS.md)** for the full walkthrough and troubleshooting instructions.

## Start in the Web UI

### Where to focus

This section separates the original technical priority from the practical investigation recommendation:

| Category | Meaning |
|---|---|
| **Investigate / continue** | Findings that still warrant investigation, including sampled errors while a linked power switch was ON. |
| **Monitoring** | A change or pattern is being watched for fresh evidence. |
| **Explanation to verify** | An explanation needs confirmation because relevant evidence is missing, unknown, or inconsistent. |
| **Sampled power-off — no immediate action** | Sampled errors for an explained finding occurred exclusively while its controlling switch was OFF. Unchecked and future errors remain open to review. |

A finding can remain **HIGH** or **RECURRING 24H+** while its recommended action changes. HA Audit preserves the underlying logs and technical priority.

### Save an investigation

Under **Issues needing review → Review / update**, you can:

- Set the status to **Investigating**, **Monitoring**, **Explained**, or **Resolved**.
- Record findings, changes, and next checks in notes (up to 4,000 characters).
- Add an optional **power-control switch** that physically supplies the affected device.
- Add an optional **scheduled maintenance window**: daily, selected weekdays, monthly calendar date, or monthly weekday occurrence, with a time zone.

Notes and settings are saved in HA Audit's private configuration storage and retained across audit runs and updates where that storage is preserved. These are **user-provided explanations**, not automatically proven causes.

### Understand automatic evidence

HA Audit can compare **sampled System Log timestamps** against recorded switch state (**OFF / ON / UNKNOWN**) or a configured maintenance window (**INSIDE / OUTSIDE / UNKNOWN**). It can also show whether a new audit detected **NEW ACTIVITY**, **RETAINED EVIDENCE**, or a **BASELINE** observation.

These checks help prioritise follow-up, but they have limits:

- Home Assistant may deduplicate repeated System Log entries; **not every occurrence has an individual timestamp**.
- A switch reporting OFF is consistent with power loss, but does not prove causation.
- An error occurring during a scheduled window does not prove maintenance actually happened or caused it.
- **RETAINED EVIDENCE** means no independently new activity was detected in that audit, not that the problem is fixed.
- Missing history or unknown evidence is never treated as proof that an error is harmless.

The original technical priority, recurrence classification, and saved investigation status remain visible.

## Core update guidance

HA Audit uses Home Assistant Repairs, official Core release evidence, local configuration and integration information, compatibility rules where available, and dynamic correlation to assess an upgrade window.

Its conclusion may be **NO KNOWN BLOCKERS FOUND**, **REVIEW BEFORE UPDATING**, **ASSESSMENT INCOMPLETE**, or **DELAY — BLOCKER EVIDENCE FOUND** (or indicate that no Core update is pending).

**ASSESSMENT INCOMPLETE** means some evidence or coverage was insufficient; it does not itself mean a blocker exists. **NO KNOWN BLOCKERS FOUND** is not a guarantee of safety. General device-health issues are kept separate from Core update readiness.

### Core readiness evidence trace

For a pending Core update, the detailed summary includes a **CORE READINESS EVIDENCE TRACE** showing how initially uncertain compatibility groups were handled:

- **Automatically assessed:** A scoped local rule checked the relevant evidence.
- **Manually confirmed:** The user explicitly confirmed the condition; this is **not machine verification**.
- **Still unresolved:** The available evidence did not resolve the uncertainty.

The trace covers reconciliation of initially uncertain groups. It does **not** establish that all official changes or UI-managed settings were inspected, or guarantee update safety.

## AI handoff and detailed reports

After an audit, use **Share with AI → Copy for AI** or **Download handoff** in the Web UI. The file `ha_audit_ai_handoff.md` combines current findings, the Core readiness evidence trace, investigation context, and sampled evidence. The companion `ha_audit_ai_evidence.json` contains more technical detail.

Other reports, including `ha_audit_latest.txt`, `log_priority_final.json`, `log_recurrence.json`, `availability_audit.json`, and `update_readiness_audit.json`, are stored in HA Audit's private app configuration folder (accessible under `/addon_configs` where supported).

**HA Audit does not automatically send reports to an AI provider.** Review reports before sharing them: they may contain device names, entity IDs, network details, and saved investigation notes.

## Safety and limitations

- HA Audit reads Home Assistant evidence but does not change Home Assistant configuration, delete entities, or install updates.
- Saving investigation feedback changes **HA Audit's own private data**, not Home Assistant settings.
- Unavailable devices or missing Recorder history are not, by themselves, reasons to delete entities.
- Some settings managed through the Home Assistant UI are outside configuration-scan scope.
- Its System Log and Recorder evidence are limited by collection windows, retention, and deduplication.

For full instructions, see the **[User Guide](ha_audit/DOCS.md)**. For changes between versions, see the **[Changelog](ha_audit/CHANGELOG.md)**.
