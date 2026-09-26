# Changelog

## 0.6.6

- Improved detailed-report location guidance in the current-run summary
- Added Studio Code Server instructions for opening HA Audit's `/addon_configs` folder
- Added guidance for finding the folder ending in `_ha_audit`
- Added instructions for returning to the user's previous Studio Code folder/workspace without assuming where they started
- Removed misleading container-only `/config/...` paths from the user-facing report section

## 0.6.5

- Added a concise current-run summary designed for repeated audit and cleanup cycles
- Added `summary_report.py` to turn detailed audit data into an actionable user-facing report
- Added `/config/ha_audit_latest.txt`, overwritten on every run so the latest audit can be read without scrolling through accumulated app logs
- Suppressed normal verbose scanner output from the Home Assistant app log
- Detailed JSON reports continue to be generated unchanged
- Scanner output is still shown automatically if a stage fails
- Added next-action guidance to the summary, including where to investigate findings in Home Assistant or Studio Code Server
- Added direct guidance for Template cleanup candidates
- 
## 0.6.4

- Added active-YAML reference checks for entities that are no longer currently provided by Home Assistant integrations
- Added a dedicated `not_provided_reference_scan.py` scanner
- Cross-references not-currently-provided entities against the active YAML tree identified by the quality audit
- Ignores fully commented-out YAML lines when checking references
- Reports not-currently-provided entities that are still referenced by active YAML
- Reports unreferenced Template entities as cleanup candidates rather than automatically treating them as safe to delete
- Saves detailed results to `not_provided_reference_audit.json`

## 0.6.3

- Added comparison between the Home Assistant entity registry and live entity source data
- Added detection of enabled registry entities that are no longer currently provided by an integration
- Added not-currently-provided entity counts grouped by platform
- Added detailed not-currently-provided entity reporting
- Added not-currently-provided results to `audit_snapshot.json`
- Kept not-currently-provided entities separate from confirmed stale entities to avoid treating temporary integration failures as safe to delete

## 0.6.2

- Added source line numbers for missing active include targets
- Added source line numbers for missing entity reference candidates
- Classified inactive YAML into:
  - blueprints
  - Zigbee2MQTT configuration
  - backup/archive files
  - orphan candidates
- Reduced false orphan warnings by separating known non-HA configuration files
- Improved configuration-quality report readability

## 0.6.1

- Added active YAML include-tree discovery starting from `configuration.yaml`
- Added separation of active and unreferenced YAML files
- Missing include checks now apply only to active configuration
- Improved entity reference detection to avoid false positives such as decimal values
- Excluded themes and blueprints from normal entity reference checking
- Continued to ignore fully commented rollback/reference blocks
- Added shared app version handling so runtime modules use the version from `config.yaml`
- Improved project and app documentation

## 0.6.0

- Added Configuration Quality Audit
- Added duplicate automation ID detection
- Added duplicate automation and script name checks
- Added missing include detection
- Added missing entity reference detection
- Added large automation and script detection
- Added comment-heavy YAML reporting
- Commented-out backup configuration is ignored as active YAML
- Added read-only Home Assistant configuration scanning
- Added documentation and branding

## 0.5.1

- Added YAML configuration inventory
- Added YAML file and line counts
- Added include discovery
- Added exact duplicate file detection
- Excluded secrets and private Home Assistant storage

## 0.4.0

- Added unavailable and unknown entity grouping by device
- Added comparison against the previous audit

## 0.3.0

- Added Home Assistant registry access
- Added platform and device mapping

## 0.2.1

- Added entity health and configuration validation
- Improved collector fault isolation

## 0.1.0

- Initial HA Audit app
- Added Core, Supervisor and OS information
