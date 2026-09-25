# HA Audit

HA Audit is a read-only Home Assistant health and configuration auditing app.

It is designed to help you understand, maintain, and improve a Home Assistant installation over time.

## What it currently checks

- Home Assistant Core, Supervisor and OS versions
- Entity and device inventory
- Unavailable and unknown entities
- Available updates
- Home Assistant configuration validation
- YAML configuration inventory
- Duplicate automation IDs and names
- Duplicate script names
- Missing include targets
- Missing entity references
- Large automations and scripts
- Comment-heavy YAML files

HA Audit does not make changes to Home Assistant.

Configuration access is read-only.
