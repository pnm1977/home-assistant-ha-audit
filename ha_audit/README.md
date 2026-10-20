# HA Audit

**Understand your Home Assistant system. Identify problems. Make better maintenance and upgrade decisions.**

HA Audit is a free, read-only health, configuration, and upgrade-readiness auditing app for Home Assistant.

It examines your actual Home Assistant installation and provides clear, evidence-based findings to help you maintain, troubleshoot, and improve your system.

HA Audit is designed for everyday Home Assistant users, while also providing detailed technical evidence for more advanced investigations.

**No automatic changes. No automatic repairs. No automatic AI data sharing.**

---

## What can HA Audit do?

### System health
- Check Home Assistant Core, Supervisor, and OS information.
- Identify unavailable and unknown entities.
- Distinguish whole-device unavailability from individual unavailable features.
- Compare findings with previous audits.
- Use available Recorder history to provide additional context.

### Configuration health
- Validate Home Assistant configuration.
- Examine active YAML files and their include relationships.
- Identify missing include files and possible missing entity references.
- Detect duplicate automation IDs, automation names, and script names.
- Identify configuration that may no longer be actively used.

### System Log analysis
- Group related warnings and errors into meaningful issue families.
- Prioritise findings as HIGH, MEDIUM, LOW, or VERY LOW.
- Distinguish isolated errors from recurring problems.
- Track independently observed activity across audit runs.
- Identify relevant automations, scripts, entities, and YAML locations where possible.

### Core update readiness
- Identify available Home Assistant Core updates.
- Retrieve relevant official Home Assistant release information.
- Examine documented breaking changes.
- Compare update requirements with the local installation.
- Identify potential compatibility concerns.
- Explain what was checked, what remains uncertain, and whether anything needs reviewing before updating.

### AI-assisted investigation
- Generate a structured handoff for ChatGPT, Claude, Gemini, and other AI assistants.
- Explain findings in plain English.
- Include supporting evidence and relevant configuration references.
- Help AI assistants suggest sensible next checks without guessing at causes.

---

## Installation

1. Open **Home Assistant → Settings → Apps**.
2. Open the **App Store**.
3. Open the menu and select **Repositories**.
4. Add the repository:

   `https://github.com/pnm1977/home-assistant-ha-audit`

5. Find **HA Audit** in the App Store.
6. Install the app.

HA Audit currently runs manually rather than continuously.

---

## Running your first audit

1. Open **Settings → Apps → HA Audit**.
2. Select **Start**.
3. Allow the audit to complete.
4. Open the **Log** tab.
5. Find the latest **USER SUMMARY**.

The app stops automatically when the audit finishes.

The recommended workflow is:

**Run → Read → Investigate → Act → Rerun**

HA Audit identifies findings and provides evidence. You remain responsible for deciding whether any changes are appropriate.

---

## Understanding the results

The USER SUMMARY is designed to be the starting point for most users.

It contains three main sections:

### STATUS

A quick overview of:
- General Home Assistant health.
- Core update guidance.
- OS update availability.
- Configuration validation.

### SYSTEM ISSUES

Shows the most important current System Log findings.

HA Audit prioritises issues using evidence rather than simply counting errors.

For example, hundreds of repeated warnings do not necessarily represent hundreds of separate problems.

An issue classified as `RECURRING 24H+` has evidence of independently observed new activity across at least 24 hours.

This does not mean the issue was continuously failing throughout that period or is necessarily failing now.

### CORE UPDATE - WHAT TO DO

Explains the evidence relevant to an available Core update.

Possible outcomes include:

| Result | Meaning |
|---|---|
| NO CORE UPDATE PENDING | No Core update currently needs assessment. |
| NO KNOWN BLOCKERS FOUND | No known blocker was identified in the evidence inspected. |
| REVIEW BEFORE UPDATING | Specific findings deserve review before proceeding. |
| ASSESSMENT INCOMPLETE | Some required evidence or compatibility coverage remains incomplete. |
| DELAY - BLOCKER EVIDENCE FOUND | Evidence indicates a reason to delay the update. |

**ASSESSMENT INCOMPLETE does not automatically mean a problem was found.**

HA Audit distinguishes between actual concerns and limitations in the evidence it was able to assess.

Likewise, **NO KNOWN BLOCKERS FOUND does not guarantee that an update is safe**.

---

## Understanding unavailable entities

An unavailable entity is not automatically faulty.

For example:
- A device may be deliberately switched off.
- A device may be undergoing maintenance.
- Only one feature of an otherwise working device may be unavailable.
- An integration may temporarily lose connectivity.
- An entity may no longer be provided by its integration.

HA Audit considers device availability, configuration references, and available Recorder history before presenting findings for review.

**HA Audit never recommends deleting entities solely because they are unavailable or have no recorded history.**

---

## Using HA Audit with AI

Each successful audit generates:

`ha_audit_ai_handoff.md`

This file is designed to be uploaded to an AI assistant for further investigation.

It includes:
- Current health and Core update guidance.
- Important System Log findings.
- Plain-English explanations.
- Relevant configuration references.
- Suggested first checks.
- Known evidence gaps and uncertainties.

A companion file is also generated:

`ha_audit_ai_evidence.json`

This contains structured evidence for more detailed AI analysis.

### How to use it

1. Run HA Audit.
2. Locate `ha_audit_ai_handoff.md`.
3. Upload it to your preferred AI assistant.
4. Ask the assistant to review your Home Assistant health.

The handoff already includes instructions explaining how the AI should interpret the evidence.

You do not need to write a complicated prompt.

**HA Audit does not automatically transmit your reports to an AI provider.**

Review files before sharing them because they may contain installation-specific device names, entity IDs, and configuration information.

---

## Detailed reports

Every successful audit generates:

`ha_audit_latest.txt`

This contains the latest detailed human-readable audit summary.

Additional JSON reports provide the underlying technical evidence.

For example:
- `quality_audit.json` — configuration findings.
- `availability_audit.json` — unavailable device context.
- `log_priority_final.json` — prioritised System Log findings.
- `ha_audit_ai_evidence.json` — structured AI evidence.

Reports are stored in HA Audit's private Home Assistant app configuration folder.

If your file editor supports access to `/addon_configs`, open that location and find the folder ending in `_ha_audit`.

See the **User Guide** for more information about interpreting results and accessing individual reports.

---

## Safety and privacy

HA Audit is designed to be read-only.

It does not:
- Modify Home Assistant configuration.
- Delete entities or devices.
- Restart Home Assistant.
- Automatically update Home Assistant.
- Execute repairs.
- Automatically upload reports to an AI service.

Configuration scanning excludes sensitive locations and files such as `secrets.yaml`.

Audit reports remain on your Home Assistant installation unless you choose to share them.

### Important limitations

HA Audit cannot guarantee that your installation is fault-free.

It does not currently:
- Inspect every UI-managed configuration setting.
- Guarantee compatibility with every integration.
- Verify that a successful backup or restore is available.
- Provide a complete historical archive of Home Assistant logs.
- Perform automated scheduled audits.
- Provide the same depth of upgrade assessment for Home Assistant OS as for Core.

These limitations are reported conservatively rather than treated as evidence that everything is working.

---

## Documentation

For more information, see:

- **User Guide** — running audits, interpreting results, and investigating findings.
- **Changelog** — release history and improvements.

---

## Project status

HA Audit is under active development.

The aim is to provide reliable, understandable, evidence-based Home Assistant auditing without unnecessary complexity or automated changes.

Future improvements will focus on genuine user needs, reliability, and maintaining compatibility with Home Assistant.

**Understand first. Change only when necessary.**
