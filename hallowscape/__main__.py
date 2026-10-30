"""Command line helpers that need no running bot.

    python -m hallowscape check    validate the story graph and the candy door,
                                   no token required
    python -m hallowscape guilds   log in with the .env token and list the servers
                                   the bot is really in, so DISCORD_GUILD_ID can be
                                   filled with an ID that works
"""

from __future__ import annotations

import sys

from . import candy, story


def _check(argv: list[str]) -> int:
    errors, warnings = story.validate()
    door_errors, door_warnings = candy.validate_door()
    for line in warnings + door_warnings:
        print(f"WARN  {line}")
    for line in errors + door_errors:
        print(f"ERROR {line}")
    print(
        f"\n{len(story.NODES)} nodes · {len(story.PAYOFFS)} payoff rules · "
        f"{sum(len(n.get('choices', [])) for n in story.NODES.values())} choices"
    )
    print(
        f"{len(candy.VISITORS)} visitors over {candy.NIGHTS_TOTAL} nights at the candy door · "
        f"{candy.real_count()} of them are children · {candy.candy_budget()} sweets in a whole run"
    )
    if errors or door_errors:
        print("FAILED")
        return 1
    print("Story graph and the candy door both check out.")
    return 0


def _guilds() -> int:
    import asyncio
    import os

    import discord

    from .bot import load_env

    load_env()
    token = (os.getenv("DISCORD_TOKEN") or "").strip()
    if not token or token == "put_your_bot_token_here":
        print("Set DISCORD_TOKEN in .env first — this helper needs the token the bot uses.")
        return 1

    async def probe() -> int:
        client = discord.Client(intents=discord.Intents.none())
        try:
            await client.login(token)
            app = await client.application_info()
            found = [guild async for guild in client.fetch_guilds(limit=None)]
        except discord.DiscordException as exc:
            print(f"Discord refused that token: {exc}")
            return 1
        finally:
            await client.close()
        print(f"Application: {app.name} (id {app.id})")
        if not found:
            print("This bot is in no servers yet.")
            print("In the developer portal: OAuth2 -> URL Generator, scopes `bot` and")
            print("`applications.commands`, then open the generated URL to invite the bot.")
            return 1
        print("Servers this bot can register commands in:")
        for guild in sorted(found, key=lambda g: g.name.lower()):
            print(f"  {guild.id}  {guild.name}")
        print("\nPut the server ID you want into DISCORD_GUILD_ID in .env.")
        return 0

    return asyncio.run(probe())


def main(argv: list[str]) -> int:
    if argv and argv[0] == "check":
        return _check(argv)
    if argv and argv[0] == "guilds":
        return _guilds()
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
