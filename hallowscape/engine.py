"""Orchestration: render a node against what the town remembers."""

from __future__ import annotations

import importlib
import os
import random
from dataclasses import dataclass, field
from typing import Any

from . import story
from .db import NotInStory, StaleChoice, Store
from .rules import PlayerState, RenderedNode, apply_effects, render_node

ORDER = story.chapter_order()


@dataclass
class Scene:
    state: PlayerState
    node: RenderedNode
    away: list[str] = field(default_factory=list)
    digest: list[str] = field(default_factory=list)
    scares: list[str] = field(default_factory=list)

    @property
    def finished(self) -> bool:
        return bool(self.state.ending)


def _gif_urls() -> dict[str, list[str]]:
    """JUMPSCARE_GIFS accepts `tag=url` pairs and bare urls (wildcard pool).

    Only https is accepted: the safety screen fetches the file before it is
    shown, and a plain-http URL would silently refuse forever.
    """
    buckets: dict[str, list[str]] = {"*": []}
    for raw in os.getenv("JUMPSCARE_GIFS", "").split(","):
        entry = raw.strip()
        if not entry:
            continue
        tag, _, url = entry.partition("=")
        if url.startswith("https://"):
            buckets.setdefault(tag.strip(), []).append(url.strip())
        elif entry.startswith("https://"):
            buckets["*"].append(entry)
    return buckets


@dataclass
class Scare:
    """One GIF the town earned, plus the prose line to use if it cannot play."""

    tag: str
    url: str
    caption: str


def scare_clips(tags: list[str]) -> list[Scare]:
    if not tags:
        return []
    buckets = _gif_urls()
    out: list[Scare] = []
    for tag in tags:
        pool = buckets.get(tag) or buckets["*"]
        if not pool:
            continue
        out.append(Scare(tag=tag, url=random.choice(pool), caption=story.SCARES.get(tag, "")))
    return out


async def build_scene(store: Store, sid: int, guild_id: int, user_id: int) -> Scene:
    st = await store.state(sid, user_id, guild_id)
    if st is None:
        raise NotInStory("You have no story here yet. Open **Play With Friends** to begin.")
    fired = await store.fired_payoffs(sid, user_id)
    node = story.NODES.get(st.chapter)
    if node is None:
        # /reload can retire the chapter a player is standing in; send them home
        # instead of raising a KeyError inside their story view.
        home = st.checkpoint if st.checkpoint in story.NODES else story.ENTRY
        checkpoint = home if story.NODES[home].get("checkpoint") else story.ENTRY
        await store.relocate(sid, user_id, home, checkpoint)
        st.chapter, st.checkpoint = home, checkpoint
        node = story.NODES[home]
    rendered = render_node(st.chapter, node, st, node.get("choices", []), story.PAYOFFS, ORDER, fired)

    # A payoff can move a meter past another payoff's threshold, so keep firing
    # until a pass adds nothing new. Each pass is recorded, so it cannot repeat.
    fresh: list[str] = []
    scares: list[str] = []
    while True:
        batch = [rule for rule in story.PAYOFFS if rule["id"] in rendered.payoffs and rule["id"] not in fresh]
        if not batch:
            break
        events: list[dict[str, Any]] = []
        for rule in batch:
            events.extend(apply_effects(st, rule))
            if rule.get("scare") and st.scares_enabled:
                scares.append(rule["scare"])
        ids = [str(rule["id"]) for rule in batch]
        await store.record_payoffs(sid, user_id, st, ids, events)
        fresh.extend(ids)
        fired = fired | set(ids)
        rendered = render_node(st.chapter, node, st, node.get("choices", []), story.PAYOFFS, ORDER, fired)
    rendered.payoffs = fresh

    away = [event["text"] for event in await store.drain_events(sid, user_id)]
    digest: list[str] = []
    for row in await store.party_digest(sid, user_id):
        digest.append(f"> *Word travels:* **<@{row['user_id']}>** {row['detail']}. The town repeats it behind your back.")
    return Scene(state=st, node=rendered, away=away, digest=digest, scares=scares)


async def take_choice(
    store: Store, sid: int, guild_id: int, user_id: int, node_id: str, choice_id: str
) -> tuple[Scene, list[Scare]]:
    node = story.NODES.get(node_id)
    if node is None:
        raise StaleChoice("That chapter no longer exists.")
    fired = await store.fired_payoffs(sid, user_id)
    st = await store.state(sid, user_id, guild_id)
    if st is None:
        raise NotInStory("You are not part of this story session. Join the party first.")
    rendered = render_node(node_id, node, st, node.get("choices", []), story.PAYOFFS, ORDER, fired)
    choice = next((c for c in rendered.choices if c["id"] == choice_id), None)
    if choice is None:
        raise StaleChoice("That moment has already passed you by. Use **Continue Story**.")
    missing = choice.get("_missing", [])
    if missing:
        names = ", ".join(story.ITEM_LABELS.get(item, item) for item in missing)
        raise StaleChoice(f"You would need {names} first.")

    _, scare_tags = await store.advance(sid, guild_id, user_id, node_id, choice)
    scene = await build_scene(store, sid, guild_id, user_id)
    arrived = story.NODES.get(scene.state.chapter, {}).get("scare")
    if arrived and scene.state.scares_enabled:
        scene.scares.append(arrived)
    scene.scares = list(dict.fromkeys([*scare_tags, *scene.scares]))
    return scene, scare_clips(scene.scares)


def reload_story() -> tuple[list[str], list[str]]:
    """Re-import story.py, keeping the previous graph if the new one is broken.

    The UI and the database read NODES through the module, so a successful
    reload is picked up everywhere; only ORDER needs rebuilding.
    """
    backup = dict(vars(story))
    importlib.reload(story)
    errors, warnings = story.validate()
    if errors:
        live = vars(story)
        live.clear()
        live.update(backup)
    globals()["ORDER"] = story.chapter_order()
    return errors, warnings
