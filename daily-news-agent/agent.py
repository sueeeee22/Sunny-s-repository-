#!/usr/bin/env python3
"""Daily News Agent — main entry point.

Run manually:
    python agent.py

Or via cron (example: every day at 6:30 AM):
    30 6 * * * cd /path/to/daily-news-agent && /usr/bin/python3 agent.py >> agent.log 2>&1
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from fetchers.rss_fetcher import fetch_section
from fetchers.spotify_fetcher import get_artists
from fetchers.concert_fetcher import get_new_concerts
from summarizer import summarize
from emailer import send_email


def load_config() -> dict:
    config_path = Path(__file__).parent / "sources_config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def run() -> None:
    config = load_config()

    print("[agent] Fetching legal sources...")
    legal_cfg = config["legal"]
    legal = {
        "scotus": fetch_section(legal_cfg["scotus"]),
        "employment_federal": fetch_section(legal_cfg["employment_federal"]),
        "employment_illinois": fetch_section(legal_cfg["employment_illinois"]),
        "employment_california": fetch_section(legal_cfg["employment_california"]),
        "privacy_and_ai": fetch_section(legal_cfg["privacy_and_ai"]),
    }
    total_legal = sum(len(v) for v in legal.values())
    print(f"[agent] Legal: {total_legal} items across all sub-sections")

    print("[agent] Fetching local news...")
    local = fetch_section(config["local"])
    print(f"[agent] Local: {len(local)} items")

    print("[agent] Fetching national news...")
    national = fetch_section(config["national"])
    print(f"[agent] National: {len(national)} items")

    print("[agent] Fetching Spotify artists...")
    try:
        artists = get_artists()
        print(f"[agent] Spotify: {len(artists)} artists")
    except Exception as e:
        print(f"[agent] Spotify unavailable: {e}. Skipping concert section.")
        artists = []

    print(f"[agent] Searching Ticketmaster for Chicago concerts ({len(artists)} artists)...")
    concerts = []
    if artists:
        try:
            concerts = get_new_concerts(artists, config["concerts"])
            print(f"[agent] Concerts: {len(concerts)} new shows found")
        except Exception as e:
            print(f"[agent] Concert fetch error: {e}")

    sections = {
        "legal": legal,
        "concerts": concerts,
        "local": local,
        "national": national,
    }

    print("[agent] Summarizing with Claude...")
    html_body = summarize(sections)

    print("[agent] Sending email...")
    send_email(html_body)
    print("[agent] Done.")


if __name__ == "__main__":
    run()
