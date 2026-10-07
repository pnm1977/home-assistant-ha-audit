import json

from log_scan import (
    build_report,
    collect_system_log,
    normalise_entry,
    redact_text,
)


SYSTEM_LOG_RESULT = [
    {
        "name": (
            "homeassistant.components.demo"
        ),
        "message": [
            "Connection retry scheduled",
        ],
        "level": "WARNING",
        "source": [
            "components/demo/__init__.py",
            42,
        ],
        "timestamp": 1791403205.0,
        "exception": "",
        "count": 184,
        "first_occurred": 1791400000.0,
    },
    {
        "name": (
            "custom_components.example"
        ),
        "message": [
            (
                "Authentication failed "
                "token=abc123"
            ),
            (
                "Authentication failed "
                "token=def456"
            ),
        ],
        "level": "ERROR",
        "source": [
            "custom_components/example/api.py",
            120,
        ],
        "timestamp": 1791403210.0,
        "exception": (
            "Request failed "
            "password=secret-value"
        ),
        "count": 4,
        "first_occurred": 1791401000.0,
    },
]


class FakeWebSocket:
    def __init__(
        self,
        responses,
    ):
        self.responses = list(
            responses
        )
        self.sent = []
        self.closed = False

    def recv(
        self,
    ):
        return json.dumps(
            self.responses.pop(
                0
            )
        )

    def send(
        self,
        value,
    ):
        self.sent.append(
            json.loads(
                value
            )
        )

    def close(
        self,
    ):
        self.closed = True


class FakeFactory:
    def __init__(
        self,
        websocket_instance,
    ):
        self.websocket_instance = (
            websocket_instance
        )
        self.url = None
        self.timeout = None
        self.suppress_origin = None

    def __call__(
        self,
        url,
        timeout=None,
        suppress_origin=None,
    ):
        self.url = url
        self.timeout = timeout
        self.suppress_origin = (
            suppress_origin
        )

        return self.websocket_instance


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def test_redaction():
    value = redact_text(
        (
            "token=abc123 "
            "password=secret "
            "Authorization=Bearer123"
        )
    )

    require(
        "abc123" not in value,
        "Token was not redacted.",
    )

    require(
        "secret" not in value,
        "Password was not redacted.",
    )

    require(
        "[REDACTED]"
        in value,
        "Redaction marker missing.",
    )


def test_normalise_entry():
    item = normalise_entry(
        SYSTEM_LOG_RESULT[
            1
        ]
    )

    require(
        item[
            "level"
        ] == "ERROR",
        "Incorrect level.",
    )

    require(
        item[
            "count"
        ] == 4,
        "Incorrect occurrence count.",
    )

    require(
        item[
            "source"
        ][
            "file"
        ]
        == (
            "custom_components/"
            "example/api.py"
        ),
        "Incorrect source file.",
    )

    require(
        item[
            "source"
        ][
            "line"
        ] == 120,
        "Incorrect source line.",
    )

    require(
        "abc123"
        not in item[
            "messages"
        ][
            0
        ],
        "Message token was not redacted.",
    )

    require(
        "secret-value"
        not in item[
            "exception"
        ],
        "Exception secret was not redacted.",
    )

    require(
        item[
            "first_seen"
        ]
        is not None,
        "First timestamp missing.",
    )

    require(
        item[
            "last_seen"
        ]
        is not None,
        "Last timestamp missing.",
    )


def test_collection_success():
    fake_ws = FakeWebSocket(
        [
            {
                "type": (
                    "auth_required"
                ),
            },
            {
                "type": (
                    "auth_ok"
                ),
            },
            {
                "id": 1,
                "type": "result",
                "success": True,
                "result": (
                    SYSTEM_LOG_RESULT
                ),
            },
        ]
    )

    factory = FakeFactory(
        fake_ws
    )

    result = collect_system_log(
        ws_factory=factory,
        token="test-token",
    )

    require(
        result[
            "status"
        ] == "ok",
        "Collection did not succeed.",
    )

    require(
        len(
            result[
                "entries"
            ]
        ) == 2,
        "Unexpected entry count.",
    )

    require(
        factory.url
        == (
            "ws://supervisor/"
            "core/websocket"
        ),
        "Wrong WebSocket URL.",
    )

    require(
        fake_ws.sent[
            0
        ][
            "type"
        ]
        == "auth",
        "Authentication message missing.",
    )

    require(
        fake_ws.sent[
            0
        ][
            "access_token"
        ]
        == "test-token",
        "Authentication token missing.",
    )

    require(
        fake_ws.sent[
            1
        ]
        == {
            "id": 1,
            "type": (
                "system_log/list"
            ),
        },
        "Wrong System Log command.",
    )

    require(
        fake_ws.closed,
        "WebSocket was not closed.",
    )


def test_command_denied():
    fake_ws = FakeWebSocket(
        [
            {
                "type": (
                    "auth_required"
                ),
            },
            {
                "type": (
                    "auth_ok"
                ),
            },
            {
                "id": 1,
                "type": "result",
                "success": False,
                "error": {
                    "code": (
                        "unauthorized"
                    ),
                    "message": (
                        "Unauthorized"
                    ),
                },
            },
        ]
    )

    result = collect_system_log(
        ws_factory=FakeFactory(
            fake_ws
        ),
        token="test-token",
    )

    require(
        result[
            "status"
        ] == "command_failed",
        (
            "Denied command should be "
            "reported cleanly."
        ),
    )


def test_missing_token():
    fake_ws = FakeWebSocket(
        []
    )

    result = collect_system_log(
        ws_factory=FakeFactory(
            fake_ws
        ),
        token="",
    )

    require(
        result[
            "status"
        ]
        == "token_unavailable",
        "Missing-token state incorrect.",
    )


def test_report():
    collection = {
        "status": "ok",
        "entries": (
            SYSTEM_LOG_RESULT
        ),
        "error": None,
    }

    report = build_report(
        collection
    )

    require(
        report[
            "collection"
        ][
            "status"
        ] == "ok",
        "Collection status lost.",
    )

    require(
        report[
            "scope"
        ][
            "judgement_produced"
        ]
        is False,
        "Probe produced a judgement.",
    )

    require(
        report[
            "scope"
        ][
            "severity_produced"
        ]
        is False,
        "Probe produced severity.",
    )

    require(
        report[
            "summary"
        ][
            "entries_returned"
        ] == 2,
        "Incorrect entry summary.",
    )

    require(
        report[
            "summary"
        ][
            "total_occurrence_count"
        ] == 188,
        "Incorrect occurrence total.",
    )

    require(
        report[
            "summary"
        ][
            "highest_repeat_count"
        ] == 184,
        "Incorrect highest repeat count.",
    )

    require(
        report[
            "entries"
        ][
            0
        ][
            "count"
        ] == 184,
        (
            "Highest recurring entry "
            "should sort first."
        ),
    )


def main():
    test_redaction()
    test_normalise_entry()
    test_collection_success()
    test_command_denied()
    test_missing_token()
    test_report()

    print("")
    print("=" * 62)
    print(
        "HA AUDIT SYSTEM LOG COLLECTION TEST"
    )
    print("=" * 62)
    print(
        "Sensitive-value redaction:    PASS"
    )
    print(
        "System Log normalisation:     PASS"
    )
    print(
        "WebSocket authentication:     PASS"
    )
    print(
        "system_log/list collection:   PASS"
    )
    print(
        "Denied-command handling:      PASS"
    )
    print(
        "Missing-token handling:       PASS"
    )
    print(
        "Occurrence counts retained:   PASS"
    )
    print(
        "No severity judgement:        PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
