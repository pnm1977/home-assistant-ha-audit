import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone


CONFIG_ROOT = "/homeassistant"
OUTPUT_FILE = "/config/config_inventory.json"

# Deliberately excluded from scanning.
EXCLUDED_DIRS = {
    ".git",
    ".storage",
    ".cloud",
    "backup",
    "backups",
    "custom_components",
    "deps",
    "esphome",
    "media",
    "tts",
    "www",
}

INCLUDE_PATTERN = re.compile(
    r"!(include(?:_dir_(?:list|named|merge_list|merge_named))?)\s+([^\s#]+)"
)


if not os.path.isdir(CONFIG_ROOT):
    raise RuntimeError(
        f"Home Assistant config mount not found: {CONFIG_ROOT}"
    )


files = []
by_top_level = Counter()
hashes = defaultdict(list)

total_lines = 0
total_secret_references = 0


for root, dirs, filenames in os.walk(CONFIG_ROOT):

    # Prevent traversal into private/unnecessary locations.
    dirs[:] = [
        directory
        for directory in dirs
        if directory not in EXCLUDED_DIRS
        and not directory.startswith(".")
    ]

    for filename in filenames:
        lower = filename.lower()

        # Never inspect any YAML file whose name suggests secrets.
        if "secret" in lower:
            continue

        if not lower.endswith((".yaml", ".yml")):
            continue

        full_path = os.path.join(root, filename)

        relative_path = os.path.relpath(
            full_path,
            CONFIG_ROOT,
        )

        try:
            with open(full_path, "rb") as handle:
                content = handle.read()

            text = content.decode(
                "utf-8",
                errors="replace",
            )

            line_count = len(text.splitlines())
            total_lines += line_count

            secret_reference_count = text.count(
                "!secret "
            )

            total_secret_references += (
                secret_reference_count
            )

            include_directives = [
                {
                    "type": match.group(1),
                    "target": match.group(2),
                }
                for match in INCLUDE_PATTERN.finditer(text)
            ]

            digest = hashlib.sha256(
                content
            ).hexdigest()

            hashes[digest].append(
                relative_path
            )

            first_component = relative_path.split(
                os.sep,
                1,
            )[0]

            top_level = (
                "(root)"
                if first_component == relative_path
                else first_component
            )

            by_top_level[top_level] += 1

            stat = os.stat(full_path)

            files.append(
                {
                    "path": relative_path,
                    "size_bytes": stat.st_size,
                    "lines": line_count,
                    "modified_utc": datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    ).isoformat(),
                    "sha256": digest,
                    "secret_reference_count":
                        secret_reference_count,
                    "include_directives":
                        include_directives,
                }
            )

        except Exception as error:
            files.append(
                {
                    "path": relative_path,
                    "error": str(error),
                }
            )


duplicate_groups = [
    {
        "sha256": digest,
        "files": sorted(paths),
    }
    for digest, paths in hashes.items()
    if len(paths) > 1
]


largest_files = sorted(
    [
        item
        for item in files
        if "lines" in item
    ],
    key=lambda item: item["lines"],
    reverse=True,
)[:20]


inventory = {
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "scanner_version": "0.6.0",

    "config_root": CONFIG_ROOT,

    "yaml_file_count": len(files),

    "total_yaml_lines": total_lines,

    "total_secret_references":
        total_secret_references,

    "files_by_top_level": dict(
        sorted(by_top_level.items())
    ),

    "exact_duplicate_group_count": len(
        duplicate_groups
    ),

    "exact_duplicate_groups":
        duplicate_groups,

    "largest_yaml_files":
        largest_files,

    "files": sorted(
        files,
        key=lambda item: item["path"],
    ),

    "excluded_directories": sorted(
        EXCLUDED_DIRS
    ),

    "secret_named_files_excluded": True,

    "stores_file_contents": False,
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:

    json.dump(
        inventory,
        handle,
        indent=2,
    )


print("")
print("Configuration inventory")
print("------------------------------------------")

print(
    f"YAML files:          "
    f"{inventory['yaml_file_count']}"
)

print(
    f"YAML lines:          "
    f"{inventory['total_yaml_lines']}"
)

print(
    f"!secret references:  "
    f"{inventory['total_secret_references']}"
)

print(
    f"Exact duplicates:    "
    f"{inventory['exact_duplicate_group_count']}"
)


print("")
print("Files by top-level location:")

for location, count in by_top_level.most_common():
    print(
        f"{location:<32} {count:>5}"
    )


print("")
print("Largest YAML files:")

for item in largest_files[:15]:
    print(
        f"{item['path']:<48} "
        f"{item['lines']:>7} lines"
    )


if duplicate_groups:
    print("")
    print("Exact duplicate YAML groups:")

    for group in duplicate_groups[:10]:
        print(
            "  "
            + "  <->  ".join(
                group["files"]
            )
        )


print("")
print(
    f"Inventory saved: {OUTPUT_FILE}"
)
