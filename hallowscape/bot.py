"""Bot wiring: commands, startup validation, lifecycle."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from . import engine, media, story, timer
from .db import Store
from .ui import MenuView

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("hallowscape")


def db_path() -> Path:
    """Resolved when the store connects, not at import, so .env is honoured."""
    return Path(os.getenv("HALLOWSCAPE_DB", ROOT / "hallowscape.sqlite3"))


def story_report() -> tuple[list[str], list[str]]:
    return story.validate()


class HallowScapeBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.store = Store(db_path)
        self.clock_stop = asyncio.Event()
        self.clock_task: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        errors, warnings = story_report()
        for line in warnings:
            log.warning("story: %s", line)
        if errors:
            raise RuntimeError("Story graph failed validation:\n" + "\n".join(f"  - {line}" for line in errors))
        log.info("story graph valid: %d nodes, %d payoffs", len(story.NODES), len(story.PAYOFFS))
        await self.store.initialize()
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if guild_id.isdigit():
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("synced commands to development guild %s", guild_id)
        else:
            await self.tree.sync()
            log.info("synced global commands")
        if os.getenv("HALLOWSCAPE_CLOCK", "1") != "0":
            self.clock_task = self.loop.create_task(timer.run(self.store, self.clock_stop))
            log.info(
                "town clock running: every %s min, for players idle %s h, one event per %s h per player",
                timer.clock_minutes(),
                timer.idle_after(),
                timer.event_every(),
            )

    async def close(self) -> None:
        self.clock_stop.set()
        if self.clock_task:
            self.clock_task.cancel()
        await media.DEFAULT.close()
        await self.store.close()
        await super().close()


bot = HallowScapeBot()


@bot.tree.command(name="start", description="Open HALLOWSCAPE and enter the town")
async def start(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="🎃 HALLOWSCAPE",
        description=(
            "*The town is waiting for you.*\n\n"
            "> It's October 31st, 11:59 PM.\n"
            "> You don't remember arriving here.\n"
            "> Your phone has no signal, the road behind you has disappeared, and someone is "
            "standing inside the abandoned house across the street.\n\n"
            'Your phone vibrates with a message from an unknown user:\n*"Don\'t let it know '
            'you\'re awake."*'
        ),
        color=discord.Color.dark_purple(),
    )
    embed.set_footer(text="A button-driven horror story • Your choices are saved automatically")
    await interaction.response.send_message(embed=embed, view=MenuView(bot), ephemeral=True)


@bot.tree.command(name="help", description="How to play HALLOWSCAPE")
async def help_command(interaction: discord.Interaction) -> None:
    embed = discord.Embed(
        title="🎃 HALLOWSCAPE — Help",
        description=(
            "**/start** opens your menu. **Play With Friends** creates a party or joins one by "
            "session ID, then **Begin Chapter 1** starts your story. Five chapters, five ways for a "
            "run to end.\n\n"
            "Every chapter is read with buttons. **Continue Story** resumes from your last "
            "checkpoint, and anything the town learned about you — debts, bonds, who you left at "
            "the door — comes back later.\n\n"
            "**Explore Town** lets you walk back to places you have already stood in. They will not "
            "be as you left them, and **🕯️ Return to Your Story** brings you back to your chapter.\n\n"
            "Party members each live their own story. What the others did returns to you as rumor. "
            "The town also moves on nights you are not here, and tells you about it when you return.\n\n"
            "**Settings** holds your jumpscare toggle and the name the town should call you. Every "
            "GIF is screened for flashing before it is sent and arrives spoiler-tagged. An admin "
            "sets the GIF pool with `JUMPSCARE_GIFS` in `.env`, uses **/reload** to publish new "
            "chapters without a restart, and can force a night to pass with **/townclock**."
        ),
        color=discord.Color.dark_purple(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="reload", description="(Admin) Re-read the chapters without a restart")
@app_commands.checks.has_permissions(administrator=True)
async def reload_chapters(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    errors, warnings = engine.reload_story()
    if errors:
        await interaction.followup.send(
            "**Rejected.** The new chapters do not validate, so the town is unchanged:\n"
            + "\n".join(f"- {line}" for line in errors[:10]),
            ephemeral=True,
        )
        log.error("story reload rejected: %s", errors)
        return
    for line in warnings:
        log.warning("story: %s", line)
    await interaction.followup.send(
        f"📖 The town was rewritten: **{len(story.NODES)}** nodes, **{len(story.PAYOFFS)}** payoffs, "
        f"**{len(story.TOWN_EVENTS)}** things it does on its own."
        + (f"\n{len(warnings)} warning(s) in the log." if warnings else ""),
        ephemeral=True,
    )


@bot.tree.command(name="townclock", description="(Admin) Make the town move right now")
@app_commands.checks.has_permissions(administrator=True)
async def town_clock(interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    written = await timer.tick(bot.store, away_for=timedelta(0), since_last_gap=timedelta(0))
    if not written:
        await interaction.followup.send("Nobody was away long enough to be missed.", ephemeral=True)
        return
    await interaction.followup.send(
        f"🕯️ The town moved while nobody was watching ({len(written)}):\n" + "\n".join(f"> {line}" for line in written),
        ephemeral=True,
    )


@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        message = "That command is for the people who own the town — administrator only."
    elif isinstance(error, app_commands.CheckFailure):
        message = "You don't have permission for that."
    else:
        log.exception("command failed", exc_info=error)
        message = "Something in the house broke. The log knows what."
    try:
        await interaction.response.send_message(message, ephemeral=True)
    except discord.errors.InteractionResponded:
        await interaction.followup.send(message, ephemeral=True)


async def run() -> None:
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "put_your_bot_token_here":
        raise RuntimeError("Set DISCORD_TOKEN in the .env file. See README.md for setup steps.")
    async with bot:
        await bot.start(token)


def load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
