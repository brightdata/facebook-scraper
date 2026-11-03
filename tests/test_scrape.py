"""These run without a token. The API is a stub."""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
from pathlib import Path

import pytest

import facebook_scraper.__main__ as cli

# the package exports a function named scrape, which hides the module of that name
fb = sys.modules["facebook_scraper.scrape"]

ROOT = Path(__file__).resolve().parents[1]


class FakeApi:
    """Answers trigger, progress and snapshot the way the live API does."""

    def __init__(self, rows=None, states=("ready",)):
        self.rows = rows or []
        self.states = list(states)
        self.calls = []

    def __call__(self, path, body=None):
        self.calls.append((path, body))
        if path.startswith("/trigger"):
            return {"snapshot_id": "sd_test"}
        if path.startswith("/progress/"):
            return {"status": self.states.pop(0) if len(self.states) > 1 else self.states[0]}
        if path.startswith("/snapshot/"):
            return self.rows
        raise AssertionError(path)

    def trigger(self):
        path, body = self.calls[0]
        return dict(urllib.parse.parse_qsl(path.split("?", 1)[1])), body


@pytest.fixture
def api(monkeypatch):
    def install(**kwargs):
        fake = FakeApi(**kwargs)
        monkeypatch.setattr(fb, "_call", fake)
        monkeypatch.setattr(fb, "POLL_SECONDS", 0)
        return fake

    return install


@pytest.fixture
def no_login(monkeypatch, tmp_path):
    """No token in the environment and no CLI login: the stranger's machine."""
    monkeypatch.delenv("BRIGHTDATA_API_TOKEN", raising=False)
    monkeypatch.setattr(fb, "_cli_credentials", lambda: tmp_path / "missing.json")


def test_page_posts_send_the_limit_as_num_of_posts_and_only_options_given(api):
    fake = api()
    fb.page_posts("https://www.facebook.com/Meta", 3, start_date="10-01-2026", end_date=None)

    query, body = fake.trigger()
    assert query == {"dataset_id": fb.PAGE_POSTS, "include_errors": "true"}
    assert body == [{"url": "https://www.facebook.com/Meta", "num_of_posts": 3, "start_date": "10-01-2026"}]


def test_comments_are_capped_with_limit_records_not_num_of_comments(api):
    """The API rejects num_of_comments, the name the Python SDK sends, with a 400."""
    fake = api()
    fb.comments(["https://www.facebook.com/Meta/posts/1"], 3)

    query, body = fake.trigger()
    assert query["dataset_id"] == fb.COMMENTS
    assert body == [{"url": "https://www.facebook.com/Meta/posts/1", "limit_records": 3}]


def test_each_collect_by_url_scraper_uses_its_own_dataset(api):
    for call, dataset in (
        (fb.posts, fb.POSTS),
        (fb.pages, fb.PAGES),
        (fb.profiles, fb.PROFILES),
        (fb.events, fb.EVENTS),
        (fb.marketplace, fb.MARKETPLACE),
        (fb.ads, fb.AD_LIBRARY),
    ):
        fake = api()
        call(["https://www.facebook.com/x", "https://www.facebook.com/y"])
        query, body = fake.trigger()
        assert query == {"dataset_id": dataset, "include_errors": "true"}
        assert body == [{"url": "https://www.facebook.com/x"}, {"url": "https://www.facebook.com/y"}]


def test_limits_use_the_input_name_each_scraper_validates(api):
    for call, dataset, field in (
        (fb.group_posts, fb.GROUP_POSTS, "num_of_posts"),
        (fb.reels, fb.REELS, "num_of_posts"),
        (fb.reviews, fb.REVIEWS, "num_of_reviews"),
    ):
        fake = api()
        call("https://www.facebook.com/x", 4)
        query, body = fake.trigger()
        assert query["dataset_id"] == dataset and "discover_by" not in query
        assert body == [{"url": "https://www.facebook.com/x", field: 4}]


def test_each_discovery_is_capped_and_names_its_method(api):
    for call, args, dataset, discover_by, item in (
        (fb.events_search, ("https://www.facebook.com/events/search/?q=marathon", 3), fb.EVENTS, "url",
         {"url": "https://www.facebook.com/events/search/?q=marathon"}),
        (fb.events_by_venue, ("https://www.facebook.com/TheGarden/events", 3), fb.EVENTS, "venue",
         {"url": "https://www.facebook.com/TheGarden/events", "upcoming_events_only": True}),
        (fb.marketplace_search, ("bicycle", "New York", 3), fb.MARKETPLACE, "keyword",
         {"keyword": "bicycle", "city": "New York"}),
        (fb.marketplace_category, ("https://www.facebook.com/marketplace/category/vehicles", 3),
         fb.MARKETPLACE, "url", {"url": "https://www.facebook.com/marketplace/category/vehicles"}),
        (fb.ads_search, ("coffee", "us", 3), fb.AD_LIBRARY, "keyword",
         {"keyword": "coffee", "country": "US", "ad_type": "All ads"}),
    ):
        fake = api()
        call(*args)
        query, body = fake.trigger()
        assert query == {
            "dataset_id": dataset,
            "include_errors": "true",
            "type": "discover_new",
            "discover_by": discover_by,
            "limit_per_input": "3",
        }
        assert body == [item]


def test_a_page_can_be_a_name_a_handle_or_a_url():
    for given in ("Meta", "@Meta", "facebook.com/Meta", "https://www.facebook.com/Meta/"):
        assert fb.page_url(given) == "https://www.facebook.com/Meta"
    for bad in ("", "two words", "https://www.facebook.com/"):
        with pytest.raises(ValueError):
            fb.page_url(bad)


def test_run_polls_until_the_snapshot_is_ready(api):
    fake = api(rows=[{"page_name": "Meta"}], states=("running", "running", "ready"))
    assert fb.run(fb.PAGES, [{"url": "x"}]) == [{"page_name": "Meta"}]
    assert [p for p, _ in fake.calls].count("/progress/sd_test") == 3


def test_a_dropped_poll_does_not_lose_the_job(api, monkeypatch):
    fake = api(rows=[{"page_name": "Meta"}])
    real = fake.__call__
    dropped = []

    def flaky(path, body=None):
        if path.startswith("/progress/") and not dropped:
            dropped.append(path)
            raise urllib.error.URLError("connection reset")
        return real(path, body)

    monkeypatch.setattr(fb, "_call", flaky)
    assert fb.run(fb.PAGES, [{"url": "x"}]) == [{"page_name": "Meta"}]
    assert dropped


def test_a_failed_snapshot_is_an_error(api):
    api(states=("failed",))
    with pytest.raises(fb.ApiError, match="sd_test failed"):
        fb.run(fb.PAGES, [{"url": "x"}])


def test_a_job_that_never_finishes_times_out(api):
    api(states=("running",))
    with pytest.raises(TimeoutError, match="timeout"):
        fb.run(fb.PAGES, [{"url": "x"}], timeout=0)


def test_an_http_error_names_the_status_and_the_reason(monkeypatch):
    monkeypatch.setenv("BRIGHTDATA_API_TOKEN", "test")

    def refuse(request, timeout):
        body = io.BytesIO(b'{"error":"validation_error"}')
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, body)

    monkeypatch.setattr(fb.urllib.request, "urlopen", refuse)
    with pytest.raises(fb.ApiError, match="HTTP 400.*validation_error"):
        fb.trigger(fb.PAGES, [{"url": "x"}])


def test_the_token_comes_from_the_environment_then_the_cli_login(monkeypatch, tmp_path, no_login):
    with pytest.raises(fb.TokenMissing, match="export BRIGHTDATA_API_TOKEN"):
        fb.token()

    credentials = tmp_path / "credentials.json"
    credentials.write_text(json.dumps({"api_key": "from-login"}), encoding="utf-8")
    monkeypatch.setattr(fb, "_cli_credentials", lambda: credentials)
    assert fb.token() == "from-login"

    monkeypatch.setenv("BRIGHTDATA_API_TOKEN", "from-env")
    assert fb.token() == "from-env"


def test_error_rows_alone_fail_the_page(api):
    api(rows=[{"error": "The navigation resulted in a dead page (404 status code)", "error_code": "dead_page"}])
    outcome = fb.scrape_page("zzqqxx-no-such-page")

    assert not outcome.ok
    assert outcome.line() == (
        "failed  zzqqxx-no-such-page: The navigation resulted in a dead page (404 status code)"
    )


def test_posts_already_paid_for_are_kept_when_some_rows_fail(api):
    api(rows=[{"url": "p1"}, {"error": "Crawler error", "error_code": "crawl_failed"}])
    outcome = fb.scrape_page("Meta")

    assert outcome.ok
    assert outcome.posts == [{"url": "p1"}]
    assert outcome.line() == "got     Meta: 1 posts, 1 error rows: Crawler error"


def test_rows_cancelled_by_the_limit_are_not_errors():
    records, errors = fb.split([{"url": "ad1"}, {"error": fb.CANCELLED}, {"error": fb.CANCELLED}])
    assert records == [{"url": "ad1"}] and errors == []


def test_a_bad_page_name_fails_without_a_request(api):
    fake = api()
    outcome = fb.scrape_page("two words")
    assert not outcome.ok and fake.calls == []


def test_one_bad_page_does_not_end_the_run(monkeypatch):
    def page_posts(url, limit):
        if url.endswith("/boom"):
            raise RuntimeError("boom")
        return [{"url": url}]

    monkeypatch.setattr(fb, "page_posts", page_posts)
    first, second = fb.scrape(["boom", "Meta"])

    assert first.error == "RuntimeError: boom"
    assert second.ok and second.posts == [{"url": "https://www.facebook.com/Meta"}]


def test_a_run_writes_what_it_found(api, tmp_path):
    api(rows=[{"url": "p1", "likes": 722}])
    path = fb.write(fb.scrape(["Meta"], 1), tmp_path / "out.json")

    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["pages"] == [{"page": "Meta", "posts": [{"url": "p1", "likes": 722}]}]
    assert document["generated_at"]


def fake_cli(monkeypatch, outcome_for):
    monkeypatch.setattr(cli, "token", lambda: "test")
    monkeypatch.setattr(cli, "scrape_page", lambda page, limit: outcome_for(page))


def test_the_cli_exit_code_says_whether_every_page_worked(monkeypatch, tmp_path):
    fake_cli(monkeypatch, lambda p: fb.Outcome(p, posts=[{"url": "x"}]))
    assert cli.main(["Meta", "--out", str(tmp_path / "ok.json")]) == 0

    fake_cli(monkeypatch, lambda p: fb.Outcome(p, error="boom"))
    assert cli.main(["Meta", "--out", str(tmp_path / "bad.json")]) == 1


def test_each_result_prints_before_the_next_page_starts(monkeypatch, tmp_path, capsys):
    fake_cli(monkeypatch, lambda p: fb.Outcome(p, posts=[{"url": "x"}]))
    cli.main(["Meta", "Microsoft", "--out", str(tmp_path / "o.json")])

    out = capsys.readouterr().out.splitlines()
    assert [ln for ln in out if ln.startswith(("asking", "got"))] == [
        "asking  Meta...",
        "got     Meta: 1 posts",
        "asking  Microsoft...",
        "got     Microsoft: 1 posts",
    ]


def test_a_bad_limit_is_refused_before_any_request(capsys):
    for bad in (["x", "--limit", "0"], ["x", "--limit", "-3"]):
        with pytest.raises(SystemExit):
            cli.main(bad)
    assert "1 or more" in capsys.readouterr().err


def test_a_missing_token_is_a_message_not_a_traceback(no_login, capsys):
    assert cli.main(["Meta"]) == 2
    err = capsys.readouterr().err
    assert "export BRIGHTDATA_API_TOKEN" in err and "bdata login" in err
    assert "Traceback" not in err


def test_piped_output_keeps_the_header_before_the_error(tmp_path):
    """A log or an agent reads a pipe. The header must not land after the error."""
    env = {k: v for k, v in os.environ.items() if k != "BRIGHTDATA_API_TOKEN"}
    env["HOME"] = str(tmp_path)  # no CLI login: the stranger's machine
    env["APPDATA"] = str(tmp_path)
    run = subprocess.run(
        [sys.executable, "-m", "facebook_scraper", "Meta"],
        cwd=tmp_path,
        env={**env, "PYTHONPATH": str(ROOT / "src")},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )
    assert run.returncode == 2, run.stdout
    assert run.stdout.index("Fetching up to") < run.stdout.index("API token required")


def test_the_readme_excerpt_is_the_start_of_the_example_file():
    """The README shows the first 20 lines of the real file, verbatim, and links it."""
    sample = (ROOT / "examples" / "sample_output.json").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "\n".join(sample.splitlines()[:20]) in readme, "README excerpt drifted from the file"
    assert "](examples/sample_output.json)" in readme


def test_every_in_page_link_has_its_heading():
    """A renamed heading would break the header row silently; the link check sees only URLs."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    headings = re.findall(r"^#{1,6} (.+)$", readme, re.M)
    anchors = {re.sub(r"[^a-z0-9 -]", "", h.lower()).replace(" ", "-") for h in headings}
    for anchor in re.findall(r"\]\(#([^)]+)\)", readme):
        assert anchor in anchors, f"#{anchor} points at no heading"
