import json
import os
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

INPUT_FILE = (
    "/config/log_issue_families.json"
)

OUTPUT_FILE = (
    "/config/log_issue_ownership.json"
)


OWNER_USER = (
    "USER / LOCAL CONFIGURATION"
)

OWNER_DEVICE = (
    "DEVICE / LOCAL NETWORK"
)

OWNER_INTEGRATION = (
    "INTEGRATION / APP"
)

OWNER_EXTERNAL = (
    "EXTERNAL SERVICE"
)

OWNER_HA = (
    "HOME ASSISTANT PLATFORM"
)

OWNER_UNKNOWN = (
    "MIXED / UNKNOWN"
)


CONFIDENCE_HIGH = "HIGH"
CONFIDENCE_MEDIUM = "MEDIUM"
CONFIDENCE_LOW = "LOW"


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(
    path,
):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(
            handle
        )


def clean_text(
    value,
):
    return " ".join(
        str(
            value or ""
        ).split()
    )


def family_text(
    family,
):
    parts = [
        family.get(
            "family_id",
            "",
        ),
        family.get(
            "title",
            "",
        ),
    ]

    for key in (
        "logger_names",
        "sources",
        "message_samples",
    ):
        value = family.get(
            key,
            [],
        )

        if isinstance(
            value,
            list,
        ):
            parts.extend(
                value
            )

    return " ".join(
        clean_text(
            part
        )
        for part in parts
        if clean_text(
            part
        )
    ).lower()


OWNERSHIP_RULES = {
    "zigbee_delivery": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The family contains Zigbee/ZHA "
            "packet-delivery, acknowledgement, "
            "route or device-response failures. "
            "Automation/script errors are treated "
            "as consequences of the delivery "
            "failure rather than the primary "
            "ownership domain."
        ),
    },
    "shelly": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_MEDIUM,
        "basis": (
            "The evidence shows repeated failure "
            "retrieving data from a local Shelly "
            "device. Device reachability or local "
            "network communication is the most "
            "likely action domain, but the current "
            "evidence does not exclude an "
            "integration problem."
        ),
    },
    "apple_tv": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_MEDIUM,
        "basis": (
            "The evidence is dominated by local "
            "device connection loss, failed "
            "connections and reconnection."
        ),
    },
    "hue_sync": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The evidence contains timeouts while "
            "fetching data directly from local "
            "Hue Sync Box devices."
        ),
    },
    "octopus_energy": {
        "ownership": OWNER_EXTERNAL,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The evidence contains explicit "
            "Octopus remote API/service failures, "
            "including temporary service errors "
            "and failed remote data retrieval."
        ),
    },
    "missing_targets": {
        "ownership": OWNER_UNKNOWN,
        "confidence": CONFIDENCE_LOW,
        "basis": (
            "Home Assistant reports that referenced "
            "targets are missing or unavailable. "
            "That can result from local configuration, "
            "temporary device availability or an "
            "integration state, so ownership cannot "
            "be assigned safely from this evidence "
            "alone."
        ),
    },
    "slow_entity_update": {
        "ownership": OWNER_UNKNOWN,
        "confidence": CONFIDENCE_LOW,
        "basis": (
            "Slow entity updates can originate from "
            "devices, the local network, integration "
            "behaviour or platform load. The System "
            "Log evidence alone does not identify "
            "the responsible domain."
        ),
    },
    "lg_tv_off": {
        "ownership": OWNER_USER,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "A local automation is attempting an "
            "action while the target LG TV is off. "
            "The automation logic can potentially "
            "guard or suppress that action."
        ),
    },
    "esphome": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The evidence contains direct local "
            "ESPHome API connection failures, "
            "timeouts and unreachable-device "
            "errors."
        ),
    },
    "robovac": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The evidence contains local RoboVac "
            "communication timeouts, failed updates "
            "and retry/backoff behaviour."
        ),
    },
    "supervisor_store_reload": {
        "ownership": OWNER_HA,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The failures are Home Assistant "
            "Supervisor/App Store reload requests "
            "rather than device or user automation "
            "operations."
        ),
    },
    "music_queue_info": {
        "ownership": OWNER_USER,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The failure is an undefined template "
            "variable inside local Music automation "
            "and script execution."
        ),
    },
    "invalid_auth": {
        "ownership": OWNER_USER,
        "confidence": CONFIDENCE_MEDIUM,
        "basis": (
            "The evidence shows failed authentication "
            "from a local Home Assistant client. "
            "Local client credentials, sessions or "
            "authentication state are the most "
            "likely action domain. This does not by "
            "itself indicate a security compromise."
        ),
    },
    "mypyllant": {
        "ownership": OWNER_EXTERNAL,
        "confidence": CONFIDENCE_MEDIUM,
        "basis": (
            "The evidence contains failures returned "
            "while communicating with the remote "
            "myVAILLANT service. A custom integration "
            "issue cannot be excluded from this "
            "evidence alone."
        ),
    },
    "nabu_casa": {
        "ownership": OWNER_EXTERNAL,
        "confidence": CONFIDENCE_MEDIUM,
        "basis": (
            "The connection was closed by the remote "
            "Home Assistant Cloud service. The "
            "current evidence does not establish a "
            "local configuration fault."
        ),
    },
    "sonos": {
        "ownership": OWNER_DEVICE,
        "confidence": CONFIDENCE_HIGH,
        "basis": (
            "The evidence contains a failed local "
            "network connection to the Sonos device."
        ),
    },
}


def fallback_ownership(
    family,
):
    text = family_text(
        family
    )

    if (
        "components/hassio/"
        in text
        or "homeassistant.components.hassio"
        in text
        or "supervisor api"
        in text
    ):
        return {
            "ownership": OWNER_HA,
            "confidence": CONFIDENCE_MEDIUM,
            "basis": (
                "The evidence originates from the "
                "Home Assistant Supervisor/platform "
                "communication path."
            ),
        }

    if (
        "components/template/"
        in text
        and (
            "expected a number"
            in text
            or "invalid sensor state"
            in text
        )
    ):
        return {
            "ownership": OWNER_USER,
            "confidence": CONFIDENCE_MEDIUM,
            "basis": (
                "A Home Assistant template received "
                "a state that did not meet its local "
                "numeric expectation. Local template "
                "handling is a plausible action "
                "domain, although the upstream sensor "
                "state may also contribute."
            ),
        }

    if (
        "already running"
        in text
        and (
            "automation."
            in text
            or "script."
            in text
        )
    ):
        return {
            "ownership": OWNER_USER,
            "confidence": CONFIDENCE_HIGH,
            "basis": (
                "The warning is produced by local "
                "automation/script execution because "
                "another run is already active."
            ),
        }

    if (
        "websocket_api"
        in text
        and "no pong received"
        in text
    ):
        return {
            "ownership": OWNER_DEVICE,
            "confidence": CONFIDENCE_LOW,
            "basis": (
                "The evidence shows a Home Assistant "
                "client WebSocket losing its heartbeat. "
                "Client behaviour or local network "
                "connectivity are plausible, but the "
                "evidence is insufficient to assign a "
                "more specific cause."
            ),
        }

    return {
        "ownership": OWNER_UNKNOWN,
        "confidence": CONFIDENCE_LOW,
        "basis": (
            "The available System Log evidence does "
            "not identify one ownership domain with "
            "enough confidence. HA Audit leaves this "
            "unresolved rather than guessing."
        ),
    }


def classify_ownership(
    family,
):
    family_id = clean_text(
        family.get(
            "family_id",
            "",
        )
    )

    rule = OWNERSHIP_RULES.get(
        family_id
    )

    if rule is not None:
        return {
            "ownership": rule[
                "ownership"
            ],
            "confidence": rule[
                "confidence"
            ],
            "basis": rule[
                "basis"
            ],
            "method": (
                "deterministic_family_rule"
            ),
        }

    fallback = fallback_ownership(
        family
    )

    return {
        "ownership": fallback[
            "ownership"
        ],
        "confidence": fallback[
            "confidence"
        ],
        "basis": fallback[
            "basis"
        ],
        "method": (
            "conservative_evidence_fallback"
        ),
    }


def build_ownership_record(
    family,
):
    classification = (
        classify_ownership(
            family
        )
    )

    return {
        "family_id": family.get(
            "family_id"
        ),
        "title": family.get(
            "title"
        ),
        "grouping_method": family.get(
            "grouping_method"
        ),
        "source_entry_count": family.get(
            "source_entry_count",
            0,
        ),
        "occurrence_count": family.get(
            "occurrence_count",
            0,
        ),
        "first_seen": family.get(
            "first_seen"
        ),
        "last_seen": family.get(
            "last_seen"
        ),
        "ownership": classification[
            "ownership"
        ],
        "ownership_confidence": (
            classification[
                "confidence"
            ]
        ),
        "ownership_method": (
            classification[
                "method"
            ]
        ),
        "ownership_basis": (
            classification[
                "basis"
            ]
        ),
    }


def build_report(
    family_report,
):
    source_collection = (
        family_report.get(
            "source_collection",
            {},
        )
    )

    if not isinstance(
        source_collection,
        dict,
    ):
        source_collection = {}

    source_status = (
        source_collection.get(
            "status",
            "unknown",
        )
    )

    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "system_log_ownership_probe"
            ),
            "input": (
                "log_issue_families.json"
            ),
            "ownership_produced": True,
            "priority_produced": False,
            "severity_produced": False,
            "action_recommendation_produced": (
                False
            ),
            "ownership_note": (
                "Ownership identifies the most "
                "likely action or cause domain from "
                "the available evidence. It is not "
                "proof of root cause."
            ),
            "confidence_note": (
                "LOW confidence is intentionally "
                "used when multiple plausible domains "
                "remain. HA Audit prefers MIXED / "
                "UNKNOWN over unsupported certainty."
            ),
        },
        "source_collection": {
            "status": source_status,
            "error": source_collection.get(
                "error"
            ),
        },
        "summary": {},
        "families": [],
    }

    if source_status != "ok":
        return report

    families = family_report.get(
        "families",
        [],
    )

    if not isinstance(
        families,
        list,
    ):
        families = []

    records = [
        build_ownership_record(
            family
        )
        for family in families
        if isinstance(
            family,
            dict,
        )
    ]

    ownership_counts = {}

    confidence_counts = {}

    for record in records:
        ownership = record[
            "ownership"
        ]

        confidence = record[
            "ownership_confidence"
        ]

        ownership_counts[
            ownership
        ] = (
            ownership_counts.get(
                ownership,
                0,
            )
            + 1
        )

        confidence_counts[
            confidence
        ] = (
            confidence_counts.get(
                confidence,
                0,
            )
            + 1
        )

    report[
        "summary"
    ] = {
        "family_count": len(
            records
        ),
        "ownership_counts": (
            ownership_counts
        ),
        "confidence_counts": (
            confidence_counts
        ),
        "unresolved_family_count": sum(
            1
            for record in records
            if record[
                "ownership"
            ]
            == OWNER_UNKNOWN
        ),
        "priority_produced": False,
    }

    report[
        "families"
    ] = records

    return report


def main():
    try:
        family_report = load_json(
            INPUT_FILE
        )
    except Exception as exc:
        family_report = {
            "source_collection": {
                "status": (
                    "input_unavailable"
                ),
                "error": str(
                    exc
                ),
            },
            "families": [],
        }

    report = build_report(
        family_report
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            report,
            handle,
            indent=2,
            sort_keys=False,
        )

        handle.write(
            "\n"
        )


if __name__ == "__main__":
    main()
