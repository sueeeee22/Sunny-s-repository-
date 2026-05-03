# Daily News Agent

Emails a structured daily briefing covering:

- **Legal** — US Supreme Court opinions; federal, Illinois, and California employment law (new statutes, binding cases, agency decisions); US data privacy and AI legislation
- **Music** — New Chicago-area concert announcements for artists you follow on Spotify
- **Local** — Forest Park and Oak Park news
- **National** — Breaking and top national news

---

## Setup

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in the four services below.

#### Claude API key
Get one at [console.anthropic.com](https://console.anthropic.com/settings/keys).

#### Gmail App Password
1. Enable 2-Factor Authentication on your Google account if not already done.
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
3. Create an app password for "Mail" and paste it into `.env`.

#### Spotify
1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and create a free app.
2. In the app settings, add `http://localhost:8888/callback` as a Redirect URI.
3. Copy the Client ID and Client Secret into `.env`.
4. Run the one-time OAuth setup:
   ```bash
   python setup_spotify.py
   ```
   A browser tab will open for you to log in. After approving, a token cache file is saved locally and reused automatically on every run.

#### Ticketmaster
Get a free API key at [developer.ticketmaster.com](https://developer.ticketmaster.com/products-and-docs/apis/getting-started/). The free tier allows 5,000 calls/day.

---

## Running the agent

```bash
python agent.py
```

The first run may take a few minutes while Ticketmaster is queried for each of your Spotify artists. Subsequent runs are much faster — only newly announced shows are surfaced.

---

## Scheduling (daily at 6:30 AM)

**macOS / Linux — cron:**
```bash
crontab -e
```
Add:
```
30 6 * * * cd /full/path/to/daily-news-agent && /full/path/to/.venv/bin/python agent.py >> agent.log 2>&1
```

**GitHub Actions (cloud, always-on, free):**

Create `.github/workflows/daily-briefing.yml` in your repo:

```yaml
name: Daily Briefing
on:
  schedule:
    - cron: '30 11 * * *'   # 6:30 AM CT (UTC-5) / adjust for DST
  workflow_dispatch:         # allows manual trigger from GitHub UI

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r daily-news-agent/requirements.txt
      - run: python daily-news-agent/agent.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
          SPOTIFY_CLIENT_ID: ${{ secrets.SPOTIFY_CLIENT_ID }}
          SPOTIFY_CLIENT_SECRET: ${{ secrets.SPOTIFY_CLIENT_SECRET }}
          TICKETMASTER_API_KEY: ${{ secrets.TICKETMASTER_API_KEY }}
```

Add the secrets in your GitHub repo under **Settings → Secrets → Actions**.

For the Spotify token cache in GitHub Actions, upload the `.spotify_token_cache` file contents as a secret (`SPOTIFY_TOKEN_CACHE`) and add a step to write it before running the agent:
```yaml
      - run: echo "$SPOTIFY_TOKEN_CACHE" > daily-news-agent/.spotify_token_cache
        env:
          SPOTIFY_TOKEN_CACHE: ${{ secrets.SPOTIFY_TOKEN_CACHE }}
```

---

## Customizing sources

Edit `sources_config.yaml` to add, remove, or re-categorize RSS feeds. Each entry can include an optional `keywords` list to filter articles — useful for jurisdiction-specific filtering on feeds that mix multiple topics.

---

## Subscription sources

Most major outlets (NYT, WSJ, Bloomberg Law, etc.) provide full-content RSS feeds for authenticated subscribers via a personal feed URL. To use these:

1. Log in to the publication in your browser.
2. Navigate to a section or topic page.
3. Find the RSS link (often shown when logged in) and copy it — it typically contains a session token or subscriber ID embedded in the URL.
4. Add it to `sources_config.yaml` under the appropriate section.

The agent fetches these URLs directly; as long as the URL itself grants access, no additional authentication is needed.
