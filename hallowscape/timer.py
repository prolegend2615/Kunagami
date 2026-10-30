"""The town clock: the world moves on the nights nobody is watching.

This is the one part that needs an always-on process. Every pass looks for
players who have been away long enough, works out which town changes their own
story has earned, and queues exactly one of them. It lands in the same queue the
story drains, so the player still reads it as "WHILE YOU WERE AWAY".
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import timedelta
from typing import Any

from . import config, story
from .db import Store, iso, now
from .rules import matches, with_names

log = logging.getLogger("hallowscape.clock")


def clock_minutes() -> int:
    return config.integer("HALLOWSCAPE_CLOCK_MINUTES", 30)


def idle_after() -> timedelta:
    return timedelta(hours=config.number("HALLOWSCAPE_IDLE_HOURS", 6))


def event_every() -> timedelta:
    """How often one player may receive a town change, so the clock never nags."""
    return timedelta(hours=config.number("HALLOWSCAPE_EVENT_HOURS", 12))


def eligible(event: dict[str, Any], st: Any) -> bool:
    try:
        return matches(event.get("when"), st)
    except ValueError as exc:
        log.warning("town event %r has a broken predicate: %s", event.get("text"), exc)
        return False


async def tick(store: Store, away_for: timedelta | None = None, since_last_gap: timedelta | None = None) -> list[str]:
    """Visit every idle player once. Returns the lines the town wrote."""
    away_for = away_for or idle_after()
    since_last_gap = since_last_gap or event_every()
    moment = now()
    written: list[str] = []
    for row in await store.idle_players(iso(moment - away_for)):
        sid, user_id, guild_id = int(row["session_id"]), int(row["user_id"]), int(row["guild_id"])
        last = (await store.town_clock_row(sid, user_id))["last_event_at"]
        if last and last > iso(moment - since_last_gap):
            continue
        st = await store.state(sid, user_id, guild_id)
        if st is None or st.ending:
            continue
        pool = [event for event in story.TOWN_EVENTS if eligible(event, st)]
        if not pool:
            continue
        event = random.choice(pool)
        text = with_names(str(event["text"]), st)
        await store.apply_town_event(sid, user_id, event, text, moment)
        written.append(text)
        log.info("town moved for user %s in session %s: %s", user_id, sid, text)
    return written


async def run(store: Store, stop: asyncio.Event) -> None:
    """Boot catches the town up, then it keeps its own hours."""
    while not stop.is_set():
        try:
            await tick(store)
        except Exception:
            log.exception("town clock pass failed; trying again next interval")
        if stop.is_set():
            return
        try:
            await asyncio.wait_for(stop.wait(), timeout=clock_minutes() * 60)
        except asyncio.TimeoutError:
            pass
