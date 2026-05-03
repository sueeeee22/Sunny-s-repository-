"""Query the Ticketmaster Discovery API for upcoming Chicago-area concerts.

For each artist from the user's Spotify library, searches for music events
within the configured radius of Chicago.  Returns only events not yet seen
in a local seen-events cache so each show is only reported once.

Requires TICKETMASTER_API_KEY in the environment (or .env file).
Free tier: https://developer.ticketmaster.com  (5,000 calls/day)
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

_BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
_CACHE_FILE = Path(__file__).parent.parent / ".seen_concerts.json"


def _load_seen() -> set[str]:
    if _CACHE_FILE.exists():
        try:
            return set(json.loads(_CACHE_FILE.read_text()))
        except Exception:
            pass
    return set()


def _save_seen(seen: set[str]) -> None:
    _CACHE_FILE.write_text(json.dumps(sorted(seen), indent=2))


def _search_artist(artist: str, config: dict, api_key: str) -> list[dict]:
    """Return upcoming Chicago-area events for a single artist."""
    now = datetime.now(tz=timezone.utc)
    end = now + timedelta(days=config.get("days_ahead", 90))

    params = {
        "apikey": api_key,
        "keyword": artist,
        "classificationName": "music",
        "city": config.get("city", "Chicago"),
        "stateCode": config.get("state_code", "IL"),
        "radius": config.get("radius_miles", 50),
        "unit": "miles",
        "startDateTime": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": 10,
        "sort": "date,asc",
    }

    try:
        resp = requests.get(_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[concerts] Error searching '{artist}': {e}")
        return []

    events = data.get("_embedded", {}).get("events", [])
    results = []
    for ev in events:
        venues = ev.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}
        dates = ev.get("dates", {}).get("start", {})
        results.append({
            "id": ev.get("id", ""),
            "artist": artist,
            "event_name": ev.get("name", artist),
            "venue": venue.get("name", "Unknown Venue"),
            "address": f"{venue.get('city', {}).get('name', '')}, {venue.get('state', {}).get('stateCode', '')}",
            "date": dates.get("localDate", ""),
            "time": dates.get("localTime", ""),
            "url": ev.get("url", ""),
        })
    return results


def get_new_concerts(artists: list[str], concert_config: dict) -> list[dict]:
    """Return concerts for the given artists that haven't been reported before.

    Results are cached by Ticketmaster event ID so each show surfaces only once
    across daily runs.
    """
    api_key = os.environ["TICKETMASTER_API_KEY"]
    seen = _load_seen()
    new_events: list[dict] = []

    for i, artist in enumerate(artists):
        events = _search_artist(artist, concert_config, api_key)
        for ev in events:
            if ev["id"] and ev["id"] not in seen:
                seen.add(ev["id"])
                new_events.append(ev)

        # Respect Ticketmaster's rate limit (5 req/sec on free tier)
        if i < len(artists) - 1:
            time.sleep(0.25)

    _save_seen(seen)

    new_events.sort(key=lambda e: e["date"])
    return new_events
