# HA Audit — User Guide

HA Audit is a read-only Home Assistant health, configuration and upgrade-readiness auditing app.

It is designed to help you work through Home Assistant maintenance systematically:

**run → review → investigate → act → rerun**

HA Audit does not automatically repair, delete or rewrite anything.

This guide explains how to use the current audit output and how to interpret the evidence it provides.

---

# 1. Running HA Audit

HA Audit currently runs manually.

In Home Assistant:

1. Go to **Settings → Apps**
2. Open **HA Audit**
3. Select **Start**
4. Wait for the audit to finish
5. Open the **Log** tab

HA Audit stops automatically when the audit is complete.

A successful run ends with:

```text
HA Audit finished
```

Messages from `s6-rc` that appear afterwards are part of the app shutting down and are not HA Audit findings.

HA Audit currently supports:

```text
amd64
```

---

# 2. Finding the latest run

The Home Assistant app log may contain several previous HA Audit runs.

Each new run contains a clearly marked section:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

Use the **last occurrence** of this heading in the Log tab.

HA Audit also writes:

```text
ha_audit_latest.txt
```

This file is overwritten on every run so there is always a clean copy of the latest summary in HA Audit's private app storage.

The detailed JSON reports are also retained.

For normal use, start with the **CURRENT RUN SUMMARY** rather than reading every JSON report.

---

# 3. How to read the summary

The current summary contains several evidence layers.

Depending on what is applicable to the installation and pending updates, you may see sections including:

```text
SYSTEM

UPDATE READINESS

OFFICIAL RELEASE EVIDENCE

COMPATIBILITY COVERAGE

DYNAMIC UPGRADE CORRELATION

CORRELATION VALIDATION

UPGRADE COMPATIBILITY

CONFIGURATION

ENTITY HEALTH

AVAILABILITY CONTEXT

UNAVAILABLE HISTORY CONTEXT

REVIEW

NOT-PROVIDED HISTORY SAFETY

NEXT ACTIONS

DETAILED REPORTS
```

Do not assume that every non-zero value is a fault.

Some sections are:

* inventory
* evidence
* context
* uncertainty
* review candidates
* actual findings requiring attention

A useful workflow is:

1. Confirm the audit completed correctly
2. Check **SYSTEM**
3. If a Core update is pending, review the upgrade-readiness sections
4. Check **CONFIGURATION**
5. Review entity and availability findings
6. Read **NEXT ACTIONS**
7. Investigate one finding or category at a time
8. Make the smallest appropriate change
9. Validate Home Assistant configuration where appropriate
10. Rerun HA Audit
11. Confirm the expected finding changed

---

# 4. SYSTEM

Example:

```text
SYSTEM
----------------------------------------------------------
Core:                       2026.x.x
Supervisor:                 2026.xx.x
OS:                         xx.x
Config check:               VALID
Updates available:          2
Collector errors:           0
```

## Config check

The preferred result is:

```text
Config check: VALID
```

This means Home Assistant's configuration validation completed successfully.

If the result is not `VALID`, investigate the configuration problem before restarting Home Assistant simply to test whether it works.

You can also check configuration validation in:

**Developer tools → YAML**

---

## Updates available

This is the number of Home Assistant `update` entities currently reporting an available update.

It does **not** mean HA Audit recommends installing every available update.

Review available updates in:

**Settings → System → Updates**

More detailed update information appears in the **UPDATE READINESS** section.

---

## Collector errors

The preferred result is:

```text
Collector errors: 0
```

A collector error means that part of the audit did not complete normally.

If the value is greater than zero:

1. Stay in **Settings → Apps → HA Audit → Log**
2. Look above the summary for `ERROR` or `failed`
3. Review the captured output from the failed stage

Do not treat evidence from a failed collector as complete.

---

# 5. UPDATE READINESS

This section collects the local context needed to begin assessing pending updates.

It can include:

* pending update count
* installed and target versions
* the pending Core upgrade window
* Home Assistant Repair issues
* Repair issues relevant to the Core upgrade window
* status of the supporting Core upgrade evidence

Example structure:

```text
UPDATE READINESS
----------------------------------------------------------
Pending updates:             2

Core: 2026.x.x -> 2026.x.x
OS: xx.x -> xx.x

Core upgrade window:         2026.x.x -> 2026.x.x

Repair issues:               ...
Unignored Repairs:           ...
Relevant to Core upgrade:    ...

Deterministic reference:     ...
Compatibility coverage:      ...
Dynamic correlation:         ...
Correlation validation:      ...
Official release evidence:   ...
Readiness verdict:           NOT PRODUCED
```

## Pending updates

HA Audit separates pending updates into categories such as:

* Core
* OS
* Supervisor
* apps
* HACS
* firmware
* other update entities

This is update inventory and context, not an instruction to install them.

---

## Core upgrade window

When a Core update is available, HA Audit records the version range being assessed.

For example:

```text
Core upgrade window: 2026.8.3 -> 2026.9.4
```

The other Core readiness scanners use this version range when collecting and correlating evidence.

---

## Repairs

HA Audit records the current Home Assistant Repair issues and identifies Repair evidence that appears relevant to the pending Core upgrade window.

A relevant unignored Repair should be reviewed before installing the Core update.

A Repair that is not identified as relevant may still matter for Home Assistant generally.

The current Repair evidence is a snapshot from the audit run.

Persistent Repair history and longer-term health intelligence are not yet part of 0.7.x.

---

# 6. What does `Readiness verdict: NOT PRODUCED` mean?

HA Audit 0.7.x deliberately does **not** turn the available evidence into a final:

```text
safe to update
```

or:

```text
do not update
```

decision.

Instead, 0.7.x builds the evidence foundation needed for a useful readiness decision.

It answers questions such as:

* What Core version is installed?
* What Core version is pending?
* What changed in the releases being crossed?
* Are those changes relevant to anything installed locally?
* Are there Repair issues relevant to the upgrade?
* Did the evidence collectors complete?
* Is optional reference evidence available?
* Is any part of the assessment incomplete?

The final human-facing guidance layer is still being developed.

Therefore:

```text
Readiness verdict: NOT PRODUCED
```

is normal behaviour in 0.7.x.

It is not itself an audit failure.

---

# 7. OFFICIAL RELEASE EVIDENCE

This section gathers Home Assistant release evidence for the Core versions being crossed.

It can report:

* Core releases crossed
* release families examined
* official releases fetched
* breaking-change groups
* crossed change groups
* successful or partial parses
* failed parses
* whether official sources only were used
* whether evidence collection completed

The important distinction is:

**release evidence describes what changed in Home Assistant.**

It does not by itself prove that the local installation is affected.

For example, an official breaking change may concern an integration that is not installed locally.

That is why release evidence is passed to the later correlation stages.

---

## Evidence collection states

The preferred result for an applicable Core upgrade is:

```text
Evidence collection: COMPLETE
```

If evidence collection is partial, incomplete or failed, review:

```text
release_evidence_audit.json
```

before treating the upgrade assessment as complete.

A complete official-evidence collection means the release evidence was collected successfully.

It does **not** mean the installation has been proven compatible or safe to update.

---

# 8. COMPATIBILITY COVERAGE

HA Audit can use version-specific deterministic compatibility rules as an additional reference.

These rules are intended to improve precision for known Home Assistant changes.

They are **not required for every future release**.

The compatibility coverage section answers questions such as:

* Is deterministic reference information available?
* Which official breaking-change groups are covered?
* Is only part of the release range covered?
* Are expected rules or mappings missing?

This is primarily a quality and coverage check on the optional reference layer.

---

## Reference states

HA Audit uses the following reference states.

### `complete`

The applicable deterministic reference is present and the expected coverage evidence is complete.

### `partial_reference`

Deterministic reference exists for only part of the applicable release evidence.

The remaining evidence can still use dynamic correlation.

### `no_reference`

No deterministic reference exists for the release family.

This is a **supported state**.

It does not mean the scanner failed.

HA Audit can continue using:

```text
Official release evidence
        ↓
Dynamic correlation
        ↓
Local installation evidence
```

without a deterministic rule pack.

### `incomplete`

A deterministic reference exists or is expected, but its mapping or rule evidence is incomplete.

This deserves review.

### `not_applicable`

Deterministic reference comparison is not relevant to the current run.

---

## Important distinction

These two statements are different:

```text
Reference status: NO REFERENCE
Collector health: OK
```

That combination is valid.

It means the optional deterministic reference does not exist, but the scanner itself completed normally.

---

# 9. DYNAMIC UPGRADE CORRELATION

Dynamic correlation is the generic path intended to work with future Home Assistant releases without requiring a hand-maintained rule for every change.

It compares:

```text
Official Home Assistant release evidence
              ↓
Local Home Assistant evidence
```

For each official change group, HA Audit looks for relevant evidence in the installation.

Possible evidence levels include:

### Specific code evidence

A stronger local match was found.

This may indicate that local configuration contains something specifically related to the official change.

### Local surface evidence

The installation contains a relevant integration, platform or configuration surface, but the evidence is not specific enough to conclude that it is affected.

### Partial evidence

Some related evidence was found, but the available information is incomplete.

### No local evidence

HA Audit did not find local evidence corresponding to the official change group.

This is useful evidence, but it is not proof that no possible dependency exists.

### Insufficient evidence

HA Audit could not gather enough information to make a meaningful local comparison.

This should remain uncertain rather than being converted into a reassuring result.

---

## What dynamic correlation does not do

Dynamic correlation identifies local evidence related to official Home Assistant changes.

It does **not** independently decide that the installation is:

* affected
* unaffected
* compatible
* incompatible
* safe to update

Those would be stronger conclusions than the evidence currently supports.

---

# 10. CORRELATION VALIDATION

Where deterministic reference information exists, HA Audit can compare the generic dynamic-correlation result against that reference.

This is primarily used to test and improve the accuracy of the generic correlation approach.

It can identify:

* aligned local relevance
* dynamic gaps
* deterministic gaps
* unresolved comparisons
* precision-review differences

This helps answer:

**Did the generic approach find the same locally relevant areas as the known reference?**

---

## `NO REFERENCE` validation

For a future release with no deterministic reference, HA Audit may report:

```text
Correlation validation: NO REFERENCE
Collector health: OK
```

This is valid.

There is simply nothing deterministic to compare the dynamic result against.

The dynamic correlation remains usable independently.

---

## Precision review

A precision-review difference does not automatically mean either scanner is wrong.

It means the two evidence methods classified something differently enough to deserve inspection.

HA Audit keeps that difference visible rather than forcing both methods to agree.

---

# 11. UPGRADE COMPATIBILITY

Where an applicable deterministic rule pack exists, HA Audit can assess those rules against the local installation.

Possible outcomes include:

```text
No local match
Local match, no affected use
Review required
Manual review
```

## No local match

The rule did not find the relevant local integration or configuration evidence.

## Local match, no affected use

A related local component exists, but HA Audit did not find evidence of the affected usage covered by that rule.

## Review required

Local evidence matched strongly enough that the user should review the finding before updating.

## Manual review

The rule cannot be resolved confidently using the evidence HA Audit can currently inspect.

Human review is required.

---

## Compatibility rules are evidence, not a verdict

Even when every deterministic rule completes successfully, the result is not automatically:

```text
safe to update
```

The rule set is an additional precision layer.

Official evidence, dynamic correlation, local evidence, collector completeness and known limitations still matter.

---

## UI-managed configuration

Some Home Assistant configuration exists outside the YAML and local surfaces currently inspected by HA Audit.

For example, the current compatibility output can explicitly report when UI-managed LLM prompt content was not inspected.

When HA Audit says a surface was not inspected, treat that as a limitation rather than assuming the configuration is unaffected.

---

# 12. Core readiness versus OS readiness

HA Audit currently has much deeper readiness analysis for **Home Assistant Core** than for **Home Assistant OS**.

For Core, 0.7.x can combine:

* installed and target versions
* official release evidence
* breaking-change groups
* Repair context
* local installation evidence
* dynamic correlation
* optional deterministic reference
* reference validation

OS updates currently receive useful update/version context but do not yet have an equivalent full evidence pipeline.

Do not interpret the presence of an OS update in the report as an OS safety assessment.

---

# 13. CONFIGURATION

Example:

```text
CONFIGURATION
----------------------------------------------------------
Active YAML files:           ...
Missing active includes:     ...
Missing entity candidates:   ...
Orphan YAML candidates:      ...
Duplicate automation IDs:    ...
Active duplicate auto names: ...
Unresolved duplicate names:  ...
Duplicate script names:      ...
```

---

## Active YAML files

This is inventory information.

There is no preferred number.

A change may simply mean configuration files were added, removed, merged or reorganised.

---

## Missing active includes

The preferred result is:

```text
Missing active includes: 0
```

A non-zero value means active YAML refers to a file or directory that HA Audit could not find.

Use the reported source file and line to investigate.

Check whether:

* the target exists
* the path is correct
* the file was renamed
* the file was moved
* the include is obsolete

After correcting the configuration, rerun HA Audit.

---

## Missing entity candidates

The preferred result is:

```text
Missing entity candidates: 0
```

These are entity IDs referenced in active YAML that HA Audit could not match to a current Home Assistant entity.

They are **candidates**, not automatically confirmed errors.

Investigate the entity in:

**Settings → Devices & services → Entities**

Then inspect the YAML location reported by HA Audit.

Possible causes include:

* a typo
* an old entity ID
* a removed entity
* configuration that should use a replacement entity
* obsolete YAML

---

## Orphan YAML candidates

An orphan candidate is a YAML file that is not part of the active Home Assistant include tree and has not been classified as a known excluded or backup/archive type.

It is not automatically safe to delete.

Check whether the file is:

* old unused configuration
* an intentional backup
* reference material
* configuration that should actually be included

---

## Duplicate automation IDs

Automation IDs should be unique.

A reported duplicate automation ID should be reviewed.

Do not simply delete one occurrence without identifying which automations use it.

---

## Duplicate automation names

HA Audit distinguishes duplicate automation aliases from duplicate IDs.

Duplicate names are primarily a maintainability finding.

The normal summary promotes duplicate aliases when two or more matching automations are currently on.

It can also report aliases whose live-state classification could not be fully resolved.

Duplicate names do not automatically mean the automations are broken.

---

## Duplicate script names

Duplicate script aliases are also primarily a maintainability finding.

Review the reported scripts and determine whether the duplicate naming is intentional.

---

# 14. ENTITY HEALTH

Example:

```text
ENTITY HEALTH
----------------------------------------------------------
Entities:                   ...
Unavailable:                ...
Unknown:                    ...
Not currently provided:     ...
New unavailable:            ...
Recovered unavailable:      ...
```

Large non-zero values here do **not** automatically mean Home Assistant is unhealthy.

The important question is why those entities have those states.

---

## Unavailable

An unavailable entity still exists in Home Assistant but currently has no usable state.

Possible causes include:

* powered-off devices
* disconnected devices
* temporarily unavailable integrations
* cloud-service outages
* maintenance
* retired devices
* stale configuration

Do not bulk-delete unavailable entities simply because they appear in this count.

---

## Unknown

An entity with an `unknown` state exists but Home Assistant does not currently have a meaningful value for it.

This can be normal for some entity types.

Investigate unexpected examples rather than treating the entire count as a fault.

---

## New unavailable

This compares the current audit with the previous audit.

It can be more useful than the total unavailable count because it highlights change.

Check the affected entities before assuming they are faults.

---

## Recovered unavailable

These entities were unavailable during the previous audit but are no longer unavailable.

This is normally informational.

Recovery after maintenance or troubleshooting can help confirm that a change had the intended effect.

---

# 15. AVAILABILITY CONTEXT

HA Audit classifies ordinary unavailable entities to provide more useful context.

Possible categories include:

### Expected offline

The device has the optional:

```text
HA Audit - Expected Offline
```

label.

This can be used for devices that are intentionally powered down or commonly offline.

### Maintenance

The device has the optional:

```text
HA Audit - Maintenance
```

label.

This can identify devices temporarily offline because of maintenance, building work or similar activity.

### Partial availability

Some entities belonging to the device are unavailable while other entities remain healthy.

This is different from a whole device appearing offline.

### Whole device unavailable

No healthy state entities were found for an unlabelled device.

This deserves investigation, but it is not automatically proof of a fault.

### Ungrouped unavailable

The unavailable entity is not attached to a device that HA Audit can use for device-level classification.

---

## Labels are optional

You do not need to maintain HA Audit labels simply to make the report look cleaner.

The labels are optional context.

HA Audit keeps the underlying unavailable count visible.

---

# 16. UNAVAILABLE HISTORY CONTEXT

HA Audit checks Recorder history for ordinary unavailable entities.

Possible results include:

```text
usable_history_found
history_found_no_usable_state
no_history_returned
history_query_failed
```

This helps distinguish an entity that previously worked from one for which no usable state is visible in the available Recorder window.

However:

**Recorder history is context, not a cleanup verdict.**

Recent, old or absent history does not independently prove that an entity is broken or stale.

Recorder retention and exclusions can also limit what HA Audit can see.

---

# 17. NOT CURRENTLY PROVIDED

This is different from ordinary `Unavailable`.

A registry entity can remain stored in Home Assistant even when its integration no longer currently creates or provides it.

HA Audit compares the enabled entity registry with the entities currently supplied by integrations.

Possible reasons include:

* an integration no longer exposing an old entity
* a device being removed
* an integration being removed
* an integration changing its entity model
* old registry entries remaining
* an integration currently failing to load

Therefore:

**Not currently provided does not automatically mean safe to delete.**

It is a review list.

---

# 18. REVIEW

The summary narrows some of the larger inventories into findings that deserve closer attention.

Two important examples are:

```text
Not provided + active YAML
Template review candidates
```

---

## Not provided + active YAML

This means:

1. Home Assistant still has the entity in its registry
2. its integration is not currently providing it
3. HA Audit found the entity ID referenced in active YAML

This is an important finding.

Do **not** delete the entity first.

Investigate why active configuration still expects it.

Possible actions might include:

* replacing an old entity ID
* correcting a typo
* removing obsolete YAML
* restoring a required integration or device

After making a change:

1. validate Home Assistant configuration where appropriate
2. rerun HA Audit
3. confirm the finding changed as expected

---

# 19. NOT-PROVIDED HISTORY SAFETY

HA Audit also checks available Recorder history for entities that are no longer currently provided.

The report distinguishes:

* recent/protective activity
* older activity
* no usable history
* history-query failure
* usable intervals whose end cannot be proven

The effective history window is limited by the actual Recorder history available.

---

## Protective history

If HA Audit finds recent usable history, that is evidence that the entity was genuinely active within the available history window.

Treat this as a reason to investigate before removing it.

---

## Older history

Older usable history can support an investigation but still does not prove that an entity is now safe to remove.

---

## No usable history

This means HA Audit did not find usable state history in the effective Recorder window.

It does **not** mean:

```text
safe to delete
```

Possible reasons include:

* Recorder retention
* Recorder exclusions
* the entity being older than retained history
* incomplete history
* the entity genuinely never having a usable state

Absence of evidence is not deletion approval.

---

## Unknown interval end

If Recorder shows a usable state but does not contain the later transition proving when that usable interval ended, HA Audit keeps that history protective.

It does not assume the state became old merely because the transition is missing.

---

# 20. Template review candidates

A Template review candidate is an entity that:

1. remains in Home Assistant's entity registry
2. is no longer currently provided by the Template integration
3. has no active YAML reference found by HA Audit

This is stronger cleanup evidence than an ordinary unavailable entity.

It is still a review candidate rather than an automatic deletion instruction.

Before deleting, confirm that:

* HA Audit found no active YAML reference
* you recognise the entity as obsolete
* Home Assistant says it is no longer provided
* available Recorder evidence does not show a reason to retain it
* it is not intentionally used somewhere outside the configuration HA Audit can inspect

After deleting an entity you have independently confirmed is obsolete, rerun HA Audit and confirm the expected counts changed.

---

# 21. NEXT ACTIONS

The:

```text
NEXT ACTIONS
```

section turns selected audit findings into practical review steps.

Entries beginning with:

```text
[!]
```

deserve attention.

Entries beginning with:

```text
[i]
```

are normally informational, maintenance or review opportunities.

For Core updates, `NEXT ACTIONS` can also highlight:

* relevant unignored Repairs
* incomplete official release evidence
* incomplete deterministic-reference evidence
* incomplete dynamic correlation
* incomplete reference validation
* deterministic compatibility findings needing review

A `NO REFERENCE` state should not be promoted as an error when the collector completed normally.

Work through findings one category at a time.

There is no benefit in trying to force every non-zero count to zero.

---

# 22. Recommended maintenance workflow

A practical HA Audit session is:

1. Go to **Settings → Apps → HA Audit**
2. Start HA Audit
3. Open the **Log** tab
4. Find the latest **CURRENT RUN SUMMARY**
5. Confirm the audit collectors completed
6. Confirm **Config check = VALID**
7. If a Core update is pending, review the readiness evidence
8. Read **NEXT ACTIONS**
9. Pick one finding or category
10. Investigate it
11. Make only the intended change
12. Validate Home Assistant configuration where appropriate
13. Run HA Audit again
14. Confirm the expected result changed
15. Continue only when ready

Repeated reruns are expected.

---

# 23. DETAILED REPORTS

HA Audit generates detailed evidence files as well as the short summary.

Current reports include:

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
```

`ha_audit_latest.txt` is overwritten on every run.

The JSON files contain the detailed evidence used by HA Audit.

Normal users should not need to read every report.

Use them when:

* the summary identifies a finding
* `NEXT ACTIONS` points to a report
* you need deeper evidence
* you are troubleshooting HA Audit
* you are helping develop or validate the project

---

# 24. Finding detailed reports

Reports are stored in HA Audit's private app-config folder.

This is primarily an advanced investigation and development path.

If your Home Assistant file-access tool can browse:

```text
/addon_configs
```

open the folder whose name ends in:

```text
_ha_audit
```

The part before `_ha_audit` is generated by Home Assistant and may differ between installations.

---

## Studio Code Server example

If you use Studio Code Server:

1. Select **File → Open Folder...**
2. Enter:

```text
/addon_configs
```

3. Open the folder ending in:

```text
_ha_audit
```

When finished, use **File → Open Recent** to return to your previous workspace.

Studio Code Server is not required to run HA Audit.

Direct file browsing should be considered an advanced/debugging route rather than the intended long-term user experience.

---

# 25. Configuration inventory

HA Audit scans Home Assistant YAML using read-only access.

It records information including:

* YAML file count
* YAML line count
* active configuration layout
* include relationships
* largest YAML files
* exact duplicate YAML files
* inactive or unreferenced YAML
* `!secret` usage

The inventory is intended to describe the configuration structure without treating size alone as a fault.

---

# 26. Commented backup configuration

Fully commented-out YAML is not treated as active configuration.

This is deliberate.

Users may retain old templates, automations or other configuration as commented rollback/reference blocks.

HA Audit therefore ignores fully commented lines when checking active entity references.

A high proportion of comments may still appear as informational inventory.

It is not automatically a problem.

---

# 27. Large automations and scripts

HA Audit can identify unusually large automation and script definitions.

This is informational.

A large automation or script is not automatically badly designed or broken.

The purpose is to identify configuration that may be worth reviewing later for maintainability.

Do not split or rewrite working configuration purely because HA Audit reports it as large.

---

# 28. Security and privacy

HA Audit currently operates locally except where a scanner explicitly fetches public Home Assistant release evidence required for the upgrade-readiness analysis.

HA Audit does not currently send the user's audit report to:

* OpenAI
* ChatGPT
* Claude
* Gemini
* another AI analysis service

The app has:

* read-only access to the Home Assistant configuration directory
* access to Home Assistant and Supervisor APIs required for the audit
* writable access to its own private app configuration/storage area

HA Audit does not modify Home Assistant configuration.

Sensitive and unrelated areas are excluded from normal YAML scanning.

Files with `secret` in the filename are excluded.

`secrets.yaml` is therefore not read by the configuration scanners.

---

# 29. Current limitations

HA Audit is under active development.

Version 0.7.x does not yet:

* produce a final human-friendly Core update recommendation
* provide equivalent deep readiness analysis for Home Assistant OS
* maintain persistent Repair history
* perform comprehensive recurring Home Assistant log analysis
* run audits on a schedule
* expose native HA Audit status sensors
* provide an Ingress/web dashboard
* automatically send reports to an AI service
* inspect every possible UI-managed Home Assistant configuration surface
* automatically repair configuration
* automatically delete stale entities

These are limitations, not assumptions that the missing evidence is safe.

---

# 30. Important safety rule

Treat HA Audit as an **investigation assistant**, not an automatic cleanup tool.

A finding means:

> check this

not necessarily:

> delete this

Likewise, an upgrade report showing no obvious local match does not by itself mean:

> definitely safe to update

When changing Home Assistant configuration:

1. understand the finding
2. verify the evidence
3. make the smallest appropriate change
4. validate where appropriate
5. rerun HA Audit
6. confirm the result

When reviewing a Core update:

1. confirm the evidence collectors completed
2. review relevant Repairs
3. review official release evidence
4. review locally relevant matches
5. note any incomplete or unavailable evidence
6. do not treat absence of evidence as proof of compatibility

---

# 31. What HA Audit is trying to achieve

HA Audit is intended to make Home Assistant maintenance understandable without hiding the evidence behind the result.

The long-term aim is for a user to be able to answer questions such as:

* Is my Home Assistant configuration healthy?
* What should I investigate first?
* Are unavailable entities expected or suspicious?
* Is old configuration still referenced?
* What changed in the Core update I am considering?
* Does that change appear relevant to my installation?
* Is important evidence missing?
* What should I review before making a change?

The technical reports exist to support those answers.

The normal user experience should become simpler as the project develops, not more complicated.

---

# Version

Current release: **0.7.18**
