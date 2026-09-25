# HA Audit

HA Audit is a read-only health and configuration auditing app for Home Assistant.

It is designed to help understand, maintain, troubleshoot, and improve a Home Assistant installation over time.

## Current capabilities

HA Audit currently provides:

- Home Assistant Core, Supervisor and OS information
- device and entity inventory
- unavailable and unknown entity analysis
- update detection
- Home Assistant configuration validation
- YAML configuration inventory
- active YAML include-tree discovery
- detection of unreferenced YAML
- duplicate automation ID checks
- duplicate automation and script name checks
- missing include detection
- missing entity reference candidates
- large automation and script detection
- comparison with previous audit results

## Safety

HA Audit is designed to be read-only.

It does not modify Home Assistant configuration and currently does not send audit data to any external service.

Sensitive locations such as `.storage` and `secrets.yaml` are excluded from configuration scanning.

## Installation

Add this repository to the Home Assistant App Store:

`https://github.com/pnm1977/home-assistant-ha-audit`

Then install **HA Audit** from the App Store.

## Status

HA Audit is under active development.

The project is currently focused on Home Assistant system health, configuration quality, upgrade readiness, maintenance, and future-proofing.
