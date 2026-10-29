"""Reusable read-only checks for Home Assistant Core compatibility rules.

The generic rule selector determines the target-version policy. Checks in
this module know nothing about specific Core releases or patch dates.

Never interpret a clean result as a safe-to-update verdict. A YAML parse or
inspection error must be propagated to the caller as INCOMPLETE coverage.
"""

import re

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


# Names identify detectable YAML *patterns*, not specific release rules.
STATE_DURATION_PATTERNS = frozenset({
    "attribute_with_for",
    "state_list_with_for",
    "helper_state_with_for",
})

# State references to these helpers are explicitly supported in the existing
# condition syntax. Other dynamic references are outside this check's scope.
_HELPER_STATE = re.compile(
    r"input_(?:boolean|datetime|number|select|text)\." r"[a-z0-9_]+\Z",
    re.IGNORECASE,
)
_MAX_NODE_VISITS = 50_000
_MAX_NESTING = 80


def _mapping_fields(node):
    if not isinstance(node, MappingNode):
        return {}
    return {
        key.value: value
        for key, value in node.value
        if isinstance(key, ScalarNode)
    }


def _scalar(node):
    return node.value if isinstance(node, ScalarNode) else None


def find_state_condition_conflicts(
    text, source="active_yaml", *, rule_id, prohibited_patterns
):
    """Find state-condition patterns forbidden by a selected compatibility rule.

    ``rule_id`` and ``prohibited_patterns`` are supplied by the *version-aware
    rule runner*, not hardcoded here. This allows a later patch/release to
    enable a previously forbidden pattern without modifying this scanner.

    Returns findings with a source and one-based line number, including
    nested conditions. No verdict is produced. The caller must handle
    ValueError/yaml.YAMLError as uninspected rather than clear.
    """
    if not isinstance(text, str):
        raise ValueError("YAML source must be text")
    if not isinstance(rule_id, str) or not re.fullmatch(r"[a-z0-9_]+", rule_id):
        raise ValueError("Valid compatibility rule_id required")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Valid source path required")
    if not isinstance(prohibited_patterns, (list, tuple, set, frozenset)):
        raise ValueError("prohibited_patterns must be a list or set")
    if any(not isinstance(item, str) for item in prohibited_patterns):
        raise ValueError("prohibited_patterns must contain strings")
    prohibited = frozenset(prohibited_patterns)
    if not prohibited.issubset(STATE_DURATION_PATTERNS):
        raise ValueError("Unknown state-duration compatibility pattern")

    document = yaml.compose(text, Loader=yaml.SafeLoader)
    if document is None:
        return []

    findings = []
    visited = 0

    def visit(node, ancestors, depth):
        nonlocal visited
        visited += 1
        if visited > _MAX_NODE_VISITS or depth > _MAX_NESTING:
            raise ValueError("YAML structure exceeds safe inspection limits")
        if id(node) in ancestors:
            raise ValueError("Cyclic YAML alias prevents complete inspection")

        parents = ancestors | {id(node)}
        if isinstance(node, MappingNode):
            fields = _mapping_fields(node)
            if _scalar(fields.get("condition")) == "state" and "for" in fields:
                patterns = []
                if "attribute" in fields:
                    patterns.append("attribute_with_for")
                if isinstance(fields.get("state"), SequenceNode):
                    patterns.append("state_list_with_for")
                state_text = _scalar(fields.get("state"))
                if state_text and _HELPER_STATE.fullmatch(state_text):
                    patterns.append("helper_state_with_for")

                reasons = [name for name in patterns if name in prohibited]
                if reasons:
                    findings.append({
                        "rule_id": rule_id,
                        "file": source,
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
