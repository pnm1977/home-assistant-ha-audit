# HA Audit

HA Audit is a read-only health and configuration auditing app for Home Assistant.

It is designed to help you understand, maintain, troubleshoot and gradually improve a Home Assistant installation without automatically changing anything.

The normal workflow is:

**run → read → investigate → act → rerun**

HA Audit collects evidence from Home Assistant, analyses configuration and entity health, and produces a concise current-run summary plus detailed JSON reports for deeper investigation.

It does not automatically repair, delete or modify Home Assistant configuration.

---

## What HA Audit checks

HA Audit currently checks:

* Home Assistant Core version
* Home Assistant Supervisor version
* Home Assistant OS version
* device inventory
* entity inventory
* unavailable entities
* unknown entities
* newly unavailable entities
* recovered unavailable entities
* available updates
* Home Assistant configuration validity
* YAML configuration inventory
* the active YAML include tree
* unreferenced YAML files
* missing active include targets
* missing entity reference candidates
* duplicate automation IDs
* duplicate automation aliases/names
* live Home Assistant states for duplicate automation aliases
* duplicate script names
* large automations
* large scripts
* registry entities no longer currently provided by integrations
* active YAML references to not-currently-provided entities
* Template entity review candidates
* Recorder history availability
* Recorder history for not-currently-provided entities
* device-level context for ordinary unavailable entities
* Recorder history for ordinary unavailable entities

HA Audit also compares selected results with the previous audit so changes between runs can be identified.

---

## How to run HA Audit

HA Audit is currently designed to run manually.

In Home Assistant:

1. Go to **Settings → Apps**
2. Select **HA Audit**
3. Select **Start**
4. Wait for the audit to complete
5. Open the **Log** tab

The audit normally takes only a short time.

A successful run ends with:

```text
HA Audit finished
```

The app then stops because HA Audit is configured as a run-once app rather than a continuously running service.

You may see `s6-rc` shutdown messages after:

```text
HA Audit finished
```

These messages are part of the Home Assistant app container shutting down.

They are not HA Audit findings.

---

## What to look at after a run

Find the latest section beginning with:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

The current summary is deliberately much shorter than the detailed audit data.

Typical sections are:

```text
SYSTEM
CONFIGURATION
ENTITY HEALTH
AVAILABILITY CONTEXT
UNAVAILABLE HISTORY CONTEXT
REVIEW
NOT-PROVIDED HISTORY SAFETY
NEXT ACTIONS
DETAILED REPORTS
```

Start by checking:

```text
Config check
Collector errors
```

The preferred results are:

```text
Config check:               VALID
Collector errors:           0
```

Then review the other sections and finish with:

```text
NEXT ACTIONS
```

Do not assume every non-zero number means something is wrong.

Many HA Audit results are inventory, context or review information rather than fault verdicts.

---

## Latest-run summary

HA Audit also writes:

```text
ha_audit_latest.txt
```

This file contains the same concise summary shown in the app log.

It is overwritten on every run.

This means you can use it when you want the latest audit without working through older entries in the Home Assistant app log.

---

## Important result types

### Unavailable

An unavailable entity exists in Home Assistant but currently has no usable state.

This does **not** automatically mean the entity is broken or stale.

Examples include:

* deliberately powered-off equipment
* temporarily disconnected Wi-Fi devices
* temporarily disconnected Zigbee devices
* MQTT devices that are currently offline
* cloud integrations that are temporarily unavailable
* battery-powered devices
* equipment under maintenance
* optional or unsupported feature entities
* genuinely failed devices
* stale entities

The headline unavailable count is therefore inventory, not a fault count.

HA Audit keeps the raw number visible while adding more context elsewhere in the audit.

---

### Unknown

An entity with state:

```text
unknown
```

exists in Home Assistant but does not currently have a meaningful value.

This can be normal for some entity types.

As with unavailable entities, the count should be investigated in context rather than treated as an automatic fault count.

---

### Not currently provided

A **not-currently-provided** entity is different from an ordinary unavailable entity.

It exists in the Home Assistant entity registry but is not currently present in the live entity source data supplied by Home Assistant.

Possible explanations include:

* an integration changing its entity model
* a removed device
* a disabled or unavailable integration
* an old registry entry
* a configuration change
* a genuinely stale entity

HA Audit deliberately keeps these entities separate from ordinary unavailable entities.

They are review candidates, not automatic deletion candidates.

---

### Not provided + active YAML

This is a stronger finding.

It means an entity is:

1. no longer currently provided by Home Assistant, **and**
2. still referenced by the active YAML configuration tree.

These entities should normally be investigated before any cleanup because removing them could leave active configuration referring to a missing entity.

The detailed evidence is stored in:

```text
not_provided_reference_audit.json
```

---

### Template review candidates

HA Audit can identify Template entities that:

* are no longer currently provided
* are not referenced by active YAML

These are stronger review candidates than a generic not-currently-provided entity.

They are still not automatic deletion recommendations.

Before deleting anything, check the entity in Home Assistant and confirm that it is genuinely obsolete.

---

## Availability context

Ordinary unavailable entities are analysed separately in:

```text
availability_audit.json
```

HA Audit looks at the other current state entities belonging to the same Home Assistant device.

This allows unavailable entities to be placed into more useful context.

### Partial availability

A device has **partial availability** when:

* one or more entities are unavailable
* at least one other entity on the same device is healthy

For example, an integration may expose:

* a healthy main device entity
* healthy battery information
* unavailable notification entities
* unavailable diagnostic controls
* unavailable optional features

That should not automatically be described as a whole-device failure.

HA Audit therefore reports partial availability as feature-level context.

---

### Whole device unavailable

A device is classified as **whole device unavailable** when HA Audit can see no healthy current state entities belonging to that device.

This is still observational context rather than a fault verdict.

Possible explanations include:

* the device is deliberately powered off
* it is temporarily offline
* it is undergoing maintenance
* it has lost network connectivity
* a Zigbee or MQTT device is disconnected
* a cloud integration is unavailable
* the device has genuinely failed

The detailed history report can provide additional evidence.

---

### Ungrouped unavailable

Some unavailable entities are not attached to a Home Assistant device.

These are reported separately as:

```text
ungrouped_unavailable
```

Review the entity itself when more context is needed.

---

### Optional availability labels

HA Audit supports optional Home Assistant labels that can provide extra context for deliberately unavailable equipment or equipment under maintenance.

These labels are optional.

HA Audit does **not** require users to configure them.

Missing labels are not treated as a health issue.

The normal `NEXT ACTIONS` output does not ask users to create or maintain labels.

This allows HA Audit to remain useful without creating extra Home Assistant administration work.

---

## Unavailable history context

HA Audit can use Home Assistant Recorder history to provide additional context for ordinary unavailable entities.

The detailed report is:

```text
unavailable_history_audit.json
```

The requested history window is up to:

```text
90 days
```

However, HA Audit first checks the Recorder history actually available.

If Home Assistant only has 30 days of Recorder history, HA Audit does not pretend that 90 days were checked.

The effective history window is reported explicitly.

---

### Matching history to the availability snapshot

The unavailable-history scan uses the timestamp of the availability snapshot as its history endpoint.

This prevents the history scanner from analysing states that occurred after the current-state availability classification was captured.

The two reports therefore refer to the same audit point as closely as possible.

---

### Unavailable history statuses

Ordinary unavailable entities can receive one of these history statuses:

```text
usable_history_found
history_found_no_usable_state
no_history_returned
history_query_failed
```

#### usable_history_found

Recorder returned at least one state other than:

```text
unavailable
unknown
none
```

HA Audit can then record:

```text
last_usable_state
last_usable_state_started_at
last_usable_state_ended_at
```

`last_usable_state_started_at` records when the final usable state began.

`last_usable_state_ended_at` is populated only when Recorder contains a later non-usable transition that proves when that usable interval ended.

This is important because the start of a long-running state is not necessarily the time the entity became unavailable.

---

#### history_found_no_usable_state

Recorder returned history for the entity, but every usable candidate within the effective history window was:

```text
unavailable
unknown
none
```

This means HA Audit has Recorder evidence but did not find a usable state in the available window.

It does **not** prove that the entity has always been unavailable or that it is faulty.

---

#### no_history_returned

Recorder returned no history for the entity.

Possible reasons include:

* Recorder retention
* Recorder exclusions
* entity-specific history behaviour
* the entity not existing during the available Recorder window

No history is unknown evidence.

It is not a fault verdict or a cleanup recommendation.

---

#### history_query_failed

HA Audit attempted to obtain Recorder history but the query failed.

A failed history request is reported separately so it cannot be confused with absence of history.

HA Audit requests history in batches for efficiency.

If a batch request fails, the affected entities are retried individually.

Only genuine individual failures remain classified as:

```text
history_query_failed
```

---

### How to interpret unavailable history

Recorder history is observational context only.

Old, recent or absent usable history does not by itself indicate:

* a fault
* a stale entity
* a configuration problem
* an entity that should be deleted
* a required action

Combine Recorder evidence with:

* the current availability classification
* the device involved
* the integration involved
* whether the equipment is intentionally powered
* how the equipment is normally used

---

## Not-provided history safety

HA Audit also uses Recorder history as protective evidence for entities that are no longer currently provided.

The detailed report is:

```text
not_provided_history_audit.json
```

The requested lookback is up to 90 days but is limited by the Recorder history actually available.

The report distinguishes:

* recent or protective usable history
* older usable history
* no usable history
* history query failures

---

### Final usable interval

For not-currently-provided entities, HA Audit now distinguishes between:

```text
last_usable_state_started_at
```

and:

```text
last_usable_state_ended_at
```

when Recorder provides enough information to establish both.

This prevents a long-running healthy state from being treated as old merely because that state began a long time ago.

An entity is only classified as having older activity when Recorder proves that its final usable interval ended before the recent-history window.

If Recorder shows a usable state but contains no following transition proving when that usable interval ended, HA Audit treats the result conservatively as protective context.

It does not assume that the entity became old when the final usable state began.

No usable history is not approval to delete an entity.

---

## Duplicate automation IDs

Automation IDs should be unique.

A duplicate automation ID is therefore treated as a structural configuration finding.

The detailed information is stored in:

```text
quality_audit.json
```

Review the reported files and line numbers before changing anything.

---

## Duplicate automation names

Duplicate automation names or aliases are different from duplicate automation IDs.

Duplicate names can be intentional.

For example, a user may retain a disabled rollback copy of an automation.

HA Audit therefore cross-checks duplicate aliases against the live Home Assistant automation states.

The normal summary surfaces duplicate aliases when:

* two or more matching automations are currently on
* the live states cannot be fully resolved

Disabled or mixed-state duplicate aliases remain available in the detailed report without being promoted as normal health findings.

HA Audit does not guess intent from names such as:

```text
Old
Backup
Previous
Test
```

The live Home Assistant automation state is used instead.

This prevents deliberately disabled rollback copies from creating unnecessary routine warnings.

---

## Missing active includes

A missing active include means a YAML file in the active configuration tree references another file that HA Audit could not find.

The detailed report contains the source file and source line.

Investigate the exact location before making changes.

A missing include can be important because Home Assistant configuration may depend on that target file.

---

## Missing entity candidates

HA Audit scans active YAML for entity IDs and compares them with the current Home Assistant entity inventory.

A missing entity candidate means HA Audit found an entity reference in active YAML that it could not match to a current entity.

This is not automatically a confirmed error.

The entity may be:

* renamed
* temporarily unavailable from an integration
* dynamically generated in a way the scanner cannot fully resolve
* genuinely missing

Use the reported source file and line number to investigate it.

---

## Orphan YAML candidates

HA Audit identifies YAML files that are not part of the active include tree.

It also separates known categories such as:

* blueprints
* Zigbee2MQTT configuration
* backup or archive material

Files left as orphan candidates deserve review.

Do not delete a YAML file merely because it is not in the active include tree.

It may be deliberately retained reference material or a manual backup.

---

## Commented rollback configuration

HA Audit is designed to tolerate commented-out rollback and reference blocks.

Fully commented YAML is not treated as active configuration when performing checks such as:

* entity-reference analysis
* duplicate active automation checks

This allows commented backup material to remain in YAML without creating false active findings.

---

## Large automations and scripts

HA Audit records unusually large automations and scripts as maintainability information.

Large does not automatically mean bad.

A long automation may be entirely appropriate.

The finding simply identifies configuration that may be harder to maintain and may deserve review over time.

---

## After making a change

HA Audit is designed around repeated audit cycles.

After correcting or cleaning something:

1. Save the Home Assistant change
2. Validate the Home Assistant configuration where appropriate
3. Reload or restart only when required
4. Run HA Audit again
5. Compare the latest result with the previous result

Useful fields include:

```text
New unavailable
Recovered unavailable
```

and the configuration counts in the latest summary.

The goal is not to force every count to zero.

The goal is to understand what each finding represents and remove genuine problems without removing intentional configuration.

---

## Full user guide

More detailed investigation guidance is available in:

```text
DOCS.md
```

The user guide explains how to investigate individual finding types and where to check them in Home Assistant.

---

## Detailed reports

HA Audit stores detailed reports in its private app-config folder.

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
ha_audit_latest.txt
```

### audit_snapshot.json

Contains the detailed current Home Assistant audit snapshot.

### audit_snapshot_previous.json

Contains the previous snapshot used for selected run-to-run comparisons.

### config_inventory.json

Contains the YAML configuration inventory and include information.

### quality_audit.json

Contains detailed configuration-quality findings such as:

* missing includes
* missing entity candidates
* duplicate automation IDs
* duplicate automation aliases
* duplicate script names
* large automations
* large scripts

### not_provided_reference_audit.json

Contains active-YAML reference analysis for entities that are no longer currently provided.

### recorder_health_audit.json

Contains information about the Recorder history window available to HA Audit.

### not_provided_history_audit.json

Contains protective Recorder-history evidence for entities that are no longer currently provided.

### availability_audit.json

Contains device-level availability context for ordinary unavailable entities.

### unavailable_history_audit.json

Contains Recorder-history context for ordinary unavailable entities.

### ha_audit_latest.txt

Contains the concise latest-run summary.

This file is overwritten on each run.

---

## Finding the detailed reports

The report files are stored in HA Audit's own app-config folder.

They are not stored in your normal:

```text
/config
```

directory.

If your Home Assistant file-access tool can browse:

```text
/addon_configs
```

open that location and find the folder whose name ends in:

```text
_ha_audit
```

The prefix before `_ha_audit` is generated by Home Assistant and may differ between installations.

### Studio Code Server example

In Studio Code Server:

1. Select **File → Open Folder...**
2. Enter:

```text
/addon_configs
```

3. Open the folder whose name ends in:

```text
_ha_audit
```

When you have finished reviewing the reports, select:

**File → Open Recent**

to return to the folder or workspace you were previously using.

If the previous workspace is not listed, use:

**File → Open Folder...**

and select it manually.

For normal use, start with the summary in:

**Settings → Apps → HA Audit → Log**

Open the detailed JSON reports only when the summary points you towards them or when deeper investigation is needed.

---

## Safety

HA Audit is designed to be read-only.

It does not:

* modify Home Assistant configuration
* delete entities
* disable entities
* remove devices
* alter integrations
* change automations
* change scripts
* install updates
* restart Home Assistant

Home Assistant configuration is mounted read-only.

The app writes only its own audit report files to its private app-config directory.

---

## Sensitive configuration

Configuration scanning excludes sensitive or unrelated areas including:

```text
.storage
.cloud
backups
custom_components
esphome
media
tts
www
```

Files with `secret` in the filename are excluded from configuration scanning.

This includes:

```text
secrets.yaml
```

HA Audit therefore does not need to read Home Assistant secrets in order to perform its configuration checks.

---

## External services

HA Audit currently performs its analysis locally within the Home Assistant app environment.

It does not currently send audit data to:

* OpenAI
* ChatGPT
* GitHub
* another external AI analysis service

Future AI-assisted analysis is planned as a later, optional stage of the project rather than part of the current local audit.

---

## Troubleshooting

### The app stops after the audit

This is expected.

HA Audit is a run-once app.

When the audit finishes, the app stops automatically.

Look for:

```text
HA Audit finished
```

in the log.

---

### I see s6-rc messages after the audit

This is normal.

The `s6-rc` messages shown afterwards are part of the app shutting down and are not HA Audit findings.

Only investigate them if the log shows an actual error before:

```text
HA Audit finished
```

---

### Collector errors is not zero

If the current-run summary reports:

```text
Collector errors:           1
```

or another non-zero value, part of the audit did not complete correctly.

Review the app log.

When a scanner stage fails, HA Audit attempts to print the captured output from that failed stage so the collection problem can be investigated.

Do not rely on the affected report until the collector issue is understood.

---

### Config check is not VALID

If the summary does not show:

```text
Config check:               VALID
```

investigate the Home Assistant configuration before restarting Home Assistant.

Home Assistant's own configuration validation is available under:

**Developer tools → YAML**

---

### I cannot find the report files

The detailed reports are in HA Audit's app-config directory rather than the normal Home Assistant configuration directory.

Browse:

```text
/addon_configs
```

and open the folder ending in:

```text
_ha_audit
```

---

### The log contains several audits

Use the final:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

section in the log.

Alternatively use:

```text
ha_audit_latest.txt
```

which contains only the latest concise summary.

---

### An unavailable count looks very high

Do not assume that the number represents failed devices.

Review:

```text
AVAILABILITY CONTEXT
```

and, where useful:

```text
unavailable_history_audit.json
```

A large unavailable count can be caused by integrations that create many feature, diagnostic or optional entities.

---

### Recorder history is shorter than 90 days

This is expected when Home Assistant Recorder does not retain 90 days of history.

HA Audit reports both:

* the requested lookback
* the effective history actually available

It does not treat missing older Recorder data as evidence against an entity.

---

## Current status

HA Audit is under active development.

The current focus is read-only health and configuration auditing.

Current development areas include:

* system health
* configuration quality
* entity and device availability context
* safe stale-configuration discovery
* Recorder evidence
* upgrade readiness
* easier long-term maintenance

The next major development area is update and upgrade readiness.

Later stages are expected to include:

* a structured LLM-ready audit report
* optional AI-assisted analysis
* deeper Home Assistant health monitoring

The core principle remains:

**collect evidence first, make changes only after review.**
