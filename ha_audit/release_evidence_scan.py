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
    "https://www.home-assistant.io/blog/categories/release-notes/"
)

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_RELEASE_FAMILIES = 24

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
            return json.load(
                handle
            )

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

    if month < 1 or month > 12:
        return None

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


def parse_year_month(value):
    value = major_minor(
        value
    )

    if not value:
        return None

    year_text, month_text = value.split(
        ".",
        1,
    )

    try:
        year = int(
            year_text
        )

        month = int(
            month_text
        )

    except ValueError:
        return None

    if month < 1 or month > 12:
        return None

    return (
        year,
        month,
    )


def month_index(year_month):
    if not year_month:
        return None

    year, month = year_month

    return (
        year * 12
        + month
        - 1
    )


def month_from_index(index):
    year = index // 12

    month = (
        index % 12
    ) + 1

    return (
        year,
        month,
    )


def format_year_month(year_month):
    if not year_month:
        return None

    year, month = year_month

    return (
        f"{year}.{month}"
    )


def calculate_release_range(
    installed_version,
    target_version,
):
    installed_year_month = parse_year_month(
        installed_version
    )

    target_year_month = parse_year_month(
        target_version
    )

    result = {
        "status": "unknown",
        "complete": False,
        "installed_major_minor": major_minor(
            installed_version
        ),
        "target_major_minor": major_minor(
            target_version
        ),
        "same_release_family": False,
        "crossed_release_families": [],
        "release_families_to_fetch": [],
        "crossed_release_family_count": 0,
        "release_family_fetch_count": 0,
        "note": None,
    }

    if not target_year_month:
        result[
            "status"
        ] = "target_version_unavailable"

        result[
            "note"
        ] = (
            "The pending Core target could not be normalised "
            "to a year.month release family."
        )

        return result

    target_family = format_year_month(
        target_year_month
    )

    if not installed_year_month:
        result[
            "status"
        ] = "installed_version_unavailable"

        result[
            "release_families_to_fetch"
        ] = [
            target_family
        ]

        result[
            "release_family_fetch_count"
        ] = 1

        result[
            "note"
        ] = (
            "The installed Core release family is unavailable, "
            "so only the target release family can be fetched. "
            "Coverage of intermediate releases is incomplete."
        )

        return result

    installed_index = month_index(
        installed_year_month
    )

    target_index = month_index(
        target_year_month
    )

    if target_index < installed_index:
        result[
            "status"
        ] = "target_precedes_installed"

        result[
            "note"
        ] = (
            "The pending Core target release family precedes "
            "the installed release family."
        )

        return result

    if target_index == installed_index:
        result[
            "status"
        ] = "same_release_family"

        result[
            "complete"
        ] = True

        result[
            "same_release_family"
        ] = True

        result[
            "release_families_to_fetch"
        ] = [
            target_family
        ]

        result[
            "release_family_fetch_count"
        ] = 1

        result[
            "note"
        ] = (
            "The update stays within one monthly Core release "
            "family. The target family is fetched for exact "
            "patch/changelog evidence, but its monthly backward-"
            "incompatible changes are not classified as newly crossed."
        )

        return result

    crossed_count = (
        target_index
        - installed_index
    )

    if crossed_count > MAX_RELEASE_FAMILIES:
        result[
            "status"
        ] = "range_too_large"

        result[
            "note"
        ] = (
            "The Core release range crosses more than "
            f"{MAX_RELEASE_FAMILIES} monthly release families. "
            "Automatic release evidence collection is intentionally "
            "bounded and coverage is incomplete."
        )

        return result

    crossed = []

    for index in range(
        installed_index + 1,
        target_index + 1,
    ):
        crossed.append(
            format_year_month(
                month_from_index(
                    index
                )
            )
        )

    result[
        "status"
    ] = "crosses_release_families"

    result[
        "complete"
    ] = True

    result[
        "crossed_release_families"
    ] = crossed

    result[
        "release_families_to_fetch"
    ] = list(
        crossed
    )

    result[
        "crossed_release_family_count"
    ] = len(
        crossed
    )

    result[
        "release_family_fetch_count"
    ] = len(
        crossed
    )

    result[
        "note"
    ] = (
        "Every monthly Core release family crossed by the "
        "installed-to-target upgrade window will be fetched."
    )

    return result


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
    release_family=None,
):
    result = {
        "purpose": purpose,
        "release_family": release_family,
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
        if (
            self._skip
            or self._href is None
        ):
            return

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
    """
    Parses the Backward-incompatible changes section.

    Home Assistant currently renders each change from a details block,
    producing HTML details/summary elements. h3 headings remain supported
    as a fallback for older or future page structures.
    """

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
        self._in_section = False

        self._heading_level = None
        self._heading_id = None
        self._heading_text = []

        self._current = None
        self._current_structure = None
        self._seen_item = False

        self._in_summary = False
        self._summary_text = []

        self._code = False
        self._code_text = []

        self._trailing = []

    def _start_item(
        self,
        heading=None,
        structure=None,
    ):
        if self._current:
            self._finish_item()

        self._current = {
            "heading":
                clean(
                    heading
                )
                or None,
            "_text":
                [],
            "links":
                [],
            "code_terms":
                [],
            "source_structure":
                structure,
        }

        self._current_structure = structure
        self._seen_item = True

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

        if (
            self._current.get(
                "heading"
            )
            or self._current.get(
                "text"
            )
        ):
            self.items.append(
                self._current
            )

        self._current = None
        self._current_structure = None

        self._in_summary = False
        self._summary_text = []

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
            and not self._current
        ):
            self._start_item(
                heading=text,
                structure="h3",
            )

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

            elif (
                level == 3
                and self._in_section
                and self._current_structure
                == "h3"
            ):
                self._finish_item()

            self._heading_level = level

            self._heading_id = attrs.get(
                "id"
            )

            self._heading_text = []

            return

        if (
            tag == "details"
            and self._in_section
        ):
            self._start_item(
                structure="details",
            )

            return

        if (
            tag == "summary"
            and self._in_section
            and self._current
        ):
            self._in_summary = True
            self._summary_text = []

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
            tag
            in (
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
            tag == "summary"
            and self._in_summary
        ):
            heading = clean(
                " ".join(
                    self._summary_text
                )
            )

            if (
                self._current
                and heading
            ):
                self._current[
                    "heading"
                ] = heading

            self._in_summary = False
            self._summary_text = []

            return

        if (
            tag == "details"
            and self._in_section
            and self._current_structure
            == "details"
        ):
            self._finish_item()
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

        if self._in_summary:
            self._summary_text.append(
                text
            )

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

        elif self._seen_item:
            self._trailing.append(
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

        if self._current:
            self._finish_item()

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
                self._trailing.insert(
                    0,
                    clean(
                        last[
                            "text"
                        ][
                            position:
                        ]
                    ),
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

        self.trailing_notes = clean(
            " ".join(
                self._trailing
            )
        )

        self._in_section = False


# ------------------------------------------------------------
# Release-note discovery
# ------------------------------------------------------------

def score_release_link(
    link,
    base_url,
    release_family,
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
        release_family.replace(
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

    if release_family in text:
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
    release_family,
):
    candidates = []

    for link in links:
        scored = score_release_link(
            link,
            base_url,
            release_family,
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
    release_family,
    attempts,
):
    changelog_url = (
        "https://www.home-assistant.io/"
        f"changelogs/core-{release_family}/"
    )

    html, attempt = fetch_html(
        "core_changelog",
        changelog_url,
        release_family=release_family,
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
            release_family,
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
        release_family=release_family,
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
            release_family,
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
            f"{release_family}."
        ),
    }


# ------------------------------------------------------------
# Release-note extraction
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
    release_family,
    target_version=None,
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
                "release_family":
                    release_family,
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
                "source_structure":
                    item.get(
                        "source_structure"
                    ),
            }
        )

    all_section_code_terms = unique(
        list(
            parser.section_code_terms
        )
        + [
            term
            for item in items
            for term
            in item.get(
                "code_terms",
                [],
            )
        ]
    )

    all_section_links = unique(
        absolute_links(
            parser.section_links,
            release_url,
        )
        + [
            link
            for item in items
            for link
            in item.get(
                "links",
                [],
            )
        ]
    )

    page_text = clean(
        " ".join(
            parser.page_text
        )
    )

    section_phrase_present = (
        "backward-incompatible changes"
        in page_text.lower()
    )

    if (
        parser.section_found
        and items
    ):
        segmentation_status = (
            "structured"
        )

    elif (
        parser.section_found
        or section_phrase_present
    ):
        segmentation_status = (
            "unstructured"
        )

    else:
        segmentation_status = (
            "no_section"
        )

    return {
        "status":
            "ok",
        "release_family":
            release_family,
        "url":
            release_url,
        "title":
            parser.title,
        "published_at":
            parser.published_at,
        "target_version":
            target_version,
        "release_family_mentioned":
            bool(
                release_family
                and release_family
                in page_text
            ),
        "target_version_mentioned":
            bool(
                target_version
                and target_version
                in page_text
            ),
        "backward_incompatible_changes": {
            "section_found":
                parser.section_found,
            "section_phrase_present":
                section_phrase_present,
            "item_count":
                len(
                    items
                ),
            "segmentation_status":
                segmentation_status,
            "intro":
                clean(
                    " ".join(
                        parser.intro
                    )
                ),
            "section_code_terms":
                all_section_code_terms,
            "section_links":
                all_section_links,
            "items":
                items,
            "trailing_notes":
                parser.trailing_notes,
        },
    }


def classify_parse_status(release_notes):
    backward = release_notes.get(
        "backward_incompatible_changes",
        {},
    )

    segmentation_status = backward.get(
        "segmentation_status"
    )

    if segmentation_status == "structured":
        return "ok"

    if segmentation_status == "no_section":
        return "ok_no_backward_incompatible_section"

    return "partial"


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

release_range = calculate_release_range(
    installed_version,
    target_version,
)

release_families_to_fetch = release_range.get(
    "release_families_to_fetch",
    [],
)

if not isinstance(
    release_families_to_fetch,
    list,
):
    release_families_to_fetch = []

crossed_release_families = release_range.get(
    "crossed_release_families",
    [],
)

if not isinstance(
    crossed_release_families,
    list,
):
    crossed_release_families = []

applicable = bool(
    update_readiness
    and pending
    and target_version
    and release_families_to_fetch
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

elif not release_families_to_fetch:
    reason = (
        release_range.get(
            "note"
        )
        or (
            "No Core release family could be "
            "selected for official evidence collection."
        )
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
        "multi_release_range_supported":
            True,
        "compatibility_assessed":
            False,
        "readiness_verdict_produced":
            False,
        "note": (
            "This report retrieves official Home Assistant "
            "release evidence for every monthly Core release "
            "family crossed by a pending upgrade window. "
            "For a same-family patch update, the target family "
            "is fetched for patch/changelog evidence but its "
            "monthly backward-incompatible changes are not "
            "classified as newly crossed. The report records "
            "source material for later matching; it does not "
            "produce a safe-to-update verdict."
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

    "release_range":
        release_range,

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
        "maximum_release_families":
            MAX_RELEASE_FAMILIES,
        "maximum_response_bytes":
            MAX_RESPONSE_BYTES,
        "request_timeout_seconds": {
            "connect": 5,
            "read": 20,
        },
    },

    "fetch_attempts":
        [],

    "releases":
        [],

    "aggregate": {
        "release_family_count":
            len(
                release_families_to_fetch
            ),
        "crossed_release_family_count":
            len(
                crossed_release_families
            ),
        "release_families_requested":
            release_families_to_fetch,
        "crossed_release_families":
            crossed_release_families,
        "release_family_success_count":
            0,
        "release_family_partial_count":
            0,
        "release_family_failure_count":
            0,
        "backward_incompatible_section_count":
            0,
        "breaking_change_group_count":
            0,
        "breaking_change_group_count_crossed_only":
            0,
        "breaking_change_groups":
            [],
        "section_code_terms":
            [],
        "section_links":
            [],
    },

    "collector_status": {
        "update_readiness_report":
            (
                "ok"
                if update_readiness
                else "unavailable"
            ),
        "release_range":
            release_range.get(
                "status"
            ),
        "overall":
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

    releases = report[
        "releases"
    ]

    for release_family in release_families_to_fetch:
        crossed_from_installed = (
            release_family
            in crossed_release_families
        )

        release_result = {
            "release_family":
                release_family,
            "crossed_from_installed":
                crossed_from_installed,
            "is_target_release_family":
                release_family
                == target_major_minor,
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
            "release_notes": {
                "status":
                    "not_fetched",
                "release_family":
                    release_family,
                "url":
                    None,
                "title":
                    None,
                "published_at":
                    None,
                "target_version":
                    (
                        target_version
                        if release_family
                        == target_major_minor
                        else None
                    ),
                "release_family_mentioned":
                    False,
                "target_version_mentioned":
                    False,
                "backward_incompatible_changes": {
                    "section_found":
                        False,
                    "section_phrase_present":
                        False,
                    "item_count":
                        0,
                    "segmentation_status":
                        "not_run",
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
                "source_discovery":
                    "not_started",
                "release_notes_fetch":
                    "not_started",
                "release_notes_parse":
                    "not_started",
            },
        }

        discovery = discover_release_url(
            release_family,
            attempts,
        )

        release_result[
            "source_discovery"
        ] = discovery

        release_result[
            "collector_status"
        ][
            "source_discovery"
        ] = discovery.get(
            "status"
        )

        release_url = discovery.get(
            "release_notes_url"
        )

        if release_url:
            html, attempt = fetch_html(
                "release_notes",
                release_url,
                release_family=release_family,
            )

            attempts.append(
                attempt
            )

            release_result[
                "collector_status"
            ][
                "release_notes_fetch"
            ] = attempt.get(
                "status"
            )

            if html:
                try:
                    parsed = parse_release_notes(
                        html,
                        (
                            attempt.get(
                                "final_url"
                            )
                            or release_url
                        ),
                        release_family,
                        target_version=(
                            target_version
                            if release_family
                            == target_major_minor
                            else None
                        ),
                    )

                    release_result[
                        "release_notes"
                    ] = parsed

                    release_result[
                        "collector_status"
                    ][
                        "release_notes_parse"
                    ] = classify_parse_status(
                        parsed
                    )

                except Exception as error:
                    release_result[
                        "release_notes"
                    ][
                        "status"
                    ] = "parse_error"

                    release_result[
                        "release_notes"
                    ][
                        "url"
                    ] = (
                        attempt.get(
                            "final_url"
                        )
                        or release_url
                    )

                    release_result[
                        "release_notes"
                    ][
                        "error"
                    ] = str(
                        error
                    )

                    release_result[
                        "collector_status"
                    ][
                        "release_notes_parse"
                    ] = "error"

            else:
                release_result[
                    "release_notes"
                ][
                    "status"
                ] = "fetch_error"

                release_result[
                    "release_notes"
                ][
                    "url"
                ] = release_url

                release_result[
                    "release_notes"
                ][
                    "error"
                ] = attempt.get(
                    "error"
                )

                release_result[
                    "collector_status"
                ][
                    "release_notes_parse"
                ] = "not_run"

        else:
            release_result[
                "collector_status"
            ][
                "release_notes_fetch"
            ] = "not_run"

            release_result[
                "collector_status"
            ][
                "release_notes_parse"
            ] = "not_run"

        releases.append(
            release_result
        )

    report[
        "scope"
    ][
        "external_fetch_performed"
    ] = bool(
        attempts
    )


# ------------------------------------------------------------
# Aggregate release evidence
# ------------------------------------------------------------

release_success_count = 0
release_partial_count = 0
release_failure_count = 0

backward_section_count = 0

breaking_groups = []

all_code_terms = []
all_links = []

for release in report[
    "releases"
]:
    statuses = release.get(
        "collector_status",
        {},
    )

    parse_status = statuses.get(
        "release_notes_parse"
    )

    if parse_status in (
        "ok",
        "ok_no_backward_incompatible_section",
    ):
        release_success_count += 1

    elif parse_status == "partial":
        release_partial_count += 1

    else:
        release_failure_count += 1

    release_notes = release.get(
        "release_notes",
        {},
    )

    backward = release_notes.get(
        "backward_incompatible_changes",
        {},
    )

    if backward.get(
        "section_found"
    ):
        backward_section_count += 1

    all_code_terms.extend(
        backward.get(
            "section_code_terms",
            [],
        )
    )

    all_links.extend(
        backward.get(
            "section_links",
            [],
        )
    )

    for item in backward.get(
        "items",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        aggregate_item = dict(
            item
        )

        aggregate_item[
            "crossed_from_installed"
        ] = bool(
            release.get(
                "crossed_from_installed"
            )
        )

        aggregate_item[
            "release_notes_url"
        ] = release_notes.get(
            "url"
        )

        breaking_groups.append(
            aggregate_item
        )

report[
    "aggregate"
][
    "release_family_success_count"
] = release_success_count

report[
    "aggregate"
][
    "release_family_partial_count"
] = release_partial_count

report[
    "aggregate"
][
    "release_family_failure_count"
] = release_failure_count

report[
    "aggregate"
][
    "backward_incompatible_section_count"
] = backward_section_count

report[
    "aggregate"
][
    "breaking_change_group_count"
] = len(
    breaking_groups
)

report[
    "aggregate"
][
    "breaking_change_group_count_crossed_only"
] = sum(
    1
    for item in breaking_groups
    if item.get(
        "crossed_from_installed"
    )
)

report[
    "aggregate"
][
    "breaking_change_groups"
] = breaking_groups

report[
    "aggregate"
][
    "section_code_terms"
] = unique(
    all_code_terms
)

report[
    "aggregate"
][
    "section_links"
] = unique(
    all_links
)

if not applicable:
    overall_status = "not_applicable"

elif release_failure_count:
    if (
        release_success_count
        or release_partial_count
    ):
        overall_status = "partial"

    else:
        overall_status = "error"

elif release_partial_count:
    overall_status = "partial"

else:
    overall_status = "ok"

report[
    "collector_status"
][
    "overall"
] = overall_status


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

print(
    f"Release-range status:          "
    f"{release_range.get('status')}"
)

print(
    f"Crossed release families:      "
    f"{len(crossed_release_families)}"
)

if crossed_release_families:
    print(
        "Crossed releases:              "
        + ", ".join(
            crossed_release_families
        )
    )

print(
    f"Release families fetched:      "
    f"{len(release_families_to_fetch)}"
)

if applicable:
    print(
        f"Successful release parses:     "
        f"{release_success_count}"
    )

    print(
        f"Partial release parses:        "
        f"{release_partial_count}"
    )

    print(
        f"Failed release parses:         "
        f"{release_failure_count}"
    )

    print(
        f"Breaking-change groups:        "
        f"{len(breaking_groups)}"
    )

    print(
        "Crossed-only change groups:    "
        f"{report['aggregate']['breaking_change_group_count_crossed_only']}"
    )

    print(
        f"Overall collection status:     "
        f"{overall_status}"
    )

    print("")
    print(
        "Per-release evidence:"
    )

    print(
        "------------------------------------------"
    )

    for release in report[
        "releases"
    ]:
        family = release.get(
            "release_family"
        )

        parse_status = release.get(
            "collector_status",
            {},
        ).get(
            "release_notes_parse"
        )

        backward = release.get(
            "release_notes",
            {},
        ).get(
            "backward_incompatible_changes",
            {},
        )

        crossed_label = (
            "crossed"
            if release.get(
                "crossed_from_installed"
            )
            else "same-family evidence"
        )

        print(
            f"{family}: "
            f"{parse_status}; "
            f"{backward.get('item_count', 0)} group(s); "
            f"{crossed_label}"
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
