# Changelog

## 0.6.10

* Improved duplicate automation alias handling by cross-checking duplicate names against live Home Assistant automation states
* Kept duplicate automation IDs as structural findings
* Normal summary output now surfaces duplicate aliases only when two or more matching automations are currently on
* Kept disabled or mixed-state duplicate aliases in detailed audit data without promoting them as routine health findings
* Added separate unresolved duplicate-alias reporting when live state cannot be fully determined
* Avoided guessing intent from alias wording such as `Old` or `Backup`
* Added a state-snapshot timestamp to `availability_audit.json`
* Changed availability wording to be observational rather than cleanup-oriented
* Kept expected-offline and maintenance labels as optional context rather than required configuration
* Removed normal `NEXT ACTIONS` prompts to create or maintain availability labels
* Added `unavailable_history_scan.py`
* Added `unavailable_history_audit.json`
* Added Recorder-history context for ordinary unavailable entities
* Tied unavailable history queries to the availability snapshot timestamp
* Limited the requested 90-day history window to actual Recorder retention
* Added four ordinary-unavailable history statuses:

  * `usable_history_found`
  * `history_found_no_usable_state`
  * `no_history_returned`
  * `history_query_failed`
* Added `last_usable_state_started_at` and `last_usable_state_ended_at`
* Derived the end of the final usable interval from the following non-usable transition where Recorder provides one
* Added individual entity retries after a failed batch history request
* Added an `UNAVAILABLE HISTORY CONTEXT` section to the current-run summary
* Kept old, recent and absent usable history as observational context rather than automatic fault or cleanup evidence
* Improved not-currently-provided history semantics so recent/older classification uses the proven end of the final usable interval where available
* Conservatively keeps a usable interval protective when Recorder does not contain its end transition
* Added the new availability-history report to detailed-report guidance
* Wired the new scanner into the app runtime

## 0.6.9

* Added unavailable-entity availability classification
* Added `availability_scan.py`
* Added `availability_audit.json`
* Added support for Home Assistant labels to distinguish deliberately unavailable devices from genuine review items
* Added `HA Audit - Expected Offline` for devices that are normally power-managed or intentionally switched off
* Added `HA Audit - Maintenance` for devices temporarily offline because of maintenance, building work, or similar activity
* Added partial-availability detection for devices that still have healthy entities while some secondary entities are unavailable
* Added whole-device-unavailable classification for unlabelled devices with no healthy state entities
* Added ungrouped-unavailable classification for unavailable entities that are not attached to a device
* Kept the raw unavailable entity count visible rather than suppressing labelled or partially available entities
* Added device-level and entity-level availability summaries
* Excluded not-currently-provided entities from availability classification because they already have separate reference and history-safety checks
* Added an `AVAILABILITY CONTEXT` section to the current-run summary
* Added next-action guidance for configuring HA Audit labels and reviewing unlabelled unavailable devices
* Continued treating unavailable state as review context rather than automatic evidence of a fault or safe cleanup

## 0.6.8

* Added Recorder health collection using Home Assistant system health data
* Added `recorder_health_audit.json`
* Added detection of the oldest available Recorder run
* Added estimated available Recorder history duration
* Changed history scanning to use the effective Recorder window rather than blindly requesting the full 90-day policy window
* Added clear separation between requested history lookback and actually available Recorder history
* Updated history-safety output to show requested lookback, Recorder start, available history, and effective history checked
* Kept history as protective context only
* Continued treating missing history as unknown rather than cleanup evidence

## 0.6.7

* Added history checks for entities that are no longer currently provided by integrations
* Added a 90-day history lookback using Home Assistant's history API
* Added conservative history classification
* Ignored `unavailable` and `unknown` states when identifying the last genuinely usable state
* Added `not_provided_history_audit.json`
* Added a history-safety section to the current-run summary
* Added recent-activity details to `NEXT ACTIONS` when the list is small
* Treated missing history as unknown rather than cleanup evidence
* Added warnings that Recorder retention or exclusions can limit available history
* Updated detailed-report guidance so Studio Code Server is an example rather than a requirement

## 0.6.6

* Improved detailed-report location guidance in the current-run summary
* Added Studio Code Server instructions for opening HA Audit's `/addon_configs` folder
* Added guidance for finding the folder ending in `_ha_audit`
* Added instructions for returning to the user's previous folder/workspace
* Removed misleading container-only `/config/...` paths from user-facing report guidance

## 0.6.5

* Added a concise current-run summary designed for repeated audit and cleanup cycles
* Added `summary_report.py`
* Added `/config/ha_audit_latest.txt`, overwritten on every run
* Suppressed normal verbose scanner output from the Home Assistant app log
* Detailed JSON reports continue to be generated
* Scanner output is shown automatically if a stage fails
* Added next-action guidance and detailed-report pointers

## 0.6.4

* Added active-YAML reference checks for entities no longer currently provided by integrations
* Added `not_provided_reference_scan.py`
* Cross-referenced not-currently-provided entities against the active YAML tree
* Ignored fully commented-out YAML when checking references
* Added Template review candidates
* Added `not_provided_reference_audit.json`

## 0.6.3

* Added comparison between the Home Assistant entity registry and live entity source data
* Added detection of enabled registry entities no longer currently provided by an integration
* Added platform-level not-currently-provided counts
* Added detailed not-currently-provided reporting
* Kept not-currently-provided separate from confirmed stale entities

## 0.6.2

* Added source line numbers for missing active include targets
* Added source line numbers for missing entity reference candidates
* Classified inactive YAML into blueprints, Zigbee2MQTT configuration, backup/archive files, and orphan candidates
* Reduced false orphan warnings
* Improved configuration-quality report readability

## 0.6.1

* Added active YAML include-tree discovery starting from `configuration.yaml`
* Added separation of active and unreferenced YAML files
* Limited missing-include checks to active configuration
* Improved entity reference detection
* Excluded themes and blueprints from normal entity-reference checks
* Continued to ignore fully commented rollback/reference blocks
* Added shared app version handling
* Improved project and app documentation

## 0.6.0

* Added Configuration Quality Audit
* Added duplicate automation ID detection
* Added duplicate automation and script name checks
* Added missing include detection
* Added missing entity reference detection
* Added large automation and script detection
* Added comment-heavy YAML reporting
* Ignored commented-out backup configuration as active YAML
* Added read-only Home Assistant configuration scanning
* Added documentation and branding

## 0.5.1

* Added YAML configuration inventory
* Added YAML file and line counts
* Added include discovery
* Added exact duplicate file detection
* Excluded secrets and private Home Assistant storage

## 0.4.0

* Added unavailable and unknown entity grouping by device
* Added comparison against the previous audit

## 0.3.0

* Added Home Assistant registry access
* Added platform and device mapping

## 0.2.1

* Added entity health and configuration validation
* Improved collector fault isolation

## 0.1.0

* Initial HA Audit app
* Added Core, Supervisor, and OS information
