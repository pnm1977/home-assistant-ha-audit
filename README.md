# HA Audit

**Read-only Home Assistant health, configuration and Core upgrade-readiness auditing.**

HA Audit helps you understand what needs attention in a Home Assistant installation before you start changing configuration, cleaning up old entities, or installing a Core update.

It is intended for Home Assistant users who want a practical **health check**, **configuration audit**, **upgrade check**, and a safer way to investigate issues such as broken YAML, unavailable entities and stale configuration.

The normal workflow is:

**run → review → investigate → act → rerun**

HA Audit does not automatically repair, delete or rewrite your Home Assistant configuration.

---

## What HA Audit checks

### Home Assistant health

* Core, Supervisor and OS information
* pending updates
* device and entity inventory
* unavailable and unknown entities
* partial and whole-device availability
* entities no longer currently provided by integrations
* Recorder/history evidence
* changes compared with the previous audit

### Configuration and YAML

* Home Assistant configuration validation
* active YAML include-tree discovery
* missing includes
* missing entity reference candidates
* active references to entities no longer provided
* duplicate automation IDs
* duplicate automation and script names
* large automations and scripts
* inactive or unreferenced YAML
* exact duplicate files
* Template cleanup/review candidates

Commented-out backup or rollback YAML is not treated as active configuration.

### Core upgrade readiness

When a Home Assistant Core update is pending, HA Audit can:

* identify the installed and target Core versions
* collect official Home Assistant release evidence
* identify breaking-change groups across the upgrade
* compare release changes with the local installation
* identify locally relevant integrations and configuration
* dynamically correlate official changes with local evidence
* use optional deterministic compatibility references for additional precision
* validate dynamic results where reference evidence exists
* report incomplete, unavailable or uncertain evidence rather than hiding it

HA Audit does **not yet produce a final “safe to update” recommendation**.

Version 0.7.x provides the evidence needed to review a Core update while deliberately avoiding stronger conclusions than the evidence supports.

Core readiness is currently more developed than Home Assistant OS readiness.

---

## Installation

In Home Assistant:

1. Go to **Settings → Apps**
2. Open the **App Store**
3. Open the App Store menu and choose **Repositories**
4. Add:

```text
https://github.com/pnm1977/home-assistant-ha-audit
```

5. Find **HA Audit**
6. Install it

HA Audit currently supports:

```text
amd64
```

---

## Running an audit

HA Audit currently runs manually.

After installation:

1. Go to **Settings → Apps → HA Audit**
2. Select **Start**
3. Wait for the audit to finish
4. Open the **Log** tab
5. Find:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

A successful run ends with:

```text
HA Audit finished
```

Start with the summary and then read:

```text
NEXT ACTIONS
```

Do not assume every non-zero count represents a problem.

---

## What the results mean

HA Audit is designed to provide **evidence and context**, not automatic cleanup decisions.

For example:

* an unavailable entity may simply belong to equipment that is powered off
* a whole-device unavailable result does not automatically prove the device is faulty
* an entity no longer provided by an integration may be stale, but may also need further investigation
* active YAML referencing an entity that is no longer provided deserves review before anything is removed
* missing Recorder history does not prove that an entity is safe to delete
* an official Core breaking change does not matter locally if the affected integration or configuration is not present
* lack of an optional deterministic compatibility reference does not mean the upgrade assessment failed

HA Audit deliberately preserves uncertainty when the evidence is incomplete.

---

## Upgrade-readiness evidence

The Core readiness pipeline is built around:

```text
Official Home Assistant release evidence
              ↓
Generic dynamic correlation
              ↓
Local installation evidence
              ↓
Optional deterministic reference
              ↓
Reference validation
```

The deterministic reference is optional.

This allows future Home Assistant releases to use the generic release-evidence and correlation path even when no version-specific rule pack has been created.

---

## Latest report

Each run creates:

```text
ha_audit_latest.txt
```

containing the latest human-readable summary.

HA Audit also produces detailed JSON evidence reports for deeper investigation and development.

Normal users should start with the app log and **CURRENT RUN SUMMARY** rather than browsing the underlying files.

---

## Safety

HA Audit is designed to be read-only.

It does not:

* modify Home Assistant configuration
* delete entities
* change devices
* automatically repair findings
* install Home Assistant updates

Home Assistant configuration is mounted read-only.

Sensitive configuration locations such as `.storage` are excluded from YAML scanning.

Files with `secret` in the filename, including `secrets.yaml`, are not read by the configuration scanners.

HA Audit does not currently send your audit results to OpenAI, ChatGPT, Claude, Gemini or another external AI analysis service.

Public Home Assistant release information may be retrieved when collecting Core upgrade evidence.

---

## Documentation

### User guide

For practical guidance on running HA Audit, understanding findings, investigating unavailable entities and interpreting Core upgrade-readiness evidence:

**[HA Audit User Guide](ha_audit/DOCS.md)**

### Release history

**[Changelog](ha_audit/CHANGELOG.md)**

---

## Project status

HA Audit is under active development.

The current foundation covers:

* Home Assistant health
* configuration quality
* YAML auditing
* availability and Recorder evidence
* stale entity investigation
* Core update and upgrade-readiness evidence

Future work will focus on making the results easier for normal Home Assistant users to understand and act on without losing the detailed evidence underneath.

Planned areas include improved top-level guidance, persistent health evidence, scheduling, native Home Assistant status entities and a more accessible in-Home-Assistant user interface.

---

## Philosophy

HA Audit is intentionally conservative.

A finding means:

**check this**

not automatically:

**delete this**

And an upgrade assessment with no obvious local problem does not automatically mean:

**definitely safe to update**

The aim is to make Home Assistant maintenance safer, clearer and easier to investigate.
