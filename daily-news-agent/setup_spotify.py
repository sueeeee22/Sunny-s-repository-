#!/usr/bin/env python3
"""One-time Spotify OAuth setup.

Run this once to authorize the agent to read your Spotify library.
It will open a browser tab for you to log in, then write a token cache
file that the agent reuses on every subsequent run.

Usage:
    python setup_spotify.py

Requirements in .env:
    SPOTIFY_CLIENT_ID
    SPOTIFY_CLIENT_SECRET
    SPOTIFY_REDIRECT_URI  (default: http://localhost:8888/callback)

How to get a Spotify client ID / secret:
    1. Go to https://developer.spotify.com/dashboard
    2. Create an app (any name, e.g. "Daily News Agent")
    3. Add http://localhost:8888/callback as a Redirect URI in the app settings
    4. Copy the Client ID and Client Secret into your .env file
"""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "user-follow-read user-top-read"
CACHE_PATH = Path(__file__).parent / ".spotify_token_cache"


def main():
    print("Starting Spotify OAuth setup...")
    print(f"Token cache will be saved to: {CACHE_PATH}\n")

    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=SCOPES,
        cache_path=str(CACHE_PATH),
        open_browser=True,
    )

    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Trigger auth by making a real API call
    me = sp.current_user()
    print(f"Authorized as: {me['display_name']} ({me['id']})")

    # Quick sanity check
    top = sp.current_user_top_artists(limit=5, time_range="medium_term")
    names = [a["name"] for a in top.get("items", [])]
    print(f"Sample top artists: {', '.join(names) if names else '(none yet)'}")

    print("\nSetup complete. The agent will use the cached token automatically.")
    print(f"Cache file: {CACHE_PATH}")


if __name__ == "__main__":
    main()
