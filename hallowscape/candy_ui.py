"""The Candy Door: five nights of deciding who gets a sweet, played beside the story.

Everything the player sees is rebuilt from the database row, so closing Discord and
coming back an hour later lands them on the same step, with the same child on it.
"""

from __future__ import annotations

import logging
from typing import Any

import discord

from . import candy
from .db import CandyStarved, NotInStory, StaleChoice, Store
from .engine import scare_clips
from .ui import _split, send_scares

log = logging.getLogger("hallowscape.candy_door")

BAND_LABELS = {
    "warm": "the lane is on your side",
    "middle": "the lane is undecided about you",
    "cold": "the lane remembers what you refused",
}
HOW_TO_PLAY = (
    "**HOW THE NIGHT GOES.** Read the note, look at who is standing there, and ask through the "
    "door with the menu below — every answer is free, and the answers are where the tells hide. "
    "Then choose: **🍬 Give Candy** or **🚪 Send Away**.\n\n"
    "A real child you send away costs you reputation. A thing that is not a child, fed, costs a "
    "heart — and the bowl is not endless. Three hearts, five nights, and the note is the only "
    "weapon you get."
)
SUPPLY_HEADLINE = "☕ **A BOX ON THE STEP**"


def _store(interaction: discord.Interaction) -> Store:
    return interaction.client.store


def _guild_id(interaction: discord.Interaction) -> int:
    return interaction.guild.id if interaction.guild else 0


def _name(vid: str) -> str:
    return candy.VISITORS[vid]["name"]


def _meter(run: dict[str, Any]) -> str:
    hearts = "❤️" * max(run["hearts"], 0) + "🖤" * max(candy.START_HEARTS - run["hearts"], 0)
    band = BAND_LABELS[candy.band(run["reputation"])]
    return f"{hearts} · 🍬 ×{run['candy']} · 🏘️ {run['reputation']} — {band}"


def _rule_card(plan: dict[str, Any]) -> str:
    lines = ["**📜 THE NOTE ON YOUR DOOR**"] + [f"• {candy.RULES[key]}" for key in plan["rules"]]
    return "\n".join(lines)


def _embeds(title: str | None, blocks: list[str], footer: str, color: discord.Color) -> list[discord.Embed]:
    """One screen, split honestly across embeds rather than truncated mid-sentence."""
    out: list[discord.Embed] = []
    for index, chunk in enumerate(_split("\n\n".join(blocks))):
        embed = discord.Embed(title=title if index == 0 else None, description=chunk, color=color)
        if index == 0:
            embed.set_footer(text=footer)
        out.append(embed)
    return out


def remaining_questions(visitor: dict[str, Any], asked: list[str]) -> list[str]:
    """Questions this visitor will still answer, in the order the menu shows them.

    Discord rejects a select menu with no options, so the view asks this before it
    adds one: a player who has tapped every question gets the decision buttons and
    nothing else.
    """
    return [qid for qid in candy.QUESTIONS if qid in visitor["answers"] and qid not in asked]


def door_screen(run: dict[str, Any]) -> tuple[list[discord.Embed], discord.ui.View]:
    plan = candy.NIGHTS[run["night"] - 1]
    visitor = candy.visitor(run["night"], run["slot"])
    doors = len(plan["visitors"])
    blocks = [
        f"**🌙 NIGHT {run['night']} OF {candy.NIGHTS_TOTAL}  ·  door {run['slot'] + 1} of {doors}**",
        plan["brief"] if run["slot"] == 0 else "",
        HOW_TO_PLAY if (run["night"] == 1 and run["slot"] == 0) else "",
        _rule_card(plan),
        f"**🚪 ON YOUR STEP: {visitor['name']} — {visitor['costume']}**\n\n{visitor['description']}",
    ]
    for qid in run["asked"]:
        answer, label = visitor["answers"].get(qid), candy.QUESTIONS.get(qid)
        if answer is None or label is None:
            continue
        blocks.append(f"❔ {label}\n> {answer}")
    if not run["asked"]:
        blocks.append("*Nothing asked through the door yet.*")
    elif not remaining_questions(visitor, run["asked"]):
        blocks.append("*That is all of it. They are waiting on the door, and so is the next one.*")
    embeds = _embeds("🍬 THE CANDY DOOR", [b for b in blocks if b], _meter(run), discord.Color.orange())
    return embeds, DoorView(run)


def resolved_screen(run: dict[str, Any], decision: dict[str, Any]) -> tuple[list[discord.Embed], discord.ui.View]:
    gave = "🍬 You handed the sweet over." if decision["give"] else "🚪 You said no, and closed the gap an inch."
    blocks = [
        f"**🌙 Night {run['night']} · {decision['name']}**",
        gave,
        decision["text"],
        "_The step is empty again. The next knock is already on the path._",
    ]
    embeds = _embeds("🍬 THE CANDY DOOR", blocks, _meter(run), discord.Color.dark_gold() if decision["give"] else discord.Color.greyple())
    return embeds, DoorView(run)


def supply_screen(run: dict[str, Any], night_done: int, summary: list[dict[str, Any]]) -> tuple[list[discord.Embed], discord.ui.View]:
    blocks = [f"**🌙 NIGHT {night_done} HELD — WHAT WAS BEHIND EACH DOOR**"]
    for row in summary:
        mark = "🍬 fed" if row["action"] == "give" else "🚪 sent away"
        blocks.append(f"**{_name(row['visitor'])}** — {mark}\n> {row['truth']}")
    embeds = _embeds("🍬 THE CANDY DOOR", blocks, _meter(run), discord.Color.dark_gold())

    key = candy.supply_band(run["reputation"])
    for row in summary:
        if row["visitor"] == "n3_wet":
            key = "wet_fed" if row["action"] == "give" else "wet_denied"
    marla = discord.Embed(
        title=SUPPLY_HEADLINE,
        description=candy.SUPPLY[key],
        color=discord.Color.dark_teal(),
    )
    marla.set_footer(
        text=f"+{candy.SUPPLY_PER_NIGHT} candy. Night {run['night']} of {candy.NIGHTS_TOTAL} is next."
    )
    embeds.append(marla)
    return embeds, DoorView(run)


def ending_screen(run: dict[str, Any], ending: dict[str, Any], pasts: list[dict[str, Any]]) -> tuple[list[discord.Embed], discord.ui.View]:
    blocks = [ending["text"], _ending_stats(run)]
    if run["status"] in {"happy", "secret", "bad"}:
        blocks.append("**📜 THE STREET REMEMBERS**")
        lines = [
            f"• night {row['nights']} · {'❤️' * max(row['hearts'], 0)} · reputation {row['reputation']} — {row['status']}"
            for row in pasts
        ]
        blocks.append("\n".join(lines))
    color = {
        "bad": discord.Color.dark_red(),
        "secret": discord.Color.dark_teal(),
        "happy": discord.Color.green(),
    }.get(run["status"], discord.Color.orange())
    embeds = _embeds(ending["title"], blocks, _meter(run), color)
    return embeds, DoorView(run)


def _ending_stats(run: dict[str, Any]) -> str:
    hearts = "❤️" * max(run["hearts"], 0) + "🖤" * max(candy.START_HEARTS - run["hearts"], 0)
    return (
        f"**Hearts left** {hearts}  ·  **Reputation** {run['reputation']} ({candy.band(run['reputation'])})  ·  "
        f"**Candy left** 🍬 ×{run['candy']}  ·  **Nights** {run['night']} of {candy.NIGHTS_TOTAL}"
    )


async def screen_for(
    store: Store, guild_id: int, user_id: int, run: dict[str, Any]
) -> tuple[list[discord.Embed], discord.ui.View]:
    """Whatever the player is standing in front of, right now."""
    if run["status"] != "active":
        ending = candy.ENDINGS[run["status"]]
        text = ending.get("text") or candy.happy_text(run["reputation"])
        pasts = await store.candy_pasts(guild_id, user_id)
        return ending_screen(run, {"title": ending["title"], "text": text}, pasts)
    if run["phase"] == "door":
        return door_screen(run)
    if run["phase"] == "resolved":
        decision = await store.candy_decision(guild_id, user_id)
        if decision is None:
            return door_screen(run)
        return resolved_screen(run, decision)
    night_done = max(run["night"] - 1, 1)
    summary = await store.candy_log_rows(guild_id, user_id, night_done)
    return supply_screen(run, night_done, summary)


class QuestionSelect(discord.ui.Select):
    """Every question this visitor will answer. Asked ones drop out of the menu and into the story."""

    def __init__(self, visitor: dict[str, Any], asked: list[str]):
        options = [
            discord.SelectOption(label=candy.QUESTIONS[qid], value=qid)
            for qid in remaining_questions(visitor, asked)
        ]
        super().__init__(
            placeholder=f"Ask {visitor['name']} through the door…",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        store = _store(interaction)
        guild_id = _guild_id(interaction)
        await interaction.response.defer(ephemeral=True)
        try:
            run = await store.candy_ask(guild_id, interaction.user.id, self.values[0])
        except (StaleChoice, NotInStory) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        if run is None:
            await interaction.followup.send("The porch light flickers. There is nothing left to ask here.", ephemeral=True)
            return
        embeds, view = door_screen(run)
        await interaction.edit_original_response(embeds=embeds, view=view)


class DoorView(discord.ui.View):
    def __init__(self, run: dict[str, Any]):
        super().__init__(timeout=60 * 60 * 6)
        self.add_item(DoorButton("🕯️ Close the Curtain", discord.ButtonStyle.secondary, 4, self._walk_away))
        if run["status"] != "active":
            self.add_item(DoorButton("🍬 Another October", discord.ButtonStyle.primary, 0, self._again))
            return
        if run["phase"] == "door":
            visitor = candy.visitor(run["night"], run["slot"])
            if remaining_questions(visitor, run["asked"]):
                self.add_item(QuestionSelect(visitor, run["asked"]))
            give = DoorButton("🍬 Give Candy", discord.ButtonStyle.success, 1, self._give)
            if run["candy"] <= 0:
                give.disabled = True
                give.tooltip = "The bowl is empty. Deny it, or wait for Marla."
            self.add_item(give)
            self.add_item(DoorButton("🚪 Send Away", discord.ButtonStyle.primary, 2, self._deny))
        elif run["phase"] == "resolved":
            self.add_item(DoorButton("▶️ Next Door", discord.ButtonStyle.primary, 1, self._advance))
        elif run["phase"] == "supply":
            self.add_item(DoorButton("🌙 Next Night", discord.ButtonStyle.primary, 1, self._advance))

    async def _walk_away(self, interaction: discord.Interaction) -> None:
        self.stop()
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🕯️ THE CURTAIN IS CLOSED",
                description="The night goes on without you and so does the queue at your gate. "
                "**/start-minigame** any time: the doorway is where you left it.",
                color=discord.Color.greyple(),
            ),
            view=None,
        )

    async def _again(self, interaction: discord.Interaction) -> None:
        store = _store(interaction)
        guild_id = _guild_id(interaction)
        await interaction.response.defer(ephemeral=True)
        run = await store.candy_start(guild_id, interaction.user.id, reset=True)
        embeds, view = door_screen(run)
        await interaction.edit_original_response(embeds=embeds, view=view)

    async def _give(self, interaction: discord.Interaction) -> None:
        await self._decide(interaction, True)

    async def _deny(self, interaction: discord.Interaction) -> None:
        await self._decide(interaction, False)

    async def _decide(self, interaction: discord.Interaction, give: bool) -> None:
        store = _store(interaction)
        guild_id = _guild_id(interaction)
        await interaction.response.defer(ephemeral=True)
        try:
            result = await store.candy_decide(guild_id, interaction.user.id, give)
        except CandyStarved:
            log.info("candy door: <@%s> reached for an empty bowl", interaction.user.id)
            await interaction.followup.send(
                "*You reach for the bowl and there is nothing in it.* The thing on your step waits "
                "anyway. Send it away, or stand there.",
                ephemeral=True,
            )
            return
        except (StaleChoice, NotInStory) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        outcome = result["outcome"]
        run = result["run"]
        embeds, view = resolved_screen(run, {**outcome, "name": result["visitor"]["name"], "give": give})
        await interaction.edit_original_response(embeds=embeds, view=view)
        if outcome["scare"] and await _scares_enabled(interaction):
            await send_scares(interaction.followup, scare_clips([outcome["scare"]]))

    async def _advance(self, interaction: discord.Interaction) -> None:
        store = _store(interaction)
        guild_id = _guild_id(interaction)
        await interaction.response.defer(ephemeral=True)
        try:
            moved = await store.candy_advance(guild_id, interaction.user.id)
        except (StaleChoice, NotInStory) as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return
        run = moved["run"]
        if moved["kind"] == "ending":
            pasts = await store.candy_pasts(guild_id, interaction.user.id)
            embeds, view = ending_screen(run, {"title": moved["title"], "text": moved["text"]}, pasts)
        elif moved["kind"] == "supply":
            embeds, view = supply_screen(run, moved["night_done"], moved["summary"])
        else:
            embeds, view = door_screen(run)
        await interaction.edit_original_response(embeds=embeds, view=view)


class DoorButton(discord.ui.Button["DoorView"]):
    """A button whose behaviour is the coroutine it was handed, so phases can differ per run."""

    def __init__(self, label: str, style: discord.ButtonStyle, row: int, handler: Any):
        super().__init__(label=label[:80], style=style, row=row)
        self._handler = handler

    async def callback(self, interaction: discord.Interaction) -> None:
        await self._handler(interaction)


async def _scares_enabled(interaction: discord.Interaction) -> bool:
    """The story's Settings switch governs the door too; one toggle, one consent."""
    store, guild_id = _store(interaction), _guild_id(interaction)
    if not guild_id:
        return True
    sessions = await store.sessions_for(interaction.user.id, guild_id)
    if not sessions:
        return True
    state = await store.state(sessions[0], interaction.user.id, guild_id)
    return True if state is None else state.scares_enabled


async def open_door(interaction: discord.Interaction, reset: bool = False) -> None:
    """Continue this year's five nights, or start the year again from night one."""
    store, guild_id = _store(interaction), _guild_id(interaction)
    await interaction.response.defer(ephemeral=True)
    run = await store.candy_start(guild_id, interaction.user.id, reset=reset)
    embeds, view = await screen_for(store, guild_id, interaction.user.id, run)
    await interaction.followup.send(embeds=embeds, view=view, ephemeral=True, wait=True)
