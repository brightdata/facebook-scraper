# Facebook scraper for Python

[![Live check](https://github.com/brightdata/facebook-scraper/actions/workflows/live.yml/badge.svg)](https://github.com/brightdata/facebook-scraper/actions/workflows/live.yml)
[![last verified](https://img.shields.io/badge/last%20verified-9%20Nov%202026-brightgreen)](https://github.com/brightdata/facebook-scraper/actions/workflows/live.yml) <!-- verified: rewritten by the daily run -->

[Quickstart](#how-to-scrape-facebook-posts-with-python) · [No login](#scrape-facebook-without-a-login-or-the-graph-api) · [CLI](#bulk-facebook-page-posts-cli) · [Endpoints](#scrape-facebook-posts-comments-marketplace-events-and-ads) · [Data](#facebook-post-data-fields-json) · [Errors](#facebook-scraper-errors) · [MCP and Claude Code](#facebook-mcp-server-and-claude-code-skill) · [Free credits](#is-this-facebook-scraper-free) · [Docs](https://docs.brightdata.com/products/scrapers/facebook/introduction) · [Support](#support)

Facebook data as JSON, in Python: page and group posts, comments, reels, page
details, profiles, reviews, Marketplace listings, events and the Meta Ad
Library. All eleven Bright Data Facebook scrapers, one function each. No
Facebook login, no browser, no dependencies. Built on the
[Bright Data Facebook Scraper API](https://brightdata.com/products/web-scraper/facebook?utm_source=github).

Also here: a one-command CLI for page posts, and the
[Bright Data CLI](#facebook-mcp-server-and-claude-code-skill), which needs no Python at all.

## How to scrape Facebook posts with Python

Python 3.10 or newer, and nothing to install: this is the standard library.

```bash
export BRIGHTDATA_API_TOKEN=YOUR_API_KEY
```

Get a token from the
[Bright Data control panel](https://brightdata.com/cp/setting/users). No
account yet? [Create one](https://brightdata.com/cp/start); new accounts get
[5,000 free credits a month](https://docs.brightdata.com/general/account/billing-and-pricing/free-tier).

```python
import json
import os
import time
import urllib.request

API = "https://api.brightdata.com/datasets/v3"
HEADERS = {
    "Authorization": f"Bearer {os.environ['BRIGHTDATA_API_TOKEN']}",
    "Content-Type": "application/json",
}


def call(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(API + path, data=data, headers=HEADERS)
    with urllib.request.urlopen(request) as response:
        return json.load(response)


page = {"url": "https://www.facebook.com/Meta", "num_of_posts": 3}
job = call("/trigger?dataset_id=gd_lkaxegm826bjpoo9m5&include_errors=true", [page])
while call(f"/progress/{job['snapshot_id']}")["status"] not in ("ready", "failed"):
    time.sleep(10)
for post in call(f"/snapshot/{job['snapshot_id']}?format=json"):
    if "error" in post:
        raise SystemExit(post["error"])
    print(post["likes"], post["num_comments"], post["url"])
```

```
723 342 https://www.facebook.com/Meta/posts/pfbid0evGHWPACd3JninWg3j3nucQjdFxoHWwJSPgFXKjZXaUiU8MctREDPRZZsAps6CGwl
4169 717 https://www.facebook.com/reel/2300984144015832/
7679 819 https://www.facebook.com/reel/29074877795478111/
```

Expect one to three minutes: the API runs a job and the loop waits for it.
Billed [per post](https://brightdata.com/pricing/web-scraper).

Two things in that snippet are not optional.

`num_of_posts` caps the run, and the bill. Without it a page returns, and
charges for, every post the scraper can reach.

`include_errors=true` makes the API report a dead or private page as a row
with an `error` key. The API default is off, and a failed page then looks the
same as a page with no posts.

The Bright Data [Python SDK](https://github.com/brightdata/sdk-python) wraps
five of the eleven Facebook scrapers, and the API rejects the
`num_of_comments` input its comments call sends. Hence the plain HTTP, here
and in this package.

## Scrape Facebook without a login or the Graph API

The Facebook Scraper API needs no Facebook account, no Facebook login, no Meta
app and no Graph API access token. The only credential is a Bright Data API
key, set as `BRIGHTDATA_API_TOKEN`. This package and its command also find the
key stored by `bdata login`. It collects what a logged-out visitor can see: a
private group or profile comes back as an error row.

## Bulk Facebook page posts CLI

The command in this repo runs the Python quickstart for several pages at once
and writes one JSON file.

```bash
pip install git+https://github.com/brightdata/facebook-scraper
facebook-scraper Meta Microsoft --limit 2
```

```
Fetching up to 2 recent posts per page, for: Meta, Microsoft
Usually one to three minutes each. Billed per post, 5,000 free credits a month.
asking  Meta...
got     Meta: 2 posts
asking  Microsoft...
got     Microsoft: 2 posts

Saved 4 posts as JSON to facebook.json (44 fields per post)
```

In a terminal the `asking` lines are replaced by a spinner and a running
clock, updating in place, so you can see it is working and how long it has
been going.

```
--limit N      posts per page, default 5, minimum 1
--out PATH     output file, default facebook.json
```

A page can be a name, `@Meta`, `facebook.com/Meta` or a full URL.
`python -m facebook_scraper` works too. The command finds the token in
`BRIGHTDATA_API_TOKEN`, or, if you ran `npx -p @brightdata/cli bdata login`
once, in the stored login, for you and for any coding agent in that terminal.

Import it instead of running it, for `ok`, `note` and `error` per page instead
of raw rows. `scrape` never raises for one bad page; check `ok` before reading
`posts`:

```python
from facebook_scraper import scrape

for outcome in scrape(["Meta", "zzqqxx-no-such-page-404"], limit=1):
    if outcome.ok:
        print(f"{outcome.page}: {len(outcome.posts)} posts")
    else:
        print(f"{outcome.page} failed: {outcome.error}")
```

```
Meta: 1 posts
zzqqxx-no-such-page-404 failed: Posts not found
```

A page that does not exist comes back as an error row, "Posts not found",
and it takes the longest: 459 seconds for that run. When a run returns some
posts and some error rows, the posts are kept, and the errors land in `note`.

## Scrape Facebook posts, comments, Marketplace, events and ads

Bright Data has eleven Facebook scrapers, each documented in the
[Facebook Scraper API docs](https://docs.brightdata.com/products/scrapers/facebook/introduction).
This package has one function for each way to call them. Every snippet below
is complete: paste it as is after the `pip install` above. Every one of them
runs in Actions each Monday, a smaller check runs every other day, and the
badge at the top is the latest result.

| you have | want | how |
| --- | --- | --- |
| page URLs | their recent posts | `page_posts(urls, 5)` |
| public group URLs | their recent posts | `group_posts(urls, 5)` |
| post URLs | those posts | `posts(urls)` |
| post URLs | their comments | `comments(urls, 10)`, billed per comment |
| page URLs | their recent reels | `reels(urls, 5)` |
| page URLs | page details: followers, category, contact info | `pages(urls)` |
| profile URLs of people | public profile details | `profiles(urls)` |
| a page's `/reviews/` URL | its reviews | `reviews(urls, 10)` |
| a keyword and a city | Marketplace listings | `marketplace_search("bicycle", "New York", 5)` |
| a Marketplace category URL | its listings | `marketplace_category(url, 5)` |
| Marketplace item URLs | those listings | `marketplace(urls)` |
| a venue page's `/events` URL | its upcoming events | `events_by_venue(url, 5)` |
| an events search URL | matching events | `events_search(url, 5)` |
| event URLs | those events | `events(urls)` |
| a keyword and a country | ads in the Meta Ad Library | `ads_search("coffee", "US", 5)` |
| Ad Library ad URLs | those ads | `ads(urls)` |

Each takes one URL or a list. A list is one job, not one per URL. Each returns
a list of rows, and a row the API could not collect carries an `error` key
instead of the record. Functions that take a limit pass any other input the
API accepts as a keyword argument, named as the API names it:
`page_posts(url, 10, start_date="10-01-2026")`.

### Scrape Facebook page posts from several pages in one job

```python
from facebook_scraper import page_posts

urls = ["https://www.facebook.com/Meta", "https://www.facebook.com/Microsoft"]
for post in page_posts(urls, 1):
    print(post["page_name"], post["date_posted"], post["likes"], post["url"])
```

```
Microsoft 2025-04-04T22:18:26.000Z 40838 https://www.facebook.com/Microsoft/posts/pfbid0347J66TDSqDpBtUS5Vmhu17t7bpCWTRzgi9yWw1387gGCJuwhAdKfsLzByvA93uRcl
Meta 2026-10-30T19:41:31.000Z 723 https://www.facebook.com/Meta/posts/pfbid0evGHWPACd3JninWg3j3nucQjdFxoHWwJSPgFXKjZXaUiU8MctREDPRZZsAps6CGwl
```

### Scrape Facebook group posts

Public groups only. The records name the people who posted; this prints the
group and the counts.

```python
from facebook_scraper import group_posts

for post in group_posts("https://www.facebook.com/groups/532855527252024", 2):
    print(post["group_name"][:40], post["group_members"], post["date_posted"], post["num_comments"])
```

```
Jobs, Work and Vacancies in Cape Town an 238700 2026-11-03T18:53:25.000Z 0
Jobs, Work and Vacancies in Cape Town an 238700 2026-11-03T18:48:29.000Z 0
```

### Scrape a Facebook post by URL

```python
from facebook_scraper import posts

url = "https://www.facebook.com/Meta/posts/pfbid0evGHWPACd3JninWg3j3nucQjdFxoHWwJSPgFXKjZXaUiU8MctREDPRZZsAps6CGwl"
post = posts(url)[0]
print(post["user_username_raw"], post["likes"], post["num_comments"], post["num_shares"])
print(post["content"][:70])
```

```
Meta 593 342 194
Meta Ray-Ban Display has been out for a while, so if you’re a develope
```

### Scrape Facebook comments from a post

Billed per comment, so check `num_comments` on the post first. The limit
goes to the API as `limit_records`.

```python
from facebook_scraper import comments

url = "https://www.facebook.com/Meta/posts/pfbid0evGHWPACd3JninWg3j3nucQjdFxoHWwJSPgFXKjZXaUiU8MctREDPRZZsAps6CGwl"
rows = comments(url, 3)
print(len(rows), "comments; first:", rows[0]["date_created"], rows[0]["num_likes"], "likes")
```

```
3 comments; first: 2026-10-31T01:48:29.000Z 10 likes
```

### Scrape Facebook reels from a page

```python
from facebook_scraper import reels

for reel in reels("https://www.facebook.com/Meta", 2):
    print(reel["date_posted"], reel["video_view_count"], "views", reel["url"])
```

```
2026-10-27T16:44:32.000Z 447000 views https://www.facebook.com/reel/2300984144015832
2026-10-22T16:25:44.000Z 1200000 views https://www.facebook.com/reel/29074877795478111
```

### Scrape Facebook page data

```python
from facebook_scraper import pages

page = pages("https://www.facebook.com/Meta")[0]
print(page["page_name"], page["followers"], "followers,", page["primary_category"])
```

```
Meta 106000000 followers, Company
```

### Scrape a Facebook profile

Public profile details only, what a logged-out visitor sees.

```python
from facebook_scraper import profiles

profile = profiles("https://www.facebook.com/zuck")[0]
print(profile["name"], "|", profile["city"])
```

```
Mark Zuckerberg | Palo Alto
```

### Scrape Facebook reviews of a business page

Pass the page's `/reviews/` URL. Many brand pages have reviews turned off and
return an error row, "Reviews not found" or a dead page, instead of zero rows.
This prints the verdicts, not the reviewers.

```python
from facebook_scraper import reviews

for review in reviews("https://www.facebook.com/TheGarden/reviews/", 3):
    print(review["company_name"], review["review_time"], "recommends:", review["recommends"])
```

```
Madison Square Garden 2026-10-31T14:43:54.000Z recommends: True
Madison Square Garden 2026-10-21T12:28:03.000Z recommends: True
Madison Square Garden 2026-10-19T22:29:17.000Z recommends: False
```

### Scrape Facebook Marketplace listings

```python
from facebook_scraper import marketplace_search

for item in marketplace_search("bicycle", "New York", 3):
    if "error" not in item:  # rows the limit cancelled carry only an error
        print(item["final_price"], item["currency"], item["title"][:40], "|", item["location"])
```

```
100 USD Bikes for sale like new | Perth Amboy, NJ
100 USD bicycle | Linden, NJ
350 USD 700c Whls 24 Spd Medium Frame Cannondale | Brooklyn, NY
```

`marketplace_category(url, 5)` does the same from a category URL, such as
`https://www.facebook.com/marketplace/category/vehicles`, and
`marketplace(urls)` collects listings you already have the URLs of.

### Scrape Facebook events at a venue

Pass the venue page's `/events` URL. The bare page URL finds no events.

```python
from facebook_scraper import events_by_venue

for event in events_by_venue("https://www.facebook.com/TheGarden/events", 3):
    print(event["event_date"], event["title"])
```

```
2026-11-04T00:00:00.000Z New York Rangers vs. St. Louis Blues
2026-11-05T00:30:00.000Z New York Knicks vs. Chicago Bulls
2026-11-04T00:00:00.000Z NY Rangers vs St. Louis Blues Premium Seating
```

`events_search(url, 5)` takes an events search URL, such as
`https://www.facebook.com/events/search/?q=marathon`. Its matching is loose:
check the titles it returns.

### Scrape the Facebook Ad Library

```python
from facebook_scraper import ads_search

for ad in ads_search("coffee", "US", 3):
    if "error" not in ad:  # rows the limit cancelled carry only an error
        print(ad["advertiser_name"], "| active:", ad["is_active"], "| since", ad["start_date"])
```

```
Wall Stadium | active: True | since 2026-04-22T07:00:00.000Z
Biggby Coffee of Wickliffe Ohio | active: True | since 2025-04-29T07:00:00.000Z
Dame Fine Coffee | active: True | since 2026-06-11T07:00:00.000Z
```

`ad_type` defaults to `"All ads"`, the value the API validates; `"all"` is
rejected. A discovery that reaches its limit cancels the crawls still running,
and each comes back as a row whose error is "Crawl aborted on job cancel".
`split()` treats those as the limit working, not as failures.

### Trigger now, fetch later

For anything bigger than a few pages, do not block a process for an hour.
Trigger, keep the snapshot id, fetch when ready. Snapshots stay downloadable
for 30 days.

```python
import time

from facebook_scraper import PAGES, fetch, status, trigger

snapshot = trigger(PAGES, [{"url": "https://www.facebook.com/Microsoft"}])
print("snapshot:", snapshot)
while (state := status(snapshot)) not in ("ready", "failed"):
    time.sleep(10)
print("status:", state)
print("fetched:", fetch(snapshot)[0]["page_name"])
```

```
snapshot: sd_mw12itsz2eyr9m4tcu
status: ready
fetched: Microsoft
```

`trigger` takes any dataset, `discover_by` and `limit_per_input`, so it reaches
every scraper in the table. Each input was accepted by the live API on
2026-11-03, and several differ from the API reference pages:

| scraper | dataset_id | discover_by | input |
| --- | --- | --- | --- |
| Page posts | `gd_lkaxegm826bjpoo9m5` | none | `{"url", "num_of_posts"}` |
| Group posts | `gd_lz11l67o2cb3r0lkj3` | none | `{"url", "num_of_posts"}` |
| Post by URL | `gd_lyclm1571iy3mv57zw` | none | `{"url"}` |
| Comments | `gd_lkay758p1eanlolqw8` | none | `{"url", "limit_records"}`. `num_of_comments` is rejected |
| Reels | `gd_lyclm3ey2q6rww027t` | none | `{"url", "num_of_posts"}` |
| Pages | `gd_mf124a0511bauquyow` | none | `{"url"}` |
| Profiles | `gd_mf0urb782734ik94dz` | none | `{"url"}` |
| Company reviews | `gd_m0dtqpiu1mbcyc2g86` | none | `{"url", "num_of_reviews"}`, a `/reviews/` URL |
| Marketplace item | `gd_lvt9iwuh6fbcwmx1a` | none | `{"url"}` |
| Marketplace search | `gd_lvt9iwuh6fbcwmx1a` | `keyword` | `{"keyword", "city"}` required |
| Marketplace category | `gd_lvt9iwuh6fbcwmx1a` | `url` | `{"url"}` |
| Event | `gd_m14sd0to1jz48ppm51` | none | `{"url"}` |
| Events search | `gd_m14sd0to1jz48ppm51` | `url` | `{"url"}`, an `/events/search/?q=` URL |
| Events at a venue | `gd_m14sd0to1jz48ppm51` | `venue` | `{"url", "upcoming_events_only"}`, a `/events` URL |
| Ad | `gd_mtveskb62h7q65ftgz` | none | `{"url"}` |
| Ads search | `gd_mtveskb62h7q65ftgz` | `keyword` | `{"keyword", "country", "ad_type"}`, `ad_type` `"All ads"` |

`bdata pipelines info <dataset_id> <method>` prints the input fields the API
validates.

## Facebook post data fields (JSON)

The fields most people want from a page post:

```
url  date_posted  content  likes  num_comments  num_shares  page_name  page_followers
```

The code hardcodes no field list. Whatever the API returns lands in each row,
and in the command's file.

<!-- fields:start -->
Regenerated every day from the published schema,
[scrapers-full.json](https://docs.brightdata.com/scrapers-full.json), so they cannot go stale. A record
carries the fields that apply to it, plus `timestamp` and `input`; the
sample file's first post has 44 keys.

<details>
<summary>All 52 page post fields, <code>gd_lkaxegm826bjpoo9m5</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | Facebook post URL |
| `post_id` | text | Unique identifier for each Facebook post |
| `user_url` | url | Unique identifier for each Facebook post |
| `user_username_raw` | text | Username of the user who posted the content |
| `content` | text | Text or media content of the post |
| `date_posted` | date | Date and time when the post was published |
| `hashtags` | array | Hashtags used in the post |
| `num_comments` | number | Number of comments on the post |
| `num_shares` | number | Number of shares of the post |
| `num_likes_type` | object | Type of likes received: The data point "count_reactions_type" contains all reactions received. |
| `page_name` | text | Name of the Facebook page where the post was published |
| `profile_id` | text | Unique identifier for the user's profile |
| `page_intro` | text | Introduction or description of the Facebook page |
| `page_category` | text | Category of the Facebook page |
| `page_logo` | image | Logo of the Facebook page |
| `page_external_website` | text | External website associated with the Facebook page |
| `page_likes` | number | Number of likes on the Facebook page |
| `page_followers` | number | Number of followers of the Facebook page |
| `page_is_verified` | boolean | Verification status of the Facebook page |
| `original_post` | object | Indicates if the post is original or a repost |
| `attachments` | array | Media attachments included in the post |
| `other_posts_url` | array | Web address of other posts by the same user |
| `post_external_link` | url | External link included in the post |
| `post_external_title` | text | Title of the external link |
| `post_external_image` | url | Post external link image |
| `page_url` | url | Web address of the Facebook page |
| `header_image` | image | Header image of the Facebook page |
| `avatar_image_url` | text | The URL of the avatar image of the Facebook page |
| `profile_handle` | text | The handle or username of the Facebook page |
| `has_handshake` | text | Indicates if the post has a handshake |
| `is_sponsored` | boolean | Indicates whether the post is sponsored or not |
| `sponsor_name` | text | The name of the sponsor if the post is sponsored |
| `shortcode` | text | The shortcode of the post URL |
| `video_view_count` | number | The number of views if the post contains a video |
| `likes` | number | The number of likes on the post |
| `post_image` | image | post image url if exists |
| `post_type` | text | The type of the post |
| `following` | number | Number of profiles following |
| `link_description_text` | text | The text that is visible under the link title |
| `count_reactions_type` | array | Type of reactions received |
| `is_page` | boolean | Is the post from a page or a profile |
| `page_phone` | text | Public phone number listed on the page |
| `page_email` | text | Public email address listed on the page |
| `page_creation_time` | date | Date the page was created |
| `page_reviews_score` | text | Average page review score |
| `page_reviewers_amount` | number | Total number of page reviewers |
| `page_price_range` | text | Price range label shown on the page |
| `about` | array | Key-value pairs extracted from the page’s About section |
| `active_ads_urls` | array | Links to the page’s active ads in Facebook Ad Library |
| `delegate_page_id` | text | ID of the page shown as responsible for this page |
| `privacy_and_legal_info` | text | The privacy and legal info of the profile |
| `play_count` | number | Represents the number of times the video started playing (or was clicked to play) |

</details>

<details>
<summary>All 44 group post fields, <code>gd_lz11l67o2cb3r0lkj3</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url |  |
| `post_id` | text | Unique identifier for each Facebook post |
| `user_url` | url | Unique identifier for each Facebook post |
| `user_username_raw` | text | Username of the user who posted the content |
| `content` | text | Text or media content of the post |
| `date_posted` | date | Date and time when the post was published |
| `hashtags` | array | Hashtags used in the post |
| `num_comments` | number | Number of comments on the post |
| `num_shares` | number | Number of shares of the post |
| `num_likes_type` | object | Type of likes received (e.g., reactions, thumbs-up) |
| `group_name` | text | Name of the Facebook group where the post was published |
| `group_id` | text | Unique identifier for the user's profile |
| `group_url` | url | Web address of the Facebook group |
| `group_intro` | text | Introduction or description of the Facebook group |
| `group_category` | text | Category of the Facebook group |
| `group_logo` | image | Logo of the Facebook group |
| `group_external_website` | text | External website associated with the Facebook group |
| `group_members` | number | Number of members of the Facebook group |
| `group_created_at` | date | The date When the group was created |
| `user_is_verified` | boolean | Verification status of the Facebook user who posted |
| `original_post` | object | Indicates if the post is original or a repost |
| `attachments` | array |  |
| `other_posts_url` | array | Web address of other posts by the same user |
| `post_external_link` | url | External link included in the post |
| `post_external_title` | text | Title of the external link |
| `post_external_image` | url | Post external link image |
| `header_image` | image | Header image of the Facebook page |
| `avatar_image_url` | text | The URL of the avatar image of the Facebook page |
| `profile_handle` | text | The handle or username of the Facebook page |
| `has_handshake` | text | Indicates if the post has a handshake |
| `is_sponsored` | boolean | Indicates whether the post is sponsored or not |
| `sponsor_name` | text | The name of the sponsor if the post is sponsored |
| `shortcode` | text | The shortcode of the post URL |
| `video_view_count` | number | The number of views if the post contains a video |
| `likes` | number | The number of likes on the post |
| `post_image` | image | post image url if exists |
| `post_type` | text | The type of the post |
| `following` | number | Number of profiles following |
| `price` | number | Price associated with the post |
| `location` | text | Location associated with the post |
| `profile_id` | text |  |
| `publisher_image_url` | url |  |
| `num_reaction_type` | array | Type of likes received (e.g., reactions, thumbs-up) |
| `delegate_page_id` | text | delegate_page_id |

</details>

<details>
<summary>All 38 post by URL fields, <code>gd_lyclm1571iy3mv57zw</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | URL |
| `post_id` | text | Unique identifier for each Facebook post |
| `user_url` | url | Unique identifier for each Facebook post |
| `user_username_raw` | text | Username of the user who posted the content |
| `content` | text | Text or media content of the post |
| `date_posted` | date | Date and time when the post was published |
| `hashtags` | array | Hashtags used in the post |
| `num_comments` | number | Number of comments on the post |
| `num_shares` | number | Number of shares of the post |
| `num_likes_type` | array | Type of likes received (e.g., reactions, thumbs-up) |
| `profile_id` | text | Unique identifier for the user's profile |
| `page_logo` | url | Logo of the Facebook page |
| `page_likes` | number | Number of likes on the Facebook page |
| `page_followers` | number | Number of followers of the Facebook page |
| `page_is_verified` | boolean | Verification status of the Facebook page |
| `original_post` | object | Indicates if the post is original or a repost |
| `attachments` | array | Attachments |
| `post_external_link` | url | External link included in the post |
| `post_external_title` | text | Title of the external link |
| `page_url` | url | Web address of the Facebook page |
| `header_image` | url | Header image of the Facebook page |
| `avatar_image_url` | text | The URL of the avatar image of the Facebook page |
| `profile_handle` | text | The handle or username of the Facebook page |
| `has_handshake` | text | Indicates if the post has a handshake |
| `is_sponsored` | boolean | Indicates whether the post is sponsored or not |
| `sponsor_name` | text | The name of the sponsor if the post is sponsored |
| `shortcode` | text | The shortcode of the post URL |
| `video_view_count` | number | The number of views if the post contains a video |
| `likes` | number | The number of likes on the post |
| `post_image` | url | post image url if exists |
| `post_type` | text | The type of the post |
| `user_handle` | text | User handle |
| `play_count` | number | Play count |
| `video_title` | text | Video title |
| `marketplace_price` | price | Price of the item from market place. This value is relevant for marketplace items that were shared in groups. |
| `delegate_page_id` | text | ID of the page delegated as “responsible for this Page” |
| `marketplace_is_sold` | text | Indicates whether the product has been sold, applicable only to marketplace posts |
| `comments` | array | Comments of the post |

</details>

<details>
<summary>All 22 comment fields, <code>gd_lkay758p1eanlolqw8</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | The URL of the page or post containing the comments |
| `post_id` | text | Unique identifier for each post |
| `post_url` | url | URL of the specific post |
| `comment_id` | text | Unique identifier for each comment |
| `user_name` | text | Name of the user who made the comment |
| `user_id` | text | Unique identifier for each user |
| `user_url` | url | URL of the user's profile |
| `date_created` | date | Date and time when the comment was created |
| `comment_text` | text | The actual text content of the comment |
| `num_likes` | number | Number of likes or reactions received by the comment |
| `num_replies` | number | Number of direct replies to the comment |
| `attached_files` | array | Any files or attachments associated with the comment |
| `video_length` | number | Length of video content, if applicable |
| `source_type` | text | Type of source (e.g., Facebook, external link) |
| `subtype` | text | Subcategory or specific type of the post or comment |
| `type` | text | General category of the post or comment |
| `commentator_profile` | url | Commentator profile |
| `comment_link` | url | Comment URL |
| `reply` | boolean | Reply |
| `parent_comment_id` | text | Parent comment id |
| `commentator_profile_url` | url | The URL of the profile picture of the commentator |
| `attached_images` | array | Any images associated with the comment |

</details>

<details>
<summary>All 27 reel fields, <code>gd_lyclm3ey2q6rww027t</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | URL of the reel |
| `post_id` | text | Unique identifier for each Facebook reel |
| `user_url` | url | Unique identifier for each Facebook reel |
| `user_username_raw` | text | Username of the user who posted the content |
| `content` | text | Text or media content of the reel |
| `date_posted` | date | Date and time when the reel was published |
| `hashtags` | array | Hashtags used in the reel |
| `num_comments` | number | Number of comments on the post |
| `num_shares` | number | Number of shares of the post |
| `video_view_count` | number | The number of views |
| `likes` | number | The number of likes on the reel |
| `page_name` | text | Name of the Facebook page where the reel was published |
| `profile_id` | text | Unique identifier for the user's profile |
| `page_logo` | url | URL of the Logo of the Facebook page |
| `page_likes` | number | Number of likes on the Facebook page |
| `page_followers` | number | Number of followers of the Facebook page |
| `page_is_verified` | boolean | Verification status of the Facebook page |
| `thumbnail` | url | URL of the reel thumbnail |
| `external_link` | url | External link included in the reel |
| `page_url` | url | Web address of the Facebook page |
| `header_image` | url | URL of the header image of the Facebook page |
| `avatar_image_url` | url | The URL of the avatar image of the Facebook page |
| `profile_handle` | text | The handle or username of the Facebook page |
| `shortcode` | text | The shortcode of the post URL |
| `length` | number | Length of the reel |
| `audio` | text | Audio of the reel |
| `video_url` | url | The Reel video URL |

</details>

<details>
<summary>All 28 page fields, <code>gd_mf124a0511bauquyow</code></summary>

| field | type | description |
| --- | --- | --- |
| `id` | text | Internal record ID |
| `url` | url | Facebook page URL |
| `page_name` | text | Page display name |
| `username` | text | Page handle (username) |
| `entity_type` | text | Page or Profile |
| `summary_text` | text | Intro tagline text |
| `primary_category` | text | Primary category |
| `work` | array | Employment lines |
| `education` | array | Education lines |
| `current_city` | text | Current city |
| `hometown` | text | Hometown |
| `relationship` | object | Relationship info |
| `address` | object | Business/location address |
| `phones` | array | Phone numbers |
| `emails` | array | Email addresses |
| `websites` | array | Websites and social links |
| `hours` | object | Opening hours |
| `rating` | object | Rating summary |
| `contact_and_basic_info` | object | About > Contact and basic info |
| `page_transparency` | object | About > Page transparency |
| `details_about` | object | About > Details About |
| `privacy_and_legal_info` | text | Privacy/terms/legal notes |
| `followers` | number | Number of followers |
| `logo` | url | The page logo |
| `is_verified` | boolean | Is the page verified |
| `group_members` | number | Number of members of the Facebook group (Applicable if the page is a group page) |
| `group_created_at` | date | The date When the group was created (Applicable if the page is a group page) |
| `num_posts_last_month` | number | Number of posts in the last month (Applicable if the page is a group page) |

</details>

<details>
<summary>All 11 profile fields, <code>gd_mf0urb782734ik94dz</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | URL |
| `name` | text | The name of the person |
| `id` | text | The Facebook profile ID |
| `profile_photo` | image | The profile photo |
| `cover_photo` | image | The profile's cover photo |
| `work` | array | The working places of the profile |
| `college` | array | College data of the profile |
| `high_school` | array | High school data of the profile |
| `photos` | array | The profile's photos |
| `location` | text | The location where the profile is from |
| `city` | text | The city where the profile is from |

</details>

<details>
<summary>All 18 review fields, <code>gd_m0dtqpiu1mbcyc2g86</code></summary>

| field | type | description |
| --- | --- | --- |
| `company_name` | text | The name of the company being reviewed. This field identifies which business the review is about, useful for categorizing and analyzing feedback by company. |
| `company_id` | text | A unique identifier for each company being reviewed. This field helps distinguish between different companies and allows for easy referencing and aggregation of reviews related to the same company |
| `company_url` | url | The URL of the reviewed company |
| `url` | url | The URL of the specific review on the Facebook platform. This link allows users to view the original review directly |
| `review_time` | date | The date and time when the review was posted. This helps in understanding the timeline and recency of the feedback |
| `recommends` | boolean | Indicates whether the reviewer recommends the company (true) or does not recommend it (false) |
| `review_content` | text | The textual content of the review, detailing the reviewer's experience and opinions about the company |
| `review_attachments` | array | An array of URLs pointing to any attachments included in the review, such as images or videos. These provide additional context or evidence related to the review |
| `number_of_reactions_to_review` | number | The total number of reactions (e.g., likes, loves, wows) that other Facebook users have given to the review. This indicates the level of engagement and visibility of the review |
| `review_reaction_types` | array | An array detailing the types of reactions (e.g., like, love, haha, wow, sad, angry) received by the review. This helps to understand the emotional response of the audience to the review. |
| `reviewer_profile_url` | url | The URL of the reviewer's Facebook profile. This link allows access to the reviewer's profile for further context |
| `reviewer_name` | text | reviewer_name |
| `reviewer_profile_picture_url` | url | reviewer_profile_picture_url |
| `recommended_perc` | text | The percentage of recommended reviews |
| `likes` | number | The amount of likes the page has |
| `followers` | number | The amount of followers the page has |
| `total_reviews` | number | The total number of reviews |
| `replies` | array | replies |

</details>

<details>
<summary>All 23 Marketplace listing fields, <code>gd_lvt9iwuh6fbcwmx1a</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | The direct URL of the Facebook Marketplace listing page |
| `title` | text | The title of the listing as posted by the seller |
| `initial_price` | number | The original listed price of the item before any discounts |
| `final_price` | number | The current or discounted price of the item |
| `currency` | text | The currency in which the price is listed |
| `product_id` | text | The unique identifier assigned to the listing by Facebook Marketplace. |
| `breadcrumbs` | array | A list of navigation breadcrumb items representing the category hierarchy of the listing |
| `condition` | text | The condition of the listed item as reported by the seller |
| `description` | text | The full textual description of the listing, as written by the seller |
| `location` | text | The general location |
| `country_code` | text | The two-letter ISO 3166-1 alpha-2 country code |
| `root_category` | text | The root category the listing belongs to on Facebook Marketplace |
| `images` | array | A list of URLs pointing to the listing's product images uploaded by the seller |
| `seller_description` | text | A short bio or description from the seller's Facebook Marketplace profile |
| `color` | text | The color of the listed item, if applicable and provided by the seller |
| `brand` | text | The brand or manufacturer of the listed item, if applicable |
| `videos` | array | A list of URLs pointing to any video content uploaded by the seller as part of the listing |
| `profile_id` | text | The unique Facebook profile ID of the seller who posted the listing |
| `listing_date` | date | The date and time when the listing was originally posted on Facebook Marketplace |
| `car_miles` | number | The mileage of the vehicle as reported by the seller. Only relevant for car/vehicle listings |
| `is_sold` | boolean | Indicates whether the product is sold |
| `transmission` | text | Transmission type shown in vehicle details. Only relevant for car/vehicle listings |
| `vehicle_details` | object | Detailed vehicle-specific attributes extracted from the 'About this vehicle' section of Facebook Marketplace car listings. Null for non-vehicle listings. |

</details>

<details>
<summary>All 30 event fields, <code>gd_m14sd0to1jz48ppm51</code></summary>

| field | type | description |
| --- | --- | --- |
| `event_id` | text | Unique identifier for the event |
| `url` | url | Direct URL link to the event |
| `main_image` | url | URL for the primary image of the event |
| `event_date` | date | Date of the event |
| `title` | text | Name or title of the event |
| `people_responded` | number | Number of people marked as "responded" to the event |
| `event_by` | array | Array of objects specifying the event organizer(s), with name and URL fields for each |
| `location` | object | Nested object containing address and URL |
| `access_level` | array | Indicates the privacy or access level of the event (e.g., public, private) |
| `description` | object | Object with text, links, and hashtags fields for detailed event descriptions |
| `hashtags` | array | Separate from description, this is an array that provides general hashtags associated with the event |
| `hosts` | array | Array of objects to specify event hosts, including name, URL, and verification status |
| `suggested_events` | array | Array listing other recommended or similar events, with each having fields for name, URL, date, people interested, and location |
| `tickets` | object | Object detailing ticket information, including the URL, provider, min/max prices, and currency |
| `duration` | object | Object defining the event's duration |
| `main_image_downloadable` | url | Main image downloadable |
| `responded_object` | object | Responded object |
| `event_start_time` | date | Start time of the event |
| `event_end_time` | date | End time of event |
| `event_end_date` | date | End Data of event in case the event is longer than a day |
| `full_address` | text | Address of the event |
| `longitude` | text | Longitude |
| `latitude` | text | Latitude |
| `event_timezone` | text | Timezone of the event |
| `unformatted_description_text` | text | The description text with its original structure |
| `alternative_dates` | array | Alternative dates |
| `alternative_date_time` | array | Alternative date time |
| `redirected_event_url` | url | Redirected event URL |
| `main_video` | url | main video if available |
| `is_cancelled` | boolean | Indicates whether the event is cancelled |

</details>

<details>
<summary>All 32 Ad Library ad fields, <code>gd_mtveskb62h7q65ftgz</code></summary>

| field | type | description |
| --- | --- | --- |
| `url` | url | Meta Ad Library ad detail page URL |
| `library_id` | text | Unique Meta Ad Library ID (kept as text, exceeds safe integer range) |
| `is_active` | boolean | Indicates if the ad is currently running |
| `status` | text | Ad status label (Active, Inactive) |
| `start_date` | date | Date the ad started running |
| `end_date` | date | Date the ad stopped running (empty while active) |
| `total_active_time` | text | Total active time as displayed (e.g., 8 hrs) |
| `ad_category` | text | Special ad category (Housing, Employment, Credit, Social issues, elections or politics); empty for commercial ads |
| `has_multiple_versions` | boolean | Indicates if the ad has multiple creative versions |
| `versions_count` | number | Number of creative versions (from the 1 of N indicator) |
| `creative_reuse_count` | number | Number of ads using this creative and text |
| `platforms` | array | Platforms the ad is delivered on |
| `platforms_count` | number | Number of platforms the ad runs on |
| `description` | text | Primary ad body text |
| `title` | text | Ad headline |
| `link_description` | text | Link description shown below the headline |
| `caption` | text | Display domain shown above the headline (e.g., ADIDAS.EU) |
| `cta_text` | text | Call to action button text as displayed (e.g., Shop Now) |
| `cta_type` | text | Normalized call to action type (e.g., SHOP_NOW, LEARN_MORE, SIGN_UP) |
| `link_url` | url | Destination URL of the ad |
| `image_url` | url | Main creative image URL |
| `video_url` | url | Main creative video URL |
| `video_preview_image` | url | Video thumbnail image URL |
| `ad_versions` | array | All creative versions or carousel cards of the ad |
| `advertiser_name` | text | Advertiser name from the About the advertiser section |
| `advertiser_profile_picture` | url | Advertiser profile picture URL |
| `advertiser_description` | text | Advertiser More info description text |
| `advertiser_social_accounts` | array | Advertiser social accounts listed in the About the advertiser section |
| `advertiser_and_payer` | array | Advertiser and payer entries (EU and associated territories only) |
| `eu_total_reach` | number | Total reach of the ad in the European Union |
| `transparency_by_location` | array | Reach and targeting details per location (EU and associated territories only) |
| `is_eu_ad` | boolean | Indicates if the ad is delivered in the EU and carries DSA transparency sections |

</details>
<!-- fields:end -->

<details>
<summary>The start of a real output file, from <code>facebook-scraper Meta --limit 1</code></summary>

```json
{
  "generated_at": "2026-11-03T19:25:27.615005+00:00",
  "pages": [
    {
      "page": "Meta",
      "posts": [
        {
          "url": "https://www.facebook.com/Meta/posts/pfbid0evGHWPACd3JninWg3j3nucQjdFxoHWwJSPgFXKjZXaUiU8MctREDPRZZsAps6CGwl",
          "post_id": "1181668677855674",
          "user_url": "https://www.facebook.com/Meta",
          "user_username_raw": "Meta",
          "content": "Meta Ray-Ban Display has been out for a while, so if you’re a developer, this one’s for you.\n\nbuild a game, a productivity tool, a science app — really, anything you love — and watch it run on an in-lens display, controlled by the Meta Neural Band.\n\nneed inspo? here’s what people have already cooked up: \n\nMeta Geology by @inna.sparrow.xr\nVistathlon by @stspanho\nSee DJ by @levinriegner\nSightline by @fasai.creates",
          "date_posted": "2026-10-30T19:41:31.000Z",
          "num_comments": 343,
          "num_shares": 194,
          "num_likes_type": {
            "type": "Like",
            "num": 593
          },
          "page_name": "Meta",
  ...
```

The whole file, one post with every field, is
[examples/sample_output.json](examples/sample_output.json).

</details>

## Facebook scraper errors

| you see | what it means |
| --- | --- |
| `API token required but not found.` | Exit 2, before any request. Set the token, or run `bdata login`. |
| `failed  page: Posts not found` | Exit 1. No such page, a private one, or a page with no public posts. Check the name. |
| `failed  page: timeout: snapshot ... not ready after 900s` | Exit 1. Run it again, or fetch the snapshot later with `fetch()`. |
| `failed  page: HTTP 401: ...` | The token is set but wrong. |

Any failure exits 1, so a run is safe to gate a script on.

From the functions, the same conditions look like this:

| you see | what it means |
| --- | --- |
| `TokenMissing` | No `BRIGHTDATA_API_TOKEN` and no `bdata login`. |
| `ApiError: HTTP 400: ...validation_error...` | An input field the API does not accept. The message names it; compare with the table above. |
| a row with an `error` key | The API's answer for one input: "Posts not found", a dead page, "Reviews not found", "There are no events." The other rows are fine. |
| `TimeoutError` | The job outlived the 900-second wait. Pass `timeout=` to `run`, or use `trigger` and fetch later. |

## Facebook MCP server and Claude Code skill

No Python, nothing installed. Paste both lines; the first opens a browser
once, or use `bdata login --device` over SSH and in CI:

```bash
npx -p @brightdata/cli bdata login
npx -p @brightdata/cli bdata pipelines run gd_lkaxegm826bjpoo9m5 collect_by_url --url "https://www.facebook.com/Meta" --num_of_posts 2 --pretty
```

2 records, up to 38 fields, 74 seconds on 3 Nov 2026. The CLI leaves out
fields that are null.

The CLI runs a scraper by its dataset ID, every Facebook one included.
`bdata pipelines search facebook` lists their IDs and methods, and
`--limit-per-input N` caps a discovery, 10 by default.

`npx skills add brightdata/skills` teaches Claude Code, Cursor and Codex these
commands and the docs, so plain language works afterwards. Full guide:
[Bright Data for your coding agent](https://docs.brightdata.com/quickstart-coding-agent).

No terminal, for a hosted assistant? The
[Bright Data MCP server](https://github.com/brightdata/brightdata-mcp#which-tool-to-use)
runs any pre-built scraper, Facebook included, through `search_scrapers` and
`run_scraper` in its `scrapers` group:

    https://mcp.brightdata.com/mcp?token=YOUR_API_TOKEN&groups=scrapers

An agent can also open the account itself, no signup form:
[agent registration](https://brightdata.com/auth.md). Everything else Bright
Data connects to, from LangChain to Zapier and n8n:
[integrations](https://docs.brightdata.com/integrations/introduction).

## Is this Facebook scraper free?

New Bright Data accounts get
[5,000 free credits a month](https://docs.brightdata.com/general/account/billing-and-pricing/free-tier).
Every Facebook scraper bills per record: per post, comment, reel, page,
profile, review, listing, event or ad.
[Pricing](https://brightdata.com/pricing/web-scraper) lists the rates.

## Support

Bugs in this repo:
[open an issue](https://github.com/brightdata/facebook-scraper/issues), and
[CONTRIBUTING.md](CONTRIBUTING.md) says what to put in it.
Anything about the API, your account or your credits:
[Bright Data support](https://brightdata.zendesk.com/hc/en-us/requests/new).

## License

[Apache 2.0](LICENSE).

## Facebook scraper for Node.js

The same Facebook scraper is available for Node.js: [brightdata/facebook-scraper-node](https://github.com/brightdata/facebook-scraper-node).

## More open source scrapers from Bright Data

Other Python scrapers built the same way, with live-verified examples:

- [Instagram scraper for Python](https://github.com/brightdata/instagram-scraper)
- [TikTok scraper for Python](https://github.com/brightdata/tiktok-scraper)
- [LinkedIn scraper for Python](https://github.com/brightdata/linkedin-scraper)
