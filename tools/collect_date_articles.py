"""Collect Japanese Wikipedia date-page wikitext for offline curation.

The app ships only the reviewed JSON and original wallpapers. This helper is a
research/build-time tool; installed copies make no Wikipedia/API requests.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent.parent / "work" / "research" / "date_articles_raw.json"
API = "https://ja.wikipedia.org/w/api.php"
USER_AGENT = "Daily365Calendar/0.1 (offline calendar preparation; local build)"


def date_titles() -> list[str]:
    titles = []
    for month in range(1, 13):
        days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
        for day in range(1, days + 1):
            titles.append(f"{month}月{day}日")
    return titles


def fetch_titles(titles: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if RAW.exists():
        result.update(json.loads(RAW.read_text(encoding="utf-8")))
    missing = [title for title in titles if title not in result]
    for offset in range(0, len(missing), 25):
        batch = missing[offset : offset + 25]
        query = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(batch),
            "format": "json",
            "formatversion": "2",
        }
        request = urllib.request.Request(
            API + "?" + urllib.parse.urlencode(query),
            headers={"User-Agent": USER_AGENT},
        )
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 4:
                    raise
                pause = int(error.headers.get("Retry-After", "30"))
                print(f"Rate limited; resuming after {pause}s")
                time.sleep(min(max(pause, 5), 120))
        for page in payload.get("query", {}).get("pages", []):
            revisions = page.get("revisions") or []
            if not revisions:
                continue
            main = revisions[0].get("slots", {}).get("main", {})
            content = main.get("content") or main.get("*")
            if content:
                result[page["title"]] = content
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        print(f"Fetched {len(result)}/{len(titles)} date pages")
        time.sleep(0.6)
    return result


def main() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    pages = fetch_titles(date_titles())
    RAW.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(pages)} pages to {RAW}")


if __name__ == "__main__":
    main()
