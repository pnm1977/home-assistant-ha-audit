# HA Audit

HA Audit is a read-only health and configuration auditing app for Home Assistant.

It is designed to help you understand, maintain, troubleshoot and gradually clean up a Home Assistant installation without automatically changing anything.

The intended workflow is:

**run → read → investigate → act → rerun**

---

## Current capabilities

HA Audit currently provides:

- Home Assistant Core, Supervisor and OS information
- device and entity inventory
- unavailable and unknown entity analysis
- detection of registry entities no longer currently provided by integrations
- active-YAML reference checks for not-currently-provided entities
- Template entity cleanup candidates
- comparison with previous audit results
- update detection
- Home Assistant configuration validation
- YAML configuration inventory
- active YAML include-tree discovery
- detection of unreferenced YAML
- missing include detection
- missing entity reference candidates
- duplicate automation ID checks
- duplicate automation and script name checks
- large automation and script detection
- a concise current-run summary with suggested next actions
- detailed JSON reports for deeper investigation

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

5. Find **HA Audit** in the App Store
6. Install it

HA Audit is currently run manually rather than continuously.

---

## First run

After installation:

1. Go to **Settings → Apps → HA Audit**
2. Select **Start**
3. Wait for HA Audit to finish
4. Open the **Log** tab
5. Find the latest:

```text
HA AUDIT vX.X.X - CURRENT RUN SUMMARY
```

Start with these lines:

```text
Config check
Collector errors
Missing active includes
Missing entity candidates
Not currently provided
Not provided + active YAML
Template cleanup candidates
```

Then read the:

```text
NEXT ACTIONS
```

section.

It tells you what needs investigation and, where possible, where to go in Home Assistant or Studio Code Server to check it.

Do not assume that every non-zero value is a fault.

---

## How to use the results

HA Audit is intended to guide investigation rather than automatically decide what should be deleted or changed.

For example:

- an **Unavailable** entity may simply belong to powered-off equipment
- a **Not currently provided** entity may be stale, but could also belong to an integration that has temporarily failed
- a **Template cleanup candidate** has stronger evidence that it may be obsolete, but should still be checked in Home Assistant before deletion
- a **Missing entity candidate** should be checked against the reported YAML location before making changes

After making a change, rerun HA Audit and confirm that the result changed as expected.

### Full user guide

The detailed guide explains:

- what each section of the audit means
- which values deserve attention
- exactly where to check findings in Home Assistant
- how to investigate YAML findings
- when an entity may be a cleanup candidate
- what to check before deleting anything
- how to verify a fix by rerunning the audit

See:

**[HA Audit User Guide](ha_audit/DOCS.md)**

---

## Repeated runs

Repeated audit/fix/rerun cycles are expected.

The normal app log is deliberately kept concise so repeated runs are easier to read.

HA Audit also creates:

```text
ha_audit_latest.txt
```

which is overwritten on every run and contains only the latest summary.

Detailed audit data continues to be stored in JSON reports.

---

## Safety

HA Audit is designed to be read-only.

It does not modify Home Assistant configuration or automatically delete entities.

Home Assistant configuration is mounted read-only.

Sensitive locations such as `.storage` are excluded from configuration scanning, and files with `secret` in their filename — including `secrets.yaml` — are not read by the configuration scanners.

HA Audit currently does not send audit data to OpenAI, ChatGPT, GitHub or another external analysis service.

---

## Status

HA Audit is under active development.

The project is currently focused on:

- Home Assistant system health
- configuration quality
- stale configuration and entity discovery
- update and upgrade readiness
- easier maintenance
- long-term future-proofing

See the **[User Guide](ha_audit/DOCS.md)** for current usage instructions and **[Changelog](ha_audit/CHANGELOG.md)** for release history.
