# HA Audit

HA Audit is a read-only Home Assistant health and configuration auditing app.

It is designed to help you understand what is happening inside a Home Assistant installation, identify things worth reviewing, and work through maintenance safely.

The intended workflow is:

**run → read → investigate → act → rerun**

HA Audit does not automatically repair, delete or rewrite anything.

---

## What HA Audit checks

HA Audit currently includes checks for:

- Home Assistant Core, Supervisor and OS versions
- device and entity inventory
- unavailable entities
- unknown entities
- entities no longer currently provided by integrations
- active-YAML references to not-currently-provided entities
- Template cleanup candidates
- Home Assistant configuration validation
- YAML file inventory
- active include-tree discovery
- missing includes
- missing entity reference candidates
- duplicate automation IDs
- duplicate automation names
- duplicate script names
- large automations and scripts
- comparison with the previous audit
- available updates

It also creates detailed JSON reports for deeper investigation.

---

## How to run HA Audit

In Home Assistant:

1. Go to **Settings → Apps**
2. Open **HA Audit**
3. Select **Start**
4. Wait for the audit to finish
5. Open the **Log** tab

HA Audit stops automatically when the run is complete.

A successful run ends with:

```text
HA Audit finished
```

The `s6-rc` messages shown afterwards are part of the app shutting down and are not HA Audit findings.

---

## What to look at after a run

Find the latest section headed:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

Work through these sections:

```text
SYSTEM
CONFIGURATION
ENTITY HEALTH
REVIEW
NEXT ACTIONS
```

Start by checking:

```text
Config check
Collector errors
Missing active includes
Missing entity candidates
Not currently provided
Not provided + active YAML
Template cleanup candidates
```

Then read:

```text
NEXT ACTIONS
```

This section is intended to tell you what deserves attention and, where possible, where to go in Home Assistant or Studio Code Server to investigate it.

Do not assume that every non-zero value is a fault.

---

## Latest-run summary

HA Audit also writes:

```text
ha_audit_latest.txt
```

This file is overwritten on every run.

That means repeated test/fix/rerun cycles do not require you to scroll through a long history of previous results to find the latest summary.

The normal Home Assistant app log is also kept concise so repeated runs are easier to follow.

---

## Important result types

### Unavailable

An entity still exists in Home Assistant but currently has no usable state.

This may be caused by:

- a powered-off device
- an unplugged device
- a temporarily unavailable integration
- a retired device
- stale configuration

Do not delete something simply because it is unavailable.

---

### Not currently provided

The entity still exists in Home Assistant's registry, but its integration is not currently providing it.

This is stronger evidence of stale configuration, but it is still only a review signal.

Possible causes include:

- an old entity left behind after an integration changed
- a removed device
- an integration that is currently failing
- a registry entry that is no longer needed

---

### Not provided + active YAML

This means HA Audit found an entity that:

1. is no longer currently provided
2. is still referenced in active YAML

This should be investigated before deleting the entity.

HA Audit reports the relevant file and line information in the detailed reference report.

---

### Template cleanup candidates

These are Template entities that:

1. remain in the Home Assistant entity registry
2. are no longer currently provided by the Template integration
3. have no active YAML reference found by HA Audit

These are stronger cleanup candidates, but they should still be checked manually in Home Assistant before deletion.

To review them:

1. Go to **Settings → Devices & services → Entities**
2. Set **Status → Unavailable**
3. Set **Integration → Template**
4. Open the entity
5. Check whether Home Assistant says:

```text
This entity is no longer being provided by the template integration.
If the entity is no longer in use, delete it in settings.
```

Only delete it after confirming it is genuinely obsolete.

---

## After making a change

Rerun HA Audit.

Check that the expected count changed.

For example, after deleting one stale Template entity, you would normally expect:

- the total entity count to fall by one
- the Template unavailable count to fall if that entity was unavailable
- the Template cleanup candidate count to fall by one

This confirmation step is part of the normal workflow.

---

## Full user guide

For detailed explanations of every section, including:

- what each result means
- where to check it in Home Assistant
- what to do next
- what not to delete blindly
- how to investigate YAML findings
- how to verify a fix

see:

**[HA Audit User Guide](DOCS.md)**

---

## Detailed reports

HA Audit currently produces:

```text
audit_snapshot.json
audit_snapshot_previous.json
config_inventory.json
quality_audit.json
not_provided_reference_audit.json
ha_audit_latest.txt
```

The JSON files are intended for deeper investigation and future tooling.

Normal use should begin with the **CURRENT RUN SUMMARY** in the Home Assistant app log.

---

## Safety

HA Audit is designed to be read-only.

It does not:

- modify Home Assistant configuration
- delete entities
- change devices
- repair findings automatically

Home Assistant configuration is mounted read-only.

Sensitive locations such as `.storage` are excluded from YAML scanning.

Files with `secret` in the filename, including `secrets.yaml`, are not read by the configuration scanners.

HA Audit currently does not send audit data to OpenAI, ChatGPT, GitHub or another external analysis service.

---

## Current status

HA Audit is under active development.

Current focus areas include:

- system health
- configuration quality
- stale entity and configuration discovery
- update readiness
- safer maintenance
- clearer user guidance

See **[DOCS.md](DOCS.md)** for usage instructions and **[CHANGELOG.md](CHANGELOG.md)** for release history.
