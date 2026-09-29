# HA Audit

HA Audit is a read-only health, configuration, and upgrade-readiness auditing app for Home Assistant.

It helps you understand what needs attention, investigate configuration problems, review unavailable entities, and assess a pending Home Assistant Core update using evidence from the actual installation.

HA Audit does not automatically change Home Assistant.

The intended workflow is:

**run → read → investigate → act → rerun**

## What HA Audit provides

HA Audit currently includes:

- a concise Home Assistant health overview
- Home Assistant Core, Supervisor, and OS information
- Core update guidance with evidence-collection status
- pending Core and OS update visibility
- official Home Assistant Core release and breaking-change evidence
- local compatibility and upgrade-impact checks
- Home Assistant configuration validation
- YAML configuration and active include-tree analysis
- missing include and missing entity-reference candidates
- duplicate automation and script checks
- device and entity inventory
- unavailable and unknown entity analysis
- availability classification and Recorder-history context
- conservative checks for entities no longer currently provided by integrations
- comparison with the previous audit
- suggested next actions
- detailed JSON evidence reports
- a vendor-neutral AI / LLM handoff for further analysis

## Start with the overview

Each audit produces a top-level summary designed to answer the important questions first.

For example:

```text
OVERVIEW
----------------------------------------------------------
Home Assistant health:       NEEDS ATTENTION
Core update:                 NO KNOWN BLOCKERS FOUND
OS update:                   UPDATE AVAILABLE
Core evidence collection:    COMPLETE
Config check:                VALID
```

`WHY THIS RESULT` then explains the main evidence behind those headline results.

General Home Assistant health and Core update guidance are intentionally kept separate. An unavailable device, for example, does not automatically mean that a Core update is unsafe.

## Core upgrade readiness

When a Home Assistant Core update is pending, HA Audit can combine:

- the installed and target Core versions
- Home Assistant Repairs context
- official Home Assistant release evidence
- backward-incompatible change information
- local integration and configuration evidence
- deterministic compatibility-reference checks where available
- dynamic local correlation
- evidence-completeness checks

The result is conservative guidance based on the evidence HA Audit inspected.

A result such as:

```text
Core update: NO KNOWN BLOCKERS FOUND
```

does **not** guarantee that an update cannot cause a problem.

## Availability and history

HA Audit does not assume that an unavailable entity is faulty.

Unavailable entities can be classified as:

- **partial availability** — the device still has healthy entities while some entities are unavailable
- **whole device unavailable** — no healthy state entities are currently available for that device
- **ungrouped unavailable** — the entity is not attached to a device

Recorder history is used as observational context only.

Recent, old, or absent usable history does not by itself prove that an entity is faulty, stale, or safe to remove.

## AI / LLM handoff

Every audit also generates:

```text
ha_audit_ai_handoff.md
```

This is a concise, vendor-neutral handoff designed for analysis by AI assistants such as ChatGPT, Claude, Gemini, local LLMs, or other compatible systems.

The handoff includes selected health, update-readiness, configuration, availability, history, and next-action evidence together with instructions that tell the receiving AI to:

- distinguish HA Audit evidence from its own inference
- avoid claiming that an update is guaranteed safe
- avoid recommending destructive cleanup solely because something is unavailable or not currently provided
- explain uncertainty and missing evidence
- prioritise actionable findings over informational context

HA Audit does **not** automatically send this file to an AI service.

The user decides whether and where to share it.

## Installation

In Home Assistant:

1. Go to **Settings → Apps**
2. Open the App Store
3. Open the App Store menu and choose **Repositories**
4. Add:

   `https://github.com/pnm1977/home-assistant-ha-audit`

5. Find **HA Audit**
6. Install it

HA Audit is currently run manually rather than continuously.

## Running an audit

1. Go to **Settings → Apps → HA Audit**
2. Select **Start**
3. Wait for HA Audit to finish
4. Open the **Log** tab
5. Find the latest:

   `HA AUDIT vX.X.X - CURRENT RUN SUMMARY`

Start with:

- `OVERVIEW`
- `WHY THIS RESULT`
- `NEXT ACTIONS`

Only move into the technical evidence sections when you need more detail.

## Generated files

HA Audit stores its reports in its own app-config folder.

Important files include:

- `audit_snapshot.json`
- `audit_snapshot_previous.json`
- `config_inventory.json`
- `quality_audit.json`
- `not_provided_reference_audit.json`
- `recorder_health_audit.json`
- `not_provided_history_audit.json`
- `availability_audit.json`
- `unavailable_history_audit.json`
- `update_readiness_audit.json`
- `upgrade_impact_audit.json`
- `upgrade_compatibility_audit.json`
- `release_evidence_audit.json`
- `compatibility_coverage_audit.json`
- `upgrade_correlation_audit.json`
- `correlation_validation_audit.json`
- `ha_audit_latest.txt`
- `ha_audit_ai_handoff.md`

`ha_audit_latest.txt` contains the latest user-facing summary.

`ha_audit_ai_handoff.md` contains the concise AI / LLM analysis handoff.

If your Home Assistant file-access tool can browse `/addon_configs`, open the folder whose name ends in `_ha_audit`.

## Safety and privacy

HA Audit is designed to be read-only.

It does not modify Home Assistant configuration or automatically delete entities.

Home Assistant configuration is mounted read-only.

Sensitive locations such as `.storage` are excluded from configuration scanning, and files with `secret` in their filename — including `secrets.yaml` — are not read by the configuration scanners.

HA Audit does not automatically send audit data to OpenAI, ChatGPT, Claude, Gemini, GitHub, or another external analysis service.

The AI / LLM handoff remains local until the user chooses to share it.

## Project status

HA Audit is under active development.

Current areas include:

- Home Assistant health auditing
- configuration quality
- availability and Recorder-history context
- Core upgrade readiness
- AI / LLM-assisted investigation
- easier long-term Home Assistant maintenance

See the app's **User Guide** for practical instructions and the **Changelog** for development history.
