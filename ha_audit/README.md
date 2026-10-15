HA Audit

HA Audit is a read-only Home Assistant health, configuration, and upgrade-readiness auditing app.

It is designed to help you understand, maintain, troubleshoot, and improve a Home Assistant installation using evidence from the actual system.

What it currently checks

Home Assistant Core, Supervisor, and OS versions

Home Assistant health and configuration status

entity and device inventory

unavailable and unknown entities

available Core, OS, and other updates

Home Assistant Repairs context

Core upgrade-readiness evidence

official Home Assistant release and breaking-change evidence

local upgrade compatibility and impact

Home Assistant configuration validation

YAML configuration inventory and active include tree

missing include targets and missing entity references

duplicate automation IDs

duplicate automation aliases with live-state context

duplicate script aliases

large automations and scripts

entities no longer currently provided by integrations

active-YAML references to not-currently-provided entities

Recorder history available to the audit

availability context for ordinary unavailable entities

Recorder-history context for ordinary unavailable entities

Home Assistant System Log issue grouping and prioritisation

System Log persistence and recurrence across audit runs

System Log correlation with availability, Recorder, and Repairs context

Current-run summary

Each audit writes:

ha_audit_latest.txt

This contains the latest detailed user-facing audit summary, including the health overview, Core update guidance, important evidence, and suggested next actions.

The Home Assistant app log also shows a shorter plain-English USER SUMMARY containing:

STATUS
SYSTEM ISSUES
CORE UPDATE - WHAT TO DO

General Home Assistant health and Core update guidance are kept separate so ordinary health findings do not automatically become Core update blockers.

System issues

HA Audit groups related Home Assistant System Log entries into issue families and gives them an evidence-based priority.

The concise user summary shows the highest-priority current findings first.

Priority is not the same as log severity, and a high raw occurrence count does not by itself prove recurrence or make an issue more important.

HA Audit distinguishes short-window repeats from recurrence proven across at least 24 hours.

Detailed System Log evidence remains available in the generated JSON reports.

AI / LLM handoff

Each audit also produces:

ha_audit_ai_handoff.md

This is a concise, vendor-neutral handoff designed for use with ChatGPT, Claude, Gemini, local LLMs, or other AI assistants.

It contains selected evidence from the current audit together with instructions for the receiving AI to distinguish reported facts from inference, preserve uncertainty, avoid unsafe cleanup assumptions, and avoid presenting update safety as guaranteed.

The handoff also includes HA Audit's highest-priority current System issues and tells the receiving AI not to re-rank them solely from raw occurrence count.

HA Audit does not automatically send the handoff to any AI service.

The file remains local until you choose to copy or upload it elsewhere.

The handoff may contain Home Assistant device names, entity IDs, and other installation-specific information, so review it before sharing it with a third-party service.

Availability and history

Unavailable does not automatically mean faulty.

HA Audit distinguishes partial device availability, whole-device unavailability, and ungrouped unavailable entities. Optional Home Assistant labels may add expected-offline or maintenance context, but labels are not required.

Recorder history is observational context only. Recent, old, or absent history does not by itself prove that an entity is faulty, stale, or safe to remove.

Core upgrade readiness

HA Audit combines official Home Assistant release evidence with evidence from the local installation.

Its Core update guidance is deliberately conservative.

A result such as:

Core update: NO KNOWN BLOCKERS FOUND

means no known blockers were found in the evidence HA Audit inspected. It is not a guarantee that an update cannot cause a problem.

Safety

HA Audit does not make changes to Home Assistant.

Configuration access is read-only and audit data remains local to the Home Assistant installation unless you choose to share a generated report or AI / LLM handoff.
