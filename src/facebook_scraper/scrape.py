"""Facebook pages, posts, comments, Marketplace, events and ads on the Bright Data Scraper API.

    page URL -> trigger -> poll progress -> fetch snapshot -> records

Standard library only. The Python SDK wraps five of these eleven scrapers, and
the API rejects the `num_of_comments` its comments call sends, so this module
talks to the API over HTTP. Every call is an asynchronous job: trigger it, poll
until the snapshot is ready, download it. On 2026-11-03 a run took 12 seconds
(reviews, one ad) to 234 seconds (a Marketplace category).
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = "https://api.brightdata.com/datasets/v3"

#: Every Facebook scraper, by what it returns. All take a `url` input unless noted.
PAGE_POSTS = "gd_lkaxegm826bjpoo9m5"  # posts from a page URL
GROUP_POSTS = "gd_lz11l67o2cb3r0lkj3"  # posts from a public group URL
POSTS = "gd_lyclm1571iy3mv57zw"  # one post per post URL
COMMENTS = "gd_lkay758p1eanlolqw8"  # comments on a post URL
REELS = "gd_lyclm3ey2q6rww027t"  # reels from a page URL
PAGES = "gd_mf124a0511bauquyow"  # page details: followers, category, contact info
PROFILES = "gd_mf0urb782734ik94dz"  # public profile details of a person
REVIEWS = "gd_m0dtqpiu1mbcyc2g86"  # reviews from a page's /reviews/ URL
EVENTS = "gd_m14sd0to1jz48ppm51"  # event URL, or discover by search URL or venue
MARKETPLACE = "gd_lvt9iwuh6fbcwmx1a"  # listing URL, or discover by keyword or category URL
AD_LIBRARY = "gd_mtveskb62h7q65ftgz"  # Meta Ad Library ad URL, or discover by keyword

#: The slowest run on 2026-11-03 was 234 seconds; the wait outlasts that comfortably.
TIMEOUT = 900
POLL_SECONDS = 10

NO_TOKEN = (
    "API token required but not found.\n"
    "  export BRIGHTDATA_API_TOKEN=YOUR_API_KEY   token: https://brightdata.com/cp/setting/users\n"
    "  or run once: npx -p @brightdata/cli bdata login"
)


class ApiError(Exception):
    """The API refused a request, or a job ended without a snapshot."""


class TokenMissing(ApiError):
    """No token in the environment and no Bright Data CLI login."""


def _cli_credentials() -> Path:
    """Where `bdata login` stores the key, the same path the Python SDK reads."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "brightdata-cli" / "credentials.json"


def token() -> str:
    """BRIGHTDATA_API_TOKEN, else the Bright Data CLI login. Never a key in code."""
    found = os.environ.get("BRIGHTDATA_API_TOKEN", "").strip()
    if found:
        return found
    try:
        found = json.loads(_cli_credentials().read_text(encoding="utf-8")).get("api_key", "")
    except (OSError, ValueError, AttributeError):
        found = ""
    if not found:
        raise TokenMissing(NO_TOKEN)
    return found


def _call(path: str, body: Any = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        API + path,
        data=data,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace").strip()
        raise ApiError(f"HTTP {exc.code}: {detail[:300]}") from None


def trigger(
    dataset_id: str,
    inputs: list[dict[str, Any]],
    *,
    discover_by: str | None = None,
    limit_per_input: int | None = None,
) -> str:
    """Start a job and return its snapshot id. Error rows are always asked for."""
    query: dict[str, Any] = {"dataset_id": dataset_id, "include_errors": "true"}
    if discover_by:
        query.update(type="discover_new", discover_by=discover_by)
    if limit_per_input is not None:
        query["limit_per_input"] = limit_per_input
    return _call("/trigger?" + urllib.parse.urlencode(query), inputs)["snapshot_id"]


def status(snapshot_id: str) -> str:
    """running, ready or failed."""
    return _call(f"/progress/{snapshot_id}")["status"]


def fetch(snapshot_id: str) -> list[dict[str, Any]]:
    """The rows of a ready snapshot. Snapshots stay downloadable for 30 days."""
    data = _call(f"/snapshot/{snapshot_id}?format=json")
    return [row for row in (data if isinstance(data, list) else [data]) if isinstance(row, dict)]


def _poll(snapshot_id: str) -> str:
    """status(), except that a dropped connection is not the end of a paid job.

    A poll is safe to repeat. A Node run of this same loop lost a job to one
    "fetch failed" on 2026-10-24, five minutes in. An HTTP error still raises.
    """
    try:
        return status(snapshot_id)
    except (urllib.error.URLError, OSError):
        return "running"


def run(
    dataset_id: str,
    inputs: list[dict[str, Any]],
    *,
    discover_by: str | None = None,
    limit_per_input: int | None = None,
    timeout: float = TIMEOUT,
) -> list[dict[str, Any]]:
    """Trigger, wait, fetch. Rows the API could not collect carry an `error` key."""
    snapshot_id = trigger(
        dataset_id, inputs, discover_by=discover_by, limit_per_input=limit_per_input
    )
    deadline = time.monotonic() + timeout
    while (state := _poll(snapshot_id)) not in ("ready", "failed"):
        if time.monotonic() > deadline:
            raise TimeoutError(f"timeout: snapshot {snapshot_id} not ready after {timeout:.0f}s")
        time.sleep(POLL_SECONDS)
    if state == "failed":
        raise ApiError(f"snapshot {snapshot_id} failed")
    return fetch(snapshot_id)


def _many(value: str | Iterable[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


def _items(urls: str | Iterable[str], **fields: Any) -> list[dict[str, Any]]:
    """One input per URL, with every field that was actually set."""
    extra = {name: value for name, value in fields.items() if value is not None}
    return [{"url": url, **extra} for url in _many(urls)]


def page_posts(urls: str | Iterable[str], limit: int = 5, **options: Any) -> list[dict[str, Any]]:
    """Recent posts from Facebook page URLs, `limit` per page.

    `options` go into each input as the API names them, for example
    `start_date`, `end_date` or `posts_to_not_include`.
    """
    return run(PAGE_POSTS, _items(urls, num_of_posts=limit, **options))


def group_posts(urls: str | Iterable[str], limit: int = 5, **options: Any) -> list[dict[str, Any]]:
    """Recent posts from public Facebook group URLs, `limit` per group."""
    return run(GROUP_POSTS, _items(urls, num_of_posts=limit, **options))


def posts(urls: str | Iterable[str]) -> list[dict[str, Any]]:
    """Full records for Facebook post URLs, one job for the whole list."""
    return run(POSTS, _items(urls))


def comments(urls: str | Iterable[str], limit: int = 10, **options: Any) -> list[dict[str, Any]]:
    """Comments on Facebook post URLs. Billed per comment, so set `limit`.

    The limit is the `limit_records` input. `num_of_comments`, which the Python
    SDK sends, is rejected by the API as a validation error.
    """
    return run(COMMENTS, _items(urls, limit_records=limit, **options))


def reels(urls: str | Iterable[str], limit: int = 5, **options: Any) -> list[dict[str, Any]]:
    """Recent reels from Facebook page URLs, `limit` per page."""
    return run(REELS, _items(urls, num_of_posts=limit, **options))


def pages(urls: str | Iterable[str]) -> list[dict[str, Any]]:
    """Page details for Facebook page URLs: followers, category, contact info."""
    return run(PAGES, _items(urls))


def profiles(urls: str | Iterable[str]) -> list[dict[str, Any]]:
    """Public profile details for Facebook profile URLs of people."""
    return run(PROFILES, _items(urls))


def reviews(urls: str | Iterable[str], limit: int = 10, **options: Any) -> list[dict[str, Any]]:
    """Reviews from a page's reviews URL, such as https://www.facebook.com/TheGarden/reviews/.

    Many brand pages have reviews turned off and return an error row, "Reviews
    not found" or a dead page, instead of zero rows.
    """
    return run(REVIEWS, _items(urls, num_of_reviews=limit, **options))


def events(urls: str | Iterable[str]) -> list[dict[str, Any]]:
    """Full records for Facebook event URLs."""
    return run(EVENTS, _items(urls))


def events_search(search_urls: str | Iterable[str], limit: int = 5) -> list[dict[str, Any]]:
    """Events from an events search URL, such as .../events/search/?q=marathon."""
    return run(EVENTS, _items(search_urls), discover_by="url", limit_per_input=limit)


def events_by_venue(
    venue_urls: str | Iterable[str], limit: int = 5, upcoming_only: bool = True
) -> list[dict[str, Any]]:
    """Events at a venue. Pass the page's /events URL; the bare page URL finds none."""
    items = _items(venue_urls, upcoming_events_only=upcoming_only)
    return run(EVENTS, items, discover_by="venue", limit_per_input=limit)


def marketplace(urls: str | Iterable[str]) -> list[dict[str, Any]]:
    """Full records for Facebook Marketplace item URLs."""
    return run(MARKETPLACE, _items(urls))


def marketplace_search(
    keyword: str, city: str, limit: int = 5, **options: Any
) -> list[dict[str, Any]]:
    """Marketplace listings for a keyword in a city. `radius` and `date_listed` go in options."""
    item = {"keyword": keyword, "city": city, **{k: v for k, v in options.items() if v is not None}}
    return run(MARKETPLACE, [item], discover_by="keyword", limit_per_input=limit)


def marketplace_category(urls: str | Iterable[str], limit: int = 5) -> list[dict[str, Any]]:
    """Listings from a Marketplace category URL, such as .../marketplace/category/vehicles."""
    return run(MARKETPLACE, _items(urls), discover_by="url", limit_per_input=limit)


def ads(urls: str | Iterable[str]) -> list[dict[str, Any]]:
    """Full records for Meta Ad Library ad URLs, .../ads/library/?id=..."""
    return run(AD_LIBRARY, _items(urls))


def ads_search(
    keyword: str, country: str = "US", limit: int = 5, ad_type: str = "All ads"
) -> list[dict[str, Any]]:
    """Ads in the Meta Ad Library matching a keyword in one country.

    `ad_type` is validated against a fixed list: "All ads" is accepted, "all" is not.
    """
    item = {"keyword": keyword, "country": country.upper(), "ad_type": ad_type}
    return run(AD_LIBRARY, [item], discover_by="keyword", limit_per_input=limit)


#: When a discovery reaches `limit_per_input`, the crawls still running are
#: cancelled and each comes back as a row with this error. That is the limit
#: working, not a failure.
CANCELLED = "Crawl aborted on job cancel"


def split(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Records, and the error messages of the rows that are not records."""
    records = [row for row in rows if not row.get("error")]
    errors = [str(row["error"]) for row in rows if row.get("error") and row["error"] != CANCELLED]
    return records, errors


def page_url(page: str) -> str:
    """Accept Meta, @Meta, facebook.com/Meta or a full URL. Reject anything else."""
    cleaned = (page or "").strip()
    if "facebook.com/" in cleaned:
        tail = cleaned.split("facebook.com/", 1)[1].strip("/")
        if not tail:
            raise ValueError(f"{page!r} is not a Facebook page")
        return f"https://www.facebook.com/{tail}"
    cleaned = cleaned.lstrip("@").strip("/")
    if not cleaned or not all(c.isalnum() or c in ".-_" for c in cleaned):
        raise ValueError(f"{page!r} is not a Facebook page name")
    return f"https://www.facebook.com/{cleaned}"


@dataclass
class Outcome:
    """What happened to one page."""

    page: str
    posts: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.error is None

    def line(self) -> str:
        """One line a reader can understand without having read the source."""
        if not self.ok:
            return f"failed  {self.page}: {self.error}"
        tail = f", {self.note}" if self.note else ""
        return f"got     {self.page}: {len(self.posts)} posts{tail}"


def scrape_page(page: str, limit: int = 5) -> Outcome:
    """Fetch one page's recent posts. Never raises for a bad page: a failure becomes an Outcome.

    A missing token is the exception, because it fails every page the same way.
    """
    try:
        url = page_url(page)
    except ValueError as exc:
        return Outcome(page=str(page), error=str(exc))
    outcome = Outcome(page=url.rsplit("facebook.com/", 1)[1])
    try:
        found, errors = split(page_posts(url, limit))
    except TokenMissing:
        raise
    except Exception as exc:  # one bad page must not end the run
        outcome.error = str(exc) if isinstance(exc, (ApiError, TimeoutError)) else (
            f"{type(exc).__name__}: {exc}"
        )
        return outcome
    if found:
        # Keep what was paid for. A partial run reports the rest as a note.
        outcome.posts = found
        if errors:
            outcome.note = f"{len(errors)} error rows: {errors[0]}"
    elif errors:
        outcome.error = "; ".join(dict.fromkeys(errors))
    return outcome


def scrape(pages: Iterable[str], limit: int = 5) -> list[Outcome]:
    """Run every page and return one Outcome each, in order."""
    return [scrape_page(page, limit) for page in pages]


def write(outcomes: list[Outcome], path: str | Path) -> Path:
    """Write one JSON file: when it ran, and the posts found per page."""
    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages": [{"page": o.page, "posts": o.posts} for o in outcomes],
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
