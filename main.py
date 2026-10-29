"""HALLOWSCAPE entry point. Run with `python main.py`.

Story content lives in hallowscape/story.py, persistence in hallowscape/db.py,
consequence logic in hallowscape/rules.py, and Discord UI in hallowscape/ui.py.
Check the story graph without a token using `python -m hallowscape check`.
"""

import asyncio

from hallowscape.bot import run

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
