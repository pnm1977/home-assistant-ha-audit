# Changelog

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
