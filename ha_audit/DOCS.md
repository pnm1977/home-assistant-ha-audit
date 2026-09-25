# HA Audit

HA Audit is a read-only Home Assistant system and configuration auditor.

It is designed to help understand, maintain, troubleshoot, and improve a Home Assistant installation over time.

## How to use

HA Audit is currently designed to run manually.

1. Open **Settings → Apps → HA Audit**
2. Click **Start**
3. Wait for the audit to complete
4. Open the **Log** tab
5. Review the audit summary

The app stops automatically after the audit finishes.

## What HA Audit checks

### System health

HA Audit records:

- Home Assistant Core version
- Supervisor version
- Home Assistant OS version
- entity count
- device count
- unavailable entities
- unknown entities
- pending updates
- automation count
- script count
- Home Assistant configuration validation result

Unavailable and unknown entities are grouped by integration/platform and device.

HA Audit also compares the current result with the previous run so newly unavailable and recovered entities can be identified.

## Configuration inventory

HA Audit scans the Home Assistant YAML configuration using read-only access.

It records:

- YAML file count
- YAML line count
- configuration layout
- largest YAML files
- include relationships
- exact duplicate YAML files
- use of `!secret`

File contents are not copied into the inventory report.

## Configuration Quality Audit

HA Audit follows the active YAML include tree starting from `configuration.yaml`.

This allows it to distinguish between YAML that Home Assistant is actively loading and YAML files that merely exist in the configuration directory.

It checks for:

- active YAML files
- unreferenced YAML files
- missing active YAML include targets
- duplicate automation IDs
- duplicate automation aliases
- duplicate script aliases
- unusually large automations
- unusually large scripts
- references to entity IDs that are not currently present in Home Assistant
- active YAML files containing a high proportion of comments

Missing entity references are reported as candidates for review rather than automatically being treated as faults.

### Commented backup configuration

Commented-out YAML is not treated as active configuration.

This is intentional because older versions of templates or automations may be retained as commented blocks for rollback or reference.

Fully commented lines are therefore ignored when checking active entity references.

## Security and privacy

HA Audit is currently entirely local.

It does not send audit information to OpenAI, ChatGPT, GitHub, or any other external service.

The app has:

- read-only access to the Home Assistant configuration directory
- access to Home Assistant and Supervisor information APIs
- writable access only to its own private app configuration directory

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

## Files generated

HA Audit stores its reports inside its own private app storage.

Current reports include:

- `audit_snapshot.json`
- `audit_snapshot_previous.json`
- `config_inventory.json`
- `quality_audit.json`

These files are not written into the main Home Assistant configuration directory.

## Current limitations

HA Audit is still under active development.

HA Audit does not yet:

- modify Home Assistant
- automatically repair problems
- analyse Home Assistant Repairs
- provide complete Home Assistant Core log analysis
- send reports to OpenAI
- perform scheduled automatic audits
- assess Home Assistant release notes against the installed configuration
- automatically identify deprecated YAML syntax
- automatically assess third-party integration compatibility

These are planned future capabilities.

## Project goal

The long-term goal of HA Audit is to provide a structured technical view of a Home Assistant installation so that maintenance, upgrades, troubleshooting, migration planning, and future-proofing can be based on the actual system rather than generic advice.
