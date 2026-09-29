# HA Audit User Guide

HA Audit is a read-only Home Assistant health, configuration, and upgrade-readiness auditor.

It uses evidence from the actual Home Assistant installation to help answer questions such as:

- Is my Home Assistant configuration healthy?
- What currently deserves attention?
- Are unavailable entities likely to represent whole-device or feature-level availability?
- Is there evidence relevant to a pending Home Assistant Core update?
- What should I investigate first?
- How can I hand the important audit evidence to an AI assistant for further analysis?

The normal workflow is:

**run → read → investigate → act → rerun**

---

# 1. Running HA Audit

HA Audit is currently designed to run manually.

1. Open **Settings → Apps → HA Audit**
2. Click **Start**
3. Wait for the audit to complete
4. Open the **Log** tab
5. Find the latest `CURRENT RUN SUMMARY`

The app stops automatically after the audit finishes.

Each successful run also writes the latest summary and supporting reports to HA Audit's private app-config folder.

---

# 2. Start with the overview

Each run begins with an overview similar to:

```text
OVERVIEW
----------------------------------------------------------
Home Assistant health:       NEEDS ATTENTION
Core update:                 NO KNOWN BLOCKERS FOUND
OS update:                   UPDATE AVAILABLE
Core evidence collection:    COMPLETE
Config check:                VALID
```

Immediately below this is:

```text
WHY THIS RESULT
```

This explains the main evidence behind the headline results.

For most users, these two sections should be the starting point.

Do not start by trying to interpret every technical count in the report.

---

# 3. Home Assistant health and Core updates are separate

HA Audit deliberately separates:

- general Home Assistant health
- Core update guidance

For example, a device being unavailable does not automatically mean that a Home Assistant Core update is unsafe.

Likewise, a clean Core update assessment does not mean every entity or device in the installation is healthy.

This separation prevents unrelated health findings from automatically becoming update blockers.

---

# 4. Core update guidance

When a Home Assistant Core update is pending, HA Audit collects evidence about the upgrade window.

This can include:

- installed Core version
- target Core version
- Home Assistant Repairs
- official Home Assistant release evidence
- backward-incompatible change groups
- local integrations and configuration
- deterministic compatibility references where available
- dynamic local correlation
- configuration validation
- evidence-collection completeness

Possible top-level results include:

```text
NO CORE UPDATE PENDING
ASSESSMENT INCOMPLETE
REVIEW BEFORE UPDATING
NO KNOWN BLOCKERS FOUND
```

## NO CORE UPDATE PENDING

There is no pending Home Assistant Core upgrade for HA Audit to assess.

## ASSESSMENT INCOMPLETE

HA Audit could not collect enough required evidence to complete the assessment.

Investigate the missing or failed evidence before relying on the Core update guidance.

## REVIEW BEFORE UPDATING

HA Audit found evidence that deserves review before proceeding.

This does not automatically mean the update will fail.

Review the associated findings to understand what requires attention.

## NO KNOWN BLOCKERS FOUND

HA Audit did not find a known blocker in the evidence it inspected.

This is deliberately different from saying:

```text
SAFE TO UPDATE
```

HA Audit does not guarantee that an update cannot cause a problem.

---

# 5. Core evidence collection

The overview also reports:

```text
Core evidence collection: COMPLETE
```

or an incomplete equivalent.

Evidence completeness describes whether the required assessment stages completed successfully.

It does not prove compatibility.

A complete evidence collection can still contain something that requires review.

---

# 6. OS updates

HA Audit currently reports whether a Home Assistant OS update is available.

For example:

```text
OS update: UPDATE AVAILABLE
```

This is currently update visibility rather than a full OS compatibility/readiness assessment equivalent to the Core assessment.

Do not interpret `UPDATE AVAILABLE` as either a recommendation to install or a warning not to install.

---

# 7. SYSTEM

The `SYSTEM` section contains installation context such as:

```text
Core
Supervisor
OS
Config check
Updates available
Collector errors
```

## Config check

The preferred result is:

```text
Config check: VALID
```

If configuration validation is not valid, investigate the configuration before making changes that depend on it.

Home Assistant's own configuration controls are available under:

**Developer tools → YAML**

## Collector errors

The preferred result is:

```text
Collector errors: 0
```

A non-zero value means one or more parts of the audit did not complete correctly.

When a scanner fails, HA Audit prints that scanner's captured output in the app log.

Do not fill missing evidence with assumptions.

---

# 8. UPDATE READINESS

The `UPDATE READINESS` section contains local update and Repair context.

Typical fields include:

```text
Pending updates
Core upgrade window
Repair issues
Unignored Repairs
Relevant to Core upgrade
Unavailable update entities
Deterministic reference
Compatibility coverage
Dynamic correlation
Correlation validation
Official release evidence
```

Some of these are technical evidence states rather than user-facing recommendations.

For most users, the top-level `Core update` result and `WHY THIS RESULT` are more important.

---

# 9. OFFICIAL RELEASE EVIDENCE

HA Audit can collect official Home Assistant release evidence for the Core versions crossed by an upgrade.

This includes backward-incompatible change groups identified from the relevant Home Assistant release material.

Important points:

- official release evidence describes changes in Home Assistant
- it is not by itself proof that the local installation is affected
- evidence collection being complete does not mean compatibility is guaranteed
- local compatibility evidence is assessed separately

---

# 10. UPGRADE COMPATIBILITY

The compatibility assessment compares documented Core changes with evidence available from the local installation.

Typical results include:

```text
No local match
Local match, no affected use
Review required
Manual review
```

## No local match

HA Audit found no matching local use for that rule.

## Local match, no affected use

Something related exists locally, but HA Audit did not find the affected usage described by the rule.

## Review required

Local evidence indicates that the rule deserves investigation.

## Manual review

HA Audit cannot safely determine the result automatically.

Compatibility rules are evidence for review.

They are not a guarantee that the installation is safe to update.

Some configuration may also be UI-managed or otherwise outside HA Audit's local scan scope.

---

# 11. CONFIGURATION

Typical configuration fields include:

```text
Active YAML files
Missing active includes
Missing entity candidates
Orphan YAML candidates
Duplicate automation IDs
Active duplicate auto names
Unresolved duplicate names
Duplicate script names
```

## Missing active includes

A non-zero value means active YAML points to an include target HA Audit could not find.

Use the source file and line number in `quality_audit.json` to investigate it.

## Missing entity candidates

These are entity IDs referenced in active YAML that HA Audit could not match to a current Home Assistant entity.

They are candidates for review, not automatically confirmed errors.

## Orphan YAML candidates

These are YAML files not found in the active include tree and not classified as known blueprint, Zigbee2MQTT, backup, or archive material.

Do not delete them solely because HA Audit reports them.

## Duplicate automation IDs

Automation IDs should be unique.

Duplicate IDs are structural findings and should be reviewed in their reported YAML locations.

## Duplicate automation aliases

Duplicate names are not the same as duplicate IDs.

HA Audit cross-checks duplicate aliases against current Home Assistant automation states.

The normal summary promotes duplicate aliases when:

- two or more matching automations are currently on
- their live states cannot be fully resolved

Disabled or mixed-state duplicate aliases remain available in detailed evidence without automatically becoming normal health findings.

HA Audit does not infer intent from names such as `Old`, `Backup`, or similar wording.

## Duplicate script names

Duplicate script aliases are maintainability findings rather than proof of invalid configuration.

---

# 12. ENTITY HEALTH

Typical fields include:

```text
Entities
Unavailable
Unknown
Not currently provided
New unavailable
Recovered unavailable
```

Large unavailable or unknown counts do not automatically mean Home Assistant is unhealthy.

The important question is what those states represent.

## Unavailable

Possible causes include:

- deliberately powered-off equipment
- temporary Wi-Fi, Zigbee, MQTT, or integration loss
- devices under maintenance
- battery-powered devices
- optional feature entities
- cloud-service availability
- genuinely failed equipment
- stale entities

Do not bulk-delete unavailable entities from this count.

## Unknown

An entity with state `unknown` exists but Home Assistant does not currently have a meaningful value for it.

This can be normal for some entity types.

## New unavailable / recovered unavailable

These compare the current run with the previous audit.

Changes between runs can be more useful than the total unavailable count because they show what changed.

---

# 13. AVAILABILITY CONTEXT

`availability_audit.json` adds device context to ordinary unavailable entities.

Not-currently-provided entities are excluded because they have separate reference and history checks.

## Partial availability

At least one entity on the device is healthy while one or more other entities are unavailable.

This often represents feature-level or diagnostic availability rather than a whole-device failure.

## Whole device unavailable

The device currently has no healthy state entities.

This is observational evidence only.

The device may be:

- deliberately unpowered
- temporarily offline
- under maintenance
- genuinely unavailable

## Ungrouped unavailable

The unavailable entity is not attached to a Home Assistant device.

## Optional labels

HA Audit supports optional Home Assistant labels for users who want to record known context such as expected-offline equipment or maintenance.

These labels are optional.

HA Audit does not require users to create them and does not treat missing labels as a health problem.

---

# 14. UNAVAILABLE HISTORY CONTEXT

`unavailable_history_audit.json` adds Recorder evidence to ordinary unavailable entities.

The requested history lookback is up to 90 days.

The effective window may be shorter because HA Audit respects the Recorder history actually available.

Current history states include:

```text
usable_history_found
history_found_no_usable_state
no_history_returned
history_query_failed
```

## usable_history_found

Recorder returned at least one usable state.

Where possible HA Audit records:

```text
last_usable_state
last_usable_state_started_at
last_usable_state_ended_at
```

The end is only recorded when Recorder evidence proves when the final usable interval ended.

## history_found_no_usable_state

Recorder returned history, but no usable state was found in the effective window.

This does not prove that the entity was faulty throughout the period.

## no_history_returned

Recorder returned no history records for the entity.

Possible reasons include:

- Recorder exclusions
- Recorder retention
- entity-specific history behaviour

Do not infer fault or staleness simply from missing history.

## history_query_failed

HA Audit could not obtain history for the entity.

This represents incomplete evidence.

## Interpreting history

Recorder history is observational context only.

Old, recent, or absent history does not by itself indicate:

- a fault
- a stale entity
- a configuration problem
- a required action

---

# 15. NOT CURRENTLY PROVIDED

This category is different from ordinary `Unavailable`.

A registry entity can remain stored in Home Assistant even when its integration no longer currently creates or provides that entity.

Possible causes include:

- integration entity-model changes
- removed devices
- old registry entries
- temporarily failed integrations
- configuration changes

This is a review category, not a deletion list.

## Active-YAML references

`not_provided_reference_audit.json` checks whether these entities are still referenced by active YAML.

An entity that is no longer currently provided but remains referenced by active YAML deserves investigation before cleanup.

## Template review candidates

An unreferenced Template entity that is no longer provided can be a stronger review candidate.

HA Audit still does not automatically classify it as safe to delete.

---

# 16. NOT-PROVIDED HISTORY SAFETY

`not_provided_history_audit.json` uses Recorder history as protective evidence for not-currently-provided entities.

The requested lookback is up to 90 days, limited by actual Recorder retention.

HA Audit distinguishes:

- recent or conservatively protective usable history
- older usable history
- no usable history found
- history-query failure

## Final usable interval

Where possible, HA Audit records the start and proven end of the final usable interval.

If Recorder shows a usable state but does not contain the later transition that proves when it ended, the end is considered unknown.

HA Audit keeps that evidence protective rather than assuming it became old.

No usable history is **not** approval to delete an entity.

---

# 17. NEXT ACTIONS

`NEXT ACTIONS` turns the strongest findings into practical investigation guidance.

Entries beginning with:

```text
[!]
```

normally indicate something that needs attention.

Entries beginning with:

```text
[i]
```

are informational or review items.

Availability findings remain contextual.

There is no benefit in trying to force every non-zero count to zero.

---

# 18. AI / LLM HANDOFF

Every successful audit generates:

```text
ha_audit_ai_handoff.md
```

This is a concise, vendor-neutral evidence handoff intended for use with AI assistants such as:

- ChatGPT
- Claude
- Gemini
- local LLMs
- other assistants capable of analysing Home Assistant information

The handoff is generated from the current audit summary rather than independently recreating HA Audit's health or upgrade decisions.

This keeps the normal report and AI handoff based on the same underlying assessment.

## What the handoff contains

The handoff includes selected evidence such as:

- `OVERVIEW`
- `WHY THIS RESULT`
- system and version information
- pending updates
- Core readiness evidence
- official release evidence
- upgrade compatibility results
- configuration findings
- availability context
- Recorder-history context
- review findings
- next actions

Lower-level technical evidence remains available in the detailed reports if needed.

## What the handoff tells the AI

The generated file includes instructions asking the receiving AI to:

- treat HA Audit findings as evidence rather than proof
- distinguish reported facts from its own inference
- avoid claiming that an update is guaranteed safe
- avoid destructive cleanup recommendations based only on unavailable, unknown, or not-currently-provided states
- preserve uncertainty when evidence is incomplete
- keep general Home Assistant health separate from Core update guidance
- prioritise concrete findings over informational context

## Using the handoff

A practical workflow is:

1. Run HA Audit
2. Confirm the audit completed successfully
3. Find `ha_audit_ai_handoff.md`
4. Review the file before sharing it
5. Copy its contents or upload the file to the AI assistant you want to use
6. Ask follow-up questions about the findings
7. If more evidence is required, provide the relevant detailed JSON report

You do not need to write a complex prompt.

The file already contains instructions describing how the evidence should be interpreted.

A simple request such as:

> Analyse this HA Audit handoff and tell me what deserves attention first.

is sufficient to begin.

## Privacy before sharing

The handoff remains local unless you choose to share it.

It can contain installation-specific information such as:

- entity IDs
- device-related names
- Home Assistant version information
- configuration findings
- update information

Review its contents before uploading it to any third-party AI service.

HA Audit does not automatically send the handoff to ChatGPT, OpenAI, Claude, Gemini, or another external service.

---

# 19. DETAILED REPORTS

HA Audit stores reports in its private app-config folder.

Current files include:

```text
audit_snapshot.json
audit_snapshot_previous.json
config_inventory.json
quality_audit.json
not_provided_reference_audit.json
recorder_health_audit.json
not_provided_history_audit.json
availability_audit.json
unavailable_history_audit.json
update_readiness_audit.json
upgrade_impact_audit.json
upgrade_compatibility_audit.json
release_evidence_audit.json
compatibility_coverage_audit.json
upgrade_correlation_audit.json
correlation_validation_audit.json
ha_audit_latest.txt
ha_audit_ai_handoff.md
```

`ha_audit_latest.txt` contains the latest complete user-facing summary.

`ha_audit_ai_handoff.md` contains the concise vendor-neutral AI / LLM handoff.

## Finding the files

If your Home Assistant file-access tool can browse `/addon_configs`:

1. Open `/addon_configs`
2. Open the folder whose name ends in `_ha_audit`

In Studio Code Server this can be done with:

**File → Open Folder...**

and entering:

```text
/addon_configs
```

The prefix before `_ha_audit` is generated by Home Assistant and may differ between installations.

When finished, use **File → Open Recent** to return to your previous workspace.

Studio Code Server is only one possible file-access method. It is not required by HA Audit.

---

# 20. SECURITY AND PRIVACY

HA Audit is designed to be read-only.

It has:

- read-only access to the Home Assistant configuration directory
- access to Home Assistant and Supervisor information APIs
- writable access only to its own private app configuration directory

Configuration scanning excludes sensitive or unrelated locations such as:

- `.storage`
- `.cloud`
- backups
- `custom_components`
- ESPHome configuration
- media
- TTS
- `www`

Files with `secret` in the filename are excluded.

`secrets.yaml` is therefore not read by the configuration scanners.

Generating `ha_audit_ai_handoff.md` does not send any information externally.

External sharing occurs only if the user chooses to copy or upload a generated file elsewhere.

---

# 21. CURRENT LIMITATIONS

HA Audit is under active development.

It does not currently:

- automatically repair Home Assistant
- provide complete Home Assistant Core log analysis
- perform scheduled automatic audits
- provide a full OS upgrade-readiness assessment equivalent to the Core assessment
- guarantee compatibility with every third-party integration or custom component
- inspect every UI-managed configuration path
- automatically send audit reports to an AI analysis service

These are separate from the evidence HA Audit already collects.

Do not interpret an uninspected area as either confirmed safe or confirmed problematic.

---

# 22. PROJECT GOAL

The long-term goal is to provide a structured technical view of a Home Assistant installation so that:

- maintenance
- upgrades
- troubleshooting
- migration planning
- AI-assisted investigation
- long-term future-proofing

can be based on evidence from the actual system rather than generic assumptions.
