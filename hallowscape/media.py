"""Jumpscare media: fetch, screen for strobing, and hand back a spoiler file.

A GIF is only ever sent after its frame timings have been read. Nothing here
talks to Discord; it turns a URL into bytes plus a verdict, and the UI decides
how to deliver it.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any

from . import config

MAX_BYTES_DEFAULT_KB = 6144
FLASHING_MS = 100
MIN_FRAMES_FOR_FLASH = 4

HEADER = re.compile(rb"^GIF8[79]a")


def max_bytes() -> int:
    """Read lazily: .env is not loaded until the bot starts."""
    return config.integer("HALLOWSCAPE_MAX_GIF_KB", MAX_BYTES_DEFAULT_KB) * 1024


def allow_flashing() -> bool:
    return config.text("HALLOWSCAPE_ALLOW_FLASHING", "0") == "1"


@dataclass
class Analysis:
    frames: int
    fastest_ms: int
    width: int
    height: int
    timed: bool = True

    @property
    def flashing(self) -> bool:
        """Four or more frames at 100 ms or less is a strobe, not motion.

        A delay of 0 means "as fast as the viewer will allow", so it counts. A
        GIF that declares no timings at all is left alone: viewers default it to
        roughly ten frames a second, which is not a flash.
        """
        return self.timed and self.frames >= MIN_FRAMES_FOR_FLASH and self.fastest_ms <= FLASHING_MS

    def summary(self) -> str:
        rate = f"{self.fastest_ms} ms" if self.timed else "undated"
        return f"{self.frames} frames at {self.width}×{self.height}, fastest {rate}"


def analyze(data: bytes) -> Analysis:
    """Read the GIF block chain for frame count and the shortest frame delay.

    Delays are stored in hundredths of a second; 0 means "as fast as the viewer
    will allow", which is exactly what a strobe looks like.
    """
    if not HEADER.match(data[:6]):
        raise ValueError("Not a GIF — the safety screen only understands GIF frames.")
    pos = 6
    width = int.from_bytes(data[pos : pos + 2], "little")
    height = int.from_bytes(data[pos + 2 : pos + 4], "little")
    packed = data[pos + 4]
    pos += 7
    if packed & 0x80:
        pos += 3 * (2 ** (packed & 0x07) + 1)

    frames = 0
    delay = 0
    delay_known = False
    fastest: int | None = None
    while pos + 1 <= len(data):
        block = data[pos]
        pos += 1
        if block == 0x3B:
            break
        if block == 0x21:
            label = data[pos] if pos < len(data) else 0
            pos += 1
            if label == 0xF9:  # graphic control: packed, delay lo, delay hi, transparency
                size = data[pos]
                if size >= 4:
                    delay = int.from_bytes(data[pos + 2 : pos + 4], "little") * 10
                    delay_known = True
                pos += size + 2  # size byte, body, terminator
            else:
                pos = _skip_subblocks(data, pos)
            continue
        if block == 0x2C:
            frames += 1
            if delay_known:
                fastest = delay if fastest is None else min(fastest, delay)
            delay, delay_known = 0, False
            flags = data[pos + 8] if pos + 8 < len(data) else 0
            pos += 9
            if flags & 0x80:
                pos += 3 * (2 ** (flags & 0x07) + 1)
            pos += 1  # LZW minimum code size
            pos = _skip_subblocks(data, pos)
            continue
        break
    return Analysis(
        frames=frames,
        fastest_ms=0 if fastest is None else fastest,
        width=width,
        height=height,
        timed=fastest is not None,
    )


def _skip_subblocks(data: bytes, pos: int) -> int:
    while pos < len(data):
        size = data[pos]
        pos += 1
        if size == 0:
            return pos
        pos += size
    return pos


@dataclass
class Clip:
    """A screened GIF, ready to be attached as a spoiler."""

    url: str
    data: bytes
    analysis: Analysis
    name: str

    @property
    def spoiler_name(self) -> str:
        return self.name if self.name.startswith("SPOILER_") else f"SPOILER_{self.name}"


def _safe_name(url: str) -> str:
    stem = re.split(r"[?#]", url.rsplit("/", 1)[-1])[0]
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)[:48] or "scare"
    return stem if stem.lower().endswith(".gif") else f"{stem}.gif"


class Screener:
    """Fetches once per URL and remembers the verdict for the process lifetime."""

    def __init__(self, session: Any = None):
        self._session = session
        self._verdicts: dict[str, tuple[Clip | None, str | None]] = {}

    async def session(self) -> Any:
        if self._session is None:
            import aiohttp

            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._session

    async def close(self) -> None:
        if self._session is not None and hasattr(self._session, "close"):
            await self._session.close()
            self._session = None

    async def prepare(self, url: str) -> tuple[Clip | None, str | None]:
        """Return (clip, refusal_reason); exactly one of them is set."""
        if url not in self._verdicts:
            self._verdicts[url] = await self._fetch(url)
        return self._verdicts[url]

    async def _fetch(self, url: str) -> tuple[Clip | None, str | None]:
        if not url.startswith("https://"):
            return None, "not https"
        limit = max_bytes()
        try:
            session = await self.session()
            async with session.get(url, headers={"User-Agent": "hallowscape-bot"}) as resp:
                if resp.status != 200:
                    return None, f"HTTP {resp.status}"
                if int(resp.headers.get("Content-Length") or 0) > limit:
                    return None, "too large"
                body = io.BytesIO()
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    body.write(chunk)
                    if body.tell() > limit:
                        return None, "too large"
        except Exception as exc:  # network, DNS, TLS — never let a scare break the chapter
            return None, f"fetch failed ({type(exc).__name__})"
        data = body.getvalue()
        try:
            analysis = analyze(data)
        except ValueError as exc:
            return None, str(exc)
        if analysis.flashing and not allow_flashing():
            return None, f"flashing ({analysis.summary()})"
        return Clip(url=url, data=data, analysis=analysis, name=_safe_name(url)), None


DEFAULT = Screener()
