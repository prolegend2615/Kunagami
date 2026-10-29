"""One-time upgrade from the single-file v1 database to the current schema.

v1 stored flags and choice history as JSON columns on player_state, and logged
world history under an `action` column. The current schema needs real rows for
anything the consequence engine queries, so the upgrade reads the old tables,
drops them, lets the new DDL create them, then replays the data.

Runs before the schema DDL on every boot. If a database is already current it
does nothing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import aiosqlite

from . import story

log = logging.getLogger("hallowscape.migrate")

USER_VERSION = 2


@dataclass
class Pending:
    """Rows read out of the v1 tables, waiting for the new schema to exist."""

    players: list[dict[str, Any]] = field(default_factory=list)
    world: list[dict[str, Any]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.players and not self.world


async def _columns(db: aiosqlite.Connection, table: str) -> list[str]:
    rows = await (await db.execute(f"PRAGMA table_info({table})")).fetchall()
    return [row["name"] for row in rows]


async def _table_exists(db: aiosqlite.Connection, table: str) -> bool:
    row = await (
        await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    ).fetchone()
    return row is not None


def _loads(raw: Any, fallback: Any) -> Any:
    if raw in (None, ""):
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


async def read_legacy(db: aiosqlite.Connection) -> Pending:
    """Detect v1 and capture its data. Returns nothing for a current database."""
    pending = Pending()
    if not await _table_exists(db, "player_state"):
        return pending
    columns = await _columns(db, "player_state")
    if "flags" not in columns or "watcher" in columns:
        return pending  # fresh install, or already upgraded

    log.info("detected the single-file v1 database; upgrading in place")
    rows = await (await db.execute("SELECT * FROM player_state")).fetchall()
    for row in rows:
        history = _loads(row["choices"], [])
        nodes = [entry.get("chapter") for entry in history if isinstance(entry, dict) and entry.get("chapter")]
        saved = row["chapter"]
        chapter = saved if saved in story.NODES else story.ENTRY
        if chapter != saved:
            log.warning("node %r is no longer in the graph; that player resumes at %r", saved, chapter)
        pending.players.append(
            {
                "session_id": row["session_id"],
                "user_id": row["user_id"],
                "chapter": chapter,
                "checkpoint": chapter if story.NODES[chapter].get("checkpoint") else story.ENTRY,
                "inventory": [item for item in _loads(row["inventory"], []) if item in story.ITEM_LABELS],
                "journal": _loads(row["journal"], []),
                "flags": _loads(row["flags"], []),
                "history": [entry for entry in history if isinstance(entry, dict) and entry.get("choice")],
                "visits": sorted({*[node for node in [*nodes, chapter] if node in story.NODES]}),
                "updated_at": row["updated_at"],
            }
        )
    if await _table_exists(db, "world_history"):
        world_columns = await _columns(db, "world_history")
        if "kind" not in world_columns:
            rows = await (await db.execute("SELECT * FROM world_history")).fetchall()
            for row in rows:
                pending.world.append(
                    {
                        "session_id": row["session_id"],
                        "user_id": row["user_id"],
                        "kind": row["action"],
                        "detail": row["detail"],
                        "happened_at": row["happened_at"],
                    }
                )
    return pending


async def drop_legacy(db: aiosqlite.Connection) -> None:
    """Remove the v1 tables the new DDL replaces. Sessions and members survive."""
    await db.executescript("DROP TABLE IF EXISTS player_state;DROP TABLE IF EXISTS world_history;")


async def restore(db: aiosqlite.Connection, pending: Pending) -> int:
    if pending.empty:
        return 0
    for player in pending.players:
        moment = str(player["updated_at"] or "") or "1970-01-01T00:00:00+00:00"
        await db.execute(
            "INSERT OR IGNORE INTO player_state(session_id,user_id,chapter,checkpoint,inventory,journal,"
            "watcher,scares_enabled,ending,alias,updated_at) VALUES(?,?,?,?,?,?,0,1,NULL,NULL,?)",
            (
                player["session_id"],
                player["user_id"],
                player["chapter"],
                player["checkpoint"],
                json.dumps(player["inventory"]),
                json.dumps(player["journal"]),
                moment,
            ),
        )
        for flag in player["flags"]:
            await db.execute(
                "INSERT OR IGNORE INTO flags(session_id,user_id,key,value,set_at) VALUES(?,?,?,1,?)",
                (player["session_id"], player["user_id"], flag, moment),
            )
        for entry in player["history"]:
            await db.execute(
                "INSERT INTO history(session_id,user_id,node,choice,at) VALUES(?,?,?,?,?)",
                (
                    player["session_id"],
                    player["user_id"],
                    entry.get("chapter", player["chapter"]),
                    entry["choice"],
                    entry.get("at", moment),
                ),
            )
        for node in player["visits"]:
            await db.execute(
                "INSERT OR IGNORE INTO visits(session_id,user_id,node,count) VALUES(?,?,?,1)",
                (player["session_id"], player["user_id"], node),
            )
    for row in pending.world:
        await db.execute(
            "INSERT INTO world_history(session_id,user_id,kind,detail,happened_at) VALUES(?,?,?,?,?)",
            (
                row["session_id"],
                row["user_id"],
                str(row["kind"] or "town_change"),
                str(row["detail"] or ""),
                str(row["happened_at"] or "1970-01-01T00:00:00+00:00"),
            ),
        )
    await db.commit()
    log.info(
        "upgraded %d player record(s) and %d world-history row(s) from v1",
        len(pending.players),
        len(pending.world),
    )
    return len(pending.players)
