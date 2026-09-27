# HA Audit

HA Audit is a read-only health and configuration auditing app for Home Assistant.

It is designed to help you understand, maintain, troubleshoot, and gradually improve a Home Assistant installation without automatically changing anything.

The intended workflow is:

**run → read → investigate → act → rerun**

## Current capabilities

HA Audit currently provides:

- Home Assistant Core, Supervisor, and OS information
- device and entity inventory
- unavailable and unknown entity analysis
- comparison with the previous audit
- update detection
- Home Assistant configuration validation
- YAML configuration inventory
- active YAML include-tree discovery
- detection of unreferenced YAML
- missing include detection
- missing entity reference candidates
- duplicate automation ID checks
- duplicate automation alias checks with live Home Assistant state context
- duplicate script alias checks
- large automation and script detection
- detection of registry entities no longer currently provided by integrations
- active-YAML reference checks for not-currently-provided entities
- Recorder-history context for not-currently-provided entities
- availability classification for ordinary unavailable entities
- Recorder-history context for ordinary unavailable entities
- a concise current-run summary with suggested next actions
- detailed JSON reports for deeper investigation

## Availability context

HA Audit does not assume that an unavailable entity is faulty.

Unavailable entities are classified using their current device context, for example:

- **partial availability** — the device still has healthy entities while some secondary entities are unavailable
- **whole device unavailable** — no healthy state entities are currently available for that device
- **ungrouped unavailable** — the entity is not attached to a device

Optional Home Assistant labels can also be used to add expected-offline or maintenance context, but labels are not required.

HA Audit does not ask users to create or maintain these labels as part of the normal workflow.

## Recorder history

Recorder history is used as observational context only.

For ordinary unavailable entities, HA Audit can record:

- whether usable history exists within the effective Recorder window
- the final usable state
- when that final usable state began
- when it ended, where a following unavailable/unknown transition proves the end
- whether no usable state was returned
- whether the history query failed

The requested lookback is up to 90 days, but HA Audit respects the actual Recorder history available on the Home Assistant installation.

Old, recent, or absent usable history does not by itself indicate a fault, stale entity, configuration problem, or required action.

## Duplicate automation aliases

Duplicate automation IDs remain structural findings because automation IDs should be unique.

Duplicate automation aliases/names are treated differently.

HA Audit cross-checks duplicate aliases against live Home Assistant automation states:

- aliases shared by two or more currently-on automations are surfaced as maintainability findings
- disabled or mixed-state duplicate aliases remain available in the detailed report without being promoted as normal health findings
- unresolved live states are reported separately
- HA Audit does not guess from names such as `Old`, `Backup`, or similar wording

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

## First run

After installation:

1. Go to **Settings → Apps → HA Audit**
2. Select **Start**
3. Wait for HA Audit to finish
4. Open the **Log** tab
5. Find the latest:

   `HA AUDIT vX.X.X - CURRENT RUN SUMMARY`

Start with:

- `Config check`
- `Collector errors`
- configuration findings
- `ENTITY HEALTH`
- `AVAILABILITY CONTEXT`
- `UNAVAILABLE HISTORY CONTEXT`
- `REVIEW`
- `NOT-PROVIDED HISTORY SAFETY`
- `NEXT ACTIONS`

Do not assume that every non-zero value is a fault.

## Detailed reports

HA Audit stores its reports in its own app-config folder.

Current reports include:

- `audit_snapshot.json`
- `audit_snapshot_previous.json`
- `config_inventory.json`
- `quality_audit.json`
- `not_provided_reference_audit.json`
- `recorder_health_audit.json`
- `not_provided_history_audit.json`
- `availability_audit.json`
- `unavailable_history_audit.json`
- `ha_audit_latest.txt`

`ha_audit_latest.txt` is overwritten on each run and contains the latest concise summary.

If your Home Assistant file-access tool can browse `/addon_configs`, open the folder whose name ends in `_ha_audit`.

## Safety

HA Audit is designed to be read-only.

It does not modify Home Assistant configuration or automatically delete entities.

Home Assistant configuration is mounted read-only.

Sensitive locations such as `.storage` are excluded from configuration scanning, and files with `secret` in their filename — including `secrets.yaml` — are not read by the configuration scanners.

HA Audit currently does not send audit data to OpenAI, ChatGPT, GitHub, or another external analysis service.

## Status

HA Audit is under active development.

The current focus is:

- Home Assistant system health
- configuration quality
- availability context
- safe stale-configuration discovery
- update and upgrade readiness
- easier maintenance
- long-term future-proofing

See the app's **User Guide** for current usage instructions and **Changelog** for release history.
