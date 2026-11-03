"""facebook-scraper Meta NASA, or python -m facebook_scraper Meta NASA"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from contextlib import contextmanager

from .scrape import TokenMissing, scrape_page, token, write

FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def positive(value: str) -> int:
    """Reject a limit the API would charge for and not honour."""
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"{value} is not 1 or more")
    return number



@contextmanager
def waiting(label: str):
    """A spinner and a running clock, so minutes of waiting look alive.

    Outside a terminal it prints one plain line instead: a log wants a line,
    not an animation.
    """
    if not sys.stdout.isatty():
        print(f"asking  {label}...", flush=True)
        yield
        return
    done = threading.Event()
    started = time.monotonic()

    def spin() -> None:
        frame = 0
        while not done.wait(0.1):
            secs = int(time.monotonic() - started)
            clock = f"{secs // 3600}:{secs // 60 % 60:02d}:{secs % 60:02d}"
            sys.stdout.write(f"\r\033[2K{FRAMES[frame % len(FRAMES)]} {label} {clock}")
            sys.stdout.flush()
            frame += 1

    thread = threading.Thread(target=spin, daemon=True)
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join()
        sys.stdout.write("\r\033[2K")  # leave the line clean for the result
        sys.stdout.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="facebook-scraper",
        description="Scrape recent posts from one or more Facebook pages.",
    )
    parser.add_argument(
        "pages", nargs="+", help="page names or URLs, such as Meta or facebook.com/Meta"
    )
    parser.add_argument("--limit", type=positive, default=5, help="posts per page, default 5")
    parser.add_argument("--out", default="facebook.json", help="output file, default %(default)s")
    args = parser.parse_args(argv)

    print(
        f"Fetching up to {args.limit} recent posts per page, for: {', '.join(args.pages)}\n"
        "Usually one to three minutes each. Billed per post, 5,000 free credits a month.",
        flush=True,  # piped, an unflushed header would print after the error below
    )
    try:
        token()  # fail before the first wait, not after it
    except TokenMissing as exc:
        print(exc, file=sys.stderr)
        return 2

    outcomes = []
    for page in args.pages:
        with waiting(page):
            outcome = scrape_page(page, args.limit)
        print(outcome.line(), flush=True)
        outcomes.append(outcome)

    path = write(outcomes, args.out)
    found = [post for outcome in outcomes for post in outcome.posts]
    fields = f" ({len(found[0])} fields per post)" if found else ""
    print(f"\nSaved {len(found)} posts as JSON to {path}{fields}")
    return 0 if all(o.ok for o in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
