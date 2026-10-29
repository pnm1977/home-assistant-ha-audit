"""Targeted, read-only Core 2026.10 state-condition duration check.

This module examines parsed YAML structure. It does not validate the whole
Home Assistant configuration, expand includes, or produce an update verdict.
The caller must treat YAML parse/inspection errors as incomplete coverage.
"""

import re

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


RULE_ID = "core_2026_10_state_conditions_for"

# Home Assistant supports comparing a state against these helper domains.
HELPER_STATE = re.compile(
    r"input_(?:boolean|datetime|number|select|text)\."
    r"[a-z0-9_]+\Z",
    re.IGNORECASE,
)

MAX_NODE_VISITS = 50000
MAX_NESTING = 80


def _fields(node):
    """Get scalar-key fields from a YAML mapping node."""
    if not isinstance(node, MappingNode):
        return {}
    return {
        key.value: value
        for key, value in node.value
        if isinstance(key, ScalarNode)
    }


def _scalar(node):
    return node.value if isinstance(node, ScalarNode) else None


def find_unsupported_state_durations(text, source="active_yaml"):
    """Return structurally identified Core 2026.10 incompatibilities.

    One finding is emitted per offending ``condition: state`` mapping, even
    if it has multiple conflicting options. ``line`` is the 1-based YAML
    location of the condition mapping. All nested conditions are inspected.

    Raises ``yaml.YAMLError`` or ``ValueError`` if the input cannot be
    inspected safely. Callers must NOT convert those failures into 'clear'.
    """
    if not isinstance(text, str):
        raise ValueError("YAML source must be text")

    document = yaml.compose(text, Loader=yaml.SafeLoader)
    if document is None:
        return []

    findings = []
    visited = 0

    def visit(node, ancestors, depth):
        nonlocal visited
        visited += 1
        if visited > MAX_NODE_VISITS or depth > MAX_NESTING:
            raise ValueError("YAML structure exceeds safe inspection limits")
        if id(node) in ancestors:
            raise ValueError("Cyclic YAML alias prevents complete inspection")

        parents = ancestors | {id(node)}
        if isinstance(node, MappingNode):
            fields = _fields(node)
            if (
                _scalar(fields.get("condition")) == "state"
                and "for" in fields
            ):
                reasons = []
                if "attribute" in fields:
                    reasons.append("attribute_with_for")
                if isinstance(fields.get("state"), SequenceNode):
                    reasons.append("state_list_with_for")
                state_text = _scalar(fields.get("state"))
                if state_text and HELPER_STATE.fullmatch(state_text):
                    reasons.append("helper_state_with_for")

                if reasons:
                    findings.append({
                        "rule_id": RULE_ID,
                        "file": str(source),
                        "line": node.start_mark.line + 1,
                        "entity_id": _scalar(fields.get("entity_id")),
                        "reasons": reasons,
                    })

            for key, value in node.value:
                visit(key, parents, depth + 1)
                visit(value, parents, depth + 1)
        elif isinstance(node, SequenceNode):
            for child in node.value:
                visit(child, parents, depth + 1)

    visit(document, frozenset(), 0)
    return findings
