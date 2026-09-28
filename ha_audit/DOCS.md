# HA Audit User Guide

HA Audit is a read-only Home Assistant system and configuration auditor.

It is designed to help you investigate system health, configuration quality, entity availability and maintenance issues using evidence from the actual Home Assistant installation.

The normal workflow is:

**run → read → investigate → act → rerun**

HA Audit does not automatically repair Home Assistant or decide that an entity, device or configuration file should be deleted.

Its job is to collect evidence and make investigation easier.

---

# 1. Running HA Audit

HA Audit is currently designed to run manually.

In Home Assistant:

1. Open **Settings → Apps**
2. Select **HA Audit**
3. Click **Start**
4. Wait for the audit to complete
5. Open the **Log** tab

A successful run ends with:

```text
HA Audit finished
```

HA Audit is a run-once app.

After the audit has completed, the app stops automatically.

This is expected behaviour.

---

## s6-rc shutdown messages

After:

```text
HA Audit finished
```

you may see messages from `s6-rc` as the app container shuts down.

These are normal container shutdown messages.

They are not HA Audit findings.

Only investigate them if there is an actual error before:

```text
HA Audit finished
```

or if one of the audit stages reports a failure.

---

# 2. Finding the latest run

Each run contains a clearly marked section:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

If the log contains several previous runs, use the final occurrence.

HA Audit also writes:

```text
ha_audit_latest.txt
```

This file is overwritten on every run.

It contains only the latest concise user-facing summary.

This can be easier to use than scrolling through a long app log containing several audits.

---

# 3. Reading the current-run summary

The summary contains sections such as:

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

The summary is intentionally shorter than the underlying JSON reports.

Its purpose is to tell you:

* whether the audit completed correctly
* whether Home Assistant configuration is valid
* what changed since the previous audit
* which findings deserve investigation
* where to find more detailed evidence

Do not assume that every non-zero number represents a problem.

Some values are:

* inventory
* context
* change detection
* review candidates
* informational findings

rather than faults.

---

## Recommended reading order

For a normal run:

1. Check `Config check`
2. Check `Collector errors`
3. Review `CONFIGURATION`
4. Review `ENTITY HEALTH`
5. Review `AVAILABILITY CONTEXT`
6. Review `UNAVAILABLE HISTORY CONTEXT`
7. Review `REVIEW`
8. Review `NOT-PROVIDED HISTORY SAFETY`
9. Read `NEXT ACTIONS`
10. Open detailed JSON reports only where useful

The preferred starting results are:

```text
Config check:               VALID
Collector errors:           0
```

---

# 4. SYSTEM

The `SYSTEM` section normally includes:

```text
Core
Supervisor
OS
Config check
Updates available
Collector errors
```

---

## Core

This shows the currently installed Home Assistant Core version.

It is inventory information.

HA Audit does not currently decide whether a particular Core release should be installed.

Upgrade-readiness analysis is planned as a later development area.

---

## Supervisor

This shows the installed Home Assistant Supervisor version.

Again, this is currently inventory information rather than an automatic recommendation.

---

## OS

This shows the installed Home Assistant OS version where that information is available.

---

## Config check

The preferred result is:

```text
Config check:               VALID
```

HA Audit uses Home Assistant's own configuration validation.

If the result is not valid, investigate the configuration before restarting Home Assistant.

Home Assistant's own configuration validation controls are available under:

**Developer tools → YAML**

A failed configuration check is more important than a cosmetic or informational audit finding.

---

## Updates available

This is the number of Home Assistant `update` entities currently reporting an available update.

It does not mean HA Audit recommends installing every available update immediately.

Review updates under:

**Settings → System → Updates**

The future update-readiness work is intended to add more useful context around updates rather than simply count them.

---

## Collector errors

The preferred result is:

```text
Collector errors:           0
```

A collector error means part of HA Audit did not complete correctly.

When a scanner stage fails, HA Audit attempts to print the captured output from that stage in the app log.

Do not rely on the affected report until the collection problem is understood.

For example, if a history scanner fails, absence of history in that failed report must not be interpreted as evidence about an entity.

---

# 5. CONFIGURATION

The `CONFIGURATION` section contains findings from the YAML inventory and configuration-quality scanners.

Typical fields include:

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

---

# 6. Active YAML files

HA Audit begins with:

```text
configuration.yaml
```

and follows the active include tree.

Files discovered through active includes are treated as active configuration.

This provides a more useful view than treating every `.yaml` file under `/config` as active.

---

## Why the active tree matters

A Home Assistant installation can contain YAML that is deliberately retained but no longer loaded.

Examples include:

* old configuration
* backups
* reference files
* migration copies
* retired packages
* commented rollback versions

HA Audit therefore distinguishes between:

* YAML that belongs to the active configuration tree
* YAML that exists but is not part of the active tree

This reduces false findings.

---

# 7. Commented rollback and reference configuration

HA Audit is designed to tolerate commented-out rollback material.

Fully commented YAML is not treated as active configuration when performing checks such as:

* active entity-reference analysis
* active automation duplicate checks
* active include analysis

This allows you to retain commented backup blocks without them being treated as currently running configuration.

A commented line can still contribute to overall file size or comment-density information, but it should not create an active configuration finding.

---

# 8. Missing active includes

A missing active include means a file in the active YAML tree references another file or directory that HA Audit could not find.

The summary may show:

```text
Missing active includes:    1
```

The detailed evidence is stored in:

```text
quality_audit.json
```

under the configuration-tree information.

---

## Investigating a missing include

Use the reported:

* source file
* source line
* include target

Open that location in your Home Assistant configuration.

For example, if the report says that:

```text
integrations/binary_sensors.yaml
```

references a missing target, inspect the exact include statement at the reported line.

Check for:

* a typo in the path
* an incorrect relative path
* a renamed file
* a deleted file
* a directory/include-type mismatch
* a deliberately retired include that should be removed

---

## Do not create a file just to clear the warning

The correct fix depends on the intended configuration.

Sometimes the right action is to restore a missing file.

Sometimes the right action is to remove or correct the include.

HA Audit does not choose between those possibilities automatically.

---

# 9. Missing entity candidates

HA Audit scans active YAML for Home Assistant entity IDs.

It compares those references with the current Home Assistant entity inventory.

A missing entity candidate means HA Audit found an entity reference in active YAML that it could not match to a current entity.

For example:

```text
Missing entity candidates:  3
```

does not automatically mean there are three confirmed broken automations.

---

## Why a candidate may be reported

Possible explanations include:

* the entity was renamed
* the entity was removed
* the integration creating it is currently unavailable
* configuration still refers to an old entity
* the scanner cannot fully resolve a dynamic construction
* the reference is genuinely broken

The detailed report includes the YAML location so the exact usage can be investigated.

---

## Investigating a missing entity candidate

First inspect:

```text
quality_audit.json
```

and find the reported:

* entity ID
* YAML file
* line number
* reference location

Then check Home Assistant under:

**Settings → Devices & services → Entities**

Search for the entity.

If it is not present, check whether:

* it has been renamed
* a replacement entity exists
* the integration is loaded
* the device still exists
* the YAML reference is still needed

---

## Do not perform blind replacements

An entity with a similar name is not automatically the correct replacement.

Check what the automation, script, template or configuration is supposed to do before changing the reference.

---

# 10. Unreferenced and orphan YAML

HA Audit records YAML files that are not part of the active include tree.

It separates known categories where possible.

These may include:

* blueprints
* Zigbee2MQTT configuration
* backup/archive material
* other inactive YAML
* orphan candidates

---

## Orphan YAML candidates

An orphan candidate is a YAML file that HA Audit could not associate with the active configuration tree or a known excluded category.

This is a review finding.

It is not a deletion recommendation.

---

## Investigating an orphan YAML file

Before removing anything:

1. Open the file
2. Identify what it contains
3. Search active configuration for its filename
4. Check whether it is intentionally retained
5. Check whether it is documentation or rollback material
6. Check whether another external process uses it
7. Only remove it when you understand its purpose

A file being inactive does not mean it has no value.

---

# 11. Duplicate automation IDs

Home Assistant automation IDs should be unique.

A duplicate automation ID is therefore a structural configuration finding.

The summary reports the number of duplicate ID groups.

Detailed information is stored in:

```text
quality_audit.json
```

---

## Investigating duplicate automation IDs

Review the reported:

* automation alias
* automation ID
* YAML file
* source line

Determine which automation should retain the existing ID.

If both automations are genuinely active, one should normally receive a new unique ID.

Do not change an ID merely because two automation aliases are similar.

Automation ID and automation alias are different concepts.

---

# 12. Duplicate automation aliases

Duplicate automation aliases or names are not automatically errors.

Two automations can legally share the same alias.

This may happen intentionally when:

* a previous version is retained
* a rollback copy is disabled
* an old version is kept temporarily
* two different automations happen to have the same descriptive name

HA Audit therefore treats duplicate aliases differently from duplicate IDs.

---

## Live-state-aware duplicate checking

From 0.6.10, HA Audit cross-checks duplicate automation aliases against the live Home Assistant automation states.

The normal health summary surfaces duplicate alias groups when:

* two or more matching automations are currently `on`
* the live state cannot be fully resolved

Disabled or mixed-state duplicate aliases remain available in the detailed report but are not promoted as normal routine health findings.

---

## Why this matters

Suppose two automations are both called:

```text
Music 2.0 - Check Queue - Old
```

but both are intentionally disabled rollback copies.

Static YAML inspection alone can see that the aliases are duplicated.

It cannot establish whether both automations are actually active.

The live-state cross-check prevents deliberately disabled rollback copies from creating unnecessary routine warnings.

---

## HA Audit does not guess from names

HA Audit does not assume that an automation is inactive because its alias contains words such as:

```text
Old
Backup
Previous
Test
Disabled
```

Names are descriptive text.

The live Home Assistant automation state is used instead.

---

## Active duplicate alias groups

If two or more matching automations are currently on, the summary may report:

```text
Active duplicate auto names: 1
```

This is a maintainability finding.

It is not the same as an automation-ID collision.

Review:

```text
quality_audit.json
```

and decide whether the duplicated active aliases are intentional.

---

## Unresolved duplicate aliases

If HA Audit cannot confidently resolve the live state of every member of a duplicate alias group, it is reported separately.

For example:

```text
Unresolved duplicate names:  1
```

Review the detailed report rather than assuming the group is either active or harmless.

---

# 13. Duplicate script names

Script aliases can also be duplicated.

This is normally a maintainability finding rather than proof of invalid Home Assistant configuration.

Review the detailed report where necessary.

---

# 14. Large automations and scripts

HA Audit identifies unusually large automation and script definitions.

Large does not automatically mean bad.

A long automation can be entirely appropriate.

These findings identify configuration that may:

* be harder to read
* be harder to maintain
* contain repeated logic
* benefit from future refactoring

There is no requirement to reduce every large automation or script.

---

# 15. ENTITY HEALTH

The `ENTITY HEALTH` section contains current entity-state information.

Typical fields include:

```text
Entities
Unavailable
Unknown
Not currently provided
New unavailable
Recovered unavailable
```

---

# 16. Total entities

This is the number of entities included in the current audit view.

It provides context for the unavailable and unknown counts.

The absolute number can change as integrations add, remove or restructure entities.

---

# 17. Unavailable entities

An unavailable entity exists in Home Assistant but currently has no usable state.

An unavailable entity is not automatically a failed device.

Possible causes include:

* deliberately powered-off equipment
* temporary Wi-Fi loss
* temporary Zigbee loss
* MQTT devices that are offline
* battery-powered devices
* cloud-service availability
* integration reconnects
* equipment under maintenance
* optional feature entities
* unsupported feature entities
* genuinely failed hardware
* stale entities

Do not bulk-delete unavailable entities based on the headline count.

---

# 18. Unknown entities

An entity with state:

```text
unknown
```

exists but Home Assistant does not currently have a meaningful value for it.

Some integrations legitimately expose unknown states under certain conditions.

As with unavailable entities, use context rather than treating the count itself as a fault total.

---

# 19. New unavailable and recovered unavailable

HA Audit compares the current audit with the previous audit.

This allows it to report:

```text
New unavailable
Recovered unavailable
```

These changes are often more useful than the total unavailable count.

A long-standing intentionally powered-off device is less interesting than a device that was healthy in the previous audit and has just become unavailable.

---

## Investigating new unavailable entities

If the count is non-zero:

1. Open the detailed snapshot or availability report
2. Identify the newly unavailable entity
3. Identify the device and integration
4. Check whether the change is expected
5. Check whether the device still has healthy sibling entities
6. Check Recorder history where useful
7. Only escalate when the evidence suggests a genuine problem

---

# 20. AVAILABILITY CONTEXT

The raw unavailable count cannot distinguish between:

* a completely offline device
* a healthy device with one unavailable optional feature
* deliberately powered-off equipment
* an entity not attached to a device

`availability_audit.json` adds that context.

---

## Not-currently-provided entities are excluded

Entities already classified as not currently provided are excluded from ordinary availability classification.

They have their own:

* active-YAML reference analysis
* Recorder-history safety analysis

This avoids mixing two different review categories.

---

# 21. Partial availability

A device has partial availability when:

* one or more entities are unavailable
* at least one other current entity belonging to the device is healthy

For example, a robot vacuum may have:

* a healthy main vacuum entity
* a healthy battery entity
* healthy consumable sensors
* unavailable notification or optional-cleaning feature entities

Calling that entire vacuum "unavailable" would be misleading.

HA Audit therefore records it as partial availability.

---

## How to investigate partial availability

Ask:

1. What is the main function of this device?
2. Is its primary entity healthy?
3. Which entities are unavailable?
4. Are those unavailable entities optional?
5. Have they ever had usable Recorder history?
6. Did an integration update introduce them?
7. Does Home Assistant normally expose them for this device model?

Partial availability is often feature-level context rather than a device fault.

---

# 22. Whole-device unavailable

A device is classified as whole-device unavailable when HA Audit sees no healthy current state entities belonging to that device.

The summary may show:

```text
Whole device unavailable:   5 entities / 1 device
```

This is observational context.

It is not an automatic fault verdict.

---

## Possible explanations

A whole-device unavailable result may represent:

* deliberately powered-off equipment
* temporary maintenance
* building work
* a Wi-Fi outage
* a Zigbee device that has stopped responding
* an MQTT device that is disconnected
* a cloud integration outage
* a battery issue
* genuinely failed equipment

The next useful evidence is often Recorder history.

---

# 23. Ungrouped unavailable entities

Some unavailable entities are not attached to a Home Assistant device.

These are reported separately.

The detailed report can show:

* entity ID
* platform
* name
* area where available

Review the entity individually because device-level context is unavailable.

---

# 24. Optional availability labels

HA Audit supports optional Home Assistant labels for users who want to add explicit context.

Examples supported by the scanner include expected-offline and maintenance context.

These labels are optional.

You do not need to maintain them for HA Audit to work.

---

## Missing labels are not a health issue

HA Audit does not:

* require users to create availability labels
* count missing labels as a fault
* prompt for routine label maintenance in `NEXT ACTIONS`

This keeps the normal workflow low-maintenance.

Users who find labels useful can use them.

Users who do not want to maintain them can ignore them.

---

# 25. UNAVAILABLE HISTORY CONTEXT

`unavailable_history_audit.json` adds Recorder evidence to ordinary currently unavailable entities.

Its purpose is to answer questions such as:

* Has this entity had a usable state recently?
* When did its final usable interval begin?
* Can Recorder show when that interval ended?
* Has Recorder only seen it as unavailable?
* Is there no Recorder history for it?
* Did the history query itself fail?

---

# 26. Requested and effective history windows

The requested lookback is:

```text
90 days
```

HA Audit also checks how much Recorder history is actually available.

If Recorder only retains approximately 34 days, HA Audit uses that available window.

The summary therefore distinguishes between:

* requested lookback
* Recorder history start
* effective history checked

HA Audit does not claim to have checked history that Home Assistant no longer retains.

---

# 27. Matching history to the availability snapshot

The availability scanner records when its current-state snapshot was taken.

The unavailable-history scanner uses that timestamp as the history endpoint.

This is important.

Without it, an entity could:

1. be classified as unavailable
2. recover a few seconds later
3. appear as healthy in history collected after the availability snapshot

That would mix two different points in time.

Using the availability snapshot timestamp keeps the evidence aligned.

---

# 28. Usable states

For unavailable-history analysis, these states are treated as non-usable:

```text
unavailable
unknown
none
```

Other states can provide evidence that the entity was usable.

Examples might include:

```text
on
off
idle
playing
23.4
Task finished, returning to dock
```

depending on the entity type.

---

# 29. unavailable-history statuses

An unavailable entity receives one of these statuses:

```text
usable_history_found
history_found_no_usable_state
no_history_returned
history_query_failed
```

These statuses describe the Recorder evidence.

They are not fault classifications.

---

# 30. usable_history_found

This means Recorder returned at least one usable state during the effective history window.

HA Audit records fields such as:

```text
last_usable_state
last_usable_state_started_at
last_usable_state_ended_at
```

---

## last_usable_state

This is the final usable state found in the retained history.

For example:

```text
off
```

or:

```text
idle
```

---

## last_usable_state_started_at

This records when the final usable state began.

It should not automatically be interpreted as the time the entity became unavailable.

A device may remain in the same state for hours or days.

---

## last_usable_state_ended_at

Where Recorder contains a later non-usable transition, HA Audit records that transition as the end of the final usable interval.

For example:

```text
off
```

may have started on Monday.

The device may remain healthy and `off` until Friday.

If it becomes:

```text
unavailable
```

on Friday, the relevant loss-of-usability time is Friday, not Monday.

This distinction was added to prevent misleading history interpretation.

---

## Unknown end time

If the history window contains a usable state but no later non-usable transition, HA Audit cannot prove when that usable interval ended.

It does not invent an end timestamp.

---

# 31. history_found_no_usable_state

This means Recorder returned history records, but every usable candidate in the effective history window was:

```text
unavailable
unknown
none
```

This can legitimately happen.

For example:

* an optional feature entity may have always been unavailable
* a deliberately unpowered device may already have been offline when retained Recorder history begins
* Recorder retention may no longer include its earlier healthy period

This status does not prove that the entity has always been faulty.

---

# 32. no_history_returned

This means Recorder returned no history records for the entity.

Possible reasons include:

* Recorder exclusions
* retention
* entity-specific history behaviour
* the entity being newer than expected
* the integration not recording useful state history

No history is unknown evidence.

It is not approval to delete an entity.

---

# 33. history_query_failed

This means HA Audit could not successfully retrieve Recorder history for the entity.

Query failure must remain separate from:

```text
no_history_returned
```

because a failed request is not evidence that history does not exist.

---

## Batch query retry protection

HA Audit requests unavailable history in batches for efficiency.

If a batch request fails:

1. the batch failure is recorded
2. each entity in that batch is retried individually
3. entities whose individual retry succeeds continue normally
4. only genuine individual failures remain `history_query_failed`

This prevents one problematic batch request from incorrectly making every entity in that batch appear to have failed history collection.

---

# 34. Interpreting unavailable history

Recorder history is observational context only.

Old, recent or absent usable history does not by itself indicate:

* a broken device
* a stale entity
* a configuration problem
* an entity that should be deleted
* a required action

Use history together with:

* current availability classification
* integration
* device type
* known power state
* normal usage pattern
* whether the device is deliberately offline

---

# 35. REVIEW

The `REVIEW` section currently includes stronger configuration/entity review findings such as:

```text
Not provided + active YAML
Template review candidates
```

These are different from ordinary unavailable entities.

---

# 36. NOT CURRENTLY PROVIDED

A not-currently-provided entity is an entity that remains in the Home Assistant entity registry but is not currently present in the live entity source information collected by HA Audit.

This is different from:

```text
state = unavailable
```

An unavailable entity is currently provided but has no usable state.

A not-currently-provided entity is not currently being created or exposed in the live source used by the audit.

---

## Possible explanations

A not-currently-provided entity may result from:

* an integration changing its entity model
* a removed device
* an integration that failed to load
* an entity being removed by an integration update
* old registry data
* a configuration change
* a genuinely stale entity

It is therefore a review category rather than a deletion list.

---

# 37. Active-YAML references to not-currently-provided entities

HA Audit cross-references not-currently-provided entities with the active YAML configuration tree.

The detailed report is:

```text
not_provided_reference_audit.json
```

If an entity is both:

* not currently provided
* still referenced by active YAML

it deserves stronger investigation.

---

## Why this matters

Deleting the entity from Home Assistant without checking its active references may leave:

* automations
* scripts
* templates
* conditions
* service calls
* other YAML configuration

pointing to an entity that no longer exists.

---

## Investigation workflow

For each reported entity:

1. Find the entity in `not_provided_reference_audit.json`
2. Note the reported source file and line
3. Open that YAML location
4. Understand what the reference is doing
5. Search Home Assistant for the entity ID
6. Check whether a replacement entity exists
7. Check the integration/device involved
8. Decide whether to repair the reference, restore the entity or retire the configuration

Do not delete first and investigate afterwards.

---

# 38. Template review candidates

A Template entity can be a stronger cleanup candidate when it is:

* no longer currently provided
* not referenced by active YAML

HA Audit can identify these as Template review candidates.

The summary may show:

```text
Template review candidates: 1
```

This still does not mean automatic deletion.

---

## Investigating a Template review candidate

In Home Assistant:

1. Go to **Settings → Devices & services → Entities**
2. Search for the entity ID
3. Check its integration
4. Check whether it belongs to **Template**
5. Check whether it is unavailable
6. Check whether another entity replaced it
7. Check whether it appears in dashboards or UI-created automations
8. Check Recorder evidence where useful

HA Audit currently analyses active YAML references.

It cannot guarantee that an entity is unused everywhere in every UI-managed object simply because no YAML reference exists.

Use the result as a review aid.

---

# 39. NOT-PROVIDED HISTORY SAFETY

HA Audit uses Recorder history as protective evidence for entities that are no longer currently provided.

The detailed report is:

```text
not_provided_history_audit.json
```

History is used conservatively.

Its purpose is to prevent recent evidence from being overlooked during cleanup review.

---

# 40. Requested lookback

The requested history lookback is:

```text
90 days
```

The effective lookback is limited by actual Recorder retention.

The summary shows the amount of history that could actually be checked.

---

# 41. Recent/protective usable history

If a not-currently-provided entity has usable history whose final usable interval ended within the recent window, that is protective evidence.

The normal recent window is:

```text
45 days
```

These entities should be treated as:

```text
KEEP / REVIEW
```

rather than easy cleanup candidates.

---

# 42. Final usable interval semantics

From 0.6.10, HA Audit distinguishes between:

```text
last_usable_state_started_at
```

and:

```text
last_usable_state_ended_at
```

where Recorder contains enough evidence.

This prevents an important timing error.

---

## Example

Suppose an entity changed to:

```text
off
```

60 days ago.

It stayed healthy and `off` until yesterday.

Yesterday it stopped being provided.

Using the start of the `off` state as the "last usable" time would make the entity look 60 days old.

That would be misleading.

The useful evidence is that its final usable interval continued until yesterday.

---

# 43. Unknown final-interval end

Sometimes Recorder shows a usable state but contains no later non-usable transition.

In that case HA Audit cannot prove when the final usable interval ended.

It does not assume that the interval ended when it began.

Instead, that history remains conservatively protective.

---

## Why the conservative rule exists

HA Audit is designed to avoid unsafe cleanup conclusions.

It is better to retain an entity for manual review than to call it old based on incomplete evidence.

---

# 44. Older usable activity

An entity is only classified as older activity when Recorder can prove that the final usable interval ended before the recent-history cutoff.

Older usable activity can support a cleanup investigation.

It is still not automatic permission to delete.

---

# 45. No usable history

If no usable history is found in the effective Recorder window, the summary may report:

```text
No usable history found
```

This means only that no usable evidence was found in the retained history that was checked.

Possible limitations include:

* Recorder retention
* Recorder exclusions
* earlier activity outside the retained window

No usable history is not proof that an entity is obsolete.

---

# 46. History query failure

If history collection fails, the entity is not treated as though it has no history.

The failure is reported separately.

Review the collector issue before using the history result in a cleanup decision.

---

# 47. NEXT ACTIONS

`NEXT ACTIONS` converts the strongest current findings into practical investigation prompts.

It does not list every piece of inventory.

---

## `[!]` entries

An entry beginning with:

```text
[!]
```

normally represents something requiring attention.

Examples include:

* invalid configuration
* collector failure
* missing active include
* missing active entity reference candidate
* duplicate automation ID
* history query failure
* not-currently-provided entity still referenced by active YAML

---

## `[i]` entries

An entry beginning with:

```text
[i]
```

is normally informational or a review opportunity.

Examples include:

* whole-device unavailable context
* partial availability
* ungrouped unavailable entities
* recent/protective history
* Template review candidates
* orphan YAML candidates

---

## Informational does not mean irrelevant

An `[i]` result may still deserve investigation.

It simply means the audit does not have enough evidence to present it as a definite fault.

---

## Do not force NEXT ACTIONS to zero

A healthy Home Assistant installation may legitimately retain informational findings.

The goal is:

* understand them
* remove false positives where the scanner can be improved
* act on genuine issues

rather than forcing every count to zero.

---

# 48. DETAILED REPORTS

HA Audit stores detailed reports in its private app-config folder.

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
ha_audit_latest.txt
```

---

# 49. audit_snapshot.json

Contains the detailed current Home Assistant audit snapshot.

This includes core system and entity-health information collected during the run.

---

# 50. audit_snapshot_previous.json

Contains the previous snapshot retained for selected run-to-run comparisons.

This allows HA Audit to identify changes such as:

```text
New unavailable
Recovered unavailable
```

---

# 51. config_inventory.json

Contains the YAML configuration inventory.

It includes information such as:

* discovered YAML files
* active/inactive classification
* line counts
* include relationships

---

# 52. quality_audit.json

Contains detailed configuration-quality findings.

These include areas such as:

* configuration tree
* missing include targets
* missing entity reference candidates
* duplicate automation IDs
* duplicate automation aliases
* live-state classification of duplicate automation aliases
* duplicate script names
* large automations
* large scripts

Use this file when the summary points to a YAML/configuration issue.

---

# 53. not_provided_reference_audit.json

Contains reference analysis for not-currently-provided entities.

It identifies whether those entities are still referenced in active YAML.

---

# 54. recorder_health_audit.json

Contains information about Recorder history availability.

This allows history scanners to distinguish between:

```text
requested history window
```

and:

```text
history actually retained
```

---

# 55. not_provided_history_audit.json

Contains protective Recorder-history evidence for not-currently-provided entities.

It includes final usable state information and the recent/older/no-history classifications.

---

# 56. availability_audit.json

Contains device-level classification for ordinary currently unavailable entities.

This includes categories such as:

* expected offline where explicitly labelled
* maintenance where explicitly labelled
* partial availability
* whole-device unavailable
* ungrouped unavailable

It also contains device-state context such as healthy and unavailable sibling entities.

---

# 57. unavailable_history_audit.json

Contains Recorder-history context for ordinary currently unavailable entities.

This includes:

```text
last_recorded_state
last_recorded_state_at
last_usable_state
last_usable_state_started_at
last_usable_state_ended_at
history_status
history_error
```

where appropriate.

---

# 58. ha_audit_latest.txt

Contains the concise current-run summary.

This file is overwritten on every run.

For normal day-to-day use, this is usually the most useful report after the app log.

---

# 59. Finding the detailed reports

The reports are stored in HA Audit's private app-config folder.

They are not stored in the normal:

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

The part before `_ha_audit` is generated by Home Assistant and may differ between installations.

---

## Studio Code Server example

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

You should then see the audit report files.

---

## Returning to your previous workspace

When you finish reviewing the reports:

1. Select **File → Open Recent**
2. Reopen the folder or workspace you were previously using

If it is not listed:

1. Select **File → Open Folder...**
2. Open your normal Home Assistant configuration folder or previous workspace manually

---

# 60. Investigation workflow: missing include

When `NEXT ACTIONS` reports a missing active include:

1. Open `quality_audit.json`
2. Find `configuration_tree`
3. Find the missing include entry
4. Note the source file
5. Note the source line
6. Open that YAML file
7. Check the include syntax
8. Check the target path
9. Decide whether the target should exist or the include should be removed
10. Validate Home Assistant configuration
11. Rerun HA Audit

The finding should disappear after the actual problem is corrected.

---

# 61. Investigation workflow: missing entity candidate

When an active YAML entity reference is missing:

1. Open `quality_audit.json`
2. Find the missing candidate
3. Note the source file and line
4. Open the YAML
5. Understand how the entity is being used
6. Search Home Assistant's entity registry
7. Check whether it was renamed or replaced
8. Correct the YAML only when the intended replacement is known
9. Validate/reload the appropriate configuration
10. Rerun HA Audit

---

# 62. Investigation workflow: duplicate automation ID

When a duplicate automation ID is reported:

1. Open `quality_audit.json`
2. Identify every automation using the ID
3. Open each reported YAML location
4. Determine whether both definitions are intended
5. Give each genuinely separate automation a unique ID
6. Validate/reload
7. Rerun HA Audit

The duplicate-ID group should disappear.

---

# 63. Investigation workflow: duplicate automation alias

When an active duplicate alias is reported:

1. Open `quality_audit.json`
2. Review the automations in the alias group
3. Check their automation IDs
4. Check their current Home Assistant states
5. Confirm whether the matching names are intentional
6. Rename only where clearer naming would improve maintenance

Do not change IDs just because aliases match.

If the duplicate copies are intentionally disabled rollback versions, their presence in detailed audit data is expected.

---

# 64. Investigation workflow: whole-device unavailable

When a device has no healthy state entities:

1. Identify the device in `availability_audit.json`
2. Identify its integration
3. Check whether it is intentionally powered
4. Check physical power where relevant
5. Check Wi-Fi/Zigbee/MQTT/cloud connectivity where relevant
6. Review `unavailable_history_audit.json`
7. Check when the final usable interval ended
8. Compare with known maintenance or building work
9. Decide whether any action is needed

Do not assume that whole-device unavailable means hardware failure.

---

# 65. Investigation workflow: partial availability

When a device has partial availability:

1. Identify its healthy entities
2. Identify its unavailable entities
3. Determine which entities represent the device's primary function
4. Determine whether unavailable entities are optional or diagnostic
5. Review Recorder history if useful
6. Check whether an integration update recently changed the entity set
7. Act only if unavailable features should actually be working

Partial availability often requires no action.

---

# 66. Investigation workflow: not provided + active YAML

When an entity is both not currently provided and still referenced:

1. Open `not_provided_reference_audit.json`
2. Identify every active reference
3. Open the source YAML
4. Search Home Assistant for the entity
5. Check its integration/device
6. Check Recorder history
7. Determine whether the entity has been renamed, replaced or removed
8. Repair the reference or restore the entity as appropriate
9. Rerun HA Audit

This is a stronger finding than a not-currently-provided entity with no known active references.

---

# 67. Investigation workflow: Template review candidate

For a Template review candidate:

1. Search the entity under **Settings → Devices & services → Entities**
2. Confirm the integration is Template
3. Check whether it is currently unavailable
4. Check `not_provided_reference_audit.json`
5. Check `not_provided_history_audit.json`
6. Search your dashboards or UI-managed automations if appropriate
7. Confirm it has genuinely been replaced or retired
8. Delete only after confirming it is no longer needed
9. Rerun HA Audit

---

# 68. Investigation workflow: history query failure

If history queries fail:

1. Check `Collector errors`
2. Check the HA Audit app log
3. Open the relevant history JSON
4. Identify the entity and `history_error`
5. Check whether failures affected a whole batch or only individual entities
6. Do not interpret failed queries as no history
7. Resolve the collection issue where possible
8. Rerun HA Audit

---

# 69. Investigation workflow: orphan YAML

For an orphan YAML candidate:

1. Open the file
2. Identify its purpose
3. Search the active configuration for its path/name
4. Check whether it is an intentional rollback/reference file
5. Check whether it belongs to an external tool
6. Decide whether to keep, archive or remove it
7. Rerun HA Audit if its status should change

---

# 70. Repeated audit/fix/rerun cycles

HA Audit is designed to be run repeatedly.

A typical maintenance cycle is:

1. Run HA Audit
2. Pick one clear finding
3. Investigate it
4. Make the smallest appropriate change
5. Validate Home Assistant where necessary
6. Rerun HA Audit
7. Confirm the expected result changed
8. Move to the next finding

This is safer than trying to clean dozens of findings at once.

---

# 71. Verify the result, not just the edit

After making a change, do not assume success because the YAML saved correctly.

Check:

* Home Assistant configuration validation
* relevant entity/device behaviour
* HA Audit summary
* detailed report if appropriate

For example:

* a missing entity reference should disappear
* a duplicate automation ID should disappear
* a recovered device may move out of unavailable
* a retired entity may disappear from the registry-related review list

---

# 72. SAFETY

HA Audit is designed to be read-only.

It does not:

* modify Home Assistant configuration
* delete entities
* remove devices
* disable entities
* alter integrations
* change automations
* change scripts
* install Home Assistant updates
* restart Home Assistant
* automatically apply cleanup changes

---

# 73. Configuration access

Home Assistant configuration is mounted read-only for the audit app.

HA Audit reads configuration in order to inspect it.

It does not write changes back into Home Assistant configuration.

---

# 74. Report storage

HA Audit writes its generated reports only to its own private app-config directory.

These reports are the output of the audit.

They are separate from the Home Assistant configuration files being inspected.

---

# 75. Sensitive configuration exclusions

Configuration scanning excludes sensitive or unrelated areas such as:

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

Files whose filename contains:

```text
secret
```

are excluded from configuration scanning.

This includes:

```text
secrets.yaml
```

HA Audit therefore does not need to read Home Assistant secret values to perform its normal configuration analysis.

---

# 76. External services

HA Audit currently performs its audit locally inside the Home Assistant app environment.

It does not currently send audit data to:

* OpenAI
* ChatGPT
* GitHub
* another external AI analysis service

Future AI-assisted analysis is planned as a separate optional development stage.

It is not part of the current local audit.

---

# 77. TROUBLESHOOTING

## The app stops after running

This is normal.

HA Audit is a run-once app.

Check for:

```text
HA Audit finished
```

The app stops after completing its work.

---

## I see s6-rc messages

This is normal after the audit completes.

They are container shutdown messages.

If:

```text
HA Audit finished
```

appears cleanly first, the shutdown messages themselves are not an audit problem.

---

## I see a shell or Python error before HA Audit finished

This is different.

Review the error and identify which stage failed.

The summary may also show a collector error or missing report.

Do not rely on an affected report until the run is clean.

---

## Collector errors is non-zero

Example:

```text
Collector errors:           1
```

Review the HA Audit app log.

The failed stage should be identified.

HA Audit normally captures scanner output and shows it when a stage fails.

---

## Config check is not VALID

Do not restart Home Assistant merely to see whether the problem clears.

Use:

**Developer tools → YAML**

to validate and investigate the configuration first.

---

## I cannot find the report files

Browse:

```text
/addon_configs
```

and open the folder ending:

```text
_ha_audit
```

They are not stored in the normal `/config` directory.

---

## The app log contains several runs

Use the final:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

section.

Alternatively open:

```text
ha_audit_latest.txt
```

which contains only the latest summary.

---

## The unavailable count is very high

Do not assume the number represents failed devices.

Review:

```text
AVAILABILITY CONTEXT
```

A large total can come from integrations exposing many:

* optional entities
* feature entities
* diagnostics
* controls that are not supported by a particular device

Then review:

```text
unavailable_history_audit.json
```

where more context is needed.

---

## A whole device is unavailable but I know it is powered off intentionally

That can be a valid result.

Whole-device unavailable means HA Audit saw no healthy state entities at that audit snapshot.

It does not claim to know why.

No fix is required if the state is intentional.

Optional labels can be used if you want explicit expected-offline context, but maintaining them is not required.

---

## An entity shows history_found_no_usable_state

This means Recorder returned history but no state other than:

```text
unavailable
unknown
none
```

was found during the retained window.

It does not prove the entity has never worked.

Recorder may no longer retain its earlier healthy period.

---

## Recorder history is much shorter than 90 days

This is expected when your Home Assistant Recorder retention is shorter.

HA Audit reports:

* requested lookback
* actual Recorder start
* effective history checked

Only the available history is analysed.

---

## No history was returned

Do not treat this as evidence that the entity is stale.

Possible causes include:

* Recorder exclusion
* retention
* entity-specific history behaviour

The result is unknown context.

---

## A duplicate automation name disappeared from NEXT ACTIONS

From 0.6.10, duplicate aliases are checked against live automation state.

If duplicate copies are disabled or mixed-state, they can remain in the detailed report without being promoted as a routine health finding.

This is intentional.

Duplicate automation IDs remain structural findings regardless of alias state.

---

## A report is missing

If a report expected for the current version is absent, check:

* the app log
* collector errors
* whether the relevant scanner failed

The summary should not silently treat a missing report as clean evidence.

---

# 78. Current limitations

HA Audit is under active development.

It does not yet:

* automatically repair Home Assistant
* analyse all Home Assistant Repairs
* perform complete Core log analysis
* automatically run on a schedule
* assess every release note against the installed configuration
* automatically assess all third-party integration compatibility
* make configuration changes
* send reports to an AI analysis service

---

# 79. Next development areas

The next major development area is update and upgrade readiness.

The aim is to provide more useful information before Home Assistant upgrades, including evidence relevant to:

* breaking changes
* integration compatibility
* configuration risk
* outstanding system issues

Later work is expected to include:

* a structured LLM-ready audit report
* optional AI-assisted analysis
* deeper ongoing health monitoring

---

# 80. Project goal

The long-term goal of HA Audit is to provide a structured technical view of a Home Assistant installation so that:

* maintenance
* troubleshooting
* upgrades
* migration planning
* cleanup
* future-proofing

can be based on evidence from the actual system rather than generic assumptions.

The core principle is:

**collect evidence first, make changes only after review.**
