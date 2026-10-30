# Changelog

## 0.8.30 — Core readiness evidence trace (30 October 2026)

- Added `readiness_trace.py` to explain how initially uncertain Core compatibility groups were reconciled without changing the Core readiness decision logic.
- Added **CORE READINESS EVIDENCE TRACE** to the detailed current-run summary, showing initial uncertainty, scoped automatic checks, explicit user confirmations, unresolved groups, and decision reason codes.
- Clearly labelled user confirmations as **not machine-verified** and retained warnings that zero unresolved groups does not mean every official change or UI-managed setting was inspected.
- Included the trace as a separate section in `ha_audit_ai_handoff.md`, with instructions for receiving assistants to distinguish automatic evidence from user assertions.
- Added `test_readiness_trace.py` and its GitHub Actions workflow; updated summary-output regression coverage to reflect conservative incomplete-evidence handling.
- Packaged the new trace module into the add-on Docker image.
- Validated v0.8.30 against a live Core 2026.8.3 → 2026.10.4 audit: no collector errors, one automatic reconciliation, one accepted manual confirmation, and no unresolved reconciliation groups.
- Updated the repository README, add-on README, and User Guide to explain the evidence trace and its limits.

## 0.8.x — Investigation Web UI and evidence-based guidance (through v0.8.23, 29 October 2026)

### Web UI and investigation workflow

- Added a Home Assistant Ingress Web UI that remains available after an audit completes while the app is running. Starting the app runs an audit; keeping the Web UI open does not continuously rescan Home Assistant.
- Added **Where to focus** to separate practical investigation recommendations from underlying System Log priorities.
- Added persistent per-finding investigation statuses: **Investigating**, **Monitoring**, **Explained**, and **Resolved**.
- Added user-editable investigation notes (up to 4,000 characters), with saved change history retained in the app's private configuration storage across runs and updates when that storage is preserved.
- Added in-app access to the latest audit report and **Copy for AI** / **Download handoff** actions.
- Kept user-entered context separate from independently collected evidence. Marking a finding Explained or Resolved does not automatically prove that future errors are harmless.

### Independent evidence checks

- Added an optional **power-control switch** relationship for findings involving deliberately powered-off devices.
- Added read-only comparison of **sampled** System Log timestamps against the linked switch's Recorder state, reporting **OFF**, **ON**, or **UNKNOWN**.
- Added a cautious **Sampled power-off — no immediate action** investigation category for explained findings whose checked samples all occurred with the switch OFF. ON, UNKNOWN, or insufficient evidence still requires appropriate follow-up.
- Added configurable scheduled-maintenance windows with **daily**, **selected weekdays**, **monthly calendar date**, and **monthly weekday occurrence** frequencies.
- Added time-zone-aware maintenance matching, including daylight-saving and overnight windows, reporting **INSIDE**, **OUTSIDE**, or **UNKNOWN** for sampled log timestamps.
- Added maintenance-evidence explanations that distinguish the most recent sampled timestamp from older outside-window evidence.
- Added **NEW ACTIVITY**, **RETAINED EVIDENCE**, and **BASELINE** labels based on existing cross-audit System Log history, avoiding the assumption that retained log entries represent new failures.

### Evidence presentation and safety

- Displayed sampled power and maintenance evidence directly alongside investigation notes and recommendations, with a way to inspect detailed verification results.
- Included saved investigation context, structured relationships, sampled evidence, limitations, and suggested next checks in the AI / LLM handoff.
- Preserved original technical priorities, recurrence classifications, raw findings, and investigation statuses when adding evidence-based guidance.
- Explicitly identified Home Assistant System Log deduplication and limited timestamp sampling: a match does **not** classify every grouped occurrence or prove causation.
- Kept absent Recorder history, unverified timestamps, and missing or stale evidence as **unknown**, not proof of a harmless error.
- Continued to operate read-only with respect to Home Assistant; investigation feedback changes only HA Audit's private records.

### Documentation

- Refreshed the main README and User Guide for the persistent Web UI, investigation workflow, optional evidence settings, AI handoff, and safety limitations.
- Clarified that the app's Web UI remains available after the audit finishes and that a new audit requires restarting the app.

## 0.8.x — Earlier improvements

- Added structured AI evidence in `ha_audit_ai_evidence.json` to complement the existing human-readable AI / LLM handoff.
- Added machine-readable evidence covering system information, configuration findings, System Log issues, recurrence, availability, Repairs, and identified evidence gaps.
- Added interpretation guidance to help receiving AI assistants distinguish observations from inference and uncertainty.
- Added exact configuration associations between System Log issue families and relevant automations, scripts, entities, and active YAML references.
- Included source filenames and line numbers where available to help users locate relevant configuration.
- Explicitly distinguished configuration associations from proven causes.
- Improved the AI / LLM handoff and structured evidence to provide clearer, more actionable troubleshooting information.
- Added issue-specific explanations and useful first checks for common integration, device-connectivity, automation, and Zigbee communication problems.
- Improved plain-English System Log descriptions while preserving technical evidence in the detailed reports.
- Improved recurrence explanations to distinguish independent activity across audit runs from the timestamps of messages in the current log sample.
- Added historical recurrence context and guidance for verifying 24-hour recurrence classifications.
- Validated recurrence classifications against historical audit records.
- Improved Core update decision explanations to distinguish:
  - Completed checks that found no specific update-related concern.
  - Actual findings requiring investigation.
  - Incomplete evidence or compatibility coverage.
- Clarified that `ASSESSMENT INCOMPLETE` does not automatically mean an update blocker was found.
- Preserved the conservative Core update decision model and separation between general system health and upgrade readiness.
- Extended automated AI evidence and handoff regression testing.
- Updated the GitHub Actions AI evidence contract testing workflow.
- Validated the 0.8.x improvements against live Home Assistant audit results.
- Preserved read-only operation, local evidence storage, and the requirement for users to choose whether to share reports with external AI services.

## 0.7.x

- Added the Core upgrade-readiness evidence foundation.
- Added `update_readiness_scan.py` for installed, target, and pending Core update context.
- Added `upgrade_impact_scan.py` for locally relevant upgrade-impact evidence.
- Added `upgrade_compatibility_scan.py` for deterministic compatibility-reference evaluation.
- Added `release_evidence_scan.py` for official Home Assistant release and breaking-change evidence.
- Added `compatibility_coverage_scan.py` to measure deterministic-reference coverage of official release evidence.
- Added `upgrade_correlation_scan.py` to dynamically correlate official release evidence with the local Home Assistant installation.
- Added `correlation_validation_scan.py` to compare dynamic correlation with optional deterministic reference rules.
- Integrated Core upgrade-readiness evidence into the current-run summary.
- Treated deterministic compatibility rules as optional precision/reference tools rather than a required exhaustive registry.
- Added explicit deterministic-reference states:
  - `no_reference`
  - `partial_reference`
  - `complete`
  - `incomplete`
  - `not_applicable`
- Added valid dynamic-only handling for future Core releases where no deterministic reference exists.
- Added `ha_audit/test_future_no_reference.py`.
- Added `.github/workflows/future-no-reference-test.yml`.
- Added regression coverage proving that missing optional deterministic reference does not cause coverage or validation collector failure.
- Validated the 2026.8.3 to 2026.9.4 Core path against:
  - 8 official breaking-change groups
  - 9 deterministic rules
  - 8/8 compatibility coverage
  - 8/8 local-relevance alignment
- Retained the expected Vacuum precision-review difference rather than forcing dynamic and deterministic evidence to agree.
- Kept upgrade findings evidence-based and conservative: 0.7.x reports readiness evidence and assessment completeness but does not yet produce a final update recommendation.
- Added a simplified top-level `OVERVIEW` covering Home Assistant health, Core update guidance, OS update visibility, Core evidence collection, and configuration validation.
- Added `WHY THIS RESULT` so headline health and Core-update results include concise supporting reasons.
- Kept general Home Assistant health separate from Core update guidance so ordinary availability findings do not automatically become upgrade blockers.
- Added `health_guidance.py` and `readiness_guidance.py` with dedicated regression tests and GitHub Actions workflows.
- Added output regression testing to protect the user-facing summary during refactoring.
- Extracted overview and upgrade rendering into `summary_overview.py` and `summary_upgrade.py` to reduce the size and responsibility of `summary_report.py`.
- Added `ai_handoff.py` to generate `ha_audit_ai_handoff.md` after a successful current-run summary.
- Added a concise vendor-neutral AI / LLM handoff designed for ChatGPT, Claude, Gemini, local LLMs, and other compatible assistants.
- Added receiving-AI instructions that preserve uncertainty, distinguish HA Audit evidence from inference, avoid guaranteed-safe update claims, and discourage destructive cleanup based only on unavailable or not-currently-provided states.
- Limited the default AI / LLM handoff to selected health, update-readiness, configuration, availability, history, and next-action evidence while keeping lower-level technical detail in the existing reports.
- Added `ha_audit/test_ai_handoff.py` and `.github/workflows/ai-handoff-test.yml`.
- Wired AI / LLM handoff generation to occur only after the latest summary is successfully generated, reducing the risk of presenting stale evidence as a new handoff.
- Kept AI / LLM handoff generation entirely local. HA Audit does not automatically transmit audit information to an external AI service.
- Updated the root README, app README, and User Guide with the current overview, Core upgrade-readiness, AI / LLM handoff, privacy, and usage workflow.
- Added bounded Home Assistant System Log collection for current warning and error evidence.
- Added deterministic System Log issue-family grouping so related entries can be reviewed together.
- Added stable System Log fingerprints for cross-run identity and persistence tracking.
- Added System Log ownership and evidence classification for local, network, upstream, and uncertain investigation paths.
- Added evidence-based System Log priority with `HIGH`, `MEDIUM`, `LOW`, and `VERY LOW` user-facing levels.
- Kept System Log priority separate from log severity and prevented raw occurrence count from being treated as recurrence or an independent reason to promote an issue to `HIGH`.
- Added cross-run persistence tracking while retaining historical evidence when an issue is not present in the latest run.
- Added recurrence classification with a strict distinction between `SHORT-WINDOW REPEAT` and durable `RECURRING 24H+` evidence.
- Added System Log correlation with availability, Recorder-history, and Repairs context.
- Added final enriched System Log priority with conservative promotion rules and fail-closed source alignment.
- Added the plain-English `SYSTEM ISSUES` section to show the highest-priority current findings without overwhelming the normal user summary.
- Added regression coverage for System Log grouping, fingerprinting, ownership, priority, persistence, recurrence, correlation, final priority, and user-facing rendering.
- Added System Issues to `ha_audit_ai_handoff.md`, including final priority and recurrence context.
- Added receiving-AI guidance not to re-rank System issues solely from raw occurrence count and to keep short-window repeats separate from durable recurrence.
- Kept lower-priority System Log findings and internal family/fingerprint details out of the concise AI handoff while retaining them in detailed reports.
- Updated the README, User Guide, and changelog to reflect the completed 0.7.x System Log and AI-handoff work.

## 0.6.10

- Improved duplicate automation alias handling by cross-checking duplicate names against live Home Assistant automation states.
- Kept duplicate automation IDs as structural findings.
- Normal summary output now surfaces duplicate aliases only when two or more matching automations are currently on.
- Kept disabled or mixed-state duplicate aliases in detailed audit data without promoting them as routine health findings.
- Added separate unresolved duplicate-alias reporting when live state cannot be fully determined.
- Avoided guessing intent from alias wording such as `Old` or `Backup`.
- Added a state-snapshot timestamp to `availability_audit.json`.
- Changed availability wording to be observational rather than cleanup-oriented.
- Kept expected-offline and maintenance labels as optional context rather than required configuration.
- Removed normal `NEXT ACTIONS` prompts to create or maintain availability labels.
- Added `unavailable_history_scan.py`.
- Added `unavailable_history_audit.json`.
- Added Recorder-history context for ordinary unavailable entities.
- Tied unavailable history queries to the availability snapshot timestamp.
- Limited the requested 90-day history window to actual Recorder retention.
- Added four ordinary-unavailable history statuses:
  - `usable_history_found`
  - `history_found_no_usable_state`
  - `no_history_returned`
  - `history_query_failed`
- Added `last_usable_state_started_at` and `last_usable_state_ended_at`.
- Derived the end of the final usable interval from the following non-usable transition where Recorder provides one.
- Added individual entity retries after a failed batch history request.
- Added an `UNAVAILABLE HISTORY CONTEXT` section to the current-run summary.
- Kept old, recent and absent usable history as observational context rather than automatic fault or cleanup evidence.
- Improved not-currently-provided history semantics so recent/older classification uses the proven end of the final usable interval where available.
- Conservatively keeps a usable interval protective when Recorder does not contain its end transition.
- Added the new availability-history report to detailed-report guidance.
- Wired the new scanner into the app runtime.

## 0.6.9

- Added unavailable-entity availability classification.
- Added `availability_scan.py`.
- Added `availability_audit.json`.
- Added support for Home Assistant labels to distinguish deliberately unavailable devices from genuine review items.
- Added `HA Audit - Expected Offline` for devices that are normally power-managed or intentionally switched off.
- Added `HA Audit - Maintenance` for devices temporarily offline because of maintenance, building work, or similar activity.
- Added partial-availability detection for devices that still have healthy entities while some secondary entities are unavailable.
- Added whole-device-unavailable classification for unlabelled devices with no healthy state entities.
- Added ungrouped-unavailable classification for unavailable entities that are not attached to a device.
- Kept the raw unavailable entity count visible rather than suppressing labelled or partially available entities.
- Added device-level and entity-level availability summaries.
- Excluded not-currently-provided entities from availability classification because they already have separate reference and history-safety checks.
- Added an `AVAILABILITY CONTEXT` section to the current-run summary.
- Added next-action guidance for configuring HA Audit labels and reviewing unlabelled unavailable devices.
- Continued treating unavailable state as review context rather than automatic evidence of a fault or safe cleanup.

## 0.6.8

- Added Recorder health collection using Home Assistant system health data.
- Added `recorder_health_audit.json`.
- Added detection of the oldest available Recorder run.
- Added estimated available Recorder history duration.
- Changed history scanning to use the effective Recorder window rather than blindly requesting the full 90-day policy window.
- Added clear separation between requested history lookback and actually available Recorder history.
- Updated history-safety output to show requested lookback, Recorder start, available history, and effective history checked.
- Kept history as protective context only.
- Continued treating missing history as unknown rather than cleanup evidence.

## 0.6.7

- Added history checks for entities that are no longer currently provided by integrations.
- Added a 90-day history lookback using Home Assistant's history API.
- Added conservative history classification.
- Ignored `unavailable` and `unknown` states when identifying the last genuinely usable state.
- Added `not_provided_history_audit.json`.
- Added a history-safety section to the current-run summary.
- Added recent-activity details to `NEXT ACTIONS` when the list is small.
- Treated missing history as unknown rather than cleanup evidence.
- Added warnings that Recorder retention or exclusions can limit available history.
- Updated detailed-report guidance so Studio Code Server is an example rather than a requirement.

## 0.6.6

- Improved detailed-report location guidance in the current-run summary.
- Added Studio Code Server instructions for opening HA Audit's `/addon_configs` folder.
- Added guidance for finding the folder ending in `_ha_audit`.
- Added instructions for returning to the user's previous folder/workspace.
- Removed misleading container-only `/config/...` paths from user-facing report guidance.

## 0.6.5

- Added a concise current-run summary designed for repeated audit and cleanup cycles.
- Added `summary_report.py`.
- Added `/config/ha_audit_latest.txt`, overwritten on every run.
- Suppressed normal verbose scanner output from the Home Assistant app log.
- Detailed JSON reports continue to be generated.
- Scanner output is shown automatically if a stage fails.
- Added next-action guidance and detailed-report pointers.

## 0.6.4

- Added active-YAML reference checks for entities no longer currently provided by integrations.
- Added `not_provided_reference_scan.py`.
- Cross-referenced not-currently-provided entities against the active YAML tree.
- Ignored fully commented-out YAML when checking references.
- Added Template review candidates.
- Added `not_provided_reference_audit.json`.

## 0.6.3

- Added comparison between the Home Assistant entity registry and live entity source data.
- Added detection of enabled registry entities no longer currently provided by an integration.
- Added platform-level not-currently-provided counts.
- Added detailed not-currently-provided reporting.
- Kept not-currently-provided separate from confirmed stale entities.

## 0.6.2

- Added source line numbers for missing active include targets.
- Added source line numbers for missing entity reference candidates.
- Classified inactive YAML into blueprints, Zigbee2MQTT configuration, backup/archive files, and orphan candidates.
- Reduced false orphan warnings.
- Improved configuration-quality report readability.

## 0.6.1

- Added active YAML include-tree discovery starting from `configuration.yaml`.
- Added separation of active and unreferenced YAML files.
- Limited missing-include checks to active configuration.
- Improved entity reference detection.
- Excluded themes and blueprints from normal entity-reference checks.
- Continued to ignore fully commented rollback/reference blocks.
- Added shared app version handling.
- Improved project and app documentation.

## 0.6.0

- Added Configuration Quality Audit.
- Added duplicate automation ID detection.
- Added duplicate automation and script name checks.
- Added missing include detection.
- Added missing entity reference detection.
- Added large automation and script detection.
- Added comment-heavy YAML reporting.
- Ignored commented-out backup configuration as active YAML.
- Added read-only Home Assistant configuration scanning.
- Added documentation and branding.

## 0.5.x

- Added YAML configuration inventory.
- Added YAML file and line counts.
- Added include discovery.
- Added exact duplicate file detection.
- Excluded secrets and private Home Assistant storage.

## 0.4.x

- Added unavailable and unknown entity grouping by device.
- Added comparison against the previous audit.

## 0.3.x

- Added Home Assistant registry access.
- Added platform and device mapping.

## 0.2.x

- Added entity health and configuration validation.
- Improved collector fault isolation.

## 0.1.x

- Initial HA Audit app.
- Added Core, Supervisor, and OS information.
