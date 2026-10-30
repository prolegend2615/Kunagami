"""Environment reads where a blank value means "use the default".

`.env.example` ships keys with nothing after the `=`, which is the natural way to
leave something unset. `os.getenv` returns an empty string for those, so a plain
default argument never applies and the blank becomes the value: an empty string
opens the database called `''`, and `int('')` stops the bot mid-login.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("hallowscape.config")


def text(name: str, default: str) -> str:
    value = (os.getenv(name) or "").strip()
    return value or default


def number(name: str, default: float) -> float:
    raw = text(name, "")
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        log.warning("%s=%r is not a number; using the default %s", name, raw, default)
        return default


def integer(name: str, default: int) -> int:
    return int(number(name, default))
