# HALLOWSCAPE Discord Bot

A button-based horror story bot built with Python, discord.py, and SQLite. Five chapters and six endings, per-player persistent progress, a town that remembers what you did and keeps moving while you are offline, party play with a shared world log, and `/start` plus `/help`.

## Layout

| Path | Owns |
| --- | --- |
| [main.py](main.py) | entry point only |
| [hallowscape/story.py](hallowscape/story.py) | all prose, items, locations, payoff rules, town events, and the graph validator |
| [hallowscape/rules.py](hallowscape/rules.py) | predicates, consequence resolution, node rendering (no Discord, no SQL) |
| [hallowscape/db.py](hallowscape/db.py) | SQLite schema, atomic choice application, memory tables, travel |
| [hallowscape/migrate.py](hallowscape/migrate.py) | the one-time upgrade from the old single-file database |
| [hallowscape/engine.py](hallowscape/engine.py) | builds a scene: state + payoffs + offline events + party rumor, and hot-reload |
| [hallowscape/timer.py](hallowscape/timer.py) | the town clock — what happens to players who are not here |
| [hallowscape/media.py](hallowscape/media.py) | fetches GIFs and screens them for flashing frames |
| [hallowscape/ui.py](hallowscape/ui.py) | embeds, views, buttons |
| [hallowscape/bot.py](hallowscape/bot.py) | commands, startup validation, lifecycle |

## Run locally

1. Install Python 3.10 or newer.
2. Create a Discord application and bot in the [Discord Developer Portal](https://discord.com/developers/applications). Enable the **applications.commands** and **bot** scopes when generating its invite URL. The bot only needs permission to send messages, embed links, and use application commands.
3. Copy `.env.example` to `.env` and set `DISCORD_TOKEN`. Optionally set `DISCORD_GUILD_ID` while developing so slash commands appear quickly in one server.
4. Install and start:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python main.py
   ```

5. Invite the bot to your server and use `/start`.

Before the bot logs in it validates the story graph and refuses to start on a broken one. Check the graph without a token any time:

```powershell
python -m hallowscape check
```

The `hallowscape.sqlite3` database is created automatically beside `main.py`. An older database written by the single-file version is upgraded in place on first boot — progress, journal, inventory and world log all carry over, and rows pointing at chapters that no longer exist resume at Chapter 1 instead of crashing. Keep `.env` private.

## What the town remembers

The core mechanic is a payoff table in [hallowscape/story.py](hallowscape/story.py). A rule names the chapter it lands in and the condition that earns it:

```python
{
    "id": "abandoned_photograph",
    "when": {"has_any": ["sin:left_wren", "sin:left_at_door"]},
    "chapter": "hall",
    "scare": "ground_knock",
    "line": "There is a fresh photograph face-down on the hall table...",
    "choices": [{"id": "open_for_them", "label": "🚪 Open the Door for Them", "next": "cellar", ...}],
    "once": True,
}
```

When a player reaches that chapter the rule can inject a line, add a button, fire a jumpscare, replace the node's text, or queue an event. A rule can also move the meters itself — `relation`, `ledger`, `watcher`, `item`, `clue`, `flag` all work at the top level of a payoff, not only on a clicked choice — which is how *Wren took your place* can hand you a debt you never agreed to. Firing is recorded per player, so `once` rules never repeat.

A payoff that moves a meter is re-rendered after it lands, so a consequence that pushes your watcher past another rule's threshold fires in the same scene. The loop is bounded: each pass records what it fired.

State a rule can read:

- **flags** — things that happened (`saved_stranger`, `sin:left_wren`)
- **relations** — how an NPC stands with you, as a signed number, not a boolean
- **ledger** — your debts, accumulated (`abandoned ×2`)
- **watcher** — pressure from 0 up, raised by lingering and lowered by playing safe; at 4 the Watcher stops pretending

Everything is per player. Party members live their own stories, and what the others did surfaces in your chapter as rumor (`👥 THE PARTY`) and in the Journal under **🕯️ The Town Remembers**.

Consequences can also wait: `queue_event` with `due_in` seconds lands as a **🕯️ WHILE YOU WERE AWAY** block the next time the player opens the story. Nothing is DM'd to an offline player — delivery happens on return, which is both reliable and creepier.

Finishing a run writes it to the `runs` and `echoes` tables. Start a new party in the same server and Chapter 1 already knows you: *"You have stood in this road before."*

## Play together

Use **Play With Friends → Create Party**. Share the numeric session ID; friends use **Play With Friends → Join Party**. Each player makes choices in their own private story view, while the session keeps membership and the shared world log.

## Walking the town

**Explore Town** is not a list of where you have been — you can go back there. Every location in `LOCATIONS` has a hub node in `HUBS`: a small room of its own with things to do and a **🕯️ Return to Your Story** button that puts you back at your checkpoint, mid-chapter, with nothing lost.

Hubs live outside the story graph, so they never break a branch. What they can do is move the meters. Standing on the road and watching the house costs nothing but raises the Watcher; knocking on the porch raises it faster and fires a scare; walking home lowers it. That is the trade the town is always offering — the pressure you feel in Chapter 4 is mostly what you did on the way there.

A location stays 🔒 *unmarked on any map* until your own story has physically stood in it, so exploring never spoils an unplayed chapter. Buttons are capped at ten open places to stay inside Discord's component limits; **🗺️ Refresh** re-reads your progress and redraws the page.

Travel is guarded: an ended run refuses to move, and so does any node that is not a hub. The client never gets to name a destination — the button carries the node id, and the store validates it against the current story before writing.

## The town clock

Delayed consequences land on return, which is reliable but not scary. The clock is the part that keeps moving when you are not there.

[hallowscape/timer.py](hallowscape/timer.py) runs as an asyncio task beside the bot. Every `HALLOWSCAPE_CLOCK_MINUTES` (30 by default) it looks for players idle longer than `HALLOWSCAPE_IDLE_HOURS` (6), checks which of `TOWN_EVENTS` their own state has earned, and queues exactly one of them. No DM is ever sent to an offline player — the line sits in the same queue the story drains, so it arrives as **🕯️ WHILE YOU WERE AWAY** the next time they open a chapter, and the Journal counts *Nights the town moved without you*.

Each player can be visited at most once per `HALLOWSCAPE_EVENT_HOURS` (12), so the clock notices absence without nagging. Boot ticks once, which catches the town up after a restart or a long outage. Set `HALLOWSCAPE_CLOCK=0` to run the bot without it — the story, payoffs and return-queue all still work; only calendar-driven changes stop.

The clock is a task inside the bot process, so the town only moves while the bot is up. That is the honest cost of keeping the architecture lightweight: nothing is scheduled into Discord, and downtime does not accumulate into a backlog of hauntings — the boot tick gives each long-absent player one line, then the clock keeps its own hours again.

`/townclock` (administrator) forces a pass immediately, ignoring both gaps, and reports which lines the town wrote. Use it to test an event without waiting six hours.

## What the town calls you

**Settings → 🪪 Your Name** opens a modal. Whatever you type becomes the name the town uses, and prose asks for it with `{name}`:

```python
{"when": {"has_flags": ["saved_stranger"]}, "text": "Somebody said {name} at the church door and stopped as soon as it was heard."}
```

It substitutes in node descriptions, variants, conditional lines, payoff lines and town events — everywhere prose speaks to a player. Nobody has one until they choose, and the fallback is `stranger`, so *"Somebody said stranger at the church door"* still reads correctly.

Names come from players, so they get scrubbed before they are stored: mentions (`@everyone`, `@here`, `<@123>`) are removed whole, markdown and angle brackets are stripped, and the result is capped at 32 characters. The name is only ever placed inside ephemeral embeds the owner can see, and it cannot start a ping.

## Publishing chapters without a restart

Edit [hallowscape/story.py](hallowscape/story.py) while the bot runs, then use `/reload` (administrator). It re-imports the module, runs the same validator that guards startup, and swaps the new tables in only if the result is clean. Broken prose is rejected with the first ten errors and the live story is restored from a snapshot — a typo in a chapter cannot take down a server that is mid-scene. A successful reload reports the new node, payoff and town-event counts.

Players already in a chapter are not stranded by a swap: whoever opens a story finds their state repaired — a chapter that no longer exists sends them back to their checkpoint, and a checkpoint that no longer exists wakes them at Chapter 1 — and the database is rewritten so the buttons on screen match the live graph. `ORDER`, the precomputed choice index, is rebuilt after every swap.

## Adding a chapter

Add nodes to `NODES` in [hallowscape/story.py](hallowscape/story.py). A node needs a `chapter` number, a `location`, a `title`, a `description`, and `choices` (or an `ending` string instead). Each choice needs a unique `id`, a `label`, and a `next` node.

`next` is normally a node id. Two values are resolved per player instead of per story: `@checkpoint` sends the player back to wherever their own story is paused, and `@self` leaves them exactly where they are. They only make sense on a `hub` node, which is how Explore Town travel works without a story branch having to know who is looking at it.

Optional choice fields:

- `item` / `items` — add to inventory
- `requires_item` / `requires_items` — gate it. With `hide_if_locked` the button disappears until you find the item; without it, the button shows as 🔒 disabled and says what you'd need
- `when` — only offer this choice when the predicate passes
- `clue` / `clues` — write to the journal
- `flag` / `flags` / `flags_list` — remember that this happened
- `relation` / `ledger` / `watcher` — move the memory meters
- `scare` — a jumpscare tag for this outcome
- `queue_event` / `queue_events` — land later, on the player's return
- `style` — `primary`, `secondary`, `success`, `danger`

Node-level fields:

- `variants` — conditional paragraphs, first match wins; this is how one merge point plays differently for different players
- `lines` — conditional paragraphs appended
- `echoes` — conditional text only shown to players with prior runs
- `checkpoint` — resume point for **Continue Story**
- `scare` — fires every time this node is reached
- `hub` — marks the node as a place you can visit from **Explore Town**; the validator requires at least one choice with `next: "@checkpoint"` and forbids any story node from pointing at `@checkpoint`
- `ending` — ends the run and writes the echo record

`when` predicates accept `has_flags`, `has_any`, `lacks_flags`, `flag_equals`, `has_items`, `lacks_items`, `relation`, `ledger`, `watcher_at_least`, `watcher_below`, `visits_at_least`, `visited_at_least`, `took`, `previous_runs`, `scares_enabled`. Comparisons accept plain numbers (meaning "at least") or strings like `">=2"`, `<0`, `!=1`. The same predicate language gates town events, so a rule can be written once and read by both the story and the clock.

Text is substituted before it reaches a player: `{name}` in any node description, variant, line, payoff line or town event becomes that player's alias — see **What the town calls you**.

The validator at startup catches typos in `when` keys, unreachable nodes, items required before they can be found, duplicate choice IDs, dead ends, unknown scare tags, payoff rules whose gate can never precede their target, hub nodes that cannot return you to your story, town events with a broken predicate or text too long to send, and prose that would exceed an embed. Treat its warnings as editorial notes: a single-choice node is a slideshow, and players feel that.

## Jumpscare GIFs

Scares are tied to story outcomes, never random clicks. Set `JUMPSCARE_GIFS` in `.env` to a comma-separated list of hosted URLs, optionally tagged: `behind_you=https://.../a.gif,https://.../b.gif`. Tags come from `SCARES` in `hallowscape/story.py`; a bare URL is a fallback pool for any tag. Players can turn GIFs off in **Settings**, per player and stored with their progress — the narrative still continues, just without the picture.

Scares fire from everywhere the story can be angry, not only the button you clicked: a node's own `scare`, a payoff rule's `scare`, and the destination node's `scare` all reach the player on the same turn, deduplicated, and all of them respect the per-player consent flag.

Nothing from that list is shown to a player before [hallowscape/media.py](hallowscape/media.py) has looked at it. Every URL must be `https`, is fetched with a `HALLOWSCAPE_MAX_GIF_KB` cap (6 MB) enforced against both the `Content-Length` header and the bytes actually read, and is rejected on any network failure rather than allowed to raise into the chapter. A scare that cannot be delivered becomes the prose line instead.

The bytes are then parsed as a GIF block chain — not by trusting a file extension — and the Graphic Control delays are read to find the fastest frame. Four or more frames on a sub-100 ms cycle is a strobe, and strobes are refused: photosensitive players do not get them, ever, unless the owner opts in. Refusals are remembered per URL so one bad host does not get re-fetched every chapter.

What passes is attached as a `SPOILER_`-prefixed file, so it is behind a click the player chooses to open. If `HALLOWSCAPE_ALLOW_FLASHING=1` overrides the check, the message carries an explicit ⚠️ flashing-imagery warning naming the toggle that turns GIFs off. If Discord refuses the upload, the player sees the URL and the log says why.
