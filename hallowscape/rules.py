"""Pure story-state logic: predicates, payoff rules, node rendering.

Nothing in this module imports discord or touches the database, so the whole
memory-and-consequence loop is testable by simulation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

COMPARISON = re.compile(r"^\s*(>=|<=|!=|>|<|=)?\s*(-?\d+)\s*$")

KNOWN_WHEN_KEYS = {
    "has_flags",
    "has_any",
    "lacks_flags",
    "flag_equals",
    "has_items",
    "lacks_items",
    "relation",
    "ledger",
    "watcher_at_least",
    "watcher_below",
    "visits_at_least",
    "visited_at_least",
    "took",
    "previous_runs",
    "scares_enabled",
}

# Keys a choice or payoff block may carry to mutate PlayerState.
EFFECT_KEYS = (
    "item",
    "items",
    "clue",
    "clues",
    "flag",
    "flags",
    "flags_list",
    "relation",
    "ledger",
    "watcher",
    "queue_event",
    "queue_events",
)

CHOICE_KEYS = {
    "id",
    "label",
    "next",
    "when",
    "hide_if_locked",
    "style",
    "emoji",
    "requires_item",
    "requires_items",
    "scare",
    "payoff",
    "ending",
    *EFFECT_KEYS,
}

PAYOFF_KEYS = {
    "id",
    "when",
    "chapter",
    "after_chapter",
    "line",
    "replace_text",
    "scare",
    "choices",
    "once",
    *EFFECT_KEYS,
}

# A `next` may name a place the player already holds instead of a fixed node.
DYNAMIC_TARGETS = {"@checkpoint", "@self"}


def _compare(actual: int, spec: Any) -> bool:
    if isinstance(spec, (int, float)):
        return actual >= int(spec)
    match = COMPARISON.match(str(spec))
    if not match:
        raise ValueError(f"Unreadable comparison: {spec!r}")
    op, number = match.group(1) or ">=", int(match.group(2))
    if op == ">=":
        return actual >= number
    if op == "<=":
        return actual <= number
    if op == ">":
        return actual > number
    if op == "<":
        return actual < number
    if op == "!=":
        return actual != number
    return actual == number


@dataclass
class PlayerState:
    """Everything the town remembers about one player."""

    chapter: str
    checkpoint: str = ""
    inventory: list[str] = field(default_factory=list)
    journal: list[str] = field(default_factory=list)
    flags: dict[str, Any] = field(default_factory=dict)
    relations: dict[str, int] = field(default_factory=dict)
    ledger: dict[str, int] = field(default_factory=dict)
    watcher: int = 0
    visits: dict[str, int] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    echoes: dict[str, Any] = field(default_factory=dict)
    previous_runs: int = 0
    scares_enabled: bool = True
    alias: str = ""
    ending: str | None = None

    @property
    def name(self) -> str:
        """What the town calls you."""
        return (self.alias or "stranger").strip()[:32] or "stranger"

    def choices_taken(self) -> set[str]:
        return {entry["choice"] for entry in self.history}

    def node(self) -> str:
        return self.chapter


@dataclass
class RenderedNode:
    node_id: str
    title: str
    description: str
    choices: list[dict[str, Any]]
    locked: list[dict[str, Any]]
    scares: list[str]
    payoffs: list[str] = field(default_factory=list)


def matches(when: dict[str, Any] | None, st: PlayerState) -> bool:
    if not when:
        return True
    unknown = set(when) - KNOWN_WHEN_KEYS
    if unknown:
        raise ValueError(f"Unknown predicate keys: {sorted(unknown)}")
    flags, relations, ledger = st.flags, st.relations, st.ledger

    if not all(st.flags.get(key) for key in when.get("has_flags", [])):
        return False
    if when.get("has_any") and not any(flags.get(key) for key in when["has_any"]):
        return False
    if any(flags.get(key) for key in when.get("lacks_flags", [])):
        return False
    for key, expected in when.get("flag_equals", {}).items():
        if flags.get(key) != expected:
            return False
    if not all(item in st.inventory for item in when.get("has_items", [])):
        return False
    if any(item in st.inventory for item in when.get("lacks_items", [])):
        return False
    for npc, spec in when.get("relation", {}).items():
        if not _compare(int(relations.get(npc, 0)), spec):
            return False
    for tag, spec in when.get("ledger", {}).items():
        if not _compare(int(ledger.get(tag, 0)), spec):
            return False
    if "watcher_at_least" in when and not _compare(st.watcher, when["watcher_at_least"]):
        return False
    if "watcher_below" in when and not _compare(-st.watcher, when["watcher_below"]):
        return False
    if "visits_at_least" in when and not _compare(st.visits.get(st.node(), 0), when["visits_at_least"]):
        return False
    for node, spec in when.get("visited_at_least", {}).items():
        if not _compare(st.visits.get(node, 0), spec):
            return False
    if not set(when.get("took", [])).issubset(st.choices_taken()):
        return False
    if not _compare(st.previous_runs, when.get("previous_runs", 0)):
        return False
    if "scares_enabled" in when and bool(when["scares_enabled"]) != st.scares_enabled:
        return False
    return True


def resolve_payoffs(
    rules: list[dict[str, Any]],
    node_id: str,
    order: dict[str, int],
    st: PlayerState,
    fired: set[str],
) -> list[dict[str, Any]]:
    """Payoff rules are evaluated only when the player reaches their chapter.

    `after_chapter` gates on the player having already visited that node, which
    is what lets a consequence land later in the same chapter.
    """
    ready: list[dict[str, Any]] = []
    for rule in rules:
        if rule.get("once", True) and rule["id"] in fired:
            continue
        target = rule.get("chapter")
        if target != node_id:
            continue
        gate = rule.get("after_chapter")
        if gate and not st.visits.get(gate, 0):
            continue
        if matches(rule.get("when"), st):
            ready.append(rule)
    return ready


NAME_TOKEN = re.compile(r"\{name\}")


def with_names(text: str, st: PlayerState) -> str:
    """Prose may address the player by their chosen alias."""
    return NAME_TOKEN.sub(st.name, text)


def _lines_of(node: dict[str, Any], st: PlayerState) -> list[str]:
    out: list[str] = []
    base = node.get("description", "")
    if base:
        out.append(with_names(base, st))
    for entry in node.get("echoes", []):
        if matches(entry.get("when"), st):
            out.append(with_names(entry["text"], st))
    for entry in node.get("lines", []):
        if matches(entry.get("when"), st):
            out.append(with_names(entry["text"], st))
    for entry in node.get("variants", []):
        if matches(entry.get("when"), st):
            out.append(with_names(entry["text"], st))
            break
    return out


def render_node(
    node_id: str,
    node: dict[str, Any],
    st: PlayerState,
    choices: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    order: dict[str, int],
    fired: set[str],
) -> RenderedNode:
    lines = _lines_of(node, st)
    ready = resolve_payoffs(rules, node_id, order, st, fired)
    extra_choices: list[dict[str, Any]] = []
    scares: list[str] = []
    fired_ids: list[str] = []
    for rule in ready:
        fired_ids.append(rule["id"])
        if rule.get("line"):
            lines.append(with_names(rule["line"], st))
        if rule.get("scare") and st.scares_enabled:
            scares.append(rule["scare"])
        for choice in rule.get("choices", []):
            extra_choices.append({**choice, "payoff": rule["id"]})
        if rule.get("replace_text"):
            lines.insert(0, with_names(rule["replace_text"], st))

    visible: list[dict[str, Any]] = []
    locked: list[dict[str, Any]] = []
    for choice in [*choices, *extra_choices]:
        if not matches(choice.get("when"), st):
            continue
        need = [choice["requires_item"]] if choice.get("requires_item") else list(choice.get("requires_items", []))
        missing = [item for item in need if item not in st.inventory]
        if missing and choice.get("hide_if_locked"):
            continue
        visible.append({**choice, "_missing": missing})
        if missing:
            locked.append({**choice, "_missing": missing})

    if node.get("scare") and st.scares_enabled:
        scares.append(node["scare"])
    return RenderedNode(
        node_id=node_id,
        title=node.get("title", node_id),
        description="\n\n".join([line for line in lines if line]),
        choices=visible,
        locked=locked,
        scares=scares,
        payoffs=fired_ids,
    )


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def apply_effects(st: PlayerState, spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Mutate state from a choice or payoff block; return events to queue."""
    queued: list[dict[str, Any]] = []
    for item in _as_list(spec.get("item")) + list(spec.get("items", [])):
        if item not in st.inventory:
            st.inventory.append(item)
    for clue in _as_list(spec.get("clue")) + list(spec.get("clues", [])):
        if clue not in st.journal:
            st.journal.append(clue)

    pairs: list[tuple[str, Any]] = []
    if spec.get("flag"):
        pairs.append((str(spec["flag"]), True))
    for flag in spec.get("flags_list", []):
        pairs.append((flag, True))
    for key, value in (spec.get("flags") or {}).items():
        pairs.append((key, value))
    for key, value in pairs:
        st.flags[key] = value

    for npc, delta in (spec.get("relation") or {}).items():
        st.relations[npc] = int(st.relations.get(npc, 0)) + int(delta)
    for tag, delta in (spec.get("ledger") or {}).items():
        st.ledger[tag] = int(st.ledger.get(tag, 0)) + int(delta)
    if spec.get("watcher"):
        st.watcher = max(0, st.watcher + int(spec["watcher"]))

    for event in [_as_list(spec.get("queue_event")), spec.get("queue_events", [])]:
        for entry in event:
            queued.append(
                {
                    "kind": entry.get("kind", "town_change"),
                    "text": entry["text"],
                    "due_in": int(entry.get("due_in", 0)),
                    "flag": entry.get("flag"),
                }
            )
    return queued


def missing_items(choice: dict[str, Any], st: PlayerState) -> list[str]:
    need = [choice["requires_item"]] if choice.get("requires_item") else list(choice.get("requires_items", []))
    return [item for item in need if item not in st.inventory]


def resolve_target(raw: Any, st: PlayerState) -> str:
    """Turn a `next` into a node id, honouring the dynamic targets hubs travel with."""
    if raw == "@checkpoint":
        return st.checkpoint or st.chapter
    if raw == "@self":
        return st.chapter
    return str(raw)
