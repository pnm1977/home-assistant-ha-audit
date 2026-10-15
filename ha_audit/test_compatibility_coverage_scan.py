import importlib.util
import json
import os
from pathlib import Path
import tempfile


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def load_scanner():
    source_path = (
        Path(__file__).resolve().parent
        / "compatibility_coverage_scan.py"
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(
            temp_dir
        )

        release_path = (
            temp_path
            / "release_evidence.json"
        )

        compatibility_path = (
            temp_path
            / "upgrade_compatibility.json"
        )

        output_path = (
            temp_path
            / "coverage.json"
        )

        release_path.write_text(
            json.dumps(
                {
                    "scope": {},
                    "release_range": {
                        "status": "ok",
                        "complete": True,
                    },
                    "aggregate": {
                        "breaking_change_groups": [],
                        "crossed_release_families": [],
                    },
                    "collector_status": {
                        "overall": "ok",
                    },
                }
            )
        )

        compatibility_path.write_text(
            json.dumps(
                {
                    "scope": {
                        "rule_pack":
                            "home_assistant_core_2026_9",
                    },
                    "summary": {
                        "rule_count": 0,
                    },
                    "results": [],
                }
            )
        )

        previous = {
            key: os.environ.get(
                key
            )
            for key in (
                "HA_AUDIT_RELEASE_EVIDENCE_FILE",
                "HA_AUDIT_UPGRADE_COMPATIBILITY_FILE",
                "HA_AUDIT_COMPATIBILITY_COVERAGE_FILE",
            )
        }

        os.environ[
            "HA_AUDIT_RELEASE_EVIDENCE_FILE"
        ] = str(
            release_path
        )

        os.environ[
            "HA_AUDIT_UPGRADE_COMPATIBILITY_FILE"
        ] = str(
            compatibility_path
        )

        os.environ[
            "HA_AUDIT_COMPATIBILITY_COVERAGE_FILE"
        ] = str(
            output_path
        )

        try:
            spec = (
                importlib.util.spec_from_file_location(
                    "compatibility_coverage_scan_tested",
                    source_path,
                )
            )

            module = (
                importlib.util.module_from_spec(
                    spec
                )
            )

            spec.loader.exec_module(
                module
            )

        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(
                        key,
                        None,
                    )
                else:
                    os.environ[
                        key
                    ] = value

        return module


def main():
    module = load_scanner()

    require(
        module.reference_family_mode(
            "2026.9"
        )
        == module.REFERENCE_MODE_COMPLETE,
        (
            "2026.9 must remain a complete-reference "
            "family."
        ),
    )

    require(
        module.reference_family_mode(
            "2026.10"
        )
        == module.REFERENCE_MODE_SELECTIVE,
        (
            "2026.10 must be declared selective before "
            "targeted deterministic rules are added."
        ),
    )

    complete_missing = (
        module.classify_group_reference(
            "2026.9",
            "Future unregistered 2026.9 group",
            [],
        )
    )

    require(
        complete_missing[
            "coverage_status"
        ]
        == "unmapped",
        (
            "A missing group in a complete-reference "
            "family must remain an unmapped error."
        ),
    )

    selective_unlisted = (
        module.classify_group_reference(
            "2026.10",
            "MQTT",
            [],
        )
    )

    require(
        selective_unlisted[
            "coverage_status"
        ]
        == "no_reference",
        (
            "An unlisted group in a selective-reference "
            "family must remain dynamic-only."
        ),
    )

    original_2026_10 = (
        module.RULE_GROUP_REGISTRY.get(
            "2026.10"
        )
    )

    try:
        module.RULE_GROUP_REGISTRY[
            "2026.10"
        ] = {
            "Authentication": [
                "core_2026_10_authentication",
            ],
            "State conditions": [
                "core_2026_10_state_conditions",
            ],
        }

        module.REGISTRY_INDEX = (
            module.build_registry_index()
        )

        future_rule_ids = {
            "core_2026_10_authentication",
            "core_2026_10_state_conditions",
        }

        authentication = (
            module.classify_group_reference(
                "2026.10",
                "Authentication",
                future_rule_ids,
            )
        )

        state_conditions = (
            module.classify_group_reference(
                "2026.10",
                "State conditions",
                future_rule_ids,
            )
        )

        mqtt = (
            module.classify_group_reference(
                "2026.10",
                "MQTT",
                future_rule_ids,
            )
        )

        require(
            authentication[
                "coverage_status"
            ]
            == "covered",
            (
                "A mapped selective 2026.10 group with "
                "its rule present must be covered."
            ),
        )

        require(
            state_conditions[
                "coverage_status"
            ]
            == "covered",
            (
                "The second mapped selective 2026.10 "
                "group must be covered."
            ),
        )

        require(
            mqtt[
                "coverage_status"
            ]
            == "no_reference",
            (
                "Adding targeted selective references "
                "must not turn the other 2026.10 groups "
                "into unmapped failures."
            ),
        )

        missing_rule = (
            module.classify_group_reference(
                "2026.10",
                "Authentication",
                [],
            )
        )

        require(
            missing_rule[
                "coverage_status"
            ]
            == "partial",
            (
                "A selective group that is explicitly "
                "mapped but whose expected rule result "
                "is missing must still fail closed."
            ),
        )

    finally:
        if original_2026_10 is None:
            module.RULE_GROUP_REGISTRY.pop(
                "2026.10",
                None,
            )
        else:
            module.RULE_GROUP_REGISTRY[
                "2026.10"
            ] = original_2026_10

        module.REGISTRY_INDEX = (
            module.build_registry_index()
        )

    unknown_family = (
        module.classify_group_reference(
            "2026.11",
            "Future change",
            [],
        )
    )

    require(
        unknown_family[
            "coverage_status"
        ]
        == "no_reference",
        (
            "A future family with no deterministic "
            "reference must remain a supported "
            "dynamic-only state."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT COMPATIBILITY COVERAGE TEST"
    )
    print("=" * 62)

    print(
        "Complete-family strictness:    PASS"
    )
    print(
        "Selective family declaration: PASS"
    )
    print(
        "Selective unlisted group:      PASS"
    )
    print(
        "Selective mapped groups:       PASS"
    )
    print(
        "Missing mapped rule fail-safe: PASS"
    )
    print(
        "Future dynamic-only family:    PASS"
    )

    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
