"""`python -m hallowscape check` — validate the story graph without a token."""

from __future__ import annotations

import sys

from . import story


def main(argv: list[str]) -> int:
    if argv and argv[0] == "check":
        errors, warnings = story.validate()
        for line in warnings:
            print(f"WARN  {line}")
        for line in errors:
            print(f"ERROR {line}")
        print(
            f"\n{len(story.NODES)} nodes · {len(story.PAYOFFS)} payoff rules · "
            f"{sum(len(n.get('choices', [])) for n in story.NODES.values())} choices"
        )
        if errors:
            print("FAILED")
            return 1
        print("Story graph OK.")
        return 0
    print("usage: python -m hallowscape check")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
