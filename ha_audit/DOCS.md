# HA Audit

HA Audit is a read-only Home Assistant system and configuration auditor.

Version 0.6.0 introduces the first Configuration Quality Audit.

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

HA Audit scans Home Assistant YAML configuration using read-only access.

It records:

- YAML file count
- YAML line count
- configuration layout
- largest YAML files
- include relationships
- exact duplicate YAML files
- use of `!secret`

File contents are not copied into the audit inventory.

## Configuration Quality Audit

Version 0.6.0 checks for:

- duplicate automation IDs
- duplicate automation aliases
- duplicate script aliases
- disabled automations
- disabled scripts
- unusually large automations
- unusually large scripts
- missing YAML include targets
- references to entity IDs that are not currently present in Home Assistant
- YAML files containing a high proportion of comments

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

Version 0.6.0 does not yet:

- modify Home Assistant
- automatically repair problems
- analyse Home Assistant Repairs
- provide complete Core log analysis
- send reports to OpenAI
- perform scheduled automatic audits
- assess release notes against the installation

These are planned future capabilities.

## Version

Current release: **0.6.0**
