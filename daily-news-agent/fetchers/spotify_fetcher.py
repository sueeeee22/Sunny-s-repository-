"""Retrieve the authenticated user's artists from Spotify.

Combines followed artists and top artists across all time ranges to build a
comprehensive list of artists to check for Chicago concerts.

Requires SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REFRESH_TOKEN
in the environment (or .env file).  Run setup_spotify.py once to obtain the
refresh token.
"""

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth


SCOPES = "user-follow-read user-top-read"


def _get_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
        scope=SCOPES,
        cache_path=os.path.join(os.path.dirname(__file__), "..", ".spotify_token_cache"),
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def get_artists() -> list[str]:
    """Return a deduplicated list of artist names from the user's Spotify library."""
    sp = _get_client()
    artist_names: set[str] = set()

    # Followed artists (paginated)
    results = sp.current_user_followed_artists(limit=50)
    while results:
        for artist in results["artists"]["items"]:
            artist_names.add(artist["name"])
        if results["artists"]["next"]:
            results = sp.next(results["artists"])
        else:
            break

    # Top artists across short, medium, and long time ranges
    for term in ("short_term", "medium_term", "long_term"):
        top = sp.current_user_top_artists(limit=50, time_range=term)
        for artist in top.get("items", []):
            artist_names.add(artist["name"])

    return sorted(artist_names)
