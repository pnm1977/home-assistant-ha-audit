# HA Audit — User Guide

HA Audit is a read-only Home Assistant health and configuration auditing app.

It is designed to help you work through Home Assistant maintenance systematically:

**run → read → investigate → act → rerun**

HA Audit does not automatically repair or delete anything.

---

# 1. Running HA Audit

HA Audit currently runs manually.

In Home Assistant:

1. Go to **Settings → Apps**
2. Open **HA Audit**
3. Select **Start**
4. Wait for the app to finish
5. Open the **Log** tab

HA Audit stops automatically when the audit is complete.

A successful run ends with:

```text
HA Audit finished
```

The `s6-rc` shutdown messages that appear afterwards are part of the app stopping and are not HA Audit findings.

---

# 2. Finding the latest run

The Home Assistant app log may contain several previous HA Audit runs.

Each new run therefore has a clearly marked section:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

Look for the **last occurrence** of this heading in the Log tab.

That is the audit you should use.

The summary is designed to be much shorter than the detailed audit data so repeated test/fix/rerun cycles are easier to follow.

HA Audit also writes:

```text
ha_audit_latest.txt
```

This file is overwritten on every run so there is always a clean copy of the latest summary in HA Audit's private app storage.

The detailed JSON reports are also retained, but normal use should begin with the **CURRENT RUN SUMMARY** in the app log.

---

# 3. How to read the summary

Work through the summary from top to bottom.

The main sections are:

```text
SYSTEM
CONFIGURATION
ENTITY HEALTH
REVIEW
NEXT ACTIONS
DETAILED REPORTS
```

Do not assume that every non-zero number is a fault.

Some values are inventory or review information rather than errors.

The **NEXT ACTIONS** section is the most important part after a run.

A useful workflow is:

1. Confirm the audit completed correctly
2. Check whether Home Assistant configuration is valid
3. Review any configuration findings
4. Review entity-health findings
5. Read **NEXT ACTIONS**
6. Pick one issue or category
7. Investigate it in the location HA Audit gives you
8. Make the smallest appropriate change
9. Rerun HA Audit
10. Confirm the expected count or finding changed

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

If it is not `VALID`, do not restart Home Assistant simply to see whether the configuration works.

Investigate the configuration problem first.

### Where to check manually

In Home Assistant go to:

**Developer tools → YAML**

Use Home Assistant's configuration validation/restart controls available there.

Also review the **NEXT ACTIONS** section of the HA Audit log.

---

## Updates available

This is the number of Home Assistant `update` entities currently reporting an available update.

It does not mean HA Audit recommends installing them immediately.

### Where to check

Go to:

**Settings → System → Updates**

Review the available Home Assistant and app updates there.

---

## Collector errors

The preferred result is:

```text
Collector errors: 0
```

If this is greater than zero, part of the audit did not complete correctly.

### What to do

Stay in:

**Settings → Apps → HA Audit → Log**

Look above the summary for:

```text
ERROR
```

or:

```text
failed
```

HA Audit deliberately prints the captured output from a scanner when that scanner fails.

Fix the audit collection problem before relying on that section of the report.

---

# 5. CONFIGURATION

Example:

```text
CONFIGURATION
----------------------------------------------------------
Active YAML files:          135
Missing active includes:    0
Missing entity candidates:  0
Orphan YAML candidates:     0
Duplicate automation IDs:   0
Duplicate automation names: 0
Duplicate script names:     0
```

---

## Active YAML files

This is an inventory count.

It is the number of YAML files HA Audit found in the active Home Assistant include tree.

There is no target number.

A change may simply mean that configuration files were added, removed, merged or reorganised.

---

## Missing active includes

The preferred result is:

```text
Missing active includes: 0
```

A non-zero value means active YAML points to a file or directory that HA Audit could not find.

### Where to investigate

Open **Studio Code Server** or your normal Home Assistant configuration editor.

Use the source file and line reported by HA Audit to find the relevant include.

Typical Home Assistant include syntax looks like:

```yaml
!include filename.yaml
```

or:

```yaml
!include_dir_merge_list directory/
```

Check whether:

- the target still exists
- the path is correct
- the file was renamed or moved
- the include is obsolete

After correcting the configuration, rerun HA Audit and confirm:

```text
Missing active includes: 0
```

---

## Missing entity candidates

The preferred result is:

```text
Missing entity candidates: 0
```

These are entity IDs referenced in active YAML that HA Audit could not match to a current Home Assistant entity.

They are **candidates**, not automatically confirmed errors.

### Where to investigate the entity

Go to:

**Settings → Devices & services → Entities**

Search for the complete entity ID.

If the entity does not exist, inspect the YAML location reported by HA Audit.

### Where to investigate the YAML

Open **Studio Code Server**.

Open the file and line reported by HA Audit.

Determine whether the reference:

- contains a typo
- uses an old entity ID
- refers to something that was removed
- should be replaced with a current entity
- should itself be removed

After making the change, use Home Assistant's configuration validation where appropriate and rerun HA Audit.

The goal is normally:

```text
Missing entity candidates: 0
```

---

## Orphan YAML candidates

An orphan candidate is a YAML file found by HA Audit that is not part of the active Home Assistant include tree and has not been classified as a known blueprint, Zigbee2MQTT file or backup/archive file.

This does not automatically mean the file should be deleted.

### Where to investigate

Open **Studio Code Server** and locate the reported file.

Check whether it is:

- an old unused configuration file
- an intentional backup
- documentation/reference material
- a file that should actually be included in Home Assistant

If it is no longer required, it can be removed manually.

Rerun HA Audit afterwards.

---

## Duplicate automation IDs

The preferred result is:

```text
Duplicate automation IDs: 0
```

Automation IDs should be unique.

### Where to investigate

Open **Studio Code Server** and search for the duplicate ID reported by HA Audit.

For automations stored in `automations.yaml`, check each occurrence of:

```yaml
id:
```

Do not simply delete one occurrence without checking which automation it belongs to.

---

## Duplicate automation names

This reports duplicate automation aliases/names.

Duplicate names are not necessarily a Home Assistant configuration error, but they make maintenance and troubleshooting harder.

### Where to check

Go to:

**Settings → Automations & scenes → Automations**

Search for the reported automation name.

Also check the relevant YAML if the automation is YAML-managed.

---

## Duplicate script names

This is similar to duplicate automation names.

### Where to check

Go to:

**Settings → Automations & scenes → Scripts**

Search for the reported script name.

Check `scripts.yaml` or the appropriate YAML file where necessary.

---

# 6. ENTITY HEALTH

Example:

```text
ENTITY HEALTH
----------------------------------------------------------
Entities:                   3039
Unavailable:                527
Unknown:                    222
Not currently provided:     245
New unavailable:            0
Recovered unavailable:      5
```

Large non-zero values here do **not** necessarily mean Home Assistant is unhealthy.

The important question is why the entities have those states.

---

## Unavailable

An unavailable entity still exists in Home Assistant but currently has no usable state.

Common causes include:

- powered-off devices
- disconnected devices
- integrations that cannot connect
- retired devices
- temporarily unavailable cloud services
- stale entities

### Where to check

Go to:

**Settings → Devices & services → Entities**

Set the filter:

**Status → Unavailable**

You can then add an **Integration** filter to investigate one group at a time.

For example:

**Integration → Template**

or:

**Integration → MQTT**

Do not bulk-delete unavailable entities just because they appear in this count.

---

## Unknown

An entity with an `unknown` state exists but Home Assistant does not currently have a meaningful value for it.

This can be normal for some entities.

### Where to check

Go to:

**Settings → Devices & services → Entities**

Search for the entity ID or device shown by HA Audit.

Open it and inspect its current state and integration.

---

## New unavailable

This compares the current audit with the previous run.

A value greater than zero means entities have become unavailable since the previous audit.

This is often more useful than the total unavailable count because it highlights change.

### What to do

Check the affected entities before assuming they are faults.

For device-based entities, go to:

**Settings → Devices & services → Devices**

Search for the device.

For an individual entity, go to:

**Settings → Devices & services → Entities**

Search for the entity ID.

---

## Recovered unavailable

These entities were unavailable during the previous audit but are no longer unavailable.

This is normally informational.

A rising recovered count after maintenance is often evidence that the change had the intended effect.

---

# 7. NOT CURRENTLY PROVIDED

This is different from ordinary `Unavailable`.

A registry entity can remain stored in Home Assistant even when its integration no longer currently creates or provides that entity.

HA Audit compares the enabled Home Assistant entity registry with the entities currently being supplied by integrations.

Example:

```text
Not currently provided: 245
```

This is a **review list**, not a deletion list.

Possible reasons include:

- an integration no longer exposing an old entity
- a device or integration being removed
- an integration changing its entity model
- old registry entries being retained
- an integration currently failing to load

Therefore:

**Not currently provided does not automatically mean safe to delete.**

---

# 8. REVIEW

Example:

```text
REVIEW
----------------------------------------------------------
Not provided + active YAML: 1
Template cleanup candidates: 29
```

This section narrows the larger inventory into findings that deserve attention.

---

## Not provided + active YAML

This is one of the more important findings.

It means:

1. Home Assistant still has the entity in its registry
2. its integration is not currently providing it
3. HA Audit found the entity ID referenced in active YAML

### What to do

Do **not** delete the entity first.

Use the file and line information reported by HA Audit and open that location in **Studio Code Server**.

Determine why the YAML still expects the entity.

Possible actions include:

- replacing an old entity ID
- correcting a typo
- removing obsolete YAML
- restoring the missing integration or device if it is still required

After changing the YAML, validate the configuration where appropriate and rerun HA Audit.

---

# 9. TEMPLATE CLEANUP CANDIDATES

A Template cleanup candidate is an entity that:

1. remains in Home Assistant's entity registry
2. is no longer currently provided by the Template integration
3. has no reference found in the active YAML files scanned by HA Audit

This is a much stronger cleanup signal, but it is still not an automatic deletion instruction.

### Where to check

In Home Assistant go to:

**Settings → Devices & services → Entities**

Set:

**Status → Unavailable**

Then set:

**Integration → Template**

Open the candidate entity.

For a stale Template entity, Home Assistant may display:

```text
This entity is no longer being provided by the template integration.
If the entity is no longer in use, delete it in settings.
```

### Before deleting

Confirm:

- HA Audit reports no active YAML reference
- you recognise the entity as obsolete
- Home Assistant says it is no longer provided
- you do not intentionally need it for something outside the active YAML scanned by HA Audit

If those checks are satisfied, use Home Assistant's **Delete** option on the entity screen.

### After deleting

Run HA Audit again.

Confirm that:

- the total entity count falls by one
- the Template `Unavailable` count falls if the entity was unavailable
- the Template cleanup candidate count falls by one

This rerun is an important part of the cleanup process.

---

# 10. A USEFUL EXAMPLE: UNAVAILABLE DOES NOT MEAN STALE

Suppose a Template entity is unavailable because the physical equipment it depends on has been unplugged.

Home Assistant may still actively provide the Template entity.

In that situation HA Audit should show it under:

```text
Unavailable
```

but **not** classify it as:

```text
Not currently provided
```

That entity should not be deleted simply because it is unavailable.

This is why HA Audit keeps the two categories separate.

---

# 11. NEXT ACTIONS

After checking the headline numbers, read the:

```text
NEXT ACTIONS
```

section.

This is intended to turn audit findings into practical investigation steps.

Entries beginning with:

```text
[!]
```

need attention.

Entries beginning with:

```text
[i]
```

are informational or cleanup/review opportunities.

Work through these findings one category at a time.

There is no benefit in trying to clear every non-zero count in one session.

---

# 12. RECOMMENDED CLEANUP WORKFLOW

A practical maintenance session is:

1. Go to **Settings → Apps → HA Audit**
2. Start HA Audit
3. Open the **Log** tab
4. Find the latest **CURRENT RUN SUMMARY**
5. Confirm **Config check = VALID**
6. Confirm **Collector errors = 0**
7. Review the **NEXT ACTIONS** section
8. Pick one finding or category
9. Follow the Home Assistant or Studio Code location given for that finding
10. Make only the intended change
11. Validate Home Assistant configuration where appropriate
12. Run HA Audit again
13. Confirm the expected count changed
14. Continue with the next finding only when ready

Repeated reruns are expected.

That is one reason HA Audit keeps the normal console output concise.

---

# 13. DETAILED REPORTS

HA Audit generates detailed reports as well as the short summary shown in the app log.

Current files include:

```text
audit_snapshot.json
audit_snapshot_previous.json
config_inventory.json
quality_audit.json
not_provided_reference_audit.json
ha_audit_latest.txt
```

`ha_audit_latest.txt` contains the latest user-facing summary and is overwritten on every run.

The JSON files contain the detailed data used by HA Audit and are useful when a finding tells you to inspect a particular report.

## Where to find the files

The files are stored in HA Audit's own app-config folder rather than your normal Home Assistant configuration folder.

In **Studio Code Server**:

1. Select **File → Open Folder...**
2. Enter:

```text
/addon_configs
```

3. Open the folder whose name ends with:

```text
_ha_audit
```

Inside that folder you should see the HA Audit report files.

For example:

```text
ha_audit_latest.txt
quality_audit.json
not_provided_reference_audit.json
```

The part of the folder name before `_ha_audit` is generated by Home Assistant and may differ between installations.

## Returning to your previous files

Opening `/addon_configs` changes the folder/workspace shown by Studio Code Server.

When you have finished reviewing HA Audit reports:

1. Select **File → Open Recent**
2. Reopen the folder or workspace you were using previously

If it is not shown in **Open Recent**:

1. Select **File → Open Folder...**
2. Choose the folder you were using before

HA Audit does not assume that your previous workspace was a particular folder.

## Which report should I start with?

For normal use, start with:

**Settings → Apps → HA Audit → Log**

and read the latest:

```text
CURRENT RUN SUMMARY
```

Use the detailed files only when the summary or **NEXT ACTIONS** section directs you to them.

For example:

```text
Not provided + active YAML: 1
```

may direct you to:

```text
not_provided_reference_audit.json
```

where the affected entity, YAML file and line number can be identified.

The detailed reports are primarily investigation data; you do not need to read every JSON file after every audit.

---

# 14. CONFIGURATION INVENTORY

HA Audit scans the Home Assistant YAML configuration using read-only access.

It records information including:

- YAML file count
- YAML line count
- configuration layout
- largest YAML files
- include relationships
- exact duplicate YAML files
- `!secret` usage

File contents are not copied into the inventory report.

---

# 15. COMMENTED BACKUP CONFIGURATION

Fully commented-out YAML is not treated as active configuration.

This is deliberate.

Users may retain previous versions of templates, automations or other configuration as commented blocks for rollback or reference.

HA Audit therefore ignores fully commented lines when checking active entity references.

A high proportion of comments can still be reported as informational inventory.

It is not automatically considered a problem.

---

# 16. LARGE AUTOMATIONS AND SCRIPTS

HA Audit can identify unusually large automation and script definitions.

This is informational.

A large automation is not automatically wrong.

The purpose is to identify configuration that may be worth reviewing later for maintainability.

Do not split or rewrite working automations purely because HA Audit labels them as large.

---

# 17. SECURITY AND PRIVACY

HA Audit currently operates locally.

It does not send audit information to OpenAI, ChatGPT, GitHub or another external analysis service.

The app has:

- read-only access to the Home Assistant configuration directory
- access to Home Assistant and Supervisor information APIs
- writable access only to its own private app configuration/storage area

HA Audit does not modify Home Assistant configuration.

The following locations are deliberately excluded from YAML scanning:

- `.storage`
- `.cloud`
- backups
- `custom_components`
- ESPHome configuration
- media
- TTS
- `www`

Files with `secret` in the filename are also excluded.

`secrets.yaml` is therefore not read by the configuration scanners.

---

# 18. CURRENT LIMITATIONS

HA Audit is under active development.

It does not currently:

- automatically repair problems
- automatically delete stale entities
- fully analyse Home Assistant Repairs
- provide complete Home Assistant Core log analysis
- perform scheduled automatic audits
- send reports to OpenAI
- assess Home Assistant release notes against the installation
- provide a graphical HA Audit dashboard

These are areas that may be developed later.

---

# 19. IMPORTANT SAFETY RULE

Treat HA Audit as an **investigation assistant**, not an automatic cleanup tool.

A finding means:

> check this

not necessarily:

> delete this

When changing Home Assistant configuration:

1. understand the finding
2. verify it in Home Assistant or the relevant YAML
3. make the smallest appropriate change
4. validate where appropriate
5. rerun HA Audit
6. confirm the result

---

# Version

Current release: **0.6.5**
