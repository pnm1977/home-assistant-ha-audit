# HA Audit User Guide

HA Audit is a read-only Home Assistant health, configuration, and upgrade-readiness auditing app.

It examines evidence from your Home Assistant installation to help you understand system health, investigate problems, and make informed maintenance and upgrade decisions.

**HA Audit does not automatically repair, delete, restart, or change anything in Home Assistant.**

The recommended workflow is:

**Run → Read → Investigate → Act → Rerun**

---

## Contents

1. Running HA Audit
2. Understanding the results
3. System issues and recurring problems
4. Core update guidance
5. Configuration health
6. Entity availability and history
7. Using HA Audit with AI
8. Detailed reports
9. Safety and privacy
10. Current limitations

---

# 1. Running HA Audit

HA Audit currently runs manually.

### Starting an audit

1. Open **Home Assistant → Settings → Apps → HA Audit**.
2. Select **Start**.
3. Allow the audit to finish.
4. Open the **Log** tab.
5. Find the latest `HA AUDIT vX.X.X - USER SUMMARY`.

The app stops automatically when the audit finishes.

### What happens during an audit?

HA Audit collects available information about:

- Home Assistant versions and system status.
- Configuration validity and active YAML files.
- Entities, devices, and availability.
- Home Assistant Repairs and pending updates.
- System Log warnings and errors.
- Previous audit results and available Recorder history.
- Evidence relevant to pending Home Assistant Core updates.

It combines these findings into a plain-English summary and more detailed technical reports.

### If an audit fails

Check the app log for errors.

When an individual scanner fails, HA Audit reports the failure and available diagnostic output.

An incomplete audit should not be interpreted as evidence that everything is healthy.

---

# 2. Understanding the results

**Start with the USER SUMMARY in the Home Assistant app log.**

It is intended for everyday use and highlights the information most likely to matter.

The main sections are:

```text
STATUS
SYSTEM ISSUES
CORE UPDATE - WHAT TO DO
```

## STATUS

Shows the overall Home Assistant health assessment and update guidance.

For example:

```text
Home Assistant health: NEEDS ATTENTION
Core update:          ASSESSMENT INCOMPLETE
OS update:            UPDATE AVAILABLE
Config check:         VALID
```

These are separate assessments.

### Home Assistant health

`NEEDS ATTENTION` means HA Audit identified findings worth reviewing.

It does not necessarily mean Home Assistant is experiencing a major fault.

For example, an intentionally powered-off device or a temporarily unavailable integration may contribute to health findings without affecting normal operation.

### Core update

Describes the evidence relevant to a pending Home Assistant Core update.

A health finding does not automatically mean a Core update should be delayed.

See [Core update guidance](#4-core-update-guidance).

### OS update

Reports whether a Home Assistant OS update is available.

This is update visibility, not a complete OS compatibility assessment or recommendation to install.

### Config check

The preferred result is:

```text
Config check: VALID
```

This confirms that Home Assistant configuration validation passed.

It does not prove that every automation, script, or integration behaves correctly.

## Detailed current-run summary

Each successful audit also generates:

```text
ha_audit_latest.txt
```

This provides more detailed information than the app's USER SUMMARY.

It includes supporting evidence and additional sections such as:

- `OVERVIEW`
- `WHY THIS RESULT`
- `SYSTEM`
- `UPDATE READINESS`
- `UPGRADE COMPATIBILITY`
- `CONFIGURATION`
- `AVAILABILITY CONTEXT`
- `UNAVAILABLE HISTORY CONTEXT`
- `REVIEW`
- `NEXT ACTIONS`

**You do not need to understand every technical field to use HA Audit.**

Start with the summary and investigate individual findings when appropriate.

---

# 3. System issues and recurring problems

HA Audit examines available Home Assistant System Log warnings and errors.

Related messages are grouped into issue families so that repeated messages do not overwhelm the results.

For example, several failed commands from a Zigbee automation may represent one communication problem rather than several unrelated faults.

## Priorities

HA Audit uses four priority levels:

| Priority | Meaning |
|---|---|
| HIGH | Deserves attention ahead of lower-priority findings. |
| MEDIUM | Worth reviewing, particularly if the issue affects normal operation. |
| LOW | Usually lower-priority investigation or maintenance context. |
| VERY LOW | Generally informational or limited-impact evidence. |

These priorities are based on the evidence HA Audit has collected.

**Priority is not the same as Home Assistant log severity.**

A HIGH classification does not automatically mean an urgent or confirmed hardware fault.

## What determines priority?

HA Audit considers available evidence such as:

- Whether an actual failure was observed.
- Whether there is a practical local investigation path.
- Whether recovery or fallback behaviour was observed.
- Whether the issue has genuinely recurred.
- Whether device availability or Home Assistant Repairs provide supporting context.

High occurrence counts alone do not establish a persistent problem.

## Recurrence

HA Audit distinguishes between repeated log messages and independently observed activity across audits.

### NOT ESTABLISHED

There is insufficient evidence to establish recurrence.

An issue may have appeared once, or previously collected messages may still be visible without new activity.

### SHORT-WINDOW REPEAT

New activity was independently observed again, but the proven observation span remains below 24 hours.

### RECURRING 24H+

New activity was independently observed across an audit observation period of at least 24 hours.

This provides stronger evidence of recurrence.

However, it does **not** mean the problem was continuously happening throughout that period or is still happening now.

Repeatedly running HA Audit against unchanged retained log evidence does not establish recurrence.

## Understanding the explanations

The USER SUMMARY presents the highest-priority findings first.

Where the evidence allows, HA Audit explains:

1. What Home Assistant observed.
2. Which device, automation, or integration was involved.
3. A useful first check.
4. What remains uncertain.

For example:

```text
Observed:
TV & Events tried to change the LG TV input while
the television was off.

Useful first check:
Check whether that input change should occur
when the TV is off.
```

This identifies an appropriate investigation without assuming the automation needs changing.

## Technical references

Some findings include references to:

- Entity IDs.
- Automation and script names.
- YAML filenames and line numbers.
- Relevant Home Assistant log messages.

These references identify where to investigate.

**A matching configuration reference is not proof that the configuration caused the problem.**

For the complete prioritised issue list, use:

```text
log_priority_final.json
```

For historical recurrence evidence, use:

```text
log_recurrence.json
log_issue_history.json
```

---

# 4. Core update guidance

HA Audit helps users assess available Home Assistant Core updates using official release information and local installation evidence.

It does not install updates automatically.

## Possible recommendations

| Recommendation | Meaning |
|---|---|
| NO CORE UPDATE PENDING | No Core update currently needs assessment. |
| NO KNOWN BLOCKERS FOUND | The completed assessment found no known reason to delay. |
| REVIEW BEFORE UPDATING | Specific evidence deserves attention before updating. |
| ASSESSMENT INCOMPLETE | HA Audit could not complete its required assessment. |
| DELAY - BLOCKER EVIDENCE FOUND | The assessment identified evidence supporting a delay. |

The precise recommendation depends on the available evidence.

### NO KNOWN BLOCKERS FOUND

HA Audit did not identify a known blocker within the evidence it examined.

This is deliberately different from saying:

```text
SAFE TO UPDATE
```

Home Assistant updates can still affect integrations or configurations that HA Audit cannot fully assess.

### REVIEW BEFORE UPDATING

HA Audit identified something that deserves review before proceeding.

This might include a relevant Home Assistant Repair or an affected compatibility rule.

It does not automatically mean the update will fail.

### ASSESSMENT INCOMPLETE

HA Audit could not complete all the evidence or compatibility assessment required by its current decision model.

**This does not automatically mean a problem was detected.**

Since v0.8.4, HA Audit provides clearer explanations distinguishing between:

- Completed checks that found no specific update-related issue.
- Actual findings requiring investigation.
- Evidence or compatibility coverage that remains incomplete.

For example, HA Audit may successfully validate configuration and assess several compatibility rules while still lacking sufficient coverage to produce a complete update recommendation.

This should be interpreted as **limited assessment confidence**, not proof that the update is unsafe.

When the assessment is incomplete, review the remaining uncertainty before relying on HA Audit's guidance.

### DELAY - BLOCKER EVIDENCE FOUND

HA Audit has identified evidence supporting a delay.

Review the reported findings before considering the update.

The recommendation remains evidence-based and does not independently prove that installation would fail.

## What does HA Audit check?

Depending on the upgrade and available evidence, the assessment can include:

- Installed and target Core versions.
- Relevant Home Assistant Repairs.
- Official release information.
- Documented breaking changes.
- Active local configuration and integrations.
- Deterministic compatibility rules.
- Dynamic correlation with local installation evidence.
- Configuration validation.
- Assessment completeness.

## Compatibility coverage

HA Audit does not maintain a guaranteed comprehensive compatibility rule for every Home Assistant release change.

Its deterministic rules provide more precise checks for selected changes.

Dynamic correlation provides additional context about potentially relevant changes.

This distinction matters.

For example:

```text
Official change groups:        30
Deterministic rules cover:      8
Remaining dynamic-only groups: 22
```

This does **not** mean 22 problems were detected.

It means those changes lack equivalent deterministic reference coverage.

The detailed reports provide the available evidence for review.

## Locally relevant compatibility results

Common findings include:

| Finding | Meaning |
|---|---|
| No local match | No matching local use was identified for that rule. |
| Local match, no affected use | Related functionality exists, but the affected usage was not detected. |
| Review required | Local evidence indicates the change deserves investigation. |
| Manual review | HA Audit cannot safely determine the outcome automatically. |

These results are supporting evidence, not guarantees.

Some Home Assistant configuration is managed through the UI and may not be available to HA Audit's configuration scanners.

## Before updating

Follow the reported Core update guidance.

Also ensure you have an appropriate recovery plan.

**HA Audit does not verify that a successful, restorable backup exists.**

Check your backup arrangements independently before significant updates.

## After updating

A useful follow-up is to:

1. Confirm Home Assistant starts and configuration validation passes.
2. Check Home Assistant Repairs.
3. Confirm important integrations and devices are functioning.
4. Rerun HA Audit.
5. Compare new and recovered findings with the pre-update audit.

An updated installation should be judged using the new evidence rather than assuming everything is healthy because the update completed.

---

# 5. Configuration health

HA Audit examines the active YAML configuration and related Home Assistant information.

Common findings include:

### Missing active includes

An active YAML file references an include target that HA Audit could not find.

Review the reported filename and location before making changes.

### Missing entity references

An entity ID used in active YAML could not be matched to a current Home Assistant entity.

These are review candidates, not automatically confirmed errors.

An entity might have been renamed, temporarily unavailable, or otherwise outside the matching evidence.

### Orphan YAML candidates

Files were found that do not appear to belong to the active YAML include tree.

They may be unused, but could also be intentionally retained.

Do not delete them solely because they were identified as candidates.

### Duplicate automation IDs

Automation IDs should be unique.

Duplicate IDs represent structural findings that deserve review.

### Duplicate automation names

Duplicate automation aliases are different from duplicate IDs.

HA Audit considers live automation states so that disabled or mixed-state duplicates are not automatically treated as active conflicts.

### Duplicate script names

Duplicate script aliases are maintainability findings.

They do not automatically establish invalid configuration or a runtime failure.

### Large automations and scripts

HA Audit can identify unusually large definitions.

Size alone is not proof that something is wrong or requires rewriting.

## NEXT ACTIONS

The detailed summary uses markers such as:

```text
[!] Finding needing attention
[i] Informational or review context
```

These help distinguish stronger findings from supporting information.

For configuration details, use:

```text
quality_audit.json
```

**Do not try to make every count zero.**

Investigate findings based on their evidence and actual impact.

---

# 6. Entity availability and history

HA Audit distinguishes between unavailable entities, unknown states, and entities that are no longer currently provided by their integrations.

These categories should not be treated as interchangeable.

## Unavailable entities

An unavailable entity may represent:

- A deliberately switched-off device.
- Equipment undergoing maintenance.
- A temporary network or integration problem.
- An unavailable feature of an otherwise functioning device.
- A genuinely failed or disconnected device.

Unavailable does not automatically mean faulty.

### Partial device availability

At least one entity associated with the device is healthy while another is unavailable.

This may represent feature-level or diagnostic availability rather than a complete device failure.

### Whole-device unavailability

No healthy state entities are currently available for the device.

This is an observation, not proof of a fault.

Before investigating, consider whether the device is supposed to be powered or online.

### Ungrouped unavailable entities

These are unavailable entities not attached to a Home Assistant device.

They require separate interpretation.

## Optional availability labels

HA Audit supports optional Home Assistant labels for known circumstances such as:

- Expected offline.
- Maintenance.

These labels can add context but are not necessary for normal operation.

HA Audit does not require users to maintain labels to obtain useful results.

## Unknown states

An entity with state `unknown` exists, but Home Assistant does not currently have a meaningful value for it.

Some entities may legitimately report this state.

Do not assume every unknown state requires investigation.

## Entities not currently provided

An entity may remain in the Home Assistant registry even when its integration no longer creates or supplies it.

Potential explanations include integration changes, removed devices, or temporary integration failures.

HA Audit checks available active-YAML references and history to provide additional context.

**This is a review category, not a deletion list.**

## Recorder history

HA Audit uses available Recorder history to add context.

The requested lookback may be up to 90 days, but the effective period depends on actual Recorder retention and available evidence.

For example, if Recorder only contains 18 days of history, HA Audit cannot establish what happened 60 days ago.

History results may include:

```text
usable_history_found
history_found_no_usable_state
no_history_returned
history_query_failed
```

### Usable history found

Recorder returned at least one meaningful state within the available period.

Where possible, HA Audit identifies when the final usable interval began and when it ended.

An end time is only reported when the available history supports it.

### History found without a usable state

Recorder returned records, but no usable state was identified within the effective window.

This does not prove the entity has never worked.

### No history returned

Recorder returned no history records.

Possible reasons include retention limits or exclusions.

This does not establish that an entity is unused.

### History query failed

HA Audit could not obtain the requested history.

This represents incomplete evidence.

## Important safety principle

**No history is not evidence that an entity is safe to delete.**

Likewise, unavailable, unknown, or no-longer-provided states do not independently justify deletion.

Relevant reports include:

```text
availability_audit.json
unavailable_history_audit.json
not_provided_reference_audit.json
not_provided_history_audit.json
```

---

# 7. Using HA Audit with AI

Each successful audit generates a vendor-neutral AI handoff:

```text
ha_audit_ai_handoff.md
```

It is designed for assistants including ChatGPT, Claude, Gemini, and compatible local AI systems.

## What does the handoff contain?

The handoff brings together:

- Core update guidance.
- Important Home Assistant health findings.
- Prioritised System Log issues.
- Plain-English explanations.
- Suggested initial troubleshooting checks.
- Relevant YAML and entity references.
- Known limitations and missing evidence.
- Supporting information from the latest audit.

The handoff also instructs the receiving assistant to distinguish between observed facts, reasonable interpretations, and unknowns.

## How to use it

1. Run HA Audit.
2. Locate `ha_audit_ai_handoff.md`.
3. Review the file before sharing it.
4. Upload it to your preferred AI assistant.
5. Ask the assistant to analyse the findings.

For example:

> Review this HA Audit report and explain the three most important findings and what I should check first.

The handoff contains its own interpretation instructions.

You do not need to create a complicated prompt.

## Structured AI evidence

HA Audit also generates:

```text
ha_audit_ai_evidence.json
```

This contains machine-readable information such as:

- Issue classifications and priorities.
- Supporting log evidence.
- Related entities, automations, and scripts.
- Configuration references and source locations.
- Recurrence context.
- Evidence gaps.

This file is useful when the receiving AI needs more detailed information than the readable handoff provides.

For most users, start with the Markdown handoff and provide detailed evidence only when necessary.

## What AI analysis can and cannot establish

An AI assistant can help interpret evidence, identify plausible explanations, and suggest further checks.

However:

- Matching YAML references do not prove causation.
- Error counts do not independently prove recurrence.
- An unavailable device may be intentionally offline.
- An incomplete assessment is not automatically a fault.
- No AI interpretation can guarantee that a Core update is safe.

The receiving AI should suggest non-destructive checks before proposing changes.

## Privacy

HA Audit does not automatically send reports to an AI provider.

Files remain local until you choose to share them.

The handoff and structured evidence may include device names, entity IDs, configuration information, and other installation-specific details.

Review them before uploading them to an external service.

---

# 8. Detailed reports

HA Audit stores generated reports in its private Home Assistant app configuration folder.

## Finding the reports

If your Home Assistant file-access tool supports `/addon_configs`:

1. Open `/addon_configs`.
2. Find the folder ending in `_ha_audit`.
3. Open the relevant report.

The prefix before `_ha_audit` is generated by Home Assistant and can vary between installations.

### Using Studio Code Server

If Studio Code Server is installed:

1. Open Studio Code Server.
2. Choose **File → Open Folder...**
3. Enter:

   `/addon_configs`

4. Open the HA Audit folder.
5. Select the required report.

When finished, use **File → Open Recent** to return to your previous workspace.

Studio Code Server is optional. Other compatible file-access methods can also be used.

## Which report should I open?

| Question | Recommended report |
|---|---|
| What should I investigate first? | `ha_audit_latest.txt` |
| What did the configuration checks find? | `quality_audit.json` |
| Which devices are unavailable? | `availability_audit.json` |
| What does Recorder history show? | `unavailable_history_audit.json` |
| Which entities are no longer provided? | `not_provided_reference_audit.json` |
| Is an older entity protected by history? | `not_provided_history_audit.json` |
| Which System Log issues matter most? | `log_priority_final.json` |
| Is an issue recurring across audits? | `log_recurrence.json` |
| What historical observations exist? | `log_issue_history.json` |
| What is the Core update evidence? | `update_readiness_audit.json` |
| Which compatibility checks were performed? | `upgrade_compatibility_audit.json` |
| How complete is compatibility coverage? | `compatibility_coverage_audit.json` |
| What should I upload to an AI assistant? | `ha_audit_ai_handoff.md` |
| What additional AI evidence is available? | `ha_audit_ai_evidence.json` |

Additional technical reports are generated for collection, correlation, and diagnostic purposes.

You normally do not need to open them unless investigating a specific question.

## Previous audits

HA Audit retains selected information across runs to support comparisons and recurrence analysis.

Historical visibility does not mean a problem is currently happening.

Where possible, distinguish:

- Newly observed activity.
- Previously observed activity.
- Retained evidence without new activity.
- Issues no longer present in the collected evidence.

An issue disappearing from a bounded log sample is not proof that it has been permanently resolved.

---

# 9. Safety and privacy

HA Audit is designed to be read-only.

It does not:

- Modify Home Assistant configuration.
- Automatically delete entities or devices.
- Restart Home Assistant.
- Trigger automations or scripts.
- Install software updates.
- Apply repairs.
- Automatically transmit audit reports to AI services.

## Configuration access

HA Audit uses read-only access to Home Assistant configuration.

Generated reports and audit history are written to its own private app configuration directory.

Configuration scanning excludes sensitive or unrelated locations, including:

- `.storage`
- `.cloud`
- Backups.
- Custom component source directories.
- ESPHome configuration.
- Media and TTS directories.
- `www`.

Files with `secret` in their filename, including `secrets.yaml`, are excluded from configuration scanning.

These exclusions reduce the information collected but do not guarantee that every generated report is free of installation-specific or sensitive information.

**Always review reports before sharing them externally.**

## Backups and recovery

HA Audit can identify some system and update evidence relevant to maintenance decisions.

However, it does not establish:

- Whether a recent backup completed successfully.
- Whether a backup contains everything required for recovery.
- Whether backup storage is independently protected.
- Whether a restore has been tested.

These checks remain the user's responsibility.

---

# 10. Current limitations

HA Audit is intended to support maintenance decisions, not replace Home Assistant's own diagnostic tools or the user's judgement.

Current limitations include:

- Audits must be started manually.
- It does not automatically repair Home Assistant.
- System Log collection is bounded rather than a complete historical archive.
- Recorder analysis is limited by available retention and exclusions.
- Some UI-managed configuration cannot be inspected.
- Compatibility checks do not cover every possible integration or breaking change.
- Core update guidance cannot guarantee a safe upgrade.
- OS update assessment is less extensive than Core update assessment.
- Backup and restore readiness is not verified.
- AI analysis requires the user to share the generated evidence.

## How to interpret uncertainty

When HA Audit cannot inspect something, the correct interpretation is:

**Not assessed or insufficient evidence.**

It should not automatically be treated as either healthy or faulty.

Similarly, an informational finding should not be turned into a required action without supporting evidence.

## Final advice

Use HA Audit to identify meaningful findings and investigate them one at a time.

Focus on actual problems, relevant upgrade risks, and changes in system behaviour.

There is no need to eliminate every warning, unavailable entity, or informational count.

**Understand first. Change only when necessary.**
