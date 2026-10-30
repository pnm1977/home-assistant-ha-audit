# HA Audit User Guide

**For HA Audit v0.8.30 and later in the 0.8.x series.**

HA Audit helps you understand your Home Assistant installation, decide what needs attention, investigate recurring problems, and review evidence before a Home Assistant Core update. It checks configuration, devices, availability, System Log findings, and update-readiness information.

**HA Audit does not automatically repair or change Home Assistant.** It reads Home Assistant evidence and saves its own reports and optional investigation notes in the app's private configuration storage. Nothing is automatically sent to an AI provider.

The recommended approach is **Run → Read → Investigate → Act → Rerun**. Do not try to make every warning or unavailable-entity count disappear.

## Contents

1. [Run an audit and open the Web UI](#1-run-an-audit-and-open-the-web-ui)
2. [Choose where to focus](#2-choose-where-to-focus)
3. [Record an investigation](#3-record-an-investigation)
4. [Check evidence against a power-control switch](#4-check-evidence-against-a-power-control-switch)
5. [Check evidence against scheduled maintenance](#5-check-evidence-against-scheduled-maintenance)
6. [Understand new activity and historical errors](#6-understand-new-activity-and-historical-errors)
7. [Share a report with an AI assistant](#7-share-a-report-with-an-ai-assistant)
8. [Understand Core update guidance](#8-understand-core-update-guidance)
9. [Review configuration and device availability](#9-review-configuration-and-device-availability)
10. [Find detailed reports](#10-find-detailed-reports)
11. [Safety, privacy, and limitations](#11-safety-privacy-and-limitations)

---

## 1. Run an audit and open the Web UI

### Installation

In Home Assistant, open **Settings → Apps → App Store**, then open the App Store menu and select **Repositories**. Add the HA Audit repository:

```text
https://github.com/pnm1977/home-assistant-ha-audit
```

Find **HA Audit** in the App Store and install it.

### Start an audit

1. Open **Settings → Apps → HA Audit** and select **Start**.
2. Watch the **Log** tab for the current run's summary and any errors.
3. When the audit has finished, select **Open Web UI**.
4. Start with **Where to focus**, then review individual findings or the full audit summary.

**The audit runs when the app starts; the Web UI remains available afterwards while the app is running.** The app no longer stops automatically at the end of a successful audit. It is not continuously rescanning Home Assistant in the background. To collect a fresh audit, restart the app or start it again after stopping it.

The Web UI contains the latest generated evidence, which may be older than the moment you open the page. Look at the displayed check time when deciding how current a conclusion is.

The app log remains useful for the brief user summary and any execution errors. The Web UI is the easier place to review ongoing investigations and share the AI handoff.

### If a scan fails

Check the app log. HA Audit may still have produced some usable evidence, but **an incomplete scan is not evidence that everything is healthy**. Treat unavailable reports or failed checks as unknown rather than as a pass.

---

## 2. Choose where to focus

**Where to focus** groups current higher-priority System Log findings into practical investigation categories. This is separate from the original technical priority.

| Category | What it means | What to do |
|---|---|---|
| **Investigate / continue** | Unreviewed or open issues; also issues with sampled errors while a linked power-control switch was ON. | Review these first. |
| **Monitoring** | You have recorded an investigation and are watching for further evidence. | Recheck after a change or an appropriate monitoring period. |
| **Explanation to verify** | A finding is marked Explained or Resolved, but its available power-state evidence does not support dismissing the samples. | Check the uncertainty before relying on the explanation. |
| **Sampled power-off — no immediate action** | A previously explained/resolved finding has only OFF results in the sampled power checks. | No immediate action for those samples; future or unchecked errors still deserve review. |

The cards may show short activity or maintenance notes, such as **no new activity detected in latest audit** or **latest sampled error inside maintenance; earlier sample outside**.

**Important:** An issue may still show **HIGH** and **RECURRING 24H+** after it moves into a lower-action investigation category. That is intentional. The technical finding and recurrence history have not been deleted or rewritten.

The cards show a limited number of examples. Review **Issues needing review** for the individual findings and their supporting information. Lower-priority findings remain available in the detailed reports.

### Technical priority versus recommended action

HA Audit assigns priorities such as **HIGH**, **MEDIUM**, **LOW**, and **VERY LOW** based on its log evidence. The priority is not the same as the Home Assistant log level or an instruction to make an immediate change.

For example, a repeatedly unreachable device can be a HIGH technical finding even if it is normally turned off deliberately. A verified explanation may change the **investigation recommendation**, not the underlying priority or original logs.

---

## 3. Record an investigation

Open **Issues needing review**, find the issue, and expand **Review / update**.

### Status

| Status | When to use it |
|---|---|
| **Investigating** | You are working out why the issue occurs or checking its impact. |
| **Monitoring** | You have made a change or noticed a pattern and want to see whether further problems appear. |
| **Explained** | You have an explanation for the observed behaviour, while recognising that new evidence may require another look. |
| **Resolved** | You believe the problem has been addressed; later errors must still be assessed. |

New findings without saved feedback are treated as **Not reviewed**. These status labels are **your investigation feedback**, not independently verified conclusions.

### Notes

In **What did you establish or change?**, describe what you observed, what you changed, when you changed it, and what should be checked next. Notes can contain up to **4,000 characters**. Select **Save feedback**.

Saved notes, status updates, and their history are retained in HA Audit's private configuration storage across audit runs and app updates. The latest note is shown when you reopen the form; the complete history is retained locally. The handoff includes the latest note and indicates that it is user-reported context.

You can also save an optional **Power-control switch** or **Scheduled maintenance** rule for a finding, as described below. Those settings are structured context for checking evidence; they do not create an automation or change the equipment.

### What feedback does not do

Saving **Explained** or **Resolved** does not remove the original finding, clear Home Assistant logs, change its HIGH/MEDIUM priority, or guarantee that future occurrences are harmless. If later evidence conflicts with an explanation, HA Audit can recommend renewed investigation without changing the saved status automatically.

---

## 4. Check evidence against a power-control switch

Use this when a device is intentionally disconnected from power by a Home Assistant-controlled plug or switch.

### Set it up

1. Physically identify which plug or switch actually supplies the device. Do not guess from similarly named entities.
2. Find its **actual Home Assistant switch entity**, for example `switch.tv_cabinet_socket`, using **Developer Tools → States**.
3. Open the associated finding in **Issues needing review → Review / update**.
4. Enter the entity in **Power-control switch (optional)** and save your feedback.
5. Run a new audit to refresh the stored evidence. Use **Check current evidence** if you need the separate on-demand detail page.

Use a real `switch.*` entity. A template `sensor.*` expressing the *desired* state of a plug is not necessarily evidence of its physical state.

### Understand the results

| Result | Meaning | Suggested interpretation |
|---|---|---|
| **OFF** | Recorder shows the controlling switch OFF at a sampled error timestamp. | Consistent with deliberate loss of power; not proof of causation. |
| **ON** | Recorder shows the switch ON at the sampled time. | The power-off explanation does not account for this sample; investigate. |
| **UNKNOWN** | The state cannot be established from the available evidence. | Do not assume the device was off. |

The Web UI displays **OFF / ON / UNKNOWN** counts beside the finding and a recommendation that reflects those samples. Where an Explained/Resolved finding has exclusively OFF samples, **Where to focus** can place it in **Sampled power-off — no immediate action**. An ON sample returns it to the actionable group.

### Limits of power checks

The checker uses **sampled first/last timestamps from System Log source records**, not the timestamp of every occurrence in a deduplicated log group. A result such as **OFF 4 · ON 0 · UNKNOWN 0** means four *sampled timestamps* matched OFF, not necessarily every logged error.

Recorder history may be missing or incomplete. A saved switch relationship is provided by the user; a matching history state supports an interpretation but is not independent proof of the equipment's wiring or the cause of a failure.

The main evidence card uses the last **completed audit**. The **Check current evidence** link performs a separate current check; do not confuse the two timestamps.

---

## 5. Check evidence against scheduled maintenance

Use **Scheduled maintenance (optional)** when an integration or device may briefly lose connectivity during an established maintenance period, such as a scheduled network reboot.

### Set it up

1. Open the finding's **Review / update** form.
2. Choose **Frequency**, then fill in the relevant days or monthly rule.
3. Enter **Start (local time)** and **End (local time)** in 24-hour format.
4. Enter an IANA time zone, such as `Europe/London`.
5. Save the feedback and run a new audit to check the sampled log timestamps.

Supported schedules:

| Frequency | Additional setting | Example |
|---|---|---|
| **Daily** | None | Every day, 03:00–03:05 |
| **Weekly — selected weekdays** | One or more weekdays | Sundays only, 04:00–04:15 |
| **Monthly — calendar date** | Day 1–31 | 1st of each month |
| **Monthly — nth weekday** | First, second, third, fourth, or last weekday | Last Sunday of each month |

A monthly date of 31 does not occur in months without a 31st. Windows crossing midnight are supported and belong to the day on which they **start**. Time-zone matching uses the named zone rather than assuming a fixed UTC offset, so UK summer/winter clock changes are taken into account.

To remove a schedule, clear its **Start**, **End**, and **Time zone**, then save.

### Understand the results

| Result | Meaning |
|---|---|
| **INSIDE** | A sampled error timestamp falls within the configured schedule. |
| **OUTSIDE** | A sampled timestamp falls outside the configured schedule. |
| **UNKNOWN** | The timestamp or schedule match cannot be established. |

A finding may display **INSIDE 1 · OUTSIDE 1 · UNKNOWN 0**. That means one sampled timestamp matched the maintenance window and one did not. It **does not** classify every occurrence in the underlying System Log group.

The interface also identifies the **most recent sampled log timestamp**. It may show that the latest sample is inside maintenance while an earlier one is outside. Treat the older outside-window evidence as a reason to keep reviewing, not as proof that a problem is still happening today.

**A schedule match is not proof that maintenance actually occurred or caused the error.** It is time-based context, not an independently observed router or device reboot. A recent configuration change may explain an older outside-window error, but HA Audit cannot establish that from free-text notes alone.

If the schedule changes, previously stored maintenance results are not treated as a valid verification of the new schedule; run an audit again. Existing investigation status and original technical priority are preserved.

---

## 6. Understand new activity and historical errors

Home Assistant's System Log may retain and deduplicate errors across several days. An error still appearing in the log is **not necessarily a new error today**.

HA Audit reuses its cross-audit history to display **Latest audit activity**:

| Label | Meaning |
|---|---|
| **NEW ACTIVITY** | Independently new activity was detected since the earlier audit observation. |
| **RETAINED EVIDENCE** | The finding remains visible, but the latest audit detected no independently new activity. |
| **BASELINE** | This is the first observation, without an earlier audit for comparison. |

**RETAINED EVIDENCE** is encouraging during monitoring, but it does **not** prove a problem has stopped. A bounded audit cannot guarantee that no error occurred between runs.

The activity indicator and the power/maintenance samples answer **different questions**:

- **Latest audit activity:** Did the cross-run comparison independently detect new log activity?
- **Power or maintenance evidence:** What was the switch state or scheduled time at the selected log timestamps?

The newest *sampled log timestamp* is not necessarily independently new activity in the current audit. Avoid interpreting it that way.

### Understanding recurrence

**SHORT-WINDOW REPEAT** means independently new activity was observed across a period shorter than 24 hours. **RECURRING 24H+** means independently new activity has been observed across an audit observation span of at least 24 hours. These are historical recurrence classifications, not proof that failures lasted continuously for 24 hours or are still occurring now.

Repeated audits against unchanged retained evidence do not establish recurrence. Consult `log_recurrence.json` and `log_issue_history.json` for the underlying run-to-run history.

---

## 7. Share a report with an AI assistant

After a successful audit, the Web UI's **Share with AI** section offers:

- **Copy for AI** — copies the generated handoff to the clipboard where browser permissions allow.
- **Download handoff** — downloads the Markdown report.
- **View / select handoff text** — opens the full text for review or manual copying.

The handoff, `ha_audit_ai_handoff.md`, combines the latest audit findings with saved investigation feedback and automatic sampled evidence. Its instructions ask the receiving AI to distinguish observed facts, reasonable interpretations, and unknowns. For a pending Core update, it also includes the **Core readiness evidence trace**, distinguishing automatic local checks from explicit user confirmations and unresolved evidence.

For more technical analysis, `ha_audit_ai_evidence.json` contains structured companion data. Use it only if the readable handoff does not contain enough evidence.

### Privacy before sharing

**No data is sent to an AI provider merely by running HA Audit or opening the Web UI.** You decide whether to copy, download, or share a report.

Review it first: reports can contain device names, entity IDs, network addresses, configuration details, and investigation notes. Share only what you are comfortable disclosing.

If clipboard copying is blocked by the browser, use **View / select handoff text** or **Download handoff** instead.

---

## 8. Understand Core update guidance

HA Audit compares the installed and target Home Assistant Core versions with available Repairs, official release notes, breaking-change evidence, local configuration, integrations, deterministic compatibility rules, and dynamic correlation results.

Its update guidance is **separate from general Home Assistant health**: an intentionally unavailable device is not automatically an update blocker.

| Recommendation | Meaning |
|---|---|
| **NO CORE UPDATE PENDING** | There is no Core update to assess. |
| **NO KNOWN BLOCKERS FOUND** | No known blocker was found in the assessment that was completed. |
| **REVIEW BEFORE UPDATING** | Relevant evidence deserves review first. |
| **ASSESSMENT INCOMPLETE** | Required evidence or compatibility coverage is insufficient for a complete recommendation. |
| **DELAY - BLOCKER EVIDENCE FOUND** | Evidence supports delaying the update pending investigation. |

**ASSESSMENT INCOMPLETE is not proof of an unsafe update.** Equally, **NO KNOWN BLOCKERS FOUND does not guarantee a safe update**.

### What compatibility coverage means

Official breaking-change evidence may be complete while deterministic compatibility rules cover only part of the upgrade window. Dynamic correlation can add useful context but is not equivalent to a precise compatibility rule. Missing deterministic coverage indicates an **assessment gap**, not a confirmed failure or a number of problems.

Some UI-managed configuration, including custom AI prompts, may be outside the scanner's scope. Read the detailed update-readiness and compatibility reports when HA Audit explains that coverage is incomplete.

### Core readiness evidence trace (v0.8.30)

The detailed current-run summary includes **CORE READINESS EVIDENCE TRACE** for a pending Core upgrade. It shows how compatibility groups initially classified as having insufficient evidence were handled:

- **Initially uncertain groups:** The number of groups requiring reconciliation.
- **Automatically assessed (local rule evidence):** A named, scoped local check found no affected usage within the evidence it inspected.
- **Explicitly confirmed by user (NOT machine-verified):** A user acknowledged the relevant change. This is a user assertion, not independent technical verification.
- **Still unresolved groups:** Groups that remain uncertain after local checks and accepted confirmations.

The trace also displays the Core guidance result and decision reason codes, if any. **`none` means no decision reason code was reported**; it does not mean every change was checked.

For example, an automatic **State conditions** assessment and a manually confirmed **Authentication** group are different kinds of evidence even if both contribute to resolving initial uncertainty.

**Zero unresolved groups is not proof of complete compatibility.** The trace concerns reconciliation of initially insufficient-evidence groups, not exhaustive verification of all official breaking changes or UI-managed settings. Dynamic-only groups can remain outside deterministic reference coverage. The overall update recommendation remains evidence-based and is never a guarantee of safety.

### Before and after updating

Before updating, review the reported actions and confirm you have a suitable, independently verified recovery plan. **HA Audit does not verify that a backup can be restored.** After updating, confirm that Home Assistant starts, check Repairs and important devices/integrations, and rerun HA Audit to compare the new evidence.

---

## 9. Review configuration and device availability

### Configuration health

HA Audit validates Home Assistant configuration and examines the **active YAML include tree**. Its findings may include missing includes, missing entity references, possible orphan YAML, duplicate automation IDs, duplicate automation names or script aliases, and unusually large definitions.

These are review candidates. A referenced entity may be renamed or outside the available matching evidence; an unreferenced file might be intentionally retained. A large script is not necessarily faulty. **Do not delete or rewrite configuration solely to make audit counts zero.**

Configuration validation passing does not prove every automation or integration behaves correctly.

### Availability

HA Audit distinguishes:

| Category | Meaning |
|---|---|
| **Partial device availability** | Some entities are unavailable, while the same device still has healthy entities. |
| **Whole-device unavailable** | No healthy state entities were observed for the device. |
| **Ungrouped unavailable** | An unavailable entity is not associated with a device. |
| **Unknown state** | The entity exists but Home Assistant does not currently have a meaningful value. |
| **Not currently provided** | An entity may remain registered although its integration is not currently supplying it. |

A device may be intentionally powered off, disconnected for maintenance, or temporarily unreachable. HA Audit supports optional expected-offline and maintenance labels, but does not require them.

Recorder history provides additional context, limited by retention and exclusions. Results can include `usable_history_found`, `history_found_no_usable_state`, `no_history_returned`, and `history_query_failed`.

**No history, unavailability, or a not-currently-provided classification is sufficient reason on its own to delete an entity.**

---

## 10. Find detailed reports

The Web UI displays the latest audit report and provides the AI handoff. Other evidence remains in HA Audit's private app configuration folder.

If your file-access app supports `/addon_configs`, open it and locate the folder ending in `_ha_audit`; the generated prefix can vary. In Studio Code Server, you can use **File → Open Folder... → `/addon_configs`**. Direct access to the private files is optional for everyday use.

| Question | Report |
|---|---|
| What is the latest human-readable audit summary? | `ha_audit_latest.txt` |
| Which configuration problems were found? | `quality_audit.json` |
| Which devices and entities are unavailable? | `availability_audit.json` |
| What does ordinary unavailable-entity history show? | `unavailable_history_audit.json` |
| Which entities are no longer provided? | `not_provided_reference_audit.json` |
| What protects old entity references from premature cleanup? | `not_provided_history_audit.json` |
| Which System Log families have what priority? | `log_priority_final.json` |
| What was the source System Log sample? | `log_audit.json` |
| Has a finding recurred across audits? | `log_recurrence.json` and `log_issue_history.json` |
| What evidence supports the Core update result, including automatic checks and manual confirmations? | `ha_audit_latest.txt` (**CORE READINESS EVIDENCE TRACE**), `update_readiness_audit.json`, and related upgrade reports |
| What should I share with an AI assistant? | `ha_audit_ai_handoff.md` |
| What structured evidence supports the AI handoff? | `ha_audit_ai_evidence.json` |

The investigation system also keeps its own private feedback and evidence data, including `investigation_context.json`, `investigation_evidence.json` (sampled power evidence), and `investigation_maintenance_evidence.json` (sampled maintenance evidence). **Normally you should use the Web UI rather than editing these files manually.**

Data is retained across audits where the app's private configuration storage is preserved. A report's timestamp and collection scope matter: System Log collection is bounded and Home Assistant may deduplicate messages.

---

## 11. Safety, privacy, and limitations

HA Audit is read-only **toward Home Assistant**: it does not change Home Assistant YAML, delete devices, run automations, restart Home Assistant, install Core updates, or perform repairs. Saving investigation feedback writes **only to HA Audit's private app storage**.

Configuration scanning excludes sensitive or irrelevant locations such as `.storage`, `.cloud`, backup directories, and files containing `secret` in their filenames (including `secrets.yaml`). This reduces exposure but does not guarantee reports contain no sensitive information.

HA Audit cannot:

- Guarantee that every integration, automation, or device works correctly.
- Guarantee a Home Assistant Core update will be safe.
- Fully inspect all UI-managed settings or assess every documented breaking change.
- Provide a complete historical archive of System Log events or check every deduplicated error timestamp.
- Guarantee Recorder history is available for every entity or time period.
- Prove that a device was physically powered off solely because a switch reports OFF.
- Prove that scheduled maintenance actually occurred solely because an error falls within its configured window.
- Establish backup/restore readiness or provide the same depth of OS assessment as Core assessment.
- Automatically investigate or resolve issues while the app is simply left open.

Use **UNKNOWN**, **not assessed**, or **insufficient evidence** literally; do not interpret them as healthy or faulty. Likewise, an Explained or Resolved investigation label is not proof that new errors are harmless.

**Understand first. Change only when necessary.**
