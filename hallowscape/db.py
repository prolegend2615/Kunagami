"""SQLite persistence for HALLOWSCAPE.

Ordered logs (history, journal) stay in JSON/text; everything the consequence
engine has to *query* gets real rows: flags, relations, ledger, visits, payoffs,
queued events and the cross-run echo table.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import aiosqlite

from . import migrate
from .rules import PlayerState, apply_effects, resolve_target

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    owner_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS members (
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    PRIMARY KEY(session_id, user_id)
);
CREATE TABLE IF NOT EXISTS player_state (
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    chapter TEXT NOT NULL,
    checkpoint TEXT NOT NULL DEFAULT '',
    inventory TEXT NOT NULL DEFAULT '[]',
    journal TEXT NOT NULL DEFAULT '[]',
    watcher INTEGER NOT NULL DEFAULT 0,
    scares_enabled INTEGER NOT NULL DEFAULT 1,
    ending TEXT,
    alias TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(session_id, user_id)
);
CREATE TABLE IF NOT EXISTS flags (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    set_at TEXT NOT NULL,
    PRIMARY KEY(session_id, user_id, key)
);
CREATE TABLE IF NOT EXISTS relations (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    npc TEXT NOT NULL,
    value INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(session_id, user_id, npc)
);
CREATE TABLE IF NOT EXISTS ledger (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    tag TEXT NOT NULL,
    value INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(session_id, user_id, tag)
);
CREATE TABLE IF NOT EXISTS visits (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    node TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(session_id, user_id, node)
);
CREATE TABLE IF NOT EXISTS history (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    node TEXT NOT NULL,
    choice TEXT NOT NULL,
    at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS world_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL,
    happened_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payoffs_fired (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    payoff_id TEXT NOT NULL,
    fired_at TEXT NOT NULL,
    PRIMARY KEY(session_id, user_id, payoff_id)
);
CREATE TABLE IF NOT EXISTS queued_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT NOT NULL,
    due_at TEXT NOT NULL,
    flag TEXT,
    delivered_at TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    ending TEXT NOT NULL,
    watcher INTEGER NOT NULL,
    finished_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS echoes (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    from_session INTEGER NOT NULL,
    PRIMARY KEY(guild_id, user_id, key)
);
CREATE TABLE IF NOT EXISTS town_clock (
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    last_event_at TEXT,
    nights INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(session_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_world_session ON world_history(session_id, happened_at);
CREATE INDEX IF NOT EXISTS idx_queued_pending ON queued_events(user_id, session_id, delivered_at, due_at);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(session_id, user_id, seq);
"""

ECHO_KEYS = ("saved_stranger", "sin:left_wren", "sin:left_at_door", "faced_watcher", "hid_from_watcher", "pressed_unknown")


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


ALIAS_MARKUP = re.compile(r"[`*_~>|<@&#]")
ALIAS_MENTIONS = re.compile(r"<@[!]?(\d+|everyone|here)>|@(?:everyone|here)", re.IGNORECASE)


def clean_alias(raw: str) -> str:
    """One plain line, no pings, no markdown. The name goes inside prose embeds."""
    spoken = ALIAS_MENTIONS.sub("", str(raw or ""))
    return ALIAS_MARKUP.sub("", " ".join(spoken.split())).strip()[:32]


class StaleChoice(Exception):
    """The player clicked a button from a moment they already left."""


class NotInStory(Exception):
    pass


class Store:
    def __init__(self, path: Path | Callable[[], Path]):
        self._path = path
        self.db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    @property
    def path(self) -> Path:
        """Resolved late, because .env is not loaded until the bot starts."""
        return self._path() if callable(self._path) else self._path

    async def initialize(self) -> None:
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript("PRAGMA journal_mode=WAL;PRAGMA foreign_keys=ON;")
        pending = await migrate.read_legacy(self.db)
        if not pending.empty:
            await migrate.drop_legacy(self.db)
        await self.db.executescript(SCHEMA)
        if not pending.empty:
            await migrate.restore(self.db, pending)
        await self.db.execute(f"PRAGMA user_version={migrate.USER_VERSION}")
        await self.db.commit()

    async def close(self) -> None:
        if self.db:
            await self.db.close()
            self.db = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self.db is None:
            raise RuntimeError("Store.initialize() has not run")
        return self.db

    async def create_session(self, guild_id: int, channel_id: int, owner_id: int, entry: str, first_node: str) -> int:
        moment = iso(now())
        async with self._lock:
            cur = await self.conn.execute(
                "INSERT INTO sessions(guild_id,channel_id,owner_id,created_at) VALUES(?,?,?,?)",
                (guild_id, channel_id, owner_id, moment),
            )
            sid = int(cur.lastrowid)
            await self._start_player(sid, owner_id, entry, moment)
            await self.conn.commit()
            return sid

    async def _start_player(self, sid: int, user_id: int, entry: str, moment: str) -> None:
        await self.conn.execute("INSERT OR IGNORE INTO members(session_id,user_id) VALUES(?,?)", (sid, user_id))
        await self.conn.execute(
            "INSERT OR IGNORE INTO player_state(session_id,user_id,chapter,checkpoint,updated_at) VALUES(?,?,?,?,?)",
            (sid, user_id, entry, entry, moment),
        )
        await self.conn.execute(
            "INSERT OR IGNORE INTO visits(session_id,user_id,node,count) VALUES(?,?,?,1)", (sid, user_id, entry)
        )

    async def join_session(self, sid: int, user_id: int, entry: str) -> bool:
        moment = iso(now())
        async with self._lock:
            row = await (await self.conn.execute("SELECT id FROM sessions WHERE id=?", (sid,))).fetchone()
            if not row:
                return False
            await self._start_player(sid, user_id, entry, moment)
            await self.conn.commit()
            return True

    async def session_meta(self, sid: int) -> dict[str, Any] | None:
        row = await (await self.conn.execute("SELECT * FROM sessions WHERE id=?", (sid,))).fetchone()
        return dict(row) if row else None

    async def sessions_for(self, user_id: int, guild_id: int) -> list[int]:
        rows = await (
            await self.conn.execute(
                "SELECT s.id FROM sessions s JOIN members m ON s.id=m.session_id "
                "WHERE m.user_id=? AND s.guild_id=? ORDER BY s.id DESC",
                (user_id, guild_id),
            )
        ).fetchall()
        return [int(r["id"]) for r in rows]

    async def party_members(self, sid: int) -> list[int]:
        rows = await (await self.conn.execute("SELECT user_id FROM members WHERE session_id=?", (sid,))).fetchall()
        return [int(r["user_id"]) for r in rows]

    async def state(self, sid: int, user_id: int, guild_id: int | None = None) -> PlayerState | None:
        row = await (
            await self.conn.execute("SELECT * FROM player_state WHERE session_id=? AND user_id=?", (sid, user_id))
        ).fetchone()
        if not row:
            return None
        flags = {
            r["key"]: json.loads(r["value"])
            for r in await (
                await self.conn.execute("SELECT key,value FROM flags WHERE session_id=? AND user_id=?", (sid, user_id))
            ).fetchall()
        }
        relations = {
            r["npc"]: r["value"]
            for r in await (
                await self.conn.execute(
                    "SELECT npc,value FROM relations WHERE session_id=? AND user_id=?", (sid, user_id)
                )
            ).fetchall()
        }
        ledger = {
            r["tag"]: r["value"]
            for r in await (
                await self.conn.execute("SELECT tag,value FROM ledger WHERE session_id=? AND user_id=?", (sid, user_id))
            ).fetchall()
        }
        visits = {
            r["node"]: r["count"]
            for r in await (
                await self.conn.execute("SELECT node,count FROM visits WHERE session_id=? AND user_id=?", (sid, user_id))
            ).fetchall()
        }
        history = [
            {"node": r["node"], "choice": r["choice"], "at": r["at"]}
            for r in await (
                await self.conn.execute(
                    "SELECT node,choice,at FROM history WHERE session_id=? AND user_id=? ORDER BY seq", (sid, user_id)
                )
            ).fetchall()
        ]
        echoes = await self.echoes(user_id, guild_id)
        runs = await self.run_count(user_id, guild_id)
        return PlayerState(
            chapter=row["chapter"],
            checkpoint=row["checkpoint"],
            inventory=json.loads(row["inventory"]),
            journal=json.loads(row["journal"]),
            flags=flags,
            relations=relations,
            ledger=ledger,
            watcher=int(row["watcher"]),
            visits=visits,
            history=history,
            echoes=echoes,
            previous_runs=runs,
            scares_enabled=bool(row["scares_enabled"]),
            alias=row["alias"] or "",
            ending=row["ending"],
        )

    async def fired_payoffs(self, sid: int, user_id: int) -> set[str]:
        return {
            r["payoff_id"]
            for r in await (
                await self.conn.execute(
                    "SELECT payoff_id FROM payoffs_fired WHERE session_id=? AND user_id=?", (sid, user_id)
                )
            ).fetchall()
        }

    async def echoes(self, user_id: int, guild_id: int | None) -> dict[str, Any]:
        if guild_id is None:
            return {}
        rows = await (
            await self.conn.execute("SELECT key,value FROM echoes WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    async def run_count(self, user_id: int, guild_id: int | None) -> int:
        if guild_id is None:
            return 0
        row = await (
            await self.conn.execute("SELECT COUNT(*) AS n FROM runs WHERE user_id=? AND guild_id=?", (user_id, guild_id))
        ).fetchone()
        return int(row["n"]) if row else 0

    async def set_scares(self, sid: int, user_id: int, enabled: bool) -> None:
        async with self._lock:
            await self.conn.execute(
                "UPDATE player_state SET scares_enabled=? WHERE session_id=? AND user_id=?",
                (int(bool(enabled)), sid, user_id),
            )
            await self.conn.commit()

    async def set_alias(self, sid: int, user_id: int, alias: str) -> str:
        """The town may speak your name, but it will not take orders from it."""
        clean = clean_alias(alias)
        async with self._lock:
            await self.conn.execute(
                "UPDATE player_state SET alias=? WHERE session_id=? AND user_id=?",
                (clean or None, sid, user_id),
            )
            await self.conn.commit()
        return clean

    async def seed_alias(self, sid: int, user_id: int, display_name: str) -> None:
        """Only fills the name in once, so a chosen alias is never overwritten."""
        row = await (
            await self.conn.execute(
                "SELECT alias FROM player_state WHERE session_id=? AND user_id=?", (sid, user_id)
            )
        ).fetchone()
        if row and row["alias"]:
            return
        await self.set_alias(sid, user_id, display_name)

    async def idle_players(self, before_iso: str, limit: int = 50) -> list[dict[str, Any]]:
        """Everyone still mid-story who has not been seen since `before_iso`."""
        rows = await (
            await self.conn.execute(
                "SELECT ps.session_id, ps.user_id, ps.chapter, ps.updated_at, s.guild_id "
                "FROM player_state ps JOIN sessions s ON s.id=ps.session_id "
                "WHERE ps.ending IS NULL AND ps.updated_at <= ? ORDER BY ps.updated_at LIMIT ?",
                (before_iso, limit),
            )
        ).fetchall()
        return [dict(r) for r in rows]

    async def town_clock_row(self, sid: int, user_id: int) -> dict[str, Any]:
        row = await (
            await self.conn.execute("SELECT * FROM town_clock WHERE session_id=? AND user_id=?", (sid, user_id))
        ).fetchone()
        return dict(row) if row else {"last_event_at": None, "nights": 0}

    async def apply_town_event(
        self, sid: int, user_id: int, event: dict[str, Any], text: str, moment: datetime
    ) -> None:
        """The town acted while nobody was watching. Queue it and mark the clock."""
        stamp = iso(moment)
        async with self._lock:
            await self.conn.execute(
                "INSERT INTO queued_events(session_id,user_id,kind,text,due_at,flag) VALUES(?,?,?,?,?,?)",
                (sid, user_id, event.get("kind", "town_change"), text, stamp, event.get("flag")),
            )
            await self.conn.execute(
                "INSERT INTO world_history(session_id,user_id,kind,detail,happened_at) VALUES(?,?,?,?,?)",
                (sid, user_id, "town_change", text, stamp),
            )
            await self.conn.execute(
                "INSERT INTO town_clock(session_id,user_id,last_event_at,nights) VALUES(?,?,?,1) "
                "ON CONFLICT(session_id,user_id) DO UPDATE SET last_event_at=excluded.last_event_at, "
                "nights=town_clock.nights+1",
                (sid, user_id, stamp),
            )
            await self.conn.commit()

    async def town_nights(self, sid: int, user_id: int) -> int:
        row = await (
            await self.conn.execute("SELECT nights FROM town_clock WHERE session_id=? AND user_id=?", (sid, user_id))
        ).fetchone()
        return int(row["nights"]) if row else 0

    async def travel(self, sid: int, guild_id: int, user_id: int, node_id: str) -> PlayerState:
        """Walk to a hub the town has already opened to you."""
        async with self._lock:
            st = await self.state(sid, user_id, guild_id)
            if st is None:
                raise NotInStory("You are not part of this story session. Join the party first.")
            if st.ending:
                raise StaleChoice("This run has ended. The town keeps what you left, not your feet.")
            node = _nodes().get(node_id)
            if node is None or not node.get("hub"):
                raise StaleChoice("There is no road to that place yet.")
            stamp = iso(now())
            st.chapter = node_id
            st.visits[node_id] = st.visits.get(node_id, 0) + 1
            await self.conn.execute(
                "UPDATE player_state SET chapter=?,updated_at=? WHERE session_id=? AND user_id=?",
                (node_id, stamp, sid, user_id),
            )
            await self.conn.execute(
                "INSERT INTO visits(session_id,user_id,node,count) VALUES(?,?,?,?) "
                "ON CONFLICT(session_id,user_id,node) DO UPDATE SET count=excluded.count",
                (sid, user_id, node_id, st.visits[node_id]),
            )
            await self.conn.execute(
                "INSERT INTO world_history(session_id,user_id,kind,detail,happened_at) VALUES(?,?,?,?,?)",
                (
                    sid,
                    user_id,
                    "travel",
                    f"went to {_location_label(node.get('location', ''))}",
                    stamp,
                ),
            )
            await self.conn.commit()
            return st

    async def touch(self, sid: int, user_id: int) -> None:
        """Mark the player as seen so the clock leaves them alone for a while."""
        async with self._lock:
            await self.conn.execute(
                "UPDATE player_state SET updated_at=? WHERE session_id=? AND user_id=?",
                (iso(now()), sid, user_id),
            )
            await self.conn.commit()

    async def relocate(self, sid: int, user_id: int, node_id: str, checkpoint: str) -> None:
        """Put a player back on the live map after a reload deleted the chapter they stood in."""
        async with self._lock:
            await self.conn.execute(
                "UPDATE player_state SET chapter=?,checkpoint=?,updated_at=? WHERE session_id=? AND user_id=?",
                (node_id, checkpoint, iso(now()), sid, user_id),
            )
            await self.conn.commit()

    async def advance(
        self,
        sid: int,
        guild_id: int,
        user_id: int,
        node_id: str,
        choice: dict[str, Any],
    ) -> tuple[PlayerState, list[str]]:
        """Atomically apply one choice. Returns (state, scare tags)."""
        async with self._lock:
            st = await self.state(sid, user_id, guild_id)
            if st is None:
                raise NotInStory("You are not part of this story session. Join the party first.")
            if st.chapter != node_id:
                raise StaleChoice("That moment has already passed you by. Use **Continue Story**.")
            if st.ending:
                raise StaleChoice("This run has ended. Start a new party to walk the road again.")

            moment = now()
            stamp = iso(moment)
            scares = [choice["scare"]] if choice.get("scare") and st.scares_enabled else []
            queued = apply_effects(st, choice)
            target = resolve_target(choice.get("next"), st)
            if target not in _nodes():
                raise StaleChoice("That path no longer exists. Use **Continue Story**.")
            st.visits[target] = st.visits.get(target, 0) + 1
            st.chapter = target
            if _is_checkpoint(target):
                st.checkpoint = target

            node = _node(target)
            ending = node.get("ending")
            if ending:
                st.ending = ending

            await self.conn.execute(
                "UPDATE player_state SET chapter=?,checkpoint=?,inventory=?,journal=?,watcher=?,ending=?,"
                "updated_at=? WHERE session_id=? AND user_id=?",
                (
                    st.chapter,
                    st.checkpoint,
                    json.dumps(st.inventory),
                    json.dumps(st.journal),
                    st.watcher,
                    st.ending,
                    stamp,
                    sid,
                    user_id,
                ),
            )
            await self._write_memory(sid, user_id, st, stamp)
            await self.conn.execute(
                "INSERT INTO history(session_id,user_id,node,choice,at) VALUES(?,?,?,?,?)",
                (sid, user_id, node_id, choice["id"], stamp),
            )
            detail = str(choice.get("label") or choice["id"])
            await self.conn.execute(
                "INSERT INTO world_history(session_id,user_id,kind,detail,happened_at) VALUES(?,?,?,?,?)",
                (sid, user_id, "choice", detail, stamp),
            )

            for event in queued:
                await self.queue_event(sid, user_id, event, moment)

            if ending:
                await self._finish_run(sid, guild_id, user_id, st, ending, stamp)

            await self.conn.commit()
            return st, scares

    async def _write_memory(self, sid: int, user_id: int, st: PlayerState, stamp: str) -> None:
        for key, value in st.flags.items():
            await self.conn.execute(
                "INSERT INTO flags(session_id,user_id,key,value,set_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(session_id,user_id,key) DO UPDATE SET value=excluded.value,set_at=excluded.set_at",
                (sid, user_id, key, json.dumps(value), stamp),
            )
        for npc, value in st.relations.items():
            await self.conn.execute(
                "INSERT INTO relations(session_id,user_id,npc,value) VALUES(?,?,?,?) "
                "ON CONFLICT(session_id,user_id,npc) DO UPDATE SET value=excluded.value",
                (sid, user_id, npc, int(value)),
            )
        for tag, value in st.ledger.items():
            await self.conn.execute(
                "INSERT INTO ledger(session_id,user_id,tag,value) VALUES(?,?,?,?) "
                "ON CONFLICT(session_id,user_id,tag) DO UPDATE SET value=excluded.value",
                (sid, user_id, tag, int(value)),
            )
        for node, count in st.visits.items():
            await self.conn.execute(
                "INSERT INTO visits(session_id,user_id,node,count) VALUES(?,?,?,?) "
                "ON CONFLICT(session_id,user_id,node) DO UPDATE SET count=excluded.count",
                (sid, user_id, node, int(count)),
            )

    async def queue_event(self, sid: int, user_id: int, event: dict[str, Any], moment: datetime) -> None:
        due = moment + timedelta(seconds=int(event.get("due_in", 0)))
        await self.conn.execute(
            "INSERT INTO queued_events(session_id,user_id,kind,text,due_at,flag) VALUES(?,?,?,?,?,?)",
            (sid, user_id, event.get("kind", "town_change"), event["text"], iso(due), event.get("flag")),
        )

    async def record_payoffs(
        self, sid: int, user_id: int, st: PlayerState, payoff_ids: list[str], events: list[dict[str, Any]]
    ) -> None:
        """Record that payoffs were shown, keep the state they moved, queue their events."""
        stamp = iso(now())
        async with self._lock:
            await self.conn.execute(
                "UPDATE player_state SET inventory=?,journal=?,watcher=?,updated_at=? "
                "WHERE session_id=? AND user_id=?",
                (json.dumps(st.inventory), json.dumps(st.journal), st.watcher, stamp, sid, user_id),
            )
            await self._write_memory(sid, user_id, st, stamp)
            for payoff_id in payoff_ids:
                await self.conn.execute(
                    "INSERT OR IGNORE INTO payoffs_fired(session_id,user_id,payoff_id,fired_at) VALUES(?,?,?,?)",
                    (sid, user_id, payoff_id, stamp),
                )
            for event in events:
                await self.queue_event(sid, user_id, event, now())
            await self.conn.commit()

    async def drain_events(self, sid: int, user_id: int) -> list[dict[str, Any]]:
        stamp = iso(now())
        rows = await (
            await self.conn.execute(
                "SELECT id,kind,text,flag,due_at FROM queued_events "
                "WHERE session_id=? AND user_id=? AND delivered_at IS NULL AND due_at<=? ORDER BY due_at",
                (sid, user_id, stamp),
            )
        ).fetchall()
        out = [dict(r) for r in rows]
        if not out:
            return out
        async with self._lock:
            for event in out:
                await self.conn.execute(
                    "UPDATE queued_events SET delivered_at=? WHERE id=?", (stamp, event["id"])
                )
                if event.get("flag"):
                    await self.conn.execute(
                        "INSERT INTO flags(session_id,user_id,key,value,set_at) VALUES(?,?,?,?,?) "
                        "ON CONFLICT(session_id,user_id,key) DO UPDATE SET value=excluded.value",
                        (sid, user_id, event["flag"], json.dumps(True), stamp),
                    )
                await self.conn.execute(
                    "INSERT INTO world_history(session_id,user_id,kind,detail,happened_at) VALUES(?,?,?,?,?)",
                    (sid, user_id, "town_change", event["text"], stamp),
                )
            await self.conn.commit()
        return out

    async def pending_count(self, sid: int, user_id: int) -> int:
        row = await (
            await self.conn.execute(
                "SELECT COUNT(*) AS n FROM queued_events WHERE session_id=? AND user_id=? AND delivered_at IS NULL",
                (sid, user_id),
            )
        ).fetchone()
        return int(row["n"])

    async def world_memory(self, sid: int, user_id: int, limit: int = 12) -> list[dict[str, Any]]:
        rows = await (
            await self.conn.execute(
                "SELECT kind,detail,happened_at FROM world_history "
                "WHERE session_id=? AND user_id=? AND kind!='choice' ORDER BY id DESC LIMIT ?",
                (sid, user_id, limit),
            )
        ).fetchall()
        return [dict(r) for r in rows]

    async def party_digest(self, sid: int, user_id: int, limit: int = 3) -> list[dict[str, Any]]:
        """What the rest of the party did, as the town would repeat it."""
        rows = await (
            await self.conn.execute(
                "SELECT user_id,detail,happened_at FROM world_history "
                "WHERE session_id=? AND user_id!=? ORDER BY id DESC LIMIT ?",
                (sid, user_id, limit),
            )
        ).fetchall()
        return [dict(r) for r in rows]

    async def unlockables(self, sid: int, user_id: int) -> list[str]:
        rows = await (
            await self.conn.execute("SELECT node FROM visits WHERE session_id=? AND user_id=? AND count>0", (sid, user_id))
        ).fetchall()
        return [r["node"] for r in rows]

    async def _finish_run(self, sid: int, guild_id: int, user_id: int, st: PlayerState, ending: str, stamp: str) -> None:
        await self.conn.execute(
            "INSERT INTO runs(guild_id,user_id,session_id,ending,watcher,finished_at) VALUES(?,?,?,?,?,?)",
            (guild_id, user_id, sid, ending, st.watcher, stamp),
        )
        await self.conn.execute(
            "INSERT INTO echoes(guild_id,user_id,key,value,from_session) VALUES(?,?,?,?,?) "
            "ON CONFLICT(guild_id,user_id,key) DO UPDATE SET value=excluded.value,from_session=excluded.from_session",
            (guild_id, user_id, "ending", json.dumps(ending), sid),
        )
        for key in ECHO_KEYS:
            if st.flags.get(key):
                await self.conn.execute(
                    "INSERT INTO echoes(guild_id,user_id,key,value,from_session) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(guild_id,user_id,key) DO UPDATE SET value=excluded.value",
                    (guild_id, user_id, key, json.dumps(st.flags[key]), sid),
                )
        for tag, value in st.ledger.items():
            if value:
                await self.conn.execute(
                    "INSERT INTO echoes(guild_id,user_id,key,value,from_session) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(guild_id,user_id,key) DO UPDATE SET value=excluded.value",
                    (guild_id, user_id, f"debt:{tag}", json.dumps(int(value)), sid),
                )
        await self.conn.execute(
            "INSERT INTO world_history(session_id,user_id,kind,detail,happened_at) VALUES(?,?,?,?,?)",
            (sid, user_id, "ending", f"The run ended: {ending}.", stamp),
        )


def _nodes() -> dict[str, Any]:
    from . import story

    return story.NODES


def _node(node_id: str) -> dict[str, Any]:
    return _nodes()[node_id]


def _location_label(key: str) -> str:
    from . import story

    return story.LOCATIONS.get(key, key)


def _is_checkpoint(node_id: str) -> bool:
    return bool(_node(node_id).get("checkpoint"))
