"""Discord UI: embeds and views built on the engine's scenes."""

from __future__ import annotations

import io
import logging
import re
from typing import Any

import discord

from . import media, story
from .db import NotInStory, StaleChoice, Store
from .engine import Scene, build_scene, scare_clips, take_choice

log = logging.getLogger("hallowscape.ui")
EMBED_LIMIT = 4000
PRESSURE_LABELS = ["", "watched", "noticed you", "close behind you", "in the house", "at your back", "already inside"]
FLASH_WARNING = (
    "⚠️ **Flashing imagery.** This one was allowed through by the server owner. "
    "You can turn GIF scares off in **Settings → Jumpscare GIFs**."
)


async def send_scares(target: Any, clips: list[Any], ephemeral: bool = True) -> None:
    """Attach screened GIFs as spoilers; fall back to the prose line if one refuses."""
    for clip in clips:
        prepared, refusal = await media.DEFAULT.prepare(clip.url)
        if prepared is None:
            log.info("scare GIF %s not shown: %s", clip.url, refusal)
            if clip.caption:
                await target.send(content=f"*{clip.caption}*", ephemeral=ephemeral, wait=True)
            continue
        file = discord.File(io.BytesIO(prepared.data), filename=prepared.spoiler_name)
        content = FLASH_WARNING if prepared.analysis.flashing else None
        try:
            await target.send(content=content, file=file, ephemeral=ephemeral, wait=True)
        except discord.DiscordException:
            log.warning("could not attach %s; sending the link instead", prepared.name)
            await target.send(content=f"⚠️ {clip.url}", ephemeral=ephemeral, wait=True)


def pressure_text(watcher: int) -> str:
    capped = min(max(watcher, 0), len(PRESSURE_LABELS) - 1)
    dots = "▮" * capped + "▯" * (6 - capped)
    return f"👁️ {dots} — the Watcher has {PRESSURE_LABELS[capped] or 'not noticed you yet'}"


def _split(text: str, limit: int = EMBED_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    for block in text.split("\n\n"):
        if chunks and len(chunks[-1]) + len(block) + 2 <= limit:
            chunks[-1] = f"{chunks[-1]}\n\n{block}"
        elif len(block) <= limit:
            chunks.append(block)
        else:
            for i in range(0, len(block), limit):
                chunks.append(block[i : i + limit])
    return chunks


def scene_embeds(scene: Scene, party_count: int, sid: int) -> list[discord.Embed]:
    st, node = scene.state, scene.node
    blocks: list[str] = []
    if scene.away:
        blocks.append("**🕯️ WHILE YOU WERE AWAY**\n" + "\n".join(f"> {line}" for line in scene.away))
    if scene.digest:
        blocks.append("**👥 THE PARTY**\n" + "\n".join(scene.digest[:2]))
    blocks.append(node.description)
    body = "\n\n".join(blocks)

    embeds: list[discord.Embed] = []
    for i, chunk in enumerate(_split(body)):
        embed = discord.Embed(
            title=f"🎃 HALLOWSCAPE  ·  {node.title}" if i == 0 else None,
            description=chunk,
            color=discord.Color.dark_purple() if not st.ending else discord.Color.red(),
        )
        embeds.append(embed)
    last = embeds[-1]
    last.add_field(name=pressure_text(st.watcher), value=" ", inline=False)
    debts = ", ".join(f"{story.LEDGER_LABELS[tag]} ×{value}" for tag, value in st.ledger.items() if value > 0)
    bonds = ", ".join(
        f"{story.NPC_LABELS.get(npc, npc)} {value:+d}" for npc, value in st.relations.items() if value
    )
    if debts or bonds:
        last.add_field(
            name="🩸 WHAT THE TOWN REMEMBERS",
            value="\n".join(filter(None, [f"debts: {debts}" if debts else "", f"bonds: {bonds}" if bonds else ""])),
            inline=False,
        )
    if node.payoffs:
        last.set_footer(text=f"The town remembered: {', '.join(node.payoffs)}")
    else:
        last.set_footer(
            text=f"Checkpoint: Chapter {story.NODES.get(st.checkpoint, {}).get('chapter', '?')} · "
            f"{len(st.history)} choice(s) · {party_count} in party · session {sid}"
        )
    if st.ending:
        last.add_field(name="**RUN ENDED**", value=f"*{st.ending}* — your debts and bonds carry into the next run.", inline=False)
    return embeds


class StoryView(discord.ui.View):
    def __init__(self, sid: int, scene: Scene, party_count: int):
        super().__init__(timeout=60 * 60 * 24)
        self.sid = sid
        self.scene = scene
        self.party_count = party_count
        if scene.finished:
            again = discord.ui.Button(
                label="🕯️ Walk the Road Again", style=discord.ButtonStyle.primary, custom_id=f"hs:{sid}:again", row=0
            )
            again.callback = self._restart_callback()
            self.add_item(again)
            return
        index = 0
        for choice in scene.node.choices:
            missing = choice.get("_missing", [])
            button = discord.ui.Button(
                label=("🔒 " if missing else "") + str(choice["label"])[:75],
                style=discord.ButtonStyle.secondary if missing else _style(choice),
                custom_id=f"hs:{sid}:{scene.node.node_id}:{choice['id']}",
                disabled=bool(missing),
                row=index // 5,
            )
            if missing:
                button.tooltip = "You would need " + ", ".join(
                    story.ITEM_LABELS.get(item, item) for item in missing
                )
            else:
                button.callback = self._make_callback(scene.node.node_id, choice)
            self.add_item(button)
            index += 1
        row = min((index + 4) // 5, 4)
        self.add_item(JournalButton(sid, row=row))
        self.add_item(InventoryButton(sid, row=row))

    def _make_callback(self, node_id: str, choice: dict[str, Any]):
        async def callback(interaction: discord.Interaction) -> None:
            await handle_choice(interaction, self.sid, node_id, choice["id"], self.party_count)

        return callback

    def _restart_callback(self):
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(
                "New party, same road. **Play With Friends → Create Party**.", view=PartyView(), ephemeral=True
            )

        return callback


def _style(choice: dict[str, Any]) -> discord.ButtonStyle:
    named = getattr(discord.ButtonStyle, str(choice.get("style", "secondary")).upper(), None)
    return named or discord.ButtonStyle.secondary


async def handle_choice(
    interaction: discord.Interaction, sid: int, node_id: str, choice_id: str, party_count: int
) -> None:
    store: Store = interaction.client.store
    meta = await store.session_meta(sid)
    guild_id = int(meta["guild_id"]) if meta else (interaction.guild.id if interaction.guild else 0)
    await interaction.response.defer(ephemeral=True)
    await _learn_name(interaction, sid)
    try:
        scene, clips = await take_choice(store, sid, guild_id, interaction.user.id, node_id, choice_id)
    except (StaleChoice, NotInStory, ValueError) as exc:
        await interaction.followup.send(str(exc), ephemeral=True)
        return
    await send_scares(interaction.followup, clips)
    embeds = scene_embeds(scene, party_count, sid)
    await send_scene(interaction.followup, embeds, sid, scene, party_count)


async def send_scene(followup: Any, embeds: list[discord.Embed], sid: int, scene: Scene, party_count: int) -> None:
    """Discord rejects a message that has components but no content, so the view rides on the last embed."""
    if scene.finished:
        for embed in embeds:
            await followup.send(embed=embed, ephemeral=True, wait=True)
        await followup.send(
            embed=discord.Embed(
                title="🎃 The town keeps what it takes",
                description="This run is over. **Play With Friends → Create Party** to walk the road again — "
                "it will already know which plank gives.",
                color=discord.Color.red(),
            ),
            view=PartyView(),
            ephemeral=True,
        )
        return
    *head, last = embeds
    for embed in head:
        await followup.send(embed=embed, ephemeral=True, wait=True)
    await followup.send(embed=last, view=StoryView(sid, scene, party_count), ephemeral=True)


class JournalButton(discord.ui.Button):
    def __init__(self, sid: int, row: int = 0):
        super().__init__(label="📓 Journal", style=discord.ButtonStyle.primary, row=row)
        self.sid = sid

    async def callback(self, interaction: discord.Interaction) -> None:
        await show_journal(interaction, self.sid)


class InventoryButton(discord.ui.Button):
    def __init__(self, sid: int, row: int = 0):
        super().__init__(label="🎒 Inventory", style=discord.ButtonStyle.primary, row=row)
        self.sid = sid

    async def callback(self, interaction: discord.Interaction) -> None:
        state = await _state(interaction, self.sid)
        if not state:
            await interaction.response.send_message("Join this story session to view your inventory.", ephemeral=True)
            return
        text = "\n".join(f"• {story.ITEM_LABELS.get(item, item)}" for item in state.inventory) or "Your pockets are empty."
        embed = discord.Embed(title="🎒 Inventory", description=text, color=discord.Color.dark_teal())
        embed.set_footer(text=pressure_text(state.watcher))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def _state(interaction: discord.Interaction, sid: int):
    store: Store = interaction.client.store
    meta = await store.session_meta(sid)
    guild_id = int(meta["guild_id"]) if meta else (interaction.guild.id if interaction.guild else 0)
    return await store.state(sid, interaction.user.id, guild_id)


async def _learn_name(interaction: discord.Interaction, sid: int) -> None:
    """Give the town something to call you by, once, if it does not have it yet."""
    await interaction.client.store.seed_alias(sid, interaction.user.id, interaction.user.display_name)


async def show_journal(interaction: discord.Interaction, sid: int) -> None:
    st = await _state(interaction, sid)
    if not st:
        await interaction.response.send_message("Join this story session to view your journal.", ephemeral=True)
        return
    store: Store = interaction.client.store
    memory = await store.world_memory(sid, interaction.user.id)
    pages: list[tuple[str, str]] = []
    if memory:
        pages.append(
            (
                "🕯️ The Town Remembers",
                "\n".join(f"> {row['detail']}  ·  _{row['kind']}_" for row in reversed(memory)),
            )
        )
    clues = st.journal
    if clues:
        chunk: list[str] = []
        for clue in clues:
            candidate = "\n\n".join([*chunk, f"• {clue}"])
            if len(candidate) > 3800 and chunk:
                pages.append(("📓 Clues", chunk_page(chunk)))
                chunk = [f"• {clue}"]
            else:
                chunk.append(f"• {clue}")
        if chunk:
            pages.append(("📓 Clues", chunk_page(chunk)))
    if not pages:
        pages.append(("📓 Journal", "Nothing recorded yet. The town has not given up its secrets."))
    view = JournalView(sid, pages, 0)
    embed = page_embed(pages[0], st)
    await interaction.response.send_message(embed=embed, view=view if len(pages) > 1 else None, ephemeral=True)


def page_embed(page: tuple[str, str], st: Any) -> discord.Embed:
    title, text = page
    embed = discord.Embed(title=title, description=text[:EMBED_LIMIT], color=discord.Color.dark_teal())
    if st:
        embed.set_footer(text=f"{len(st.journal)} clue(s) · {pressure_text(st.watcher)}")
    return embed


def chunk_page(lines: list[str]) -> str:
    return "\n\n".join(lines)[:EMBED_LIMIT]


class JournalView(discord.ui.View):
    def __init__(self, sid: int, pages: list[tuple[str, str]], index: int):
        super().__init__(timeout=300)
        self.sid = sid
        self.pages = pages
        self.index = index

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.turn(interaction, -1)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def nxt(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.turn(interaction, 1)

    async def turn(self, interaction: discord.Interaction, delta: int) -> None:
        self.index = max(0, min(len(self.pages) - 1, self.index + delta))
        st = await _state(interaction, self.sid)
        await interaction.response.edit_message(embed=page_embed(self.pages[self.index], st), view=self)


def location_button_label(label: str) -> str:
    """`⛪ St. Erth's, where the choir stopped` → `⛪ St. Erth's`."""
    emoji, _, rest = label.partition(" ")
    stem = re.split(r"[,—–-]", rest)[0].strip() or rest
    return f"{emoji} {stem}"[:32]


def open_locations(st: Any) -> list[str]:
    """Places the player has already stood in, in the order the town reveals them."""
    visited = {
        story.NODES[node]["location"]
        for node, count in st.visits.items()
        if count and node in story.NODES
    }
    return [key for key in story.LOCATIONS if key in visited and story.HUBS.get(key) in story.NODES]


class ExploreView(discord.ui.View):
    """The town opens where you have already been — and you can walk back to them."""

    def __init__(self, sid: int, open_keys: list[str]):
        super().__init__(timeout=300)
        self.sid = sid
        for index, key in enumerate(open_keys[:10]):
            self.add_item(
                self._travel_button(
                    story.HUBS[key], location_button_label(story.LOCATIONS[key]), min(index // 5, 3)
                )
            )
        refresh = discord.ui.Button(label="🗺️ Refresh", style=discord.ButtonStyle.secondary, row=4)
        refresh.callback = self._refresh_callback()
        self.add_item(refresh)

    def _refresh_callback(self):
        async def callback(interaction: discord.Interaction) -> None:
            await show_explore(interaction, self.sid)

        return callback

    def _travel_button(self, node_id: str, label: str, row: int) -> discord.ui.Button:
        button = discord.ui.Button(label=label, style=discord.ButtonStyle.primary, row=row)
        button.callback = self._travel_callback(node_id)
        return button

    def _travel_callback(self, node_id: str):
        async def callback(interaction: discord.Interaction) -> None:
            store: Store = interaction.client.store
            meta = await store.session_meta(self.sid)
            guild_id = int(meta["guild_id"]) if meta else (interaction.guild.id if interaction.guild else 0)
            await interaction.response.defer(ephemeral=True)
            try:
                await store.travel(self.sid, guild_id, interaction.user.id, node_id)
                scene = await build_scene(store, self.sid, guild_id, interaction.user.id)
            except (StaleChoice, NotInStory) as exc:
                await interaction.followup.send(str(exc), ephemeral=True)
                return
            await send_scares(interaction.followup, scare_clips(scene.scares))
            party = await store.party_members(self.sid)
            await send_scene(
                interaction.followup, scene_embeds(scene, len(party), self.sid), self.sid, scene, len(party)
            )

        return callback


async def show_explore(interaction: discord.Interaction, sid: int) -> None:
    st = await _state(interaction, sid)
    if not st:
        await interaction.response.send_message("No story here yet.", ephemeral=True)
        return
    keys = open_locations(st)
    rows = [f"• {label}" if key in keys else "• 🔒 *unmarked on any map*" for key, label in story.LOCATIONS.items()]
    embed = discord.Embed(
        title="🗺️ Explore Town",
        description=(
            "**The town opens where you have already been.**\n"
            + "\n".join(rows)
            + "\n\nPick a place to walk there now. You will find it changed by the last time you left it, "
            "and **🕯️ Return to Your Story** always brings you back."
        ),
        color=discord.Color.dark_teal(),
    )
    embed.set_footer(text=pressure_text(st.watcher))
    await interaction.response.send_message(embed=embed, view=ExploreView(sid, keys), ephemeral=True)


class SettingsView(discord.ui.View):
    def __init__(self, sid: int):
        super().__init__(timeout=300)
        self.sid = sid

    @discord.ui.button(label="🖼️ Jumpscare GIFs", style=discord.ButtonStyle.secondary)
    async def toggle_scares(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        st = await _state(interaction, self.sid)
        if not st:
            await interaction.response.send_message("No story here yet.", ephemeral=True)
            return
        store: Store = interaction.client.store
        await store.set_scares(self.sid, interaction.user.id, not st.scares_enabled)
        await interaction.response.send_message(
            f"Jumpscare GIFs are now **{'on' if not st.scares_enabled else 'off'}**.", ephemeral=True
        )

    @discord.ui.button(label="🪪 Your Name", style=discord.ButtonStyle.secondary)
    async def choose_name(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        st = await _state(interaction, self.sid)
        if not st:
            await interaction.response.send_message("No story here yet.", ephemeral=True)
            return
        await interaction.response.send_modal(AliasModal(self.sid, st.alias))

    @discord.ui.button(label="🩸 Memory", style=discord.ButtonStyle.secondary)
    async def memory(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        st = await _state(interaction, self.sid)
        if not st:
            await interaction.response.send_message("No story here yet.", ephemeral=True)
            return
        store: Store = interaction.client.store
        nights = await store.town_nights(self.sid, interaction.user.id)
        lines = [
            f"The town calls you **{st.name}**.",
            f"Watcher pressure: **{st.watcher}**",
            f"Checkpoint: `{st.checkpoint}`",
            f"Choices made: {len(st.history)}",
            "Bonds: " + (", ".join(f"{k} {v:+d}" for k, v in st.relations.items() if v) or "none"),
            "Debts: " + (", ".join(f"{k} ×{v}" for k, v in st.ledger.items() if v) or "none"),
            f"Nights the town moved without you: {nights}",
            f"Prior runs the town remembers: {st.previous_runs}",
        ]
        embed = discord.Embed(title="🩸 What the town holds", description="\n".join(lines), color=discord.Color.dark_red())
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AliasModal(discord.ui.Modal, title="What should the town call you?"):
    alias = discord.ui.TextInput(
        label="Name", placeholder="Wren, or whatever you answer to", max_length=32, required=False
    )

    def __init__(self, sid: int, current: str = ""):
        super().__init__()
        self.sid = sid
        self.alias.default = current or None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        store: Store = interaction.client.store
        saved = await store.set_alias(self.sid, interaction.user.id, str(self.alias.value))
        if not saved:
            await interaction.response.send_message(
                "Cleared. The town will fall back on the name your Discord account carries.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Noted. From here on, the town says **{saved}** — and so do the things that watched you come in.",
            ephemeral=True,
        )


class MenuView(discord.ui.View):
    def __init__(self, bot: Any):
        super().__init__(timeout=60 * 60 * 6)
        self.bot = bot

    async def _first_session(self, interaction: discord.Interaction) -> int | None:
        if not interaction.guild:
            return None
        sessions = await interaction.client.store.sessions_for(interaction.user.id, interaction.guild.id)
        return sessions[0] if sessions else None

    @discord.ui.button(label="📖 Continue Story", style=discord.ButtonStyle.primary, row=0)
    async def continue_story(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sid = await self._first_session(interaction)
        if sid is None:
            await interaction.response.send_message(
                "You don't have a story here yet. Press **Play With Friends** to create one.", ephemeral=True
            )
            return
        await open_story(interaction, sid)

    @discord.ui.button(label="🎒 Inventory", style=discord.ButtonStyle.secondary, row=0)
    async def inventory_menu(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sid = await self._first_session(interaction)
        if sid is None:
            await interaction.response.send_message("Start a story first.", ephemeral=True)
            return
        await InventoryButton(sid).callback(interaction)

    @discord.ui.button(label="📓 Journal", style=discord.ButtonStyle.secondary, row=0)
    async def journal_menu(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sid = await self._first_session(interaction)
        if sid is None:
            await interaction.response.send_message("Start a story first.", ephemeral=True)
            return
        await show_journal(interaction, sid)

    @discord.ui.button(label="🗺️ Explore Town", style=discord.ButtonStyle.secondary, row=1)
    async def explore(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sid = await self._first_session(interaction)
        if sid is None:
            await interaction.response.send_message("Start a story first.", ephemeral=True)
            return
        await show_explore(interaction, sid)

    @discord.ui.button(label="👥 Play With Friends", style=discord.ButtonStyle.success, row=1)
    async def play_friends(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Create a party, or join one with its session ID. Each of you lives your own story; the town repeats what the others did.",
            view=PartyView(),
            ephemeral=True,
        )

    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary, row=1)
    async def settings(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        sid = await self._first_session(interaction)
        if sid is None:
            await interaction.response.send_message(
                "**Settings**\nProgress saves automatically once you join a party.", ephemeral=True
            )
            return
        await interaction.response.send_message("**Settings**", view=SettingsView(sid), ephemeral=True)


async def open_story(interaction: discord.Interaction, sid: int) -> None:
    store: Store = interaction.client.store
    meta = await store.session_meta(sid)
    guild_id = int(meta["guild_id"]) if meta else (interaction.guild.id if interaction.guild else 0)
    await interaction.response.defer(ephemeral=True)
    await _learn_name(interaction, sid)
    try:
        scene = await build_scene(store, sid, guild_id, interaction.user.id)
    except NotInStory as exc:
        await interaction.followup.send(str(exc), ephemeral=True)
        return
    party = await store.party_members(sid)
    await send_scares(interaction.followup, scare_clips(scene.scares))
    await send_scene(interaction.followup, scene_embeds(scene, len(party), sid), sid, scene, len(party))


class PartyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="✨ Create Party", style=discord.ButtonStyle.success)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Create a party in a server channel.", ephemeral=True)
            return
        store: Store = interaction.client.store
        sid = await store.create_session(
            interaction.guild.id, interaction.channel_id or 0, interaction.user.id, story.ENTRY, story.ENTRY
        )
        await interaction.response.send_message(
            f"Your story party is ready! **Session ID: {sid}**\nShare the ID, then begin Chapter 1.",
            view=PartyLaunchView(sid),
            ephemeral=True,
        )

    @discord.ui.button(label="🔗 Join Party", style=discord.ButtonStyle.primary)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(JoinPartyModal())


class PartyLaunchView(discord.ui.View):
    def __init__(self, sid: int):
        super().__init__(timeout=600)
        self.sid = sid

    @discord.ui.button(label="🕯️ Begin Chapter 1", style=discord.ButtonStyle.primary)
    async def begin(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await open_story(interaction, self.sid)


class JoinPartyModal(discord.ui.Modal, title="Join a HALLOWSCAPE party"):
    session_id = discord.ui.TextInput(label="Party session ID", placeholder="For example: 12", max_length=10)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            sid = int(str(self.session_id.value))
        except ValueError:
            await interaction.response.send_message("Enter the numeric session ID.", ephemeral=True)
            return
        store: Store = interaction.client.store
        joined = await store.join_session(sid, interaction.user.id, story.ENTRY)
        if not joined:
            await interaction.response.send_message("That party could not be found.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"You joined party **{sid}**. Continue from the main menu to read your story.", view=PartyLaunchView(sid), ephemeral=True
        )
