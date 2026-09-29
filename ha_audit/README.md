# HA Audit

HA Audit is a read-only Home Assistant health, configuration and upgrade-readiness auditing app.

It is designed to help Home Assistant users understand what needs attention before making changes, cleaning up old configuration, or installing a Core update.

The normal workflow is:

**run → review → investigate → act → rerun**

HA Audit does not automatically repair, delete or rewrite your Home Assistant configuration.

---

## What HA Audit checks

HA Audit combines several areas of Home Assistant health and maintenance into one audit.

### System and installation

HA Audit collects information including:

* Home Assistant Core version
* Home Assistant OS version
* Supervisor information
* available updates
* device and entity inventory
* changes compared with the previous audit

### Entity health

HA Audit looks for:

* unavailable entities
* unknown entities
* devices where only some entities are unavailable
* whole devices that appear unavailable
* entities no longer currently provided by an integration
* Recorder/history evidence that can help explain availability findings

An unavailable entity is not automatically a fault or a cleanup candidate.

HA Audit deliberately keeps observation separate from conclusions.

### Configuration and YAML

HA Audit checks for:

* Home Assistant configuration validation
* YAML file inventory
* active include-tree discovery
* missing active includes
* missing entity reference candidates
* references to entities that are no longer currently provided
* duplicate automation IDs
* duplicate automation names
* duplicate script names
* large automations and scripts
* inactive or unreferenced YAML
* exact duplicate files
* Template cleanup candidates

Commented-out backup or rollback configuration is not treated as active configuration.

---

## Core upgrade readiness

HA Audit can also collect and correlate evidence for a pending Home Assistant Core update.

It can:

* identify the installed and target Core versions
* collect official Home Assistant release evidence
* identify breaking-change groups for the target release
* compare those changes with the integrations and configuration present locally
* identify locally relevant upgrade-impact evidence
* dynamically correlate official release information with the local installation
* use optional deterministic compatibility references for additional precision
* report whether supporting evidence is complete, partial, unavailable or not applicable
* preserve uncertainty where the available evidence does not justify a stronger conclusion

The deterministic compatibility reference is optional.

A future Core release can therefore still be assessed when no hand-maintained reference exists. In that situation HA Audit reports that no reference is available rather than treating the assessment as failed.

### Current limitation

HA Audit 0.7.x builds the evidence needed to assess a Core update, but it does **not yet produce a final recommendation that an update is safe to install**.

The current upgrade-readiness system is intended to answer questions such as:

* What Core update is pending?
* What changed in that release?
* Are any of those changes relevant to this installation?
* Is there evidence that something should be reviewed first?
* Is any part of the assessment incomplete?

Core readiness is currently more developed than Home Assistant OS readiness.

---

## How to run HA Audit

In Home Assistant:

1. Go to **Settings → Apps**
2. Open **HA Audit**
3. Select **Start**
4. Wait for the audit to finish
5. Open the **Log** tab

HA Audit is a run-once app and stops automatically when the audit is complete.

A successful run ends with:

```text
HA Audit finished
```

Messages from `s6-rc` shown after this are part of the app shutting down and are not HA Audit findings.

---

## Reading the results

Start with the section headed:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

The summary is intended to be the normal starting point.

It brings together the most useful findings from the detailed audit reports, including:

* installation and version context
* configuration health
* entity health
* Recorder/history context
* pending updates
* Core upgrade-readiness evidence
* findings that deserve further review
* collector or evidence limitations

Do not assume that every non-zero count represents a problem.

HA Audit intentionally uses conservative wording where the available evidence does not support a definite conclusion.

---

## Latest-run report

HA Audit writes a latest-run summary:

```text
ha_audit_latest.txt
```

This file is replaced on each run so the most recent audit can be reviewed without searching through previous app logs.

HA Audit also creates detailed JSON reports containing the evidence used by the summary.

These reports are primarily intended for:

* deeper investigation
* troubleshooting
* development and testing
* future tooling
* structured analysis

Normal use should begin with the **CURRENT RUN SUMMARY**.

See **[DOCS.md](DOCS.md)** for detailed report locations and investigation guidance.

---

## Important result types

### Unavailable

An unavailable entity still exists in Home Assistant but currently has no usable state.

Possible causes include:

* a powered-off device
* a temporarily unavailable integration
* maintenance
* connectivity problems
* an intentionally offline device
* a retired device
* stale configuration

Do not delete an entity simply because it is unavailable.

### Not currently provided

This means an entity remains in Home Assistant's entity registry but its integration is not currently providing it.

This can be useful evidence when investigating stale configuration, but it is not automatic proof that the entity should be deleted.

### Not provided + active YAML

This means an entity that is no longer currently provided is still referenced by active YAML.

That reference should be investigated before removing the entity.

### Cleanup candidates

HA Audit can identify stronger cleanup candidates where several pieces of evidence agree.

Even these remain review candidates rather than automatic deletion instructions.

The aim is to make cleanup safer, not faster at the expense of evidence.

---

## Safety

HA Audit is designed to be read-only.

It does not:

* modify Home Assistant configuration
* delete entities
* change devices
* repair findings automatically
* install Home Assistant updates

The Home Assistant configuration is mounted read-only.

Sensitive configuration locations such as `.storage` are excluded from YAML scanning.

Files with `secret` in the filename, including `secrets.yaml`, are not read by the configuration scanners.

HA Audit does not currently send audit data to OpenAI, ChatGPT, Claude, Gemini or another external AI analysis service.

---

## Platform support

HA Audit currently supports:

```text
amd64
```

Additional architecture support may be considered in future.

---

## Documentation

For practical guidance on:

* understanding audit findings
* investigating configuration issues
* reviewing unavailable entities
* interpreting upgrade-readiness evidence
* locating detailed reports
* verifying changes after a fix

see:

**[HA Audit User Guide](DOCS.md)**

For release history see:

**[CHANGELOG.md](CHANGELOG.md)**

---

## Project status

HA Audit is under active development.

The current foundation covers:

* Home Assistant health
* configuration quality
* YAML auditing
* stale entity investigation
* availability and Recorder evidence
* Core upgrade-readiness evidence
* conservative maintenance guidance

Future development will focus on making the results easier to understand and act on while retaining the underlying technical evidence.

The goal is simple:

**help Home Assistant users understand what needs attention, why it matters, and what evidence supports it.**
