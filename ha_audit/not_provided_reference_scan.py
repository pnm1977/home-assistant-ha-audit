import json
import os
import re
from collections import Counter
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

CONFIG_ROOT = "/homeassistant"

AUDIT_FILE = "/config/audit_snapshot.json"
QUALITY_FILE = "/config/quality_audit.json"

OUTPUT_FILE = (
    "/config/not_provided_reference_audit.json"
)


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def relative_path(path):
    return os.path.relpath(
        path,
        CONFIG_ROOT,
    )


audit = load_json(
    AUDIT_FILE
)

quality = load_json(
    QUALITY_FILE
)


not_provided_entities = (
    audit.get(
        "entities",
        {},
    )
    .get(
        "not_currently_provided",
        {},
    )
    .get(
        "entities",
        [],
    )
)


active_yaml = (
    quality.get(
        "configuration_tree",
        {},
    )
    .get(
        "active_yaml",
        [],
    )
)


active_files = []

for relative in active_yaml:
    path = os.path.normpath(
        os.path.join(
            CONFIG_ROOT,
            relative,
        )
    )

    if not path.startswith(
        CONFIG_ROOT + os.sep
    ):
        continue

    if os.path.isfile(
        path
    ):
        active_files.append(
            path
        )


entity_ids = {
    item.get("entity_id")
    for item in not_provided_entities
    if item.get("entity_id")
}


patterns = {
    entity_id: re.compile(
        r"(?<![A-Za-z0-9_])"
        + re.escape(
            entity_id
        )
        + r"(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
    for entity_id in entity_ids
}


reference_locations = {
    entity_id: {}
    for entity_id in entity_ids
}


for path in sorted(
    active_files
):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            lines = handle.readlines()

    except Exception:
        continue

    rel = relative_path(
        path
    )

    for line_number, line in enumerate(
        lines,
        start=1,
    ):
        if line.lstrip().startswith(
            "#"
        ):
            continue

        for entity_id, pattern in (
            patterns.items()
        ):
            if pattern.search(
                line
            ):
                reference_locations[
                    entity_id
                ].setdefault(
                    rel,
                    set(),
                ).add(
                    line_number
                )


referenced = []
unreferenced = []

referenced_by_platform = Counter()
unreferenced_by_platform = Counter()


for item in not_provided_entities:
    entity_id = item.get(
        "entity_id"
    )

    if not entity_id:
        continue

    locations = (
        reference_locations.get(
            entity_id,
            {},
        )
    )

    result = dict(
        item
    )

    if locations:
        formatted_locations = []

        for file_path in sorted(
            locations
        ):
            formatted_locations.append(
                {
                    "file": file_path,
                    "lines": sorted(
                        locations[
                            file_path
                        ]
                    ),
                }
            )

        result[
            "active_yaml_references"
        ] = formatted_locations

        referenced.append(
            result
        )

        referenced_by_platform[
            item.get(
                "platform",
                "unknown",
            )
        ] += 1

    else:
        result[
            "active_yaml_references"
        ] = []

        unreferenced.append(
            result
        )

        unreferenced_by_platform[
            item.get(
                "platform",
                "unknown",
            )
        ] += 1


referenced.sort(
    key=lambda item: (
        item.get(
            "platform",
            "",
        ),
        item.get(
            "entity_id",
            "",
        ),
    )
)

unreferenced.sort(
    key=lambda item: (
        item.get(
            "platform",
            "",
        ),
        item.get(
            "entity_id",
            "",
        ),
    )
)


template_referenced = [
    item
    for item in referenced
    if item.get(
        "platform"
    ) == "template"
]

template_unreferenced = [
    item
    for item in unreferenced
    if item.get(
        "platform"
    ) == "template"
]


report = {
    "audit_version": VERSION,

    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "summary": {
        "not_currently_provided":
            len(
                not_provided_entities
            ),

        "referenced_in_active_yaml":
            len(
                referenced
            ),

        "no_active_yaml_reference":
            len(
                unreferenced
            ),

        "template_not_currently_provided":
            (
                len(
                    template_referenced
                )
                + len(
                    template_unreferenced
                )
            ),

        "template_referenced_in_active_yaml":
            len(
                template_referenced
            ),

        "template_no_active_yaml_reference":
            len(
                template_unreferenced
            ),
    },

    "referenced_by_platform":
        dict(
            referenced_by_platform.most_common()
        ),

    "unreferenced_by_platform":
        dict(
            unreferenced_by_platform.most_common()
        ),

    "referenced_entities":
        referenced,

    "unreferenced_entities":
        unreferenced,

    "notes": {
        "scope":
            (
                "Only active YAML files from "
                "quality_audit.json are scanned."
            ),

        "fully_commented_lines_ignored":
            True,

        "interpretation":
            (
                "No active YAML reference does "
                "not by itself prove an entity is "
                "safe to delete. UI-managed "
                "configuration and external "
                "dependencies may exist."
            ),
    },
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        report,
        handle,
        indent=2,
    )


print("")
print(
    "Not-provided entity reference audit"
)
print(
    "------------------------------------------"
)

print(
    f"Not provided entities:       "
    f"{len(not_provided_entities)}"
)

print(
    f"Referenced in active YAML:   "
    f"{len(referenced)}"
)

print(
    f"No active YAML reference:    "
    f"{len(unreferenced)}"
)

print("")
print(
    "Template not-provided entities"
)
print(
    "------------------------------------------"
)

print(
    f"Total:                       "
    f"{len(template_referenced) + len(template_unreferenced)}"
)

print(
    f"Referenced in active YAML:   "
    f"{len(template_referenced)}"
)

print(
    f"No active YAML reference:    "
    f"{len(template_unreferenced)}"
)


if template_referenced:
    print("")
    print(
        "Template entities still referenced:"
    )
    print(
        "------------------------------------------"
    )

    for item in template_referenced:
        print(
            item[
                "entity_id"
            ]
        )

        for location in item[
            "active_yaml_references"
        ]:
            lines = ",".join(
                str(line)
                for line in location[
                    "lines"
                ]
            )

            print(
                f"  {location['file']}: "
                f"{lines}"
            )


if template_unreferenced:
    print("")
    print(
        "Template cleanup candidates:"
    )
    print(
        "------------------------------------------"
    )

    for item in template_unreferenced:
        print(
            item[
                "entity_id"
            ]
        )


print("")
print(
    f"Reference report saved: "
    f"{OUTPUT_FILE}"
)
