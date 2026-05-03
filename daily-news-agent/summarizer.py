"""Summarize fetched news content using Claude with prompt caching.

The system prompt is sent with cache_control so it counts as a cache write on
the first call and a cache hit on every subsequent call within the 5-minute
cache window — or across calls within the same day if you use extended caching.

Model: claude-sonnet-4-6 (good balance of intelligence and cost at this volume).
"""

import os
import anthropic

_CLIENT = None


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


_SYSTEM_PROMPT = """You are a sharp, efficient news briefing assistant. Every morning you prepare a
structured daily digest for a Chicago-area attorney. Your job is to surface what actually matters —
not volume, but signal. Be direct and concise. Never pad. Never use filler phrases like "it's worth
noting" or "in conclusion."

Formatting rules:
- Use clean HTML suitable for an email body (no <html>/<body>/<head> tags — just inner content).
- Each section gets an <h2> heading with its title.
- Each story gets a short <strong>headline</strong> followed by 2–3 sentence summary.
- Wrap each story in a <div class="story"> block.
- Link the headline to the source URL using <a href="..."> when a URL is available.
- If no items exist for a section, write a short italic note: <em>Nothing new today.</em>
- For legal items, explicitly call out the jurisdiction (federal / Illinois / California) and the
  type (new statute, court opinion, agency guidance, etc.) at the start of the summary.
- For concerts, list each show as: Artist — Venue, Date. Link to the ticket URL.
- Keep national news to the top 5–8 most significant stories.
- Preserve accuracy above all else. Do not invent details not present in the source material."""


def summarize(sections: dict) -> str:
    """Generate an HTML email body summarizing all sections.

    sections dict shape:
    {
        "legal": {
            "scotus": [{"title", "link", "summary", "source", "published"}, ...],
            "employment_federal": [...],
            "employment_illinois": [...],
            "employment_california": [...],
            "privacy_and_ai": [...],
        },
        "concerts": [{"artist", "event_name", "venue", "address", "date", "time", "url"}, ...],
        "local": [{"title", "link", "summary", "source", "published"}, ...],
        "national": [{"title", "link", "summary", "source", "published"}, ...],
    }
    """
    user_content = _build_user_content(sections)

    response = _client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    return response.content[0].text


def _format_articles(articles: list[dict]) -> str:
    if not articles:
        return "(no items)"
    lines = []
    for a in articles:
        lines.append(f"- [{a['source']}] {a['title']}")
        if a.get("published"):
            lines.append(f"  Published: {a['published']}")
        if a.get("summary"):
            lines.append(f"  {a['summary'][:600]}")
        if a.get("link"):
            lines.append(f"  URL: {a['link']}")
        lines.append("")
    return "\n".join(lines)


def _format_concerts(concerts: list[dict]) -> str:
    if not concerts:
        return "(no new shows)"
    lines = []
    for c in concerts:
        time_str = f" at {c['time']}" if c.get("time") else ""
        lines.append(f"- {c['artist']} | {c['event_name']}")
        lines.append(f"  {c['venue']}, {c['address']}")
        lines.append(f"  {c['date']}{time_str}")
        if c.get("url"):
            lines.append(f"  Tickets: {c['url']}")
        lines.append("")
    return "\n".join(lines)


def _build_user_content(sections: dict) -> str:
    legal = sections.get("legal", {})
    parts = [
        "Please produce today's daily briefing email body as HTML. Here is the raw source material:\n",

        "## SECTION 1: LEGAL\n",
        "### US Supreme Court\n",
        _format_articles(legal.get("scotus", [])),

        "\n### Federal Employment Law (new statutes, binding cases, EEOC/DOL/NLRB decisions)\n",
        _format_articles(legal.get("employment_federal", [])),

        "\n### Illinois Employment Law\n",
        _format_articles(legal.get("employment_illinois", [])),

        "\n### California Employment Law\n",
        _format_articles(legal.get("employment_california", [])),

        "\n### Data Privacy & AI Law (all US jurisdictions)\n",
        _format_articles(legal.get("privacy_and_ai", [])),

        "\n## SECTION 2: MUSIC — New Chicago-Area Concerts\n",
        _format_concerts(sections.get("concerts", [])),

        "\n## SECTION 3: LOCAL — Forest Park & Oak Park\n",
        _format_articles(sections.get("local", [])),

        "\n## SECTION 4: NATIONAL & BREAKING NEWS\n",
        _format_articles(sections.get("national", [])),
    ]
    return "\n".join(parts)
