import hashlib
import json
import os
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import requests


VERSION = os.environ.get("HA_AUDIT_VERSION", "unknown")

UPDATE_READINESS_FILE = "/config/update_readiness_audit.json"
OUTPUT_FILE = "/config/release_evidence_audit.json"

OFFICIAL_HOSTS = {
    "home-assistant.io",
    "www.home-assistant.io",
}

RELEASE_CATEGORY_URL = (
    "https://www.home-assistant.io/"
    "blog/categories/release-notes/"
)

MAX_RESPONSE_BYTES = 8 * 1024 * 1024

HEADERS = {
    "User-Agent": (
        f"HA-Audit/{VERSION} "
        "(https://github.com/pnm1977/home-assistant-ha-audit)"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_json_optional(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)

    except Exception:
        return {}


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ),
    ).strip()


def unique(values):
    seen = set()
    output = []

    for value in values:
        value = clean(
            value
        )

        if (
            value
            and value not in seen
        ):
            seen.add(
                value
            )

            output.append(
                value
            )

    return output


def normalise_core_version(value):
    if value is None:
        return None

    match = re.match(
        r"^[vV]?(\d{4})\.(\d{1,2})(?:\.(\d+))?",
        str(
            value
        ).strip(),
    )

    if not match:
        return None

    year = int(
        match.group(1)
    )

    month = int(
        match.group(2)
    )

    patch = match.group(
        3
    )

    result = (
        f"{year}.{month}"
    )

    if patch is not None:
        result += (
            f".{int(patch)}"
        )

    return result


def major_minor(value):
    value = normalise_core_version(
        value
    )

    if not value:
        return None

    parts = value.split(
        "."
    )

    return (
        f"{parts[0]}."
        f"{parts[1]}"
    )


def is_official_url(url):
    try:
        parsed = urlparse(
            url
        )

    except Exception:
        return False

    return (
        parsed.scheme == "https"
        and parsed.hostname
        in OFFICIAL_HOSTS
    )


def fetch_html(
    purpose,
    url,
):
    result = {
        "purpose": purpose,
        "url": url,
        "status": "not_started",
        "final_url": None,
        "http_status": None,
        "content_type": None,
        "etag": None,
        "last_modified": None,
        "content_sha256": None,
        "response_bytes": None,
        "error": None,
    }

    if not is_official_url(
        url
    ):
        result[
            "status"
        ] = "rejected"

        result[
            "error"
        ] = (
            "URL is not an approved official "
            "Home Assistant URL."
        )

        return None, result

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(
                5,
                20,
            ),
            allow_redirects=True,
        )

        result[
            "http_status"
        ] = response.status_code

        result[
            "final_url"
        ] = response.url

        result[
            "content_type"
        ] = response.headers.get(
            "Content-Type"
        )

        result[
            "etag"
        ] = response.headers.get(
            "ETag"
        )

        result[
            "last_modified"
        ] = response.headers.get(
            "Last-Modified"
        )

        if not is_official_url(
            response.url
        ):
            raise RuntimeError(
                "Official URL redirected to a "
                "non-approved host."
            )

        response.raise_for_status()

        content = response.content

        result[
            "response_bytes"
        ] = len(
            content
        )

        if len(
            content
        ) > MAX_RESPONSE_BYTES:
            raise RuntimeError(
                f"Response exceeded "
                f"{MAX_RESPONSE_BYTES} bytes."
            )

        result[
            "content_sha256"
        ] = hashlib.sha256(
            content
        ).hexdigest()

        result[
            "status"
        ] = "ok"

        encoding = (
            response.encoding
            or "utf-8"
        )

        return (
            content.decode(
                encoding,
                errors="replace",
            ),
            result,
        )

    except Exception as error:
        result[
            "status"
        ] = "error"

        result[
            "error"
        ] = str(
            error
        )

        return None, result


# ------------------------------------------------------------
# Generic link parser
# ------------------------------------------------------------

class LinkParser(
    HTMLParser
):

    def __init__(
        self,
    ):
        super().__init__(
            convert_charrefs=True
        )

        self.links = []

        self._href = None
        self._text = []
        self._skip = 0

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(
            attrs
        )

        if tag in (
            "script",
            "style",
        ):
            self._skip += 1
            return

        if (
            tag == "a"
            and not self._skip
        ):
            self._href = attrs.get(
                "href"
            )

            self._text = []

    def handle_endtag(
        self,
        tag,
    ):
        if tag in (
            "script",
            "style",
        ):
            if self._skip:
                self._skip -= 1

            return

        if (
            tag == "a"
            and not self._skip
        ):
            if self._href:
                self.links.append(
                    {
                        "href":
                            self._href,
                        "text":
                            clean(
                                " ".join(
                                    self._text
                                )
                            ),
                    }
                )

            self._href = None
            self._text = []

    def handle_data(
        self,
        data,
    ):
        if self._skip:
            return

        if self._href is not None:
            text = clean(
                data
            )

            if text:
                self._text.append(
                    text
                )


# ------------------------------------------------------------
# Release notes parser
# ------------------------------------------------------------

class ReleaseParser(
    HTMLParser
):

    def __init__(
        self,
    ):
        super().__init__(
            convert_charrefs=True
        )

        self.title = None
        self.published_at = None
        self.page_text = []

        self.section_found = False
        self.intro = []
        self.items = []

        self.section_links = []
        self.section_code_terms = []

        self.trailing_notes = ""

        self._skip = 0

        self._heading_level = None
        self._heading_id = None
        self._heading_text = []

        self._in_section = False
        self._current = None

        self._code = False
        self._code_text = []

    def _finish_item(
        self,
    ):
        if not self._current:
            return

        self._current[
            "text"
        ] = clean(
            " ".join(
                self._current.pop(
                    "_text",
                    [],
                )
            )
        )

        self._current[
            "links"
        ] = unique(
            self._current.get(
                "links",
                [],
            )
        )

        self._current[
            "code_terms"
        ] = unique(
            self._current.get(
                "code_terms",
                [],
            )
        )

        self.items.append(
            self._current
        )

        self._current = None

    def _finish_heading(
        self,
    ):
        level = (
            self._heading_level
        )

        heading_id = (
            self._heading_id
        )

        text = clean(
            " ".join(
                self._heading_text
            )
        )

        self._heading_level = None
        self._heading_id = None
        self._heading_text = []

        if (
            level == 1
            and text
            and not self.title
        ):
            self.title = text
            return

        if level == 2:
            if (
                text.lower()
                == "backward-incompatible changes"
                or heading_id
                == "backward-incompatible-changes"
            ):
                self.section_found = True
                self._in_section = True

            return

        if (
            level == 3
            and self._in_section
        ):
            self._finish_item()

            self._current = {
                "heading": text,
                "_text": [],
                "links": [],
                "code_terms": [],
            }

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        attrs = dict(
            attrs
        )

        if tag in (
            "script",
            "style",
        ):
            self._skip += 1
            return

        if self._skip:
            return

        if tag == "meta":
            key = (
                attrs.get(
                    "property"
                )
                or attrs.get(
                    "name"
                )
                or ""
            ).lower()

            if (
                key
                in (
                    "article:published_time",
                    "date",
                    "datepublished",
                )
                and attrs.get(
                    "content"
                )
                and not self.published_at
            ):
                self.published_at = (
                    attrs[
                        "content"
                    ]
                )

            return

        if (
            tag == "time"
            and attrs.get(
                "datetime"
            )
            and not self.published_at
        ):
            self.published_at = (
                attrs[
                    "datetime"
                ]
            )

        if tag in (
            "h1",
            "h2",
            "h3",
        ):
            level = int(
                tag[
                    1
                ]
            )

            if (
                level == 2
                and self._in_section
            ):
                self._finish_item()
                self._in_section = False

            self._heading_level = level

            self._heading_id = attrs.get(
                "id"
            )

            self._heading_text = []

            return

        if (
            tag == "a"
            and self._in_section
            and attrs.get(
                "href"
            )
        ):
            if self._current:
                self._current[
                    "links"
                ].append(
                    attrs[
                        "href"
                    ]
                )
            else:
                self.section_links.append(
                    attrs[
                        "href"
                    ]
                )

        if (
            tag == "code"
            and self._in_section
        ):
            self._code = True
            self._code_text = []

    def handle_endtag(
        self,
        tag,
    ):
        if tag in (
            "script",
            "style",
        ):
            if self._skip:
                self._skip -= 1

            return

        if self._skip:
            return

        if (
            tag in (
                "h1",
                "h2",
                "h3",
            )
            and self._heading_level
            == int(
                tag[
                    1
                ]
            )
        ):
            self._finish_heading()
            return

        if (
            tag == "code"
            and self._code
        ):
            term = clean(
                " ".join(
                    self._code_text
                )
            )

            if term:
                if self._current:
                    self._current[
                        "code_terms"
                    ].append(
                        term
                    )
                else:
                    self.section_code_terms.append(
                        term
                    )

            self._code = False
            self._code_text = []

    def handle_data(
        self,
        data,
    ):
        if self._skip:
            return

        text = clean(
            data
        )

        if not text:
            return

        self.page_text.append(
            text
        )

        if self._heading_level is not None:
            self._heading_text.append(
                text
            )

            return

        if not self._in_section:
            return

        if self._code:
            self._code_text.append(
                text
            )

        if self._current:
            self._current[
                "_text"
            ].append(
                text
            )
        else:
            self.intro.append(
                text
            )

    def close(
        self,
    ):
        super().close()

        if self._in_section:
            self._finish_item()
            self._in_section = False

        marker = (
            "If you are a custom integration developer"
        )

        if self.items:
            last = self.items[
                -1
            ]

            position = (
                last.get(
                    "text",
                    "",
                ).find(
                    marker
                )
            )

            if position >= 0:
                self.trailing_notes = clean(
                    last[
                        "text"
                    ][
                        position:
                    ]
                )

                last[
                    "text"
                ] = clean(
                    last[
                        "text"
                    ][
                        :position
                    ]
                )


# ------------------------------------------------------------
# Release notes discovery
# ------------------------------------------------------------

def score_release_link(
    link,
    base_url,
    target_major_minor,
):
    href = link.get(
        "href"
    )

    if not href:
        return None

    absolute = urljoin(
        base_url,
        href,
    )

    if not is_official_url(
        absolute
    ):
        return None

    path = urlparse(
        absolute
    ).path.lower()

    text = clean(
        link.get(
            "text"
        )
    ).lower()

    if "/blog/" not in path:
        return None

    token = (
        target_major_minor.replace(
            ".",
            "",
        )
    )

    score = 0

    if "release-" in path:
        score += 20

    if (
        f"release-{token}"
        in path
    ):
        score += 50

    if target_major_minor in text:
        score += 30

    if "release notes" in text:
        score += 10

    if not score:
        return None

    return (
        score,
        absolute,
    )


def choose_release_link(
    links,
    base_url,
    target_major_minor,
):
    candidates = []

    for link in links:
        scored = score_release_link(
            link,
            base_url,
            target_major_minor,
        )

        if scored:
            candidates.append(
                scored
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[
                0
            ],
            item[
                1
            ],
        ),
        reverse=True,
    )

    return (
        candidates[
            0
        ][
            1
        ]
    )


def discover_release_url(
    target_major_minor,
    attempts,
):
    changelog_url = (
        "https://www.home-assistant.io/"
        f"changelogs/core-{target_major_minor}/"
    )

    html, attempt = fetch_html(
        "core_changelog",
        changelog_url,
    )

    attempts.append(
        attempt
    )

    if html:
        parser = LinkParser()

        parser.feed(
            html
        )

        parser.close()

        found = choose_release_link(
            parser.links,
            (
                attempt.get(
                    "final_url"
                )
                or changelog_url
            ),
            target_major_minor,
        )

        if found:
            return {
                "status":
                    "ok",
                "method":
                    "core_changelog_link",
                "changelog_url":
                    changelog_url,
                "release_notes_url":
                    found,
                "error":
                    None,
            }

    html, attempt = fetch_html(
        "release_notes_category_fallback",
        RELEASE_CATEGORY_URL,
    )

    attempts.append(
        attempt
    )

    if html:
        parser = LinkParser()

        parser.feed(
            html
        )

        parser.close()

        found = choose_release_link(
            parser.links,
            (
                attempt.get(
                    "final_url"
                )
                or RELEASE_CATEGORY_URL
            ),
            target_major_minor,
        )

        if found:
            return {
                "status":
                    "ok",
                "method":
                    "release_notes_category_fallback",
                "changelog_url":
                    changelog_url,
                "release_notes_url":
                    found,
                "error":
                    None,
            }

    return {
        "status":
            "error",
        "method":
            None,
        "changelog_url":
            changelog_url,
        "release_notes_url":
            None,
        "error": (
            "Could not discover the official "
            "release-notes page for Core "
            f"{target_major_minor}."
        ),
    }


# ------------------------------------------------------------
# Release notes extraction
# ------------------------------------------------------------

def absolute_links(
    values,
    base_url,
):
    return unique(
        urljoin(
            base_url,
            value,
        )
        for value in values
    )


def parse_release_notes(
    html,
    release_url,
    target_version,
):
    parser = ReleaseParser()

    parser.feed(
        html
    )

    parser.close()

    items = []

    for item in parser.items:
        items.append(
            {
                "heading":
                    item.get(
                        "heading"
                    ),
                "text":
                    item.get(
                        "text"
                    ),
                "code_terms":
                    unique(
                        item.get(
                            "code_terms",
                            [],
                        )
                    ),
                "links":
                    absolute_links(
                        item.get(
                            "links",
                            [],
                        ),
                        release_url,
                    ),
            }
        )

    page_text = clean(
        " ".join(
            parser.page_text
        )
    )

    return {
        "status":
            "ok",
        "url":
            release_url,
        "title":
            parser.title,
        "published_at":
            parser.published_at,
        "target_version":
            target_version,
        "target_version_mentioned":
            bool(
                target_version
                and target_version
                in page_text
            ),
        "backward_incompatible_changes": {
            "section_found":
                parser.section_found,
            "item_count":
                len(
                    items
                ),
            "intro":
                clean(
                    " ".join(
                        parser.intro
                    )
                ),
            "section_code_terms":
                unique(
                    parser.section_code_terms
                ),
            "section_links":
                absolute_links(
                    parser.section_links,
                    release_url,
                ),
            "items":
                items,
            "trailing_notes":
                parser.trailing_notes,
        },
    }


# ------------------------------------------------------------
# Existing update-readiness evidence
# ------------------------------------------------------------

update_readiness = load_json_optional(
    UPDATE_READINESS_FILE
)

core_window = update_readiness.get(
    "core_upgrade_window",
    {},
)

if not isinstance(
    core_window,
    dict,
):
    core_window = {}

pending = bool(
    core_window.get(
        "pending"
    )
)

installed_version = (
    core_window.get(
        "installed_version"
    )
)

target_version = (
    core_window.get(
        "target_version"
    )
)

target_major_minor = major_minor(
    target_version
)

applicable = bool(
    update_readiness
    and pending
    and target_version
    and target_major_minor
)

reason = None

if not update_readiness:
    reason = (
        "update_readiness_audit.json "
        "is unavailable."
    )

elif not pending:
    reason = (
        "There is no pending Home Assistant "
        "Core update."
    )

elif not target_version:
    reason = (
        "The pending Core update does not "
        "provide a target version."
    )

elif not target_major_minor:
    reason = (
        "The pending Core target could not "
        "be normalised to a year.month release."
    )


# ------------------------------------------------------------
# Report foundation
# ------------------------------------------------------------

report = {
    "audit_version":
        VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "scope": {
        "phase":
            "official_release_evidence",
        "local_evidence_only":
            False,
        "external_fetch_performed":
            False,
        "official_sources_only":
            True,
        "compatibility_assessed":
            False,
        "readiness_verdict_produced":
            False,
        "note": (
            "This report retrieves official Home Assistant "
            "release evidence for a pending Core target. "
            "It records source material for later matching; "
            "it does not decide whether the upgrade affects "
            "this installation and does not produce a "
            "safe-to-update verdict."
        ),
    },

    "core_upgrade_window": {
        "pending":
            pending,
        "installed_version":
            installed_version,
        "installed_version_source":
            core_window.get(
                "installed_version_source"
            ),
        "target_version":
            target_version,
        "target_major_minor":
            target_major_minor,
    },

    "applicability": {
        "applicable":
            applicable,
        "reason":
            reason,
    },

    "source_policy": {
        "approved_hosts":
            sorted(
                OFFICIAL_HOSTS
            ),
        "discovery_order": [
            "Predictable official Core changelog page",
            "Official release-notes category fallback",
        ],
        "maximum_response_bytes":
            MAX_RESPONSE_BYTES,
        "request_timeout_seconds": {
            "connect": 5,
            "read": 20,
        },
    },

    "source_discovery": {
        "status":
            "not_started",
        "method":
            None,
        "changelog_url":
            None,
        "release_notes_url":
            None,
        "error":
            None,
    },

    "fetch_attempts":
        [],

    "release_notes": {
        "status":
            "not_fetched",
        "url":
            None,
        "title":
            None,
        "published_at":
            None,
        "target_version":
            target_version,
        "target_version_mentioned":
            False,
        "backward_incompatible_changes": {
            "section_found":
                False,
            "item_count":
                0,
            "intro":
                "",
            "section_code_terms":
                [],
            "section_links":
                [],
            "items":
                [],
            "trailing_notes":
                "",
        },
    },

    "collector_status": {
        "update_readiness_report":
            (
                "ok"
                if update_readiness
                else "unavailable"
            ),
        "source_discovery":
            "not_started",
        "release_notes_fetch":
            "not_started",
        "release_notes_parse":
            "not_started",
    },
}


# ------------------------------------------------------------
# Official external evidence collection
# ------------------------------------------------------------

if applicable:
    attempts = report[
        "fetch_attempts"
    ]

    discovery = discover_release_url(
        target_major_minor,
        attempts,
    )

    report[
        "scope"
    ][
        "external_fetch_performed"
    ] = bool(
        attempts
    )

    report[
        "source_discovery"
    ] = discovery

    report[
        "collector_status"
    ][
        "source_discovery"
    ] = discovery[
        "status"
    ]

    release_url = discovery.get(
        "release_notes_url"
    )

    if release_url:
        html, attempt = fetch_html(
            "release_notes",
            release_url,
        )

        attempts.append(
            attempt
        )

        report[
            "collector_status"
        ][
            "release_notes_fetch"
        ] = attempt[
            "status"
        ]

        if html:
            try:
                report[
                    "release_notes"
                ] = parse_release_notes(
                    html,
                    (
                        attempt.get(
                            "final_url"
                        )
                        or release_url
                    ),
                    target_version,
                )

                report[
                    "collector_status"
                ][
                    "release_notes_parse"
                ] = "ok"

            except Exception as error:
                report[
                    "release_notes"
                ][
                    "status"
                ] = "parse_error"

                report[
                    "release_notes"
                ][
                    "url"
                ] = (
                    attempt.get(
                        "final_url"
                    )
                    or release_url
                )

                report[
                    "release_notes"
                ][
                    "error"
                ] = str(
                    error
                )

                report[
                    "collector_status"
                ][
                    "release_notes_parse"
                ] = "error"

        else:
            report[
                "release_notes"
            ][
                "status"
            ] = "fetch_error"

            report[
                "release_notes"
            ][
                "url"
            ] = release_url

            report[
                "release_notes"
            ][
                "error"
            ] = attempt.get(
                "error"
            )

            report[
                "collector_status"
            ][
                "release_notes_parse"
            ] = "not_run"

    else:
        report[
            "collector_status"
        ][
            "release_notes_fetch"
        ] = "not_run"

        report[
            "collector_status"
        ][
            "release_notes_parse"
        ] = "not_run"


# ------------------------------------------------------------
# Write report
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("")
print(
    "Official release evidence"
)

print(
    "------------------------------------------"
)

print(
    f"Applicable:                    "
    f"{applicable}"
)

print(
    f"Installed Core:                "
    f"{installed_version}"
)

print(
    f"Target Core:                   "
    f"{target_version}"
)

print(
    f"Target release:                "
    f"{target_major_minor}"
)

if applicable:
    backward = (
        report[
            "release_notes"
        ][
            "backward_incompatible_changes"
        ]
    )

    print(
        "Source discovery:              "
        f"{report['collector_status']['source_discovery']}"
    )

    print(
        "Release notes fetch:           "
        f"{report['collector_status']['release_notes_fetch']}"
    )

    print(
        "Release notes parse:           "
        f"{report['collector_status']['release_notes_parse']}"
    )

    print(
        "Backward-incompatible section: "
        f"{backward.get('section_found', False)}"
    )

    print(
        "Breaking-change headings:      "
        f"{backward.get('item_count', 0)}"
    )

    print(
        "Target patch mentioned:        "
        f"{report['release_notes'].get('target_version_mentioned', False)}"
    )

else:
    print(
        f"Reason:                        "
        f"{reason}"
    )

print("")

print(
    f"Detailed report: "
    f"{OUTPUT_FILE}"
)
