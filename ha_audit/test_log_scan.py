from log_scan import (
    analyse_log_text,
    build_report,
    fetch_core_logs,
    parse_log_line,
    redact_message,
)


SAMPLE_LOG = """
2026-10-07 19:00:00.100 INFO (MainThread) [homeassistant.core] Starting Home Assistant
2026-10-07 19:00:01.100 WARNING (MainThread) [homeassistant.components.demo] Connection retry scheduled
2026-10-07 19:00:02.100 WARNING (MainThread) [homeassistant.components.demo] Connection retry scheduled
2026-10-07 19:00:03.100 WARNING (MainThread) [homeassistant.components.demo] Connection retry scheduled
2026-10-07 19:00:04.100 ERROR (MainThread) [custom_components.example] Authentication failed token=abc123
2026-10-07 19:00:05.100 ERROR (MainThread) [custom_components.example] Authentication failed token=def456
unparsed journal line for parser review
"""


class FakeResponse:
    def __init__(
        self,
        status_code,
        text="",
    ):
        self.status_code = (
            status_code
        )
        self.text = text


class FakeSession:
    def __init__(
        self,
        response,
    ):
        self.response = response
        self.last_url = None
        self.last_headers = None
        self.last_params = None
        self.last_timeout = None

    def get(
        self,
        url,
        headers=None,
        params=None,
        timeout=None,
    ):
        self.last_url = url
        self.last_headers = headers
        self.last_params = params
        self.last_timeout = timeout

        return self.response


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def test_primary_parser():
    item = parse_log_line(
        (
            "2026-10-07 19:00:02.100 "
            "WARNING (MainThread) "
            "[homeassistant.components.demo] "
            "Connection retry scheduled"
        )
    )

    require(
        item is not None,
        "Primary parser did not match.",
    )

    require(
        item[
            "level"
        ] == "WARNING",
        "Incorrect parsed level.",
    )

    require(
        item[
            "source"
        ]
        == "homeassistant.components.demo",
        "Incorrect parsed source.",
    )

    require(
        item[
            "message"
        ]
        == "Connection retry scheduled",
        "Incorrect parsed message.",
    )


def test_redaction():
    redacted = redact_message(
        (
            "Failed request "
            "token=abc123 "
            "https://example.test/"
            "?key=value&password=secret"
        )
    )

    require(
        "abc123" not in redacted,
        "Token was not redacted.",
    )

    require(
        "secret" not in redacted,
        "Password was not redacted.",
    )

    require(
        "[REDACTED]"
        in redacted,
        "Redaction marker missing.",
    )


def test_grouping():
    result = analyse_log_text(
        SAMPLE_LOG
    )

    require(
        result[
            "nonempty_line_count"
        ] == 7,
        "Unexpected input line count.",
    )

    require(
        result[
            "parsed_line_count"
        ] == 6,
        "Unexpected parsed line count.",
    )

    require(
        result[
            "unparsed_line_count"
        ] == 1,
        "Unexpected unparsed line count.",
    )

    require(
        result[
            "repeated_group_count"
        ] >= 1,
        "Repeated group was not detected.",
    )

    demo_groups = [
        item
        for item
        in result[
            "groups"
        ]
        if (
            item.get(
                "source"
            )
            == "homeassistant.components.demo"
        )
    ]

    require(
        len(
            demo_groups
        ) == 1,
        "Demo warning should be one group.",
    )

    require(
        demo_groups[
            0
        ][
            "count"
        ] == 3,
        "Demo warning count should be 3.",
    )

    auth_groups = [
        item
        for item
        in result[
            "groups"
        ]
        if (
            item.get(
                "source"
            )
            == "custom_components.example"
        )
    ]

    require(
        len(
            auth_groups
        ) == 1,
        (
            "Redacted authentication errors "
            "should group together."
        ),
    )

    require(
        auth_groups[
            0
        ][
            "count"
        ] == 2,
        "Authentication error count should be 2.",
    )

    require(
        len(
            result[
                "unparsed_samples"
            ]
        ) == 1,
        "Unparsed sample was not retained.",
    )


def test_fetch_success():
    session = FakeSession(
        FakeResponse(
            200,
            SAMPLE_LOG,
        )
    )

    result = fetch_core_logs(
        session=session,
        token="test-token",
        lines=2000,
    )

    require(
        result[
            "status"
        ] == "ok",
        "Successful fetch did not return ok.",
    )

    require(
        session.last_url.endswith(
            "/core/logs"
        ),
        "Wrong Core log endpoint.",
    )

    require(
        session.last_headers.get(
            "Authorization"
        )
        == "Bearer test-token",
        "Supervisor token header missing.",
    )

    require(
        session.last_headers.get(
            "Accept"
        )
        == "text/x-log",
        "Annotated log Accept header missing.",
    )

    require(
        session.last_params.get(
            "lines"
        ) == 2000,
        "Requested line limit is wrong.",
    )

    require(
        "verbose"
        in session.last_params,
        "Verbose log option missing.",
    )

    require(
        "no_colors"
        in session.last_params,
        "No-colors option missing.",
    )


def test_permission_denied():
    session = FakeSession(
        FakeResponse(
            403,
            "Forbidden",
        )
    )

    result = fetch_core_logs(
        session=session,
        token="test-token",
    )

    require(
        result[
            "status"
        ] == "permission_denied",
        "403 should be permission_denied.",
    )

    report = build_report(
        result
    )

    require(
        report[
            "collection"
        ][
            "status"
        ]
        == "permission_denied",
        "Permission result not preserved.",
    )

    require(
        report[
            "scope"
        ][
            "judgement_produced"
        ]
        is False,
        "Probe must not produce a judgement.",
    )


def test_missing_token():
    session = FakeSession(
        FakeResponse(
            200,
            SAMPLE_LOG,
        )
    )

    result = fetch_core_logs(
        session=session,
        token="",
    )

    require(
        result[
            "status"
        ] == "token_unavailable",
        "Missing token state incorrect.",
    )

    require(
        session.last_url is None,
        (
            "No HTTP request should occur "
            "without a token."
        ),
    )


def main():
    test_primary_parser()
    test_redaction()
    test_grouping()
    test_fetch_success()
    test_permission_denied()
    test_missing_token()

    print("")
    print("=" * 62)
    print("HA AUDIT CORE LOG COLLECTION TEST")
    print("=" * 62)
    print(
        "Core log parser:              PASS"
    )
    print(
        "Sensitive-value redaction:    PASS"
    )
    print(
        "Repeated-message grouping:    PASS"
    )
    print(
        "Supervisor API request:       PASS"
    )
    print(
        "Bounded 2000-line request:    PASS"
    )
    print(
        "Permission-denied handling:   PASS"
    )
    print(
        "Missing-token handling:       PASS"
    )
    print(
        "No severity judgement:        PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
