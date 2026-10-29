#!/usr/bin/env python3
"""Read-only power-state evidence for HA Audit investigation context.

Correlates selected System Log record timestamps against a user-identified
physical power switch in Home Assistant Recorder. This does NOT identify every
error occurrence, prove a root cause, or change audit priority/status.

No files are written. All network calls use the Supervisor -> Core REST proxy.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

LOG_FAMILIES = Path('/config/log_issue_families.json')
SUPERVISOR_API = 'http://supervisor/core/api'
MAX_LOG_JSON_BYTES = 1024 * 1024
MAX_HISTORY_BYTES = 256 * 1024
MAX_EVENT_SAMPLES = 4
TIMEOUT_SECONDS = 5
POWER_SWITCH_PATTERN = re.compile(r'switch\.[a-z0-9_]+\Z')


def _read_json(path: Path, max_bytes: int) -> object | None:
    try:
        if path.stat().st_size > max_bytes:
            return None
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        return None


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 50:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except ValueError:
        return None


def _logged_times(family_id: str, source_file: Path) -> list[datetime]:
    """Use only actual first/last timestamps supplied by log source records."""
    data = _read_json(source_file, MAX_LOG_JSON_BYTES)
    if not isinstance(data, dict) or not isinstance(data.get('families'), list):
        return []
    family = next((f for f in data['families']
                   if isinstance(f, dict) and f.get('family_id') == family_id), None)
    members = family.get('members', []) if family else []
    if not isinstance(members, list):
        return []
    observed: set[datetime] = set()
    current_time = datetime.now(timezone.utc)
    for member in members[:25]:
        if isinstance(member, dict):
            for key in ('first_seen', 'last_seen'):
                instant = _timestamp(member.get(key))
                if instant is not None and instant <= current_time:
                    observed.add(instant)
    return sorted(observed, reverse=True)[:MAX_EVENT_SAMPLES]


def _state_from_history(groups: object, event_at: datetime) -> str:
    """Require an actual ON/OFF Recorder state timestamped at/before event."""
    if not isinstance(groups, list) or not groups or not isinstance(groups[0], list):
        return 'unknown'
    previous: tuple[datetime, str] | None = None
    for record in groups[0]:
        if not isinstance(record, dict):
            continue
        recorded = _timestamp(record.get('last_changed'))
        state = record.get('state')
        if recorded is None or recorded > event_at or not isinstance(state, str):
            continue
        if previous is None or recorded >= previous[0]:
            previous = (recorded, state)
    if previous is None or previous[1] not in ('on', 'off'):
        return 'unknown'
    return previous[1]


def _get_recorded_state(switch_id: str, event_at: datetime) -> tuple[str, str]:
    token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not token:
        return 'unknown', 'Supervisor API token unavailable'
    begin = (event_at - timedelta(minutes=60)).isoformat(timespec='seconds')
    end = (event_at + timedelta(seconds=30)).isoformat(timespec='seconds')
    url = (SUPERVISOR_API + '/history/period/' + quote(begin, safe='')
           + '?' + urlencode({'filter_entity_id': switch_id, 'end_time': end})
           + '&minimal_response&no_attributes')
    request = Request(url, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
    }, method='GET')
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_HISTORY_BYTES + 1)
        if len(raw) > MAX_HISTORY_BYTES:
            return 'unknown', 'Recorder response too large'
        history = json.loads(raw.decode('utf-8'))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError):
        return 'unknown', 'Recorder history unavailable'
    state = _state_from_history(history, event_at)
    if state == 'unknown':
        return state, 'No reliable ON/OFF state recorded at this time'
    return state, 'Recorder state at the sampled log timestamp'


def check_power_state(family_id: str, switch_id: str,
                      *, log_file: Path = LOG_FAMILIES) -> dict:
    """Return a bounded, evidence-only comparison; never persist conclusions.

    Caller should validate that the family and switch relationship were saved
    by the user before invoking this function. The saved relationship remains
    user-confirmed, not automatically discovered by HA Audit.
    """
    if not isinstance(family_id, str) or not re.fullmatch(r'[a-z0-9_]+', family_id):
        return {'status': 'invalid', 'message': 'Invalid issue identifier', 'samples': []}
    if not isinstance(switch_id, str) or not POWER_SWITCH_PATTERN.fullmatch(switch_id):
        return {'status': 'invalid', 'message': 'Invalid switch identifier', 'samples': []}
    times = _logged_times(family_id, log_file)
    if not times:
        return {'status': 'insufficient_evidence',
                'message': 'No individual source-record timestamps available', 'samples': []}
    samples = []
    for observed_at in times:
        state, basis = _get_recorded_state(switch_id, observed_at)
        samples.append({
            'observed_at_utc': observed_at.isoformat(timespec='seconds'),
            'power_state': state,
            'evidence': basis,
            'interpretation': (
                'consistent_with_expected_power_off' if state == 'off'
                else 'needs_investigation' if state == 'on' else 'unknown'),
        })
    return {
        'status': 'ok',
        'family_id': family_id,
        'power_entity_id': switch_id,
        'samples': samples,
        'limitation': ('Only first/last timestamps from sampled System Log records '
                       'are checked, not every occurrence. An OFF match is compatible '
                       'with the user explanation but does not prove its cause or '
                       'explain other errors. Missing Recorder data means UNKNOWN.'),
    }
